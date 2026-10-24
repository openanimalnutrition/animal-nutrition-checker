"""Phase 5 tests: the Result (schema oan-check-result/1), the verdicts, the conditions and the
data of version 21OCT26b.5 (the Standards tab's notes, the standard-derived minimums, the
known limitations, the conditions and the open minimums).

The steward's answers of 22 Oct 2026 (sean-answers, "Code phase 5") that these tests hold:
deficient below the standard's part of a minimum, including the 31 standard-derived
minimums, and no verdict (open point 6) below the template's own; both tests at 7 decimal
places; the approved wording.

Run: nice -n 10 python3 -I -B tests/test_phase5.py
"""

import copy
import csv
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import real_sheets_check  # noqa: E402
import schema_check  # noqa: E402
from oan import (bands, caveats, energy, interpret, limits, outcomes, result,  # noqa: E402
                 table, validate)

DATA_DIR = os.path.join(ROOT, "data")
D = result.Data(DATA_DIR)
SCHEMA = json.load(open(os.path.join(ROOT, "docs", "result.schema.json"), encoding="utf-8"))
REQS = {r["id"]: r for r in D.tables["requirements"]}
DOG_TYPE = energy.dog_type_labels(D.tables)[3]  # average laboratory or active
CAT_TYPE = energy.cat_type_labels(D.tables)[2]  # lean domestic


def animal_for(rid):
    """Animal facts that give every requirement its energy."""
    a = {"body_weight_kg": 10.0}
    req = REQS[rid]
    if rid in ("nrc-dog-adult", "aafco-dog-adult"):
        a["adult_dog_type"] = DOG_TYPE
    if rid in ("nrc-cat-adult", "aafco-cat-adult"):
        a["adult_cat_type"] = CAT_TYPE
    if "growth" in req["life_stage"] or rid == "nrc-kitten":
        a["mature_weight_kg"] = 30.0 if req["species"] == "canine" else 5.0
    if rid in ("aafco-dog-growth-reproduction", "aafco-dog-growth-large-breed",
               "fediaf-dog-early-growth-reproduction"):
        a["life_stage"] = "Growth: weaning to 4 months"
    if rid == "aafco-cat-growth-reproduction":
        a["life_stage"] = "None"
    if rid == "nrc-dog-gestation-lactation":
        a["life_stage"] = "Gestation: week 5 to birth"
    if rid in ("nrc-cat-peak-lactation", "fediaf-cat-reproduction"):
        a.update(life_stage="3-4 Kittens", lactation_week=3)
    if req["species"] == "feline":
        a["body_weight_kg"] = 4.0
    return a


def run(rid, entries, **animal):
    a = animal_for(rid)
    a.update(animal)
    return result.check(D, {"requirement": rid, "animal": a, "entries": entries})


def edit(path, change):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    with open(path, "w", encoding="utf-8") as f:
        f.write(change(text))


def nutrient(res, nid):
    return next(n for n in res["nutrients"] if n["id"] == nid)


