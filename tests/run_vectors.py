"""Run the frozen 21OCT26b test vectors against the code.

Usage: nice -n 10 python3 -I -B tests/run_vectors.py [--show N]

Every case of every vector file is run against the frozen baseline data, in file order and
in reverse order, and counted per file: pass, difference, or pending (a part not built yet:
energy is phase 2; minimums, maximums and bands are phase 3). Numbers compare within a
relative 1e-12 (the report also counts those that are not bit-exact); every other value must
be identical: texts exactly, a blank as null, true/false only as true/false.

Each file's report also counts the cases with an input outside its rule (oan/inputs.py).
The core rejects those inputs, so the cases are one approved category of difference
(decision 1 A); the counts are fixed in tests/test_phase1b.py.

Exit status 0 when no case differs and both orders give the same results.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import sheet_map  # noqa: E402
import sheet_view  # noqa: E402
from oan import inputs, numbers, table  # noqa: E402

PARITY = os.path.join(HERE, "parity")
BASELINE = os.path.join(PARITY, "data-21OCT26b")
VECTORS = os.path.join(PARITY, "vectors-21OCT26b")
FILES = (
    "inputs.json",
    "values.json",
    "formulas-testcases.json",
    "energy-testcases.json",
    "energy-testcases-row11.json",
)
PENDING = {
    "formulas-testcases.json": "phase 3 (minimums, maximums and bands)",
    "energy-testcases.json": "phase 2 (energy)",
    "energy-testcases-row11.json": "phase 2 (energy, row 11)",
}
VALUES_PENDING = "phase 3 (minimums, maximums and bands)"


class Pending(Exception):
    pass


def compare(expected, got):
    """'exact', 'close' (numbers within 1e-12, not bit-exact) or None (a difference)."""
    if expected is None or isinstance(expected, (bool, str, dict)):
        return "exact" if type(got) is type(expected) and got == expected else None
    if numbers.is_number(expected) and numbers.is_number(got):
        if got == expected:
            return "exact"
        return "close" if numbers.close(got, expected) else None
    return None


def check_cell(cell, value, data):
    """The input rule's Verdict for a value in a Standards tab input cell, or None for a
    cell not mapped yet."""
    if cell in sheet_map.INPUT_CELLS:
        return inputs.check_fact(sheet_map.INPUT_CELLS[cell], value, data)
    col, row = cell[:1], cell[1:]
    nid = sheet_map.S01_ROWS.get(int(row)) if row.isdigit() else None
    if nid is None or col not in sheet_map.ENTRY_COLUMNS:
        return None
    return inputs.check_entry(nid, value, data)


def outside_rules(case_inputs, data):
    """(the cells whose value is outside its rule, the cells not mapped yet) of one case."""
    rejected, unmapped = [], []
    for cell, value in sorted(case_inputs.items()):
        if cell in sheet_map.RETIRED_CELLS:
            continue
        verdict = check_cell(cell, value, data)
        if verdict is None:
            unmapped.append(cell)
        elif verdict.status == "reject":
            rejected.append(cell)
    return rejected, unmapped


def run_input_case(case, data, view):
    """The input rule's verdict for one value typed into one cell."""
    verdict = check_cell(case["input"], case["value"], data)
    if verdict is None:
        raise Pending("no rule for cell %s" % case["input"])
    return [(case["input"], case["verdict"], verdict.status, "verdict")]


def run_values_case(case, data, view):
    """Group 'table': one cell of the requirement table at the default inputs."""
    if case["group"] != "table":
        raise Pending(VALUES_PENDING)
    out = []
    for ref, expected in case["outputs"].items():
        got, kind = view.cell(ref)
        out.append((ref, expected, got, kind))
    return out


RUNNERS = {"inputs.json": run_input_case, "values.json": run_values_case}


