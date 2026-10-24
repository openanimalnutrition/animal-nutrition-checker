"""Phase 3 tests: the template's figures and rows, the limits, range highs and their types,
the outcomes, the text checks, and the independent models on the data.

Run: nice -n 10 python3 -I -B tests/test_phase3.py
"""

import copy
import csv
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "models"))
import formulas_model  # noqa: E402
import model_agreement  # noqa: E402
import run_vectors  # noqa: E402
import values_model  # noqa: E402
from oan import inputs, limits, outcomes, table, validate  # noqa: E402

BASELINE = run_vectors.BASELINE
DATA = table.load(BASELINE)
REPO_DATA = os.path.join(os.path.dirname(HERE), "data")
VALUES = os.path.join(run_vectors.VECTORS, "values.json")
FORMULAS = os.path.join(run_vectors.VECTORS, "formulas-testcases.json")


def request(rid, data=DATA, entries=None, **facts):
    f = {"body_weight_kg": 15.0, "adult_dog_type": "Average laboratory or active (130 * kg BW^0.75)",
         "adult_cat_type": "Lean domestic (100 * kgBW^0.67)"}
    f.update(facts)
    return limits.Request(data, rid, f, entries or {}, template_rules=True)


def outcome(r, nid, side, value):
    return outcomes.describe(value, side, r.limits(nid)).code


class Template(unittest.TestCase):
    def test_every_figure_and_row_once_with_a_source(self):
        figures = sorted(t for t, row in DATA["template"].items() if row["kind"] == "figure")
        rows = sorted(t for t, row in DATA["template"].items() if row["kind"] == "row")
        self.assertEqual(figures, sorted(limits.FIGURES))
        self.assertEqual(rows, sorted(limits.ROWS))
        for tid, row in DATA["template"].items():
            self.assertTrue(row["source"].strip(), tid)

    def test_every_max_type_has_a_provenance(self):
        codes = {row["max_type"] for rows in DATA["limits"].values() for row in rows.values()}
        codes |= {row["max_type"] for row in DATA["template"].values()}
        self.assertEqual(codes - {""} - set(limits.PROVENANCE), set())
        self.assertEqual(set(validate.MAX_TYPES) - set(limits.PROVENANCE), set())


