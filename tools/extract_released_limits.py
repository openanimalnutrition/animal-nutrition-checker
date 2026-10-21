"""Extract the released limits (template Version 21OCT26b) for the round trip test.

Reads the s02 values cached by Google Sheets in the 21OCT26b export dump and the candidate
table JSON (b04aa7ff), checks that the two agree on every limit and max-type cell (to the
export's precision, about 10 significant digits for formula results), and writes tests/parity/released-limits-21OCT26b.json and tests/sheet_map.py (the test-side
map from nutrient ids and requirement ids to s02 rows and columns).

Usage: python3 -I -B tools/extract_released_limits.py TABLE_JSON EXPORT_S02_TSV REPO_DIR
"""

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import convert_sheet_table as conv  # noqa: E402


def cached(text, typ):
    if typ == "n":
        return float(text)
    if typ == "s":
        return text
    if typ == "b":
        return text
    raise ValueError("cell type %r" % typ)


def main(table_path, tsv_path, repo):
    table = json.load(open(table_path, encoding="utf-8"))
    rows = {r["row"]: r for r in table["rows"]}
    export = {}
    with open(tsv_path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            export[parts[0]] = (parts[1], parts[3])

    row_ids = {}
    for row_no, base in conv.BASE_IDS:
        row_ids[row_no] = base
        nxt = rows.get(row_no + 1)
        if nxt and nxt["key"] and nxt["key"].endswith(" MBW"):
            row_ids[row_no + 1] = base + "-mbw"
    req_cols = {}
    for s in table["selections"]:
        req_cols[conv.REQUIREMENTS[s["name"]][0]] = (s["min_col"], s["max_col"], s["code_col"])

    out = {}
    mismatches = 0
    for rid, (cmin, cmax, ccode) in req_cols.items():
        out[rid] = {}
        for r in sorted(row_ids):
            nid = row_ids[r]
            vals = []
            for col in (cmin, cmax, ccode):
                cand = rows[r]["cells"].get(col)
                if isinstance(cand, dict):
                    cand = cand["value_at_defaults"]
                ref = "%s%d" % (col, r)
                if ref in export:
                    exp = cached(export[ref][1], export[ref][0])
                else:
                    exp = None
                # The export keeps about 10 significant digits of a formula's result, so
                # it confirms the candidate to 1e-9; the candidate gives the full value.
                same = (cand == exp) or (
                    isinstance(cand, (int, float)) and isinstance(exp, float)
                    and math.isclose(cand, exp, rel_tol=1e-9, abs_tol=0))
                if not same:
                    mismatches += 1
                    print("MISMATCH", rid, nid, ref, repr(cand), repr(exp))
                vals.append(float(cand) if isinstance(cand, int) and not isinstance(cand, bool)
                            else cand)
            out[rid][nid] = {"min": vals[0], "max": vals[1], "max_type": vals[2]}
    if mismatches:
        sys.exit("%d mismatches between the candidate and the export" % mismatches)

    path = os.path.join(repo, "tests", "parity", "released-limits-21OCT26b.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "about": "s02 limits and max types of template Version 21OCT26b at the default "
                     "inputs (expected mature weight blank): the full-precision values of "
                     "candidate b04aa7ff, which the values Google Sheets cached in the 21 Oct "
                     "2026 export confirm on every cell to relative 1e-9 (the export keeps "
                     "about 10 significant digits of a formula's result).",
            "limits": out}, f, indent=1, sort_keys=True)
        f.write("\n")
    with open(os.path.join(repo, "tests", "sheet_map.py"), "w", encoding="utf-8") as f:
        f.write('"""Test-side map from the data ids to template cells (s02 rows and columns).\n\n'
                'Volunteers never edit this; it exists only to compare with the sheet."""\n\n')
        f.write("NUTRIENT_ROWS = {\n")
        for r in sorted(row_ids):
            f.write("    %r: %d,\n" % (row_ids[r], r))
        f.write("}\n\n# requirement id -> (MIN column, MAX column, max-type column)\n")
        f.write("REQUIREMENT_COLUMNS = {\n")
        for rid, cols in req_cols.items():
            f.write("    %r: %r,\n" % (rid, cols))
        f.write("}\n")
    n = sum(len(v) for v in out.values())
    print("requirements %d, nutrient rows %d, cells %d, mismatches 0" % (len(out), n, n * 3))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