class Data21OCT26b5(unittest.TestCase):
    def test_release(self):
        from oan import release
        r = release.read_release(DATA_DIR)
        self.assertEqual(r["data_version"], "21OCT26b.5")
        self.assertEqual(r["content_sha256"], release.content_hash(DATA_DIR))

    def test_validator_clean(self):
        rep = validate.validate(DATA_DIR)
        self.assertEqual(rep.errors, [])
        self.assertEqual(rep.warnings, [])

    def test_notes(self):
        notes = D.tables["notes"]
        self.assertEqual(len(notes), 301)
        tabs = {"Healthy Dog Cat Reqt Data tab": 0, "Standards tab": 0}
        for n in notes:
            prefix = "DDS template Version 21OCT26b, "
            self.assertTrue(n["origin"].startswith(prefix), n["id"])
            tab, cell = n["origin"][len(prefix):].rsplit(" ", 1)
            tabs[tab] += 1
        self.assertEqual(tabs, {"Healthy Dog Cat Reqt Data tab": 168, "Standards tab": 133})

    def test_standard_derived_minimums(self):
        rules = {}
        for rid, rows in D.tables["limits"].items():
            for nid, row in rows.items():
                rules.setdefault(row["min_rule"], []).append((rid, nid))
        derived = rules["standard-derived"]
        self.assertEqual(len(derived), 31)
        self.assertEqual(sum(1 for rid, _ in derived if rid == "nrc-cat-late-gestation"), 30)
        self.assertIn(("nrc-cat-peak-lactation", "pantothenic-acid"), derived)
        template = sorted(rules["template"])
        self.assertEqual(len(template), 10)
        self.assertEqual(sorted({nid for _, nid in template}), [
            "epa-dha-mbw", "taurine-mbw", "taurine-wet-mbw", "vitamin-k1-mbw"])

    def test_limits_unchanged_by_the_relabel(self):
        base = table.load(os.path.join(HERE, "parity", "data-21OCT26b"))
        for rid in REQS:
            self.assertEqual(table.compute_limits(D.tables, rid),
                             table.compute_limits(base, rid), rid)

    def test_limitations_are_the_status_block(self):
        export = real_sheets_check.load_export()["cells"]["s01"]
        for row in D.tables["limitations"]:
            cell = "A%d" % (139 + int(row["item"]))
            self.assertEqual(row["text"], export[cell][2], cell)
        self.assertEqual(len(D.tables["limitations"]), 10)

    def test_every_condition_and_open_minimum_is_used(self):
        self.assertEqual(len(D.tables["conditions"]), 26)
        self.assertEqual(len(D.tables["open_minimums"]), 15)
        self.assertEqual({int(c["item"]) for c in D.tables["conditions"]}, set(range(1, 11)))

    def test_validator_rejects_bad_conditions(self):
        import shutil
        import tempfile
        tmp = tempfile.mkdtemp()
        try:
            bad = os.path.join(tmp, "data")
            shutil.copytree(DATA_DIR, bad)
            path = os.path.join(bad, "conditions.csv")
            edit(path, lambda t: t.replace(",always,", ",sometimes,", 1).replace(
                "{k}", "{K}").replace("n099 n103 n231", "n099 n999"))
            edit(os.path.join(bad, "open-minimums.csv"), lambda t: t.replace(
                "aafco-cat-adult,linoleic-acid", "aafco-cat-adult,water", 1))
            os.remove(os.path.join(bad, "limitations.csv"))
            rep = validate.validate(bad)
            self.assertTrue(any("limitations.csv" in e and "missing" in e for e in rep.errors))
            shutil.copy(os.path.join(DATA_DIR, "limitations.csv"), bad)
            rep = validate.validate(bad)
            joined = "\n".join(rep.errors)
            self.assertIn("'sometimes' is not one of", joined)
            self.assertIn("{K}: the code fills only", joined)
            self.assertIn("note 'n999' does not exist", joined)
            self.assertIn("water has no minimum of its own under aafco-cat-adult", joined)
        finally:
            shutil.rmtree(tmp)

    def test_baseline_still_validates_without_the_new_files(self):
        rep = validate.validate(os.path.join(HERE, "parity", "data-21OCT26b"))
        self.assertEqual((rep.errors, rep.warnings), ([], []))


class StandardMinimum(unittest.TestCase):
    """Open point 6 as the steward settled it: which part of a minimum is the standard's."""

    def request(self, rid, entries=None, **facts):
        a = animal_for(rid)
        a.update(facts)
        return limits.Request(D.tables, rid, a, entries or {})

    def test_template_minimums_are_not_the_standards(self):
        r = self.request("nrc-dog-adult")
        for nid in ("vitamin-c", "carbohydrate", "fiber-total", "oxalate", "purine",
                    "energy-density"):
            self.assertIsNone(r.standard_minimum(nid), nid)
            self.assertTrue(limits.number(r.minimum(nid)), nid)
        rc = self.request("nrc-cat-adult")
        self.assertIsNone(rc.standard_minimum("vitamin-d2"))
        self.assertIsNone(rc.standard_minimum("taurine-mbw"))
        self.assertEqual(rc.standard_minimum("taurine"), rc.minimum("taurine"))

    def test_standard_derived_count_as_the_standards(self):
        r = self.request("nrc-cat-late-gestation")
        self.assertEqual(r.standard_minimum("pantothenic-acid"), 1.44)
        self.assertEqual(r.standard_minimum("fat-mbw"), r.minimum("fat-mbw"))
        self.assertEqual(r.standard_minimum("pantothenic-acid-mbw"),
                         r.minimum("pantothenic-acid-mbw"))
        self.assertIsNone(r.standard_minimum("vitamin-k1-mbw"))
        self.assertIsNone(r.standard_minimum("taurine-mbw"))
        self.assertEqual(r.standard_minimum("taurine-wet-mbw"), r.minimum("taurine-wet-mbw"))

    def test_raised_minimums_and_rules(self):
        r = self.request("nrc-dog-adult", {"protein": {"low": 40.0}},
                         caloric_restriction_percent=25)
        self.assertAlmostEqual(r.standard_minimum("calcium"), 4 / 3)
        self.assertEqual(r.standard_minimum("arginine"), r.minimum("arginine"))
        self.assertGreater(r.minimum("arginine"), r.raised(r.std("arginine", "min")))
        r = self.request("nrc-puppy-4-14-wk", puppy_body_weight_kg=10.0)
        self.assertEqual(r.standard_minimum("calcium-large-breed-puppy"),
                         r.minimum("calcium-large-breed-puppy"))

    def test_ala_floor_is_the_templates(self):
        r = self.request("nrc-dog-adult")
        self.assertEqual(r.standard_minimum("alpha-linolenic-acid"),
                         r.raised(r.std("alpha-linolenic-acid", "min")))
        # With an LA minimum high enough, the floor LA / 26 is above the standard's ALA.
        data = copy.deepcopy(D.tables)
        data["limits"]["nrc-dog-adult"]["linoleic-acid"]["min"] = "10"
        r = limits.Request(data, "nrc-dog-adult", animal_for("nrc-dog-adult"), {})
        self.assertGreater(r.minimum("alpha-linolenic-acid"),
                           r.standard_minimum("alpha-linolenic-acid"))


