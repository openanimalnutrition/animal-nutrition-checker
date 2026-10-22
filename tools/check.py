"""Every automatic check, in one command: what a pull request must pass.

1. the validator on data/ and on the frozen baseline;
2. the tests of each phase (tests/test_phase*.py);
3. every test vector against the frozen baseline (tests/run_vectors.py);
4. the real-Sheets check (tests/real_sheets_check.py);
5. with --against OLD_DATA (the data of the branch merged into): the impact report of
   data/ against it (tools/impact_report.py), which fails on validator errors or on a model
   that disagrees with the core. --summary FILE appends the report to FILE (GitHub's job
   summary).

Usage: python3 -I -B tools/check.py [--against OLD_DATA] [--summary FILE]
Exit status 0 when every check passes.
"""

import glob
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = [sys.executable, "-I", "-B"]


def steps(against=None):
    """[(name, command)] in order."""
    out = [("validator: data", PY + ["tools/validate_data.py", "data"]),
           ("validator: frozen baseline",
            PY + ["tools/validate_data.py", "tests/parity/data-21OCT26b"])]
    for path in sorted(glob.glob(os.path.join(ROOT, "tests", "test_phase*.py"))):
        rel = os.path.relpath(path, ROOT)
        out.append(("tests: " + os.path.basename(path), PY + [rel]))
    out.append(("test vectors", PY + ["tests/run_vectors.py"]))
    out.append(("real-Sheets check", PY + ["tests/real_sheets_check.py"]))
    if against:
        out.append(("impact report against " + against,
                    PY + ["tools/impact_report.py", against, "data"]))
    return out


def main(argv):
    args = argv[1:]
    against = summary = None
    if "--against" in args:
        against = args[args.index("--against") + 1]
    if "--summary" in args:
        summary = args[args.index("--summary") + 1]
    failed = []
    for name, cmd in steps(against):
        t0 = time.time()
        p = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           universal_newlines=True)
        ok = p.returncode == 0
        print("%s %s (%.1f s)" % ("PASS" if ok else "FAIL", name, time.time() - t0))
        if name.startswith("impact report"):
            if summary:
                with open(summary, "a", encoding="utf-8") as f:
                    f.write(p.stdout)
            else:
                print(p.stdout)
        elif not ok:
            print(p.stdout)
        if not ok:
            failed.append(name)
    print("ALL CHECKS PASS" if not failed else "FAILED: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
