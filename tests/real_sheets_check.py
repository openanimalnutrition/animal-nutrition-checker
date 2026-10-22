"""The one real-Sheets check: the sheet view at the export's inputs against the values Google
Sheets itself stored in the released template (Version 21OCT26b, tests/parity/
export-21OCT26b/cells.json). Every other expected value of the tests came from the project's
evaluator.

- The export's input cells must hold sheet_map.EXPORT_INPUTS.
- Every cell of the Standards tab (s01) and the requirement table (s02) that the export holds
  or the sheet view models is compared. A cell the export does not hold is blank (None).
  - A number in a formula cell: Sheets writes at most 10 significant digits, so the code's
    number is written the same way (its 15-significant-digit value rounded half away from
    zero to 10 significant digits) and must then be equal. A typed number must be equal.
  - Texts exactly; an error code only as the same error code.
- A cell the sheet view does not model needs a reason (sheet_map.layout_reason). A formula
  cell is never layout: it must be modelled.

Usage: nice -n 10 python3 -I -B tests/real_sheets_check.py [--show N]
Exit status 0 when nothing differs and every cell not compared has its reason.
"""

import collections
import json
import os
import sys
from decimal import ROUND_HALF_UP, Context, Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import sheet_map  # noqa: E402
import sheet_view  # noqa: E402
from oan import numbers, table  # noqa: E402

PARITY = os.path.join(HERE, "parity")
BASELINE = os.path.join(PARITY, "data-21OCT26b")
EXPORT = os.path.join(PARITY, "export-21OCT26b", "cells.json")
# Every cell the export holds is visited, and these grids for cells the view models that the
# export leaves blank (the requirement table's max-type columns end at BO).
GRID = {"s01": (135, 67), "s02": (125, 67)}
_CONTEXT = Context(prec=50, rounding=ROUND_HALF_UP)


def load_export(path=EXPORT):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def column_name(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def sig10(x):
    """A number as Sheets writes a formula's value in the export: the 15-significant-digit
    value rounded half away from zero to 10 significant digits."""
    d = numbers.decimal15(x)
    if d == 0:
        return d
    return d.quantize(Decimal(1).scaleb(d.adjusted() - 9), context=_CONTEXT)


def compare(entry, got):
    """'exact', 'sig10' (equal as the export writes it) or None (a difference). entry is the
    export's [formula, type, value], or None for a blank cell."""
    if entry is None:
        return "exact" if got is None else None
    formula, typ, value = entry
    if typ == "n":
        if not numbers.is_number(got):
            return None
        if got == float(value):
            return "exact"
        return "sig10" if formula and sig10(got) == Decimal(value) else None
    if typ == "e":
        return "exact" if isinstance(got, dict) and got.get("error") == value else None
    if typ == "b":
        return "exact" if got is (value == "1") else None
    return "exact" if isinstance(got, str) and got == value else None


def check_inputs(cells):
    """The input cells whose export value is not sheet_map.EXPORT_INPUTS'."""
    out = []
    for ref in sorted(sheet_map.INPUT_CELLS):
        expected = sheet_map.EXPORT_INPUTS.get(ref)
        entry = cells.get(ref)
        if entry is None:
            ok = expected is None
        elif entry[1] == "n":
            ok = numbers.is_number(expected) and float(entry[2]) == expected
        else:
            ok = entry[2] == expected
        if not ok:
            out.append((ref, entry, expected))
    return out


def run(data=None, export=None):
    """The check's result: per tab, the counts of compared cells (by kind and result), the
    differences, the cells not compared by reason, and the cells left without a reason."""
    data = data if data is not None else table.load(BASELINE)
    export = export if export is not None else load_export()
    view = sheet_view.StandardsView(data, {})
    result = {"inputs": check_inputs(export["cells"]["s01"]), "tabs": {}}
    for tab, (rows, cols) in GRID.items():
        cells = export["cells"][tab]
        refs = set(cells)
        refs.update(column_name(c) + str(r) for r in range(1, rows + 1)
                    for c in range(1, cols + 1))
        compared = collections.Counter()
        layout = collections.Counter()
        diffs, unexplained = [], []
        for ref in sorted(refs, key=lambda x: (sheet_map.col_row(x)[1],
                                               len(x), x)):
            entry = cells.get(ref)
            try:
                got = view.cell(ref if tab == "s01" else "s02!" + ref)
            except sheet_view.NotModelled:
                if entry is None:
                    continue
                reason = None if entry[0] else sheet_map.layout_reason(tab, ref)
                if reason is None:
                    unexplained.append((ref, entry))
                else:
                    layout[reason] += 1
                continue
            kind = "blank" if entry is None else ("formula" if entry[0] else "typed")
            outcome = compare(entry, got)
            compared[(kind, outcome or "differ")] += 1
            if outcome is None:
                diffs.append((ref, entry, got))
        result["tabs"][tab] = {"compared": compared, "layout": layout, "differences": diffs,
                               "unexplained": unexplained, "export_cells": len(cells)}
    return result


def passed(result):
    return not result["inputs"] and all(
        not t["differences"] and not t["unexplained"] for t in result["tabs"].values())


def report(result, show=20):
    lines = []
    lines.append("export inputs: %s" % ("as sheet_map.EXPORT_INPUTS" if not result["inputs"]
                                        else "DIFFER %r" % result["inputs"]))
    for tab, t in result["tabs"].items():
        c = t["compared"]
        n_compared = sum(c.values())
        lines.append("%s: %d export cells; %d compared: %d identical, %d equal as the export "
                     "writes them (10 significant digits), %d differ; %d not compared (layout); "
                     "%d without a reason" % (
                         tab, t["export_cells"], n_compared,
                         sum(v for (k, o), v in c.items() if o == "exact"),
                         sum(v for (k, o), v in c.items() if o == "sig10"),
                         len(t["differences"]), sum(t["layout"].values()),
                         len(t["unexplained"])))
        lines.append("    compared by kind: " + ", ".join(
            "%s %s %d" % (k, o, v) for (k, o), v in sorted(c.items())))
        for reason, n in sorted(t["layout"].items()):
            lines.append("    not compared: %s: %d" % (reason, n))
        for ref, entry, got in t["differences"][:show]:
            lines.append("    DIFFERS %s: export %r, code %r" % (ref, entry, got))
        for ref, entry in t["unexplained"][:show]:
            lines.append("    NO REASON %s: export %r" % (ref, entry))
    lines.append("REAL-SHEETS CHECK PASSES" if passed(result) else "REAL-SHEETS CHECK FAILS")
    return "\n".join(lines)


def main(argv):
    show = int(argv[argv.index("--show") + 1]) if "--show" in argv else 20
    result = run()
    print(report(result, show))
    return 0 if passed(result) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