class Verdicts(unittest.TestCase):
    def entry(self, res, nid, side="low"):
        return nutrient(res, nid)[side]

    def test_open_point_7_seven_places(self):
        res = run("nrc-dog-adult", {"calcium": 1.3333333}, caloric_restriction_percent=25)
        e = self.entry(res, "calcium")
        self.assertEqual((e["outcome"], e["verdict"]), ("range-d1", None))
        self.assertEqual(e["comparison_to_min"], "at_or_above_min")
        res = run("nrc-dog-adult", {"calcium": 1.3333332}, caloric_restriction_percent=25)
        e = self.entry(res, "calcium")
        self.assertEqual((e["outcome"], e["verdict"]), ("below-min-75-100", "deficient"))

    def test_excess_only_above_authoritative(self):
        res = run("nrc-dog-adult", {"choline": 600, "water": 2000, "vitamin-e": 100})
        self.assertEqual(self.entry(res, "choline")["verdict"], "excess")
        self.assertEqual(self.entry(res, "choline")["comparison_to_max"], "above_max")
        for nid, side in (("water", "high"), ("vitamin-e", "low")):
            e = self.entry(res, nid, side)
            self.assertIsNone(e["verdict"], nid)
            self.assertEqual(e["comparison_to_max"], "above_non_authoritative_max", nid)
        self.assertIn("not excess", self.entry(res, "vitamin-e")["status"])

    def test_aafco_maximum_conditional_with_the_factor(self):
        rid = "aafco-dog-growth-reproduction"
        e = self.entry(run(rid, {"calcium": {"high": 7.0}}), "calcium", "high")
        self.assertEqual(e["verdict"], "excess")
        res = run(rid, {"calcium": {"high": 7.0}, "energy-density": 3.5})
        e = self.entry(res, "calcium", "high")
        self.assertIsNone(e["verdict"])
        self.assertEqual(nutrient(res, "calcium")["max_provenance"], "conditional")
        self.assertIn("dry-matter-basis", [c["id"] for c in nutrient(res, "calcium")["conditions"]])

    def test_open_point_6(self):
        e = self.entry(run("nrc-dog-adult", {"carbohydrate": 10}), "carbohydrate")
        self.assertEqual((e["verdict"], e["open_reason"]), (None, "ig-open-point-6"))
        self.assertEqual(e["comparison_to_min"], "below_template_min")
        res = run("nrc-cat-late-gestation", {"pantothenic-acid": 1.0, "taurine-mbw": 0.02,
                                             "fat-mbw": 2.0, "vitamin-d2": 5})
        self.assertEqual(self.entry(res, "pantothenic-acid")["verdict"], "deficient")
        self.assertEqual(self.entry(res, "fat-mbw")["verdict"], "deficient")
        self.assertEqual(self.entry(res, "taurine-mbw")["open_reason"], "ig-open-point-6")
        self.assertEqual(self.entry(res, "vitamin-d2")["open_reason"], "ig-open-point-6")

    def test_energy_row_has_no_verdict(self):
        e = self.entry(run("nrc-dog-adult", {"energy": 100}), "energy")
        self.assertTrue(e["outcome"].startswith("below-min"))
        self.assertEqual((e["verdict"], e["open_reason"]), (None, "ig-open-point-6"))
        self.assertEqual(e["status"], caveats.STATUS["energy-below-estimate"])
        e = self.entry(run("nrc-dog-adult", {"energy": 100}, caloric_restriction_percent=20),
                       "energy")
        self.assertEqual(e["status"], caveats.STATUS["energy-below-estimate"] + " " +
                         caveats.STATUS["energy-restriction"])

    def test_conditional_line(self):
        e = self.entry(run("fediaf-dog-adult-mer95", {"zinc": 500}), "zinc")
        self.assertEqual(e["status"], "Above a FEDIAF EU legal maximum, which applies only to "
                         "amounts added as additives: conditional, not excess.")

    def test_aafco_open_minimums(self):
        rid = "aafco-dog-growth-reproduction"
        e = self.entry(run(rid, {"sodium": 0.5}), "sodium")
        self.assertEqual(e["verdict"], "deficient")
        e = self.entry(run(rid, {"sodium": 0.85, "energy-density": 3.5}), "sodium")
        self.assertEqual((e["verdict"], e["open_reason"]),
                         (None, "ig-open-point-6-aafco-dry-matter"))
        self.assertEqual(e["comparison_to_min"], "below_min")
        self.assertEqual(e["status"], caveats.STATUS["below-aafco-open-minimum"])
        e = self.entry(run(rid, {"protein": 60, "energy-density": 3.5}), "protein")
        self.assertEqual(e["verdict"], "deficient")

    def test_deficient_and_above_a_maximum(self):
        # FEDIAF dog growth: above 29.6% the raised selenium minimum passes the legal maximum.
        res = run("fediaf-dog-late-growth", {"selenium": 150}, caloric_restriction_percent=40)
        n = nutrient(res, "selenium")
        self.assertGreater(n["minimum"], n["range_high"])
        e = n["low"]
        self.assertEqual(e["verdict"], "deficient")
        self.assertEqual(e["comparison_to_max"], "above_non_authoritative_max")
        self.assertIn("Also above", e["status"])

    def test_open_point_3(self):
        # A negative entry on a row with a maximum and no minimum.
        res = run("nrc-dog-adult", {"water": {"low": -5}})
        e = self.entry(res, "water")
        self.assertEqual((e["outcome"], e["open_reason"]), ("below-min-lt25", "ig-open-point-3"))

    def test_no_minimum_low_entry(self):
        e = self.entry(run("nrc-dog-adult", {"water": {"low": 100}}), "water")
        self.assertEqual(e["outcome"], "no-minimum")
        self.assertIsNone(e["verdict"])

    def test_no_range_high_without_limits(self):
        # The template's range high of a row with no minimum and no maximum is 0 (none x K);
        # the Result gives none, and the bands are unchanged (steward, 22 Oct 2026).
        res = run("aafco-dog-adult", {"protein-mbw": {"low": 65, "high": 70}, "protein": 65,
                                      "water": 100})
        n = nutrient(res, "protein-mbw")
        self.assertEqual((n["minimum"], n["maximum"], n["range_high"], n["max_type"],
                          n["max_provenance"]), (None, None, None, None, None))
        self.assertEqual((n["low"]["outcome"], n["high"]["outcome"]), ("no-minimum", "no-range"))
        self.assertGreater(nutrient(res, "protein")["range_high"], 0)
        self.assertIsNotNone(nutrient(res, "water")["range_high"])
        none = [(rid, x["id"]) for rid in sorted(REQS)
                for x in result.get_limits(D, {"requirement": rid,
                                               "animal": animal_for(rid)})["nutrients"]
                if x["range_high"] == 0 and x["minimum"] is None and x["maximum"] is None]
        self.assertEqual(none, [])

    def test_both_entries_and_summary(self):
        res = run("nrc-dog-adult", {"phosphorus": {"low": 0.9, "high": 1.5}})
        n = nutrient(res, "phosphorus")
        self.assertEqual(n["summary"], "%s to %s" % (n["low"]["outcome"], n["high"]["outcome"]))
        res = run("nrc-dog-adult", {"phosphorus": {"low": 2.0, "high": 1.0}})
        self.assertTrue(any(i["reason"] == "low-above-high" for i in res["input_report"]))


