"""Phase 2 tests: the energy figures, the energy core, the bands and row 11.

Run: nice -n 10 python3 -I -B tests/test_phase2.py
"""

import contextlib
import copy
import csv
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import run_vectors  # noqa: E402
import sheet_map  # noqa: E402
import sheet_view  # noqa: E402
from models import energy_model  # noqa: E402
from oan import bands, energy, numbers, table, validate  # noqa: E402

BASELINE = run_vectors.BASELINE
DATA = table.load(BASELINE)
REPO_DATA = os.path.join(os.path.dirname(HERE), "data")


def energy_doc():
    with open(os.path.join(run_vectors.VECTORS, "energy-testcases.json"), encoding="utf-8") as f:
        return json.load(f)


def facts(**kw):
    out = {"body_weight_kg": 15.0}
    out.update(kw)
    return out


class Baseline(unittest.TestCase):
    def test_every_baseline_file_is_checksummed(self):
        # energy.csv was added once, in phase 2, and template.csv once, in phase 3 (steward,
        # 21 Oct 2026); the RELEASE hash was recomputed each time. The export's cell values
        # were added once, in phase 4 (steward, 22 Oct 2026). Any other file added or changed
        # fails here or in test_phase1a.
        listed = set()
        for line in open(os.path.join(run_vectors.PARITY, "SHA256SUMS"), encoding="utf-8"):
            listed.add(line.split(None, 1)[1].strip())
        found = set()
        for folder in ("data-21OCT26b", "vectors-21OCT26b", "export-21OCT26b"):
            for dirpath, _, files in os.walk(os.path.join(run_vectors.PARITY, folder)):
                for f in files:
                    found.add(os.path.relpath(os.path.join(dirpath, f), run_vectors.PARITY))
        self.assertEqual(found, listed)


class Figures(unittest.TestCase):
    def test_every_figure_once_with_a_source(self):
        self.assertEqual(sorted(DATA["energy"]), sorted(energy.FIGURES))
        for fid, row in DATA["energy"].items():
            self.assertTrue(row["source"].strip(), fid)

    def test_type_lists_are_the_templates(self):
        # The B4 and D4 lists of 21OCT26b, in order, now built from the data.
        self.assertEqual(energy.dog_type_labels(DATA), (
            "Not selected or a dog",
            "Inactive (95 * kg BW^0.75)",
            "Older laboratory/active OR Laboratory Newfoundlands (105 * kg BW^0.75)",
            "Average laboratory or active (130 * kg BW^0.75)",
            "Young laboratory/active (140 * kg BW^0.75)",
            "Laboratory/active terriers (180 * kg BW^0.75)",
            "Laboratory/active Great Danes (200 * kg BW^0.75)",
        ))
        self.assertEqual(energy.cat_type_labels(DATA), (
            "Not selected or a cat",
            "Overweight domestic (130 * BW^0.4)",
            "Lean domestic (100 * kgBW^0.67)",
        ))

    def test_every_requirement_has_an_energy_rule(self):
        self.assertEqual(sorted(r["id"] for r in DATA["requirements"]), sorted(energy.RULES))


