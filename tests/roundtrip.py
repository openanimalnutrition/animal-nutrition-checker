"""Compare the limits computed from a data folder with the released 21OCT26b limits.

Usage: python3 -I -B tests/roundtrip.py [DATA_DIR]   (default: the frozen baseline)
Exit status 0 only when every limit and max type matches.
"""

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from oan import table  # noqa: E402

BASELINE = os.path.join(HERE, "parity", "data-21OCT26b")
RELEASED = os.path.join(HERE, "parity", "released-limits-21OCT26b.json")
REL_TOL = 1e-12


def compare(data_dir, mature_weight_kg=None, released_path=RELEASED):
    """(exact, within tolerance, [differences]) over every limit and max type."""
    with open(released_path, encoding="utf-8") as f:
        released = json.load(f)["limits"]
    data = table.load(data_dir)
    exact = close = 0
    diffs = []
    for rid, expected_rows in sorted(released.items()):
        computed = table.compute_limits(data, rid, mature_weight_kg)
        rows = data["limits"][rid]
        for nid, exp in sorted(expected_rows.items()):
            got_min, got_max = computed[nid]
            for bound, got in (("min", got_min), ("max", got_max)):
                want = exp[bound]
                want = None if want == "none" else want
                if got == want:
                    exact += 1
                elif (isinstance(got, float) and isinstance(want, float)
                      and math.isclose(got, want, rel_tol=REL_TOL, abs_tol=0)):
                    close += 1
                else:
                    diffs.append((rid, nid, bound, want, got))
            want_type = exp["max_type"] or ""
            if rows[nid]["max_type"] != want_type:
                diffs.append((rid, nid, "max_type", want_type, rows[nid]["max_type"]))
    return exact, close, diffs


def main(argv):
    data_dir = argv[1] if len(argv) > 1 else BASELINE
    exact, close, diffs = compare(data_dir)
    print("data: %s" % data_dir)
    print("limits exact %d, within relative %g %d, differences %d" % (
        exact, REL_TOL, close, len(diffs)))
    for d in diffs[:40]:
        print("  DIFF %s %s %s: released %r, computed %r" % d)
    return 0 if not diffs else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