class Conditions(unittest.TestCase):
    def ids(self, res, nid):
        return [c["id"] for c in nutrient(res, nid)["conditions"]]

    def test_age_by_mature_weight(self):
        rid = "fediaf-dog-late-growth"
        self.assertIn("age", self.ids(run(rid, {"calcium": 3}), "calcium"))
        self.assertNotIn("age", self.ids(run(rid, {"calcium": 3}, mature_weight_kg=12),
                                         "calcium"))

    def test_moisture_split(self):
        res = run("fediaf-dog-adult-mer95", {"copper": 3, "selenium": 60})
        self.assertIn("moisture", self.ids(res, "copper"))
        self.assertNotIn("moisture-selenium-fediaf", self.ids(res, "copper"))
        self.assertIn("moisture-selenium-fediaf", self.ids(res, "selenium"))
        self.assertNotIn("moisture-selenium-fediaf",
                         self.ids(run("nrc-dog-adult", {"selenium": 90}), "selenium"))

    def test_legal_maximum(self):
        res = run("fediaf-dog-adult-mer95", {"copper": 3, "calcium": 3})
        self.assertIn("added-as-additive", self.ids(res, "copper"))
        self.assertNotIn("added-as-additive", self.ids(res, "calcium"))

    def test_energy_density(self):
        rid = "aafco-cat-adult"
        self.assertIn("energy-density-not-entered", self.ids(run(rid, {"protein": 70}),
                                                            "protein"))
        res = run(rid, {"protein": 70, "energy-density": 4.5})
        self.assertNotIn("energy-density-not-entered", self.ids(res, "protein"))
        self.assertNotIn("energy-density-not-entered",
                         self.ids(run("nrc-cat-adult", {"protein": 70}), "protein"))

    def test_reference_animal_and_k(self):
        res = run("nrc-kitten", {"calcium-mbw": 1, "calcium": 3})
        self.assertIn("reference-animal", self.ids(res, "calcium-mbw"))
        self.assertNotIn("reference-animal", self.ids(res, "calcium"))
        k = [c for c in nutrient(res, "calcium")["conditions"]
             if c["id"] == "template-choice-range-high"]
        if k:
            self.assertIn("× 4", k[0]["depends_on"])

    def test_limitations_listed_once(self):
        res = run("fediaf-dog-late-growth", {"calcium": 3, "copper": 3})
        items = [l["item"] for l in res["limitations"]]
        self.assertEqual(items, sorted(set(items)))
        used = {c["limitation"] for n in res["nutrients"] for c in n["conditions"]}
        self.assertEqual(set(items), used)