class Validator(unittest.TestCase):
    """Each kind of bad template.csv is rejected with a message that names the problem."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.dir = os.path.join(self.tmp, "data")
        shutil.copytree(REPO_DATA, self.dir)
        self.path = os.path.join(self.dir, "template.csv")
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

    def row(self, rows, tid):
        return next(r for r in rows if r[0] == tid)

    def set(self, tid, col, value):
        def change(rows):
            self.row(rows, tid)[col] = value
        return change

    def assertError(self, change, words):
        errors = self.errors(change)
        self.assertTrue(any(words in e for e in errors), errors)

    def test_clean(self):
        self.assertEqual(self.errors(lambda rows: None), [])

    def test_bad_files(self):
        self.assertError(self.set("epa-share-max", 3, "0,6"), "use a point")
        self.assertError(self.set("epa-share-max", 4, "%"), "the code reads")
        self.assertError(self.set("epa-share-max", 8, " "), "needs its source")
        self.assertError(self.set("epa-share-max", 9, "n999"), "does not exist")
        self.assertError(self.set("epa-share-max", 6, "nrc-dog"), "unknown requirement or species")
        self.assertError(self.set("epa-share-max", 6, "* nrc-kitten"), 'write "*"')
        self.assertError(self.set("epa-share-max", 7, "SUL"), "only a figure that is a maximum")
        self.assertError(self.set("water-max", 7, ""), "this figure is a maximum")
        self.assertError(self.set("epa-share-max", 0, "epa-share-maximum"), "unknown figure")
        self.assertError(self.set("epa-share-max", 1, "rule"), "kind is figure or row")
        self.assertError(self.set("vitamin-d2", 3, "4"), "a row has no figure")
        self.assertError(self.set("vitamin-d2", 5, ""), "the multiplier K")
        self.assertError(self.set("epa", 5, "4"), "not banded")
        self.assertError(self.set("epa", 0, "protein"), "unknown row")
        self.assertError(lambda rows: rows.remove(self.row(rows, "mct-max")), "no row for")
        self.assertError(lambda rows: rows.append(list(self.row(rows, "mct-max"))),
                         "appears twice")

    def test_rules_that_need_their_partners(self):
        self.assertError(self.set("la-ala-ratio-high-adult", 6, "nrc-dog-adult nrc-puppy-4-14-wk"),
                         "two highest LA:ALA ratios")
        self.assertError(self.set("la-ala-ratio-high-adult", 6, "nrc-cat-adult"),
                         "needs the lowest too")
        self.assertError(self.set("epa-share-range-low", 6, "nrc-dog-adult"),
                         "apply to different requirements")

    def test_a_tenfold_change_is_flagged(self):
        self.errors(self.set("water-max", 3, "15000"))
        report = validate.validate(self.dir, against=REPO_DATA)
        self.assertTrue(any("template.csv water-max" in w and "10x" in w
                            for w in report.warnings), report.warnings)


class Limits(unittest.TestCase):
    def test_the_templates_own_limits(self):
        r = request("nrc-dog-adult")
        self.assertEqual(r.limits("vitamin-c"), (11.25, None, 45.0, "K"))
        self.assertEqual(r.limits("water"), (None, 1416.0, 1416.0, "TPL"))
        self.assertEqual(r.limits("energy-density"), (3.5, 6.0, 6.0, "TPL"))
        self.assertEqual(r.limits("oxalate"), (25.0, None, 100.0, "K"))
        self.assertEqual(r.limits("mct-mbw")[1:], (17.568, 17.568, "TPL"))
        # A dog requirement has no taurine minimum: 0.67 on all four taurine rows.
        for nid in limits.TAURINE_ROWS:
            self.assertEqual(r.limits(nid)[1:], (0.67, 0.67, "TPL"), nid)

    def test_no_requirement(self):
        r = limits.Request(DATA, None, {"body_weight_kg": 15.0}, {}, template_rules=True)
        need = limits.Unavailable(limits.REQUIREMENT_NEEDED)
        self.assertEqual(r.minimum("protein"), need)
        self.assertEqual(r.aafco_factor, need)
        self.assertEqual(r.limits("water")[1], 1416.0)
        self.assertEqual(r.minimum("purine"), 200.0)
        self.assertIsNone(r.minimum("calcium-large-breed-puppy"))
        self.assertIsNone(r.minimum("vitamin-d2"))

    def test_the_ig_restriction_examples(self):
        r = request("nrc-dog-adult", caloric_restriction_percent=25.0)
        self.assertEqual(r.minimum("calcium"), 1.0 * (1 / (1 - (25.0 / 100))))
        self.assertEqual(r.limits("calcium").range_high, r.minimum("calcium") * 4)
        # Arginine with 40 g/Mcal protein entered as low: 1.03, and 1.24 at 25%.
        protein = {"protein": {"low": 40.0}}
        self.assertEqual(round(request("nrc-dog-adult", entries=protein).minimum("arginine"), 2),
                         1.03)
        self.assertEqual(round(request("nrc-dog-adult", entries=protein,
                                       caloric_restriction_percent=25.0).minimum("arginine"), 2),
                         1.24)
        # Fat is not raised by a restriction; the MBW rows neither.
        self.assertEqual(r.minimum("fat"), request("nrc-dog-adult").minimum("fat"))
        self.assertEqual(r.minimum("calcium-mbw"), request("nrc-dog-adult").minimum("calcium-mbw"))

    def test_the_aafco_factor(self):
        dense = {"energy-density": {"low": 3.6}}
        r = request("aafco-cat-adult", entries=dense)
        self.assertEqual(r.aafco_factor, 4 / 3.6)
        self.assertEqual(round(r.minimum("protein"), 1), 72.2)
        self.assertEqual(request("nrc-cat-adult", entries=dense).aafco_factor, 1.0)
        self.assertEqual(request("aafco-cat-adult", entries={"energy-density": {"low": 4.0}})
                         .aafco_factor, 1.0)

    def test_rules_from_other_rows(self):
        # The ALA floor from LA under NRC puppies; vitamin D2 for cats; Ca:P 1 to 2 (5b A).
        self.assertEqual(request("nrc-puppy-4-14-wk", mature_weight_kg=35.0)
                         .minimum("alpha-linolenic-acid"), 3.3 / 16)
        cat = request("nrc-cat-adult")
        self.assertEqual(cat.minimum("vitamin-d2"), cat.minimum("vitamin-d") / 0.7)
        self.assertEqual(cat.maximum_typed("vitamin-d2"), cat.maximum_typed("vitamin-d"))
        self.assertEqual(request("nrc-dog-adult").limits("vitamin-d2"), (None, None, 0.0, "K"))
        self.assertEqual(request("aafco-cat-adult").limits("ca-p-ratio"), (1.0, None, 2.0, "K"))

    def test_the_large_breed_puppy_calcium_row(self):
        r = request("nrc-puppy-4-14-wk", mature_weight_kg=35.0)
        self.assertEqual(r.limits("calcium-large-breed-puppy"), (3.0, 4.5, 4.5, "SUL"))
        # IG conflicts item 12: a 20 kg puppy eating 1,324 kcal a day.
        r = request("nrc-puppy-4-14-wk", mature_weight_kg=35.0, body_weight_kg=20.0,
                    puppy_body_weight_kg=20.0, energy_intake_kcal_per_day=1324.0)
        low, high, _, code = r.limits("calcium-large-breed-puppy")
        self.assertEqual((round(low, 2), round(high, 2), code), (8.16, 8.97, "TPL"))
        self.assertIsNone(request("nrc-puppy-14-wk-plus", mature_weight_kg=35.0)
                          .minimum("calcium-large-breed-puppy"))

    def test_types_per_request(self):
        r = request("aafco-dog-adult")
        self.assertEqual(r.limits("calcium").max_code, "AAFCO")
        self.assertEqual(limits.provenance("AAFCO", r.aafco_factor), "authoritative")
        r = request("aafco-dog-adult", entries={"energy-density": {"low": 3.5}})
        self.assertEqual(limits.provenance(r.limits("calcium").max_code, r.aafco_factor,
                                           r.template_rules),
                         "conditional")
        self.assertEqual(request("nrc-dog-adult").limits("vitamin-d-mbw").max_code, "SULm")
        self.assertEqual(request("fediaf-dog-adult-mer95").limits("calcium-mbw").max_code, "CALC")
        self.assertEqual(request("nrc-kitten", mature_weight_kg=4.0, body_weight_kg=1.0)
                         .limits("vitamin-a-mbw").max_code, "SULm*")
        self.assertEqual(request("nrc-dog-adult").limits("potassium").max_code, "K")
        self.assertEqual(limits.provenance("K", 1.0), "derived-provisional")
        self.assertEqual(request("nrc-dog-adult").limits("alpha-linolenic-acid").max_code, "TPL")
        self.assertEqual(request("nrc-dog-adult").limits("carbohydrate").max_code, "TPL")
        self.assertEqual(request("nrc-dog-adult").limits("choline").max_code, "PSM")


class Outcomes(unittest.TestCase):
    def test_the_ig_worked_example(self):
        r = request("nrc-dog-adult")
        got = [outcome(r, "calcium", "low", v) for v in (0.9, 1.0, 3.4, 4.0, 5.0)]
        self.assertEqual(got, ["below-min-75-100", "range-d1", "range-d9", "range-d10",
                               "range-d10"])
        r = request("nrc-dog-adult", caloric_restriction_percent=25.0)
        got = [outcome(r, "calcium", "low", v) for v in (0.9, 1.0, 1.2, 1.34, 4.0)]
        self.assertEqual(got, ["below-min-50-75", "below-min-75-100", "below-min-75-100",
                               "range-d1", "range-d7"])
        r = request("aafco-dog-adult")
        self.assertEqual(outcome(r, "calcium", "low", 2.0), "range-d2")
        self.assertEqual(outcome(r, "potassium", "low", 2.5), "range-d3")

    def test_rows_with_no_minimum_or_no_range(self):
        r = request("nrc-dog-adult")
        self.assertEqual(outcome(r, "taurine", "low", 0.5), outcomes.NO_MINIMUM)
        self.assertEqual(outcome(r, "taurine", "low", -0.1), "below-min-lt25")
        self.assertEqual(outcome(r, "taurine", "high", 0.0), "range-d1")
        self.assertEqual(outcome(r, "ca-p-ratio", "high", 1.2), outcomes.NO_RANGE)
        self.assertEqual(outcome(r, "ca-p-ratio", "low", 1.2), outcomes.NO_MINIMUM)
        self.assertEqual(outcome(r, "ca-p-ratio", "low", -1.0), outcomes.NO_RANGE)
        self.assertEqual(outcome(r, "water", "low", 900.0), outcomes.NO_MINIMUM)
        self.assertEqual(outcome(r, "water", "high", 900.0), "range-d7")
        self.assertEqual(outcome(r, "protein", "low", None), outcomes.NOT_ENTERED)
        self.assertEqual(outcome(r, "epa", "low", 0.1), outcomes.NOT_BANDED)

    def test_a_maximum_below_the_minimum(self):
        # At 55% the choline minimum (340 / 0.45) is above NRC's 500 mg/Mcal.
        r = request("nrc-dog-adult", caloric_restriction_percent=55.0)
        self.assertGreater(r.minimum("choline"), r.maximum("choline"))
        self.assertEqual(outcome(r, "choline", "low", 800.0), "range-d10")
        self.assertEqual(outcome(r, "choline", "low", 600.0), "below-min-75-100")

    def test_unavailable(self):
        r = request("nrc-kitten", body_weight_kg=1.0)  # no expected mature body weight
        o = outcomes.describe(50.0, "low", r.limits("protein-mbw"))
        self.assertEqual(o, (outcomes.UNAVAILABLE, "mature-weight-needed"))
        self.assertNotEqual(outcome(r, "protein", "low", 50.0), outcomes.UNAVAILABLE)


class TextChecks(unittest.TestCase):
    def applying(self, cid):
        return sorted(rid for rid in DATA["limits"]
                      if cid in outcomes.checks(request(rid, mature_weight_kg=35.0)))

    def test_where_they_apply(self):
        self.assertEqual(self.applying("la-ala-ratio"), [
            "nrc-dog-adult", "nrc-dog-gestation-lactation", "nrc-puppy-14-wk-plus",
            "nrc-puppy-4-14-wk"])
        self.assertEqual(len(self.applying("epa-share-max")), 5)
        self.assertEqual(self.applying("epa-share-range"),
                         ["nrc-dog-adult", "nrc-dog-gestation-lactation"])
        self.assertEqual(self.applying("epa-share-max-dha-only"), ["nrc-cat-adult"])

    def test_results(self):
        fa = {"linoleic-acid": {"low": 10.0, "high": 30.0},
              "alpha-linolenic-acid": {"low": 1.0, "high": 1.0}}
        got = outcomes.checks(request("nrc-dog-adult", entries=fa))["la-ala-ratio"]
        self.assertEqual((got["low"].result, got["high"].result), ("ok", "outside"))
        epa = {"epa-dha": {"low": 0.028, "high": 1.0}, "epa": {"low": 0.004, "high": 0.3}}
        got = outcomes.checks(request("nrc-cat-adult", entries=epa))["epa-share-max-dha-only"]
        self.assertEqual((got["low"].result, got["high"].result),
                         ("dha-below-minimum", "outside"))


class Inputs(unittest.TestCase):
    def test_the_templates_rows_take_entries(self):
        for nid in limits.ROWS:
            self.assertEqual(inputs.check_entry(nid, 0.5, DATA).status, "accept", nid)
        self.assertEqual(inputs.check_entry("protein-dm", 30.0, DATA).status, "reject")
        self.assertEqual(inputs.check_entry("vitamin-d3", 1.0, DATA).status, "reject")


class Models(unittest.TestCase):
    """The independent models, reading the baseline data, agree with every case."""

    def test_values_model(self):
        checked, bad = values_model.run(DATA, values_model.load_cases(VALUES))
        self.assertEqual((checked, bad), (8595, []))

    def test_formulas_model(self):
        cases, cells = formulas_model.load(FORMULAS)
        checked, bad, skipped = formulas_model.run(DATA, cases, cells)
        self.assertEqual((checked, bad, skipped), (51229, [], 53))


class ChangedData(unittest.TestCase):
    """One changed template figure: the core and the independent models still agree, and
    the change shows in the cells that use it."""

    def changed(self, fid, figure):
        data = copy.deepcopy(DATA)
        data["template"][fid]["figure"] = figure
        return data

    def formulas_agree(self, data):
        checked, bad, changed = model_agreement.formulas_agreement(data)
        self.assertEqual(bad, [])
        return changed

    def values_agree(self, data):
        checked, bad, changed = model_agreement.values_agreement(data)
        self.assertEqual(bad, [])
        return changed

    def test_formulas_figures(self):
        for fid, figure in (("la-ala-ratio-high-adult", "20"),
                            ("large-breed-puppy-calcium-min", "3.5"),
                            ("epa-share-max-dha-only", "0.15"),
                            ("carbohydrate-max-fat-energy", "8.5"),
                            ("aafco-energy-density", "3.8")):
            self.assertGreater(self.formulas_agree(self.changed(fid, figure)), 0, fid)

    def test_values_figures(self):
        for fid, figure in (("taurine-max-default", "0.7"), ("mct-max", "18"),
                            ("vitamin-d2-per-vitamin-d", "0.75")):
            self.assertGreater(self.values_agree(self.changed(fid, figure)), 0, fid)

    def test_a_changed_expected_value_is_a_difference(self):
        import json
        cases, _ = run_vectors.load_cases("formulas-testcases.json")
        cases = copy.deepcopy(cases)
        with open(FORMULAS, encoding="utf-8") as f:
            cells = json.load(f)["cells"]
        results = run_vectors.run_file("formulas-testcases.json", cases, DATA, "forward")
        passing = [c for c in cases if results[c["id"]][0] == "pass"]
        number = next(c for c in passing if isinstance(c["outputs"]["C12"], float))
        number["outputs"]["C12"] *= 1 + 2e-12
        text = next(c for c in passing if c["outputs"]["L58"] == "OK")
        text["outputs"]["L58"] = "Not applicable"
        sentence = next(c for c in passing if c["descriptors"].get("AR130"))
        sentence["descriptors"]["AR130"] += " "
        results = run_vectors.run_file("formulas-testcases.json", cases, DATA, "forward")
        for c in (number, text, sentence):
            self.assertEqual(results[c["id"]][0], "difference", c["id"])
        self.assertIn("C12", cells)


if __name__ == "__main__":
    unittest.main(verbosity=1)