def run_file(name, cases, data, order):
    """{case id: (status, [(cell, expected, got, kind, result)], pending reason)}."""
    view = sheet_view.TableView(data)
    runner = RUNNERS.get(name)
    results = {}
    ordered = cases if order == "forward" else list(reversed(cases))
    for case in ordered:
        if runner is None:
            results[case["id"]] = ("pending", [], PENDING[name])
            continue
        try:
            rows = runner(case, data, view)
        except (Pending, sheet_view.NotModelled) as e:
            results[case["id"]] = ("pending", [], str(e))
            continue
        checked = [(cell, exp, got, kind, compare(exp, got)) for cell, exp, got, kind in rows]
        status = "pass" if all(r[4] for r in checked) else "difference"
        results[case["id"]] = (status, checked, None)
    return results


def load_cases(name):
    with open(os.path.join(VECTORS, name), encoding="utf-8") as f:
        doc = json.load(f)
    return doc["cases"], doc.get("outside_rule_cases", [])


def outside_counts(cases, data):
    """(number of cases outside the input rules, {inputs: count}, {cell not mapped: count})."""
    n, by_inputs, unmapped = 0, {}, {}
    for case in cases:
        rejected, missing = outside_rules(case.get("inputs", {}), data)
        for cell in missing:
            unmapped[cell] = unmapped.get(cell, 0) + 1
        if rejected:
            n += 1
            key = "+".join(rejected)
            by_inputs[key] = by_inputs.get(key, 0) + 1
    return n, by_inputs, unmapped


def summarise(name, cases, outside, results, data):
    counts = {"pass": 0, "difference": 0, "pending": 0}
    close = exact = 0
    kinds = {}
    pending = {}
    for case in cases:
        status, checked, reason = results[case["id"]]
        counts[status] += 1
        if reason:
            pending[reason] = pending.get(reason, 0) + 1
        for _, _, _, kind, result in checked:
            kinds[kind] = kinds.get(kind, 0) + 1
            exact += result == "exact"
            close += result == "close"
    line = "%s: %d cases: %d pass, %d differ, %d pending" % (
        name, len(cases), counts["pass"], counts["difference"], counts["pending"])
    if outside:
        line += " (+ %d outside-rule cases, pending)" % len(outside)
    lines = [line]
    n, by_inputs, unmapped = outside_counts(cases, data)
    if n:
        lines.append("    outside the input rules: %d (%s)" % (
            n, ", ".join("%s %d" % kv for kv in sorted(by_inputs.items()))))
    if outside:
        not_rejected = [c["id"] for c in outside if not outside_rules(c["inputs"], data)[0]]
        lines.append("    outside-rule cases the input rules reject: %d of %d%s" % (
            len(outside) - len(not_rejected), len(outside),
            " (not: %s)" % ", ".join(not_rejected) if not_rejected else ""))
    if unmapped:
        lines.append("    input cells not mapped yet: %s" % (
            ", ".join("%s in %d" % kv for kv in sorted(unmapped.items()))))
    if exact or close:
        lines.append("    values: %d identical, %d within 1e-12, by kind: %s" % (
            exact, close, ", ".join("%s %d" % kv for kv in sorted(kinds.items()))))
    for reason, n in sorted(pending.items()):
        lines.append("    pending %d: %s" % (n, reason))
    return counts, lines


def main(argv):
    show = int(argv[argv.index("--show") + 1]) if "--show" in argv else 20
    data = table.load(BASELINE)
    total_diff = 0
    orders_agree = True
    for name in FILES:
        cases, outside = load_cases(name)
        forward = run_file(name, cases, data, "forward")
        reverse = run_file(name, cases, data, "reverse")
        if forward != reverse:
            orders_agree = False
            print("%s: the two orders give different results" % name)
        counts, lines = summarise(name, cases, outside, forward, data)
        print("\n".join(lines))
        total_diff += counts["difference"]
        shown = 0
        for case in cases:
            status, checked, _ = forward[case["id"]]
            if status != "difference":
                continue
            for cell, exp, got, kind, result in checked:
                if result is None and shown < show:
                    print("    DIFF %s %s (%s): expected %r, got %r" % (
                        case["id"], cell, kind, exp, got))
                    shown += 1
    print("orders: forward and reverse %s" % ("agree" if orders_agree else "DIFFER"))
    print("ALL RUN CASES PASS" if total_diff == 0 and orders_agree else "DIFFERENCES FOUND")
    return 0 if total_diff == 0 and orders_agree else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