class Requests(unittest.TestCase):
    def test_shape_errors(self):
        for bad in ([], {"requirement": "x", "colour": 1}, {"entries": []},
                    {"entries": {"calcium": {"mid": 1}}}, {"entries": {"calcium": {}}},
                    {"animal": {"age": 3}}, {"subject": "food"}, {"entries": {"calcium": None}}):
            with self.assertRaises(result.RequestError, msg=repr(bad)):
                result.check(D, bad)

    def test_rejected_inputs_are_reported_and_not_used(self):
        res = result.check(D, {"requirement": "nrc-dog-adult",
                               "animal": {"body_weight_kg": 500, "adult_dog_type": DOG_TYPE},
                               "entries": {"calcium": "1.2", "energy-density": 12,
                                           "protein-mbw": {"low": True}}})
        statuses = {(i["input"], i["status"]) for i in res["input_report"]}
        self.assertIn(("animal.body_weight_kg", "rejected"), statuses)
        self.assertIn(("entries.calcium", "rejected"), statuses)
        self.assertIn(("entries.energy-density", "rejected"), statuses)
        self.assertIn(("entries.protein-mbw.low", "rejected"), statuses)
        self.assertEqual(res["nutrients"], [])
        self.assertNotIn("body_weight_kg", res["inputs"]["normalized"]["animal"])

    def test_requirement_by_name_or_id(self):
        a = result.check(D, {"requirement": "nrc-dog-adult", "entries": {"calcium": 1}})
        b = result.check(D, {"requirement": "NRC RA Dog Maintenance", "entries": {"calcium": 1}})
        self.assertEqual(a["nutrients"], b["nutrients"])
        self.assertEqual(a["requirement"]["id"], "nrc-dog-adult")

    def test_missing_facts(self):
        res = result.check(D, {"requirement": "nrc-dog-adult",
                               "entries": {"calcium-mbw": 1, "calcium": 1}})
        missing = [i["input"] for i in res["input_report"] if i["status"] == "missing"]
        self.assertEqual(missing, ["animal.body_weight_kg"])
        self.assertEqual(nutrient(res, "calcium")["low"]["outcome"], "range-d1")
        res = result.check(D, {"entries": {"calcium": 1}})
        self.assertIn("requirement", [i["input"] for i in res["input_report"]])

    def test_bare_number_placement(self):
        res = run("nrc-dog-adult", {"water": 1000, "calcium": 1})
        self.assertIsNotNone(nutrient(res, "water")["high"])
        self.assertIsNotNone(nutrient(res, "calcium")["low"])

    def test_subject_is_a_label(self):
        a = run("nrc-dog-adult", {"phosphorus": {"low": 0.5, "high": 0.9}})
        r = dict(a["inputs"]["submitted"], subject="requirement range")
        b = result.check(D, r)
        self.assertEqual(b["subject"], "requirement range")
        self.assertEqual(a["nutrients"], b["nutrients"])


