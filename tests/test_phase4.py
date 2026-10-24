"""Phase 4 tests: the real-Sheets check, the impact report, the one command that runs every
check, and the difference list (docs/parity-21OCT26b.md).

Run: nice -n 10 python3 -I -B tests/test_phase4.py
"""

import copy
import csv
import os
import shutil
import sys
import tempfile
import unittest
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import check  # noqa: E402
import impact_report  # noqa: E402
import real_sheets_check  # noqa: E402
import run_vectors  # noqa: E402
import sheet_map  # noqa: E402
from oan import limits, outcomes, table, validate  # noqa: E402

BASELINE = run_vectors.BASELINE
DATA = table.load(BASELINE)
EXPORT = real_sheets_check.load_export()
DOC = os.path.join(ROOT, "docs", "parity-21OCT26b.md")


def compared(tab_result, kind, outcome=None):
    return sum(v for (k, o), v in tab_result["compared"].items()
               if k == kind and (outcome is None or o == outcome))


class RealSheets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = real_sheets_check.run(DATA, EXPORT)

    def test_passes(self):
        self.assertTrue(real_sheets_check.passed(self.result),
                        real_sheets_check.report(self.result))
        self.assertEqual(self.result["inputs"], [])

    def test_every_formula_cell_is_compared(self):
        for tab, t in self.result["tabs"].items():
            formulas = sum(1 for c in EXPORT["cells"][tab].values() if c[0])
            self.assertEqual(compared(t, "formula"), formulas, tab)

    def test_counts(self):
        s01, s02 = self.result["tabs"]["s01"], self.result["tabs"]["s02"]
        self.assertEqual((s01["export_cells"], compared(s01, "formula", "exact"),
                          compared(s01, "formula", "sig10"), compared(s01, "typed"),
                          compared(s01, "blank"), sum(s01["layout"].values())),
                         (4839, 1746, 2050, 357, 40, 686))
        self.assertEqual((s02["export_cells"], compared(s02, "formula", "exact"),
                          compared(s02, "formula", "sig10"), compared(s02, "typed"),
                          compared(s02, "blank"), sum(s02["layout"].values())),
                         (5803, 338, 58, 5221, 2082, 186))

    def test_sig10_is_sheets_rounding(self):
        # AG72: the code's value as stored; Sheets wrote 1.975000001. Rounding the stored
        # binary value to 10 digits would give 1.975.
        x = 1.9750000004999999
        self.assertEqual(real_sheets_check.sig10(x), Decimal("1.975000001"))
        self.assertEqual("%.10g" % x, "1.975")
        self.assertEqual(EXPORT["cells"]["s01"]["AG72"], [1, "n", "1.975000001"])
        self.assertEqual(real_sheets_check.sig10(990.8588589014987), Decimal("990.8588589"))

    def test_a_changed_export_value_differs(self):
        export = copy.deepcopy(EXPORT)
        export["cells"]["s01"]["C12"][2] = "100.0000001"
        export["cells"]["s02"]["E52"][2] = "1.01"
        result = real_sheets_check.run(DATA, export)
        self.assertFalse(real_sheets_check.passed(result))
        self.assertEqual([d[0] for d in result["tabs"]["s01"]["differences"]], ["C12"])
        self.assertEqual([d[0] for d in result["tabs"]["s02"]["differences"]], ["E52"])

    def test_changed_data_differs_where_it_is_used(self):
        data = copy.deepcopy(DATA)
        data["template"]["water-max"]["figure"] = "1417"
        result = real_sheets_check.run(data, EXPORT)
        cells = {d[0] for d in result["tabs"]["s01"]["differences"]}
        self.assertIn("E123", cells)
        self.assertIn("AR123", cells)
        self.assertTrue(all(sheet_map.col_row(c)[1] == 123 for c in cells), cells)

    def test_a_formula_cell_is_never_layout(self):
        export = copy.deepcopy(EXPORT)
        export["cells"]["s01"]["A12"][0] = 1  # a row ID marked as a formula
        result = real_sheets_check.run(DATA, export)
        self.assertEqual([u[0] for u in result["tabs"]["s01"]["unexplained"]], ["A12"])

    def test_export_inputs(self):
        export = copy.deepcopy(EXPORT)
        export["cells"]["s01"]["B3"][2] = "16.0"
        self.assertEqual([i[0] for i in real_sheets_check.check_inputs(
            export["cells"]["s01"])], ["B3"])


def set_field(data_dir, rel, key, field, value):
    path = os.path.join(data_dir, rel)
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    col = rows[0].index(field)
    for r in rows[1:]:
        if r[0] == key:
            r[col] = value
    with open(path, "w", encoding="utf-8", newline="") as f:
        csv.writer(f, lineterminator="\n").writerows(rows)