class Validator(unittest.TestCase):
    """Each kind of bad energy.csv is rejected with a message that names the problem."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.dir = os.path.join(self.tmp, "data")
        shutil.copytree(REPO_DATA, self.dir)
        self.path = os.path.join(self.dir, "energy.csv")
        with open(self.path, encoding="utf-8", newline="") as f:
            self.rows = list(csv.reader(f))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def errors(self, change):
        rows = copy.deepcopy(self.rows)
        change(rows)
        with open(self.path, "w", encoding="utf-8", newline="") as f:
            csv.writer(f, lineterminator="\n").writerows(rows)
        return validate.validate(self.dir).errors

    def row(self, rows, fid):
        return next(r for r in rows if r[0] == fid)

    def set(self, fid, col, value):
        def change(rows):
            self.row(rows, fid)[col] = value
        return change

    def assertError(self, change, words):
        errors = self.errors(change)
        self.assertTrue(any(words in e for e in errors), errors)

    def test_clean(self):
        self.assertEqual(self.errors(lambda rows: None), [])

    def test_bad_files(self):
        self.assertError(self.set("nrc-puppy-rate", 1, "0,87"), "use a point")
        self.assertError(self.set("nrc-puppy-rate", 1, ""), "not a plain decimal")
        self.assertError(self.set("nrc-puppy-rate", 2, "kcal/kg BW"), "the code reads")
        self.assertError(self.set("nrc-puppy-rate", 4, " "), "needs its source")
        self.assertError(self.set("nrc-puppy-rate", 5, "n999"), "does not exist")
        self.assertError(self.set("nrc-puppy-rate", 3, "x"), "only the adult dog and cat")
        self.assertError(self.set("nrc-puppy-rate", 0, "nrc-puppy-speed"), "unknown figure")
        self.assertError(lambda rows: rows.remove(self.row(rows, "avcn-rer")), "no row for")
        self.assertError(lambda rows: rows.append(list(self.row(rows, "avcn-rer"))),
                         "appears twice")

    def test_a_type_label_cannot_go_stale(self):
        # A changed figure without its label, or the reverse; the exponent the label prints.
        self.assertError(self.set("nrc-dog-maintenance-inactive", 1, "90"),
                         "the label prints 95 but the figure is 90")
        self.assertError(self.set("nrc-dog-maintenance-inactive", 3,
                                  "Inactive (90 * kg BW^0.75)"), "the label prints 90")
        self.assertError(self.set("nrc-cat-maintenance-overweight-exponent", 1, "0.45"),
                         "the label prints the exponent 0.4")
        self.assertError(self.set("nrc-cat-maintenance-lean", 3, "Lean domestic"),
                         "ends with its equation")
        self.assertEqual(self.errors(lambda rows: (
            self.set("nrc-dog-maintenance-inactive", 1, "90")(rows),
            self.set("nrc-dog-maintenance-inactive", 3, "Inactive (90 * kg BW^0.75)")(rows))),
            [])

    def test_a_new_requirement_needs_an_energy_rule(self):
        saved = energy.RULES.pop("nrc-kitten")
        try:
            self.assertError(lambda rows: None, "no energy rule for 'nrc-kitten'")
        finally:
            energy.RULES["nrc-kitten"] = saved

    def test_a_tenfold_change_is_flagged(self):
        self.errors(self.set("nrc-kitten-rate", 1, "2"))  # more than 10x 0.189
        report = validate.validate(self.dir, against=REPO_DATA)
        self.assertTrue(any("nrc-kitten-rate" in w and "10x" in w for w in report.warnings),
                        report.warnings)


class Core(unittest.TestCase):
    def test_reasons(self):
        def reason(rid, **kw):
            return energy.requirement_energy(DATA, rid, facts(**kw)).reason
        self.assertEqual(energy.requirement_energy(DATA, "nrc-dog-adult", {}).reason,
                         "body-weight-needed")
        self.assertEqual(reason("nrc-dog-adult"), "adult-dog-type-needed")
        self.assertEqual(reason("nrc-cat-adult"), "adult-cat-type-needed")
        self.assertEqual(reason("nrc-kitten"), "mature-weight-needed")
        self.assertEqual(reason("nrc-kitten", mature_weight_kg=10.0),
                         "mature-weight-below-body-weight")
        self.assertIsNone(reason("nrc-kitten", mature_weight_kg=15.0))  # BW = mature computes
        self.assertEqual(reason("aafco-dog-growth-large-breed"), "life-stage-not-covered")
        self.assertEqual(reason("nrc-dog-gestation-lactation", life_stage="Lactation: bitch"),
                         "lactation-week-and-puppies-needed")
        self.assertEqual(reason("nrc-dog-gestation-lactation", life_stage="Lactation: bitch",
                                puppies_nursing=3.0, lactation_week=5.0),
                         "no-estimate-after-lactation-week-4")
        self.assertEqual(reason("nrc-cat-peak-lactation", life_stage="3-4 Kittens Nursing"),
                         "lactation-week-and-kittens-needed")
        self.assertEqual(set(energy.REASONS) - {"body-weight-needed"},
                         set(sheet_map.ENERGY_MESSAGES))

    def test_intake_takes_the_place_of_the_requirement(self):
        needs_type = energy.requirement_energy(DATA, "nrc-dog-adult", facts())
        self.assertEqual(energy.energy_used(needs_type, 1500.0), (1500.0, None))
        self.assertEqual(energy.energy_used(needs_type, None), needs_type)

    def test_source_examples(self):
        # The 18 worked examples of the sources (energy spec section 7), within each one's
        # printed rounding; the sheet's value within 1e-12.
        examples = energy_doc()["source_examples"]
        self.assertEqual(len(examples), 18)
        for ex in examples:
            cells = dict(ex["inputs"], O1=ex["selection"])
            got = sheet_view.EnergyView(DATA, cells).cells()["G4"]
            self.assertTrue(numbers.close(got, ex["sheet"]), ex["name"])
            self.assertLessEqual(abs(got - ex["source_value"]), ex["tolerance"], ex["name"])

    def test_the_kitten_example_uses_the_equations_figure(self):
        # NRC Table 15-9's example prints 6.732 and 198 kcal; the equation's 6.7 gives 196.88
        # (Sean's correction of the printed 198, handwritten on the scan).
        got = energy.requirement_energy(DATA, "nrc-kitten", {
            "body_weight_kg": 1.0, "mature_weight_kg": 4.0}).kcal
        self.assertAlmostEqual(got, 196.88, places=2)


class IndependentModel(unittest.TestCase):
    """The energy model written from the sources (tests/models), on the same figures, agrees
    with every expected value and with the core."""

    def test_every_case(self):
        energy_model.use(DATA)
        for case in energy_doc()["cases"]:
            inp = case["inputs"]
            got = energy_model.energy_row(case["selection"], inp, inp.get("K4"))
            for cell in ("G4", "C11", "C11_highlighted"):
                exp = case["expected"][cell]
                if numbers.is_number(exp):
                    self.assertTrue(numbers.close(got[cell], exp), (case["id"], cell))
                else:
                    self.assertEqual(got[cell], exp, (case["id"], cell))


class Bands(unittest.TestCase):
    def test_edges(self):
        self.assertEqual(bands.lower_edges(1.0, 4.0)[:4], [0.25, 0.5, 0.75, 1.0])
        self.assertEqual(bands.lower_edges(1.0, 4.0)[-2], ((4.0 - 1.0) * 0.8) + 1.0)
        self.assertEqual(bands.lower_edges(None, 10.0)[:4], [0.0, 0.0, 0.0, 0.0])

    def test_the_ig_examples(self):
        # The 80% calcium edge under NRC RA Dog Maintenance (1 to 4 g/Mcal) computes as
        # 3.4000000000000004; at 7 places an entered 3.4 is on it, in range-d9.
        self.assertEqual(bands.band(3.4, 1.0, 4.0, has_max=True), "range-d9")
        self.assertEqual(bands.band(3.3999999, 1.0, 4.0, has_max=True), "range-d8")
        # 0.99999995 against a minimum of 1 rounds up to 1: range-d1.
        self.assertEqual(bands.band(0.99999995, 1.0, 4.0, has_max=True), "range-d1")
        self.assertEqual(bands.band(0.99999994, 1.0, 4.0, has_max=True), "below-min-75-100")
        # A value on an edge is in the band that starts there; below 25%, negatives included.
        self.assertEqual(bands.band(0.25, 1.0, 4.0, has_max=True), "below-min-25-50")
        self.assertEqual(bands.band(-3.0, 1.0, 4.0, has_max=True), "below-min-lt25")
        self.assertEqual(bands.band(99.0, 1.0, 4.0, has_max=True), "range-d10")

    def test_no_minimum_no_range_and_max_below_min(self):
        # No minimum, a maximum: 0 is range-d1, a negative value is below-min-lt25.
        self.assertEqual(bands.band(0.0, None, 0.67, has_max=True), "range-d1")
        self.assertEqual(bands.band(-0.1, None, 0.67, has_max=True), "below-min-lt25")
        # Neither limit (the Ca:P ratio under NRC RA Dog Maintenance): No range.
        self.assertEqual(bands.band(1.2, None, 0.0, has_max=False), bands.NO_RANGE)
        # A maximum below the minimum: everything at or above the minimum is range-d10.
        self.assertEqual(bands.band(10.0, 10.0, 5.0, has_max=True), "range-d10")
        self.assertEqual(bands.band(9.0, 10.0, 5.0, has_max=True), "below-min-75-100")


class Runner(unittest.TestCase):
    def test_energy_files(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = run_vectors.main(["run_vectors.py"])
        text = out.getvalue()
        self.assertEqual(status, 0, text)
        self.assertIn("energy-testcases.json: 2360 cases: 2360 pass, 0 differ, 0 outside-rule, "
                      "0 pending", text)
        self.assertIn("29 rejected by the input rules, 1 reported as a missing input, "
                      "0 computed", text)
        self.assertIn("energy-testcases-row11.json: 1092 cases: 1088 pass, 0 differ, "
                      "4 outside-rule, 0 pending", text)

    def test_outside_rule_cases(self):
        # Decision 1 A: the energy file's 30 outside-rule cases are never computed; the one
        # the rules do not reject has a blank body weight, reported as missing.
        _, outside = run_vectors.load_cases("energy-testcases.json")
        ran = run_vectors.run_outside(outside, DATA)
        self.assertEqual((ran["rejected"], ran["missing"], ran["computed"]), (29, 1, []))
        cases, _ = run_vectors.load_cases("energy-testcases-row11.json")
        results = run_vectors.run_file("energy-testcases-row11.json", cases, DATA, "forward")
        self.assertEqual(sorted(i for i, r in results.items() if r[0] == "outside-rule"),
                         ["R11-1089", "R11-1090", "R11-1091", "R11-1092"])

    def changed_data(self, fid, figure):
        data = copy.deepcopy(DATA)
        data["energy"][fid]["figure"] = figure
        return data

    def differing_selections(self, data):
        cases, _ = run_vectors.load_cases("energy-testcases.json")
        results = run_vectors.run_file("energy-testcases.json", cases, data, "forward")
        return {c["selection"] for c in cases if results[c["id"]][0] == "difference"}

    def test_negative_controls(self):
        # One changed figure changes exactly the requirements that use it.
        self.assertEqual(self.differing_selections(self.changed_data(
            "nrc-kitten-multiplier", "6.732")), {"NRC RA Kitten Growth", "FEDIAF Cat Growth"})
        self.assertEqual(self.differing_selections(self.changed_data(
            "fediaf-queen-lactation-week-3", "1.25")), {"FEDIAF Cat Reproduction"})
        self.assertEqual(self.differing_selections(self.changed_data(
            "nrc-queen-lactation-week-3", "1.25")),
            {"NRC RA Cat Peak Lactation", "AAFCO Cat Growth and Reproduction"})
        # An expected value off by more than 1e-12, a message, the highlight, a band name.
        cases, _ = run_vectors.load_cases("energy-testcases.json")
        cases = copy.deepcopy(cases)
        number = next(c for c in cases if numbers.is_number(c["expected"]["G4"]))
        number["expected"]["G4"] *= 1 + 2e-12
        message = next(c for c in cases if c["expected"]["C11_highlighted"])
        message["expected"]["C11_highlighted"] = False
        results = run_vectors.run_file("energy-testcases.json", cases, DATA, "forward")
        self.assertEqual(results[number["id"]][0], "difference")
        self.assertEqual(results[message["id"]][0], "difference")
        cases, _ = run_vectors.load_cases("energy-testcases-row11.json")
        cases = copy.deepcopy(cases)
        described = next(c for c in cases if c["expected"]["L11"])
        described["expected"]["L11"] = "Lower (10 to <20% of Range)" if (
            described["expected"]["L11"] != "Lower (10 to <20% of Range)") else "Low (20 to <30% of Range)"
        results = run_vectors.run_file("energy-testcases-row11.json", cases, DATA, "forward")
        self.assertEqual(results[described["id"]][0], "difference")


if __name__ == "__main__":
    unittest.main(verbosity=1)