class MBWRows(unittest.TestCase):
    """MBW rows are per Mcal; the requirement per kg BW^n a day and the conversion are given
    (steward, 22 Oct 2026, after the GUI review)."""

    def test_unit_and_conversion(self):
        res = run("nrc-dog-adult", {"calcium-mbw": 8, "fat-mbw": 30},
                  body_weight_kg=35.0, energy_intake_kcal_per_day=950.0)
        ca = nutrient(res, "calcium-mbw")
        self.assertEqual(ca["unit"], "g/Mcal")
        self.assertEqual(ca["mbw"]["unit"], "g/kg BW^0.75")
        self.assertEqual(ca["mbw"]["minimum"], 0.13)
        self.assertIsNone(ca["mbw"]["maximum"])
        self.assertEqual((ca["mbw"]["energy_kcal_per_day"], ca["mbw"]["body_weight_kg"]),
                         (950.0, 35.0))
        self.assertIn("0.13 g/kg BW^0.75 (1.96911363883933 g/Mcal)", ca["mbw"]["text"])
        fat = nutrient(res, "fat-mbw")
        self.assertEqual((fat["mbw"]["minimum"], fat["mbw"]["maximum"]), (1.8, 10.8))
        self.assertIsNone(nutrient(run("nrc-dog-adult", {"calcium": 1}), "calcium")["mbw"])

    def test_cats_and_describe_inputs(self):
        res = run("nrc-cat-adult", {"taurine-mbw": 0.5})
        self.assertEqual(nutrient(res, "taurine-mbw")["mbw"]["unit"], "g/kg BW^0.67")
        items = {i["id"]: i for i in result.describe_inputs(D)["entries"]}
        self.assertEqual(items["calcium-mbw"]["unit"], "g/Mcal")
        self.assertEqual(items["calcium-mbw"]["description"], caveats.MBW_ENTRY_TEXT)

    def test_no_conversion_without_energy(self):
        res = result.check(D, {"requirement": "nrc-dog-adult", "entries": {"calcium-mbw": 1}})
        self.assertIsNone(nutrient(res, "calcium-mbw")["mbw"])


class NoMaximum(unittest.TestCase):
    """When the requirement sets no maximum of its own, the result says so (steward, 22 Oct
    2026: AI readers brought in other standards' or life stages' limits from memory)."""

    def test_line(self):
        res = run("nrc-dog-adult", {"calcium-mbw": 8, "calcium": 2},
                  body_weight_kg=35.0, energy_intake_kcal_per_day=950.0)
        text = ("NRC RA Dog Maintenance sets no calcium maximum, per Mcal or per kg BW^0.75; "
                "limits from other standards or life stages do not apply to this check.")
        for nid in ("calcium", "calcium-mbw"):
            self.assertEqual(nutrient(res, nid)["requirement_maximum"],
                             {"set": False, "text": text})
        self.assertTrue(nutrient(res, "calcium-mbw")["low"]["status"].endswith(text))
        self.assertNotIn(text, nutrient(res, "calcium")["low"]["status"])  # within the range

    def test_standards_own_maximum(self):
        for rid in ("aafco-dog-adult", "fediaf-dog-adult-mer95"):
            n = nutrient(run(rid, {"calcium": 8}), "calcium")
            self.assertEqual(n["requirement_maximum"], {"set": True, "text": None}, rid)
        # A template estimate (EST) is not the standard's own maximum.
        n = nutrient(run("nrc-dog-adult", {"iodine": 1}), "iodine")
        self.assertTrue(n["requirement_maximum"]["set"])  # NRC's own iodine SUL
        n = nutrient(run("aafco-dog-adult", {"sodium": 1}), "sodium")
        self.assertEqual(n["requirement_maximum"]["text"],
                         "AAFCO Dog Maintenance sets no sodium maximum, per Mcal; limits from "
                         "other standards or life stages do not apply to this check.")
        self.assertIsNone(nutrient(run("nrc-dog-adult", {"energy": 900}), "energy")[
            "requirement_maximum"])