class Copy(unittest.TestCase):
    """A copy of the frozen baseline to change."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="oan-phase4-")
        self.new = os.path.join(self.tmp, "data")
        shutil.copytree(BASELINE, self.new)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def set_field(self, rel, key, field, value):
        set_field(self.new, rel, key, field, value)


class CheckDhaDivergence(Copy):
    """Difference 3: with no number for NRC RA Cat Maintenance's EPA + DHA minimum (changed
    data), row 58 keeps the EPA share result and skips the DHA comparison, where the template
    would show an error. The validator rejects removing the minimum alone: the LA + AA :
    EPA + DHA maximum is computed from it, so that maximum needs a figure of its own too."""

    CAT = "standards/NRC-2006/nrc-cat-adult.csv"

    def remove_minimum(self):
        for field, value in (("min", "none"), ("min_unit", ""), ("min_rule", "printed")):
            self.set_field(self.CAT, "epa-dha", field, value)

    def test_removing_the_minimum_alone_is_rejected_in_plain_words(self):
        self.remove_minimum()
        errors = validate.validate(self.new).errors
        self.assertEqual(len(errors), 1)
        self.assertIn("la-aa-to-epa-dha-ratio max is computed by the rule la-aa-over-epa-dha "
                      "from epa-dha min, which is none", errors[0])

    def test_no_epa_dha_minimum(self):
        entries = {"epa-dha": {"low": 0.028}, "epa": {"low": 0.004}}
        facts = {"body_weight_kg": 4.0, "adult_cat_type": "Lean domestic (100 * kgBW^0.67)"}
        r = limits.Request(DATA, "nrc-cat-adult", facts, entries, template_rules=True)
        self.assertEqual(outcomes.checks(r)["epa-share-max-dha-only"]["low"].result,
                         outcomes.DHA_BELOW_MINIMUM)
        self.remove_minimum()
        for field, value in (("max", "none"), ("max_rule", "printed"), ("max_type", "")):
            self.set_field(self.CAT, "la-aa-to-epa-dha-ratio", field, value)
        self.assertEqual(validate.validate(self.new).errors, [])
        r = limits.Request(table.load(self.new), "nrc-cat-adult", facts, entries,
                           template_rules=True)
        self.assertIsNone(r.minimum("epa-dha"))
        self.assertEqual(outcomes.checks(r)["epa-share-max-dha-only"]["low"].result,
                         outcomes.OK)


class ImpactReport(Copy):
    def test_no_change_reports_nothing(self):
        text, status = impact_report.report(BASELINE, self.new)
        self.assertEqual(status, 0)
        old, new = table.load(BASELINE), table.load(self.new)
        self.assertEqual(impact_report.changed_figures(BASELINE, self.new), [])
        self.assertEqual(impact_report.grid(old, new), ([], [], [], []))
        self.assertTrue(all(not d for _, d in impact_report.cases(old, new).values()))
        self.assertIn("| Model disagreements with the core | 0 |", text)

    def test_one_value_names_exactly_the_affected_outcomes(self):
        rel = "standards/NRC-2006/nrc-dog-adult.csv"
        self.set_field(rel, "calcium", "min", "1.1")
        self.assertEqual(impact_report.changed_figures(BASELINE, self.new),
                         [(rel, "calcium", "min", "1.0", "1.1")])
        old, new = table.load(BASELINE), table.load(self.new)
        changed_limits, changed_outcomes, added, removed = impact_report.grid(old, new)
        self.assertEqual({(r, n) for r, _, n, _, _ in changed_limits},
                         {("nrc-dog-adult", "calcium")})
        self.assertEqual(len(changed_limits), 5)  # every variant of the grid
        self.assertEqual({(r, n) for r, _, n, *_ in changed_outcomes},
                         {("nrc-dog-adult", "calcium")})
        self.assertEqual((added, removed), ([], []))
        # The test cases: only the calcium row of the Standards tab (row 63) and the
        # requirement table's NRC RA Dog Maintenance calcium minimum (s02 E52) change.
        for name, (_, diffs) in impact_report.cases(old, new).items():
            for case_id, ref, kind, a, b in diffs:
                self.assertTrue(ref == "s02!E52" or (not ref.startswith("s02!") and
                                                     sheet_map.col_row(ref)[1] == 63),
                                (name, case_id, ref))
        self.assertTrue(all(not bad for _, (_, bad, _) in impact_report.models(new)))

    def test_bad_data_fails(self):
        self.set_field("standards/NRC-2006/nrc-dog-adult.csv", "calcium", "min", "1,1")
        text, status = impact_report.report(BASELINE, self.new)
        self.assertEqual(status, 1)
        self.assertIn("ERROR", text)


class OneCommand(unittest.TestCase):
    def test_every_check_is_run(self):
        names = [n for n, _ in check.steps()]
        tests = sorted(f for f in os.listdir(HERE) if f.startswith("test_phase"))
        self.assertEqual([n for n in names if n.startswith("tests: ")],
                         ["tests: " + f for f in tests])
        for name in ("validator: data", "validator: frozen baseline", "test vectors",
                     "real-Sheets check"):
            self.assertIn(name, names)
        self.assertFalse(any(n.startswith("impact report") for n in names))
        self.assertTrue(check.steps("OLD")[-1][0].startswith("impact report"))


class DifferenceList(unittest.TestCase):
    """The counts on docs/parity-21OCT26b.md are the runner's and the check's."""

    @classmethod
    def setUpClass(cls):
        with open(DOC, encoding="utf-8") as f:
            cls.doc = f.read()

    def test_vector_counts(self):
        for name in run_vectors.FILES + run_vectors.EXTRA_FILES:
            cases, outside = run_vectors.load_cases(name)
            results = run_vectors.run_file(name, cases, DATA, "forward")
            counts, _ = run_vectors.summarise(name, cases, outside, results, DATA)
            row = "| `%s` | {:,} | {:,} | {:,} | {:,} |".format(
                len(cases), counts["pass"], counts["difference"], counts["outside-rule"]) % name
            self.assertIn(row, self.doc)

    def test_real_sheets_counts(self):
        result = real_sheets_check.run(DATA, EXPORT)
        for tab, label in (("s01", "Standards tab (s01)"), ("s02", "Requirement table (s02)")):
            t = result["tabs"][tab]
            formulas = sum(1 for c in EXPORT["cells"][tab].values() if c[0])
            row = "| {} | {:,} | {:,} of {:,} | {:,} | {:,} | {:,} | {:,} |".format(
                label, t["export_cells"], compared(t, "formula"), formulas,
                compared(t, "typed"), compared(t, "blank"), len(t["differences"]),
                sum(t["layout"].values()))
            self.assertIn(row, self.doc)


if __name__ == "__main__":
    unittest.main(verbosity=1)