class Notes(unittest.TestCase):
    def test_get_notes(self):
        res = result.get_notes(D, {"ids": ["n231", "n005", "n231"]})
        self.assertEqual(list(res)[:2], ["schema", "caveats"])
        self.assertEqual([n["id"] for n in res["note_texts"]], ["n231", "n005"])
        self.assertTrue(res["note_texts"][0]["origin"].endswith("Standards tab B63"))
        self.assertEqual(schema_check.errors(res, SCHEMA), [])
        for bad in ({"ids": ["n999"]}, {"ids": []}, {"ids": ["n001"] * 51}, {"id": ["n001"]},
                    {"ids": "n001"}):
            with self.assertRaises(result.RequestError, msg=repr(bad)):
                result.get_notes(D, bad)

    def test_entries_explained(self):
        res = result.describe_inputs(D)
        self.assertIn(caveats.ENTRIES_TEXT, res["request"]["entries"])
        self.assertEqual(res["entries"][0]["description"], caveats.ENERGY_ENTRY_TEXT)


class TextChecks(unittest.TestCase):
    def test_texts(self):
        res = run("nrc-dog-adult", {"linoleic-acid": 3.0, "alpha-linolenic-acid": 0.01})
        c = next(c for c in res["checks"] if c["id"] == "la-ala-ratio")
        self.assertEqual(c["low"]["result"], "outside")
        self.assertIn("NRC's advised ratio", c["low"]["text"])
        self.assertIn("not a verdict", c["status"])
        self.assertEqual(c["high"], {"result": "not-entered", "text": None})
        res = run("nrc-cat-late-gestation", {"epa-dha": 0.02, "epa": {"high": 0.019}})
        c = next(c for c in res["checks"] if c["id"] == "epa-share-max")
        self.assertEqual(c["high"]["text"],
                         "EPA is above 60% of EPA + DHA, NRC's advised maximum share.")

    def test_dha_not_compared_caveat(self):
        data = copy.deepcopy(D.tables)
        row = data["limits"]["nrc-cat-adult"]["epa-dha"]
        row["min"] = "none"
        row["min_unit"] = ""
        ratio = data["limits"]["nrc-cat-adult"]["la-aa-to-epa-dha-ratio"]
        ratio.update(max="30", max_rule="printed", max_type="CALC", max_source="test")
        d = copy.copy(D)
        d.tables = data
        res = result.check(d, {"requirement": "nrc-cat-adult",
                               "animal": animal_for("nrc-cat-adult"),
                               "entries": {"epa-dha": 0.05, "epa": 0.005}})
        c = next(c for c in res["checks"] if c["id"] == "epa-share-max-dha-only")
        self.assertEqual(c["caveat"], caveats.DHA_NOT_COMPARED)


def grid_requests():
    """Every requirement, every enterable row, at values around its limits."""
    for rid in sorted(REQS):
        lim_result = result.get_limits(D, {"requirement": rid, "animal": animal_for(rid)})
        entries = {}
        for n in lim_result["nutrients"]:
            if n["limits_unavailable"] is not None:
                continue
            lo = n["minimum"] if n["minimum"] is not None else 0.0
            hi = n["range_high"] if n["range_high"] is not None else lo * 2 + 1
            for i, value in enumerate((lo * 0.5, lo, (lo + hi) / 2, hi, hi * 1.5 + 0.1)):
                entries.setdefault(i, {})[n["id"]] = {"low": value, "high": value}
        for i in sorted(entries):
            if "energy-density" in entries[i]:
                v = entries[i]["energy-density"]["low"]
                entries[i]["energy-density"] = {"low": min(max(v, 2), 9),
                                                "high": min(max(v, 2), 9)}
            yield rid, entries[i]


class Contract(unittest.TestCase):
    """The plan's contract tests that need no server: the caveats in every result, no excess
    above a non-authoritative maximum, verdict and band agreement, the schema, determinism."""

    @classmethod
    def setUpClass(cls):
        cls.results = [(rid, run(rid, entries)) for rid, entries in grid_requests()]

    def test_schema_keywords_known(self):
        self.assertLessEqual(schema_check.keywords(SCHEMA), schema_check.KEYWORDS)

    def test_every_result_conforms(self):
        others = [result.list_requirements(D), result.describe_inputs(D),
                  result.get_limits(D, {"requirement": "nrc-kitten",
                                        "animal": animal_for("nrc-kitten")})]
        for res in [r for _, r in self.results] + others:
            self.assertEqual(schema_check.errors(res, SCHEMA), [], res["tool"])

    def test_caveats_first_everywhere(self):
        expected = [cid for cid, _ in caveats.CAVEATS]
        others = [result.list_requirements(D), result.describe_inputs(D)]
        for res in [r for _, r in self.results] + others:
            self.assertEqual(list(res)[:2], ["schema", "caveats"])
            self.assertEqual([c["id"] for c in res["caveats"]], expected)
            self.assertIn(D.version, res["caveats"][0]["text"])

    def test_verdicts(self):
        counts = {"deficient": 0, "excess": 0, "open": 0}
        for rid, res in self.results:
            for n in res["nutrients"]:
                for side in ("low", "high"):
                    e = n[side]
                    if e is None:
                        continue
                    where = (rid, n["id"], side, e["value"])
                    self.assertEqual(e["verdict_status"], "proposed, pending ratification")
                    if e["verdict"] == "excess":
                        counts["excess"] += 1
                        self.assertEqual(n["max_provenance"], "authoritative", where)
                        # A low entry on a row with no minimum reads "no minimum" in the
                        # template; above an authoritative maximum it is still excess.
                        self.assertIn(e["outcome"], ("range-d10", "no-minimum"), where)
                        self.assertEqual(e["comparison_to_max"], "above_max", where)
                    if n["max_provenance"] != "authoritative":
                        self.assertNotEqual(e["verdict"], "excess", where)
                        self.assertNotEqual(e["comparison_to_max"], "above_max", where)
                    if e["verdict"] == "deficient":
                        counts["deficient"] += 1
                        self.assertTrue(e["outcome"].startswith("below-min"), where)
                        self.assertEqual(e["comparison_to_min"], "below_min", where)
                    if e["outcome"].startswith("range-") or e["outcome"] in (
                            "no-range", "no-minimum"):
                        self.assertIsNone(e["open_reason"], where)
                        self.assertNotEqual(e["verdict"], "deficient", where)
                    if e["open_reason"]:
                        counts["open"] += 1
                        self.assertIsNone(e["verdict"] if e["verdict"] != "excess" else None)
                    if e["outcome"] not in ("not-banded",):
                        self.assertTrue(e["status"], where)
        for k, v in counts.items():
            self.assertGreater(v, 50, k)

    def test_notes_resolve(self):
        for _, res in self.results:
            ids = res["notes"]["general"] + res["notes"]["requirement"]
            for n in res["nutrients"]:
                ids += n["notes"]
                for c in n["conditions"]:
                    ids += c["notes"]
            for c in res["checks"]:
                ids += c["notes"]
            for l in res["limitations"]:
                ids += l["notes"]
            for i in ids:
                self.assertIn(i, D.notes)

    def test_same_request_same_bytes(self):
        rid, entries = next(grid_requests())
        a = result.to_json(run(rid, entries))
        b = result.to_json(run(rid, copy.deepcopy(entries)))
        self.assertEqual(a, b)
        self.assertNotIn("NaN", a)
        self.assertEqual(json.loads(a)["schema"], "oan-check-result/1")


class Wording(unittest.TestCase):
    """The approved wording (22 Oct 2026) is what the code says."""

    def test_caveats(self):
        texts = dict(caveats.CAVEATS)
        self.assertTrue(texts["non_normative_reference"].startswith(
            "Reference implementation, not a ratified standard."))
        self.assertIn("sells nutritional supplements", texts["steward_disclosed_interest"])
        self.assertTrue(texts["not_a_safety_or_compliance_assessment"].startswith(
            "Not a safety or compliance assessment, and not veterinary advice."))
        self.assertEqual(len(texts), 4)


if __name__ == "__main__":
    unittest.main(verbosity=1)
