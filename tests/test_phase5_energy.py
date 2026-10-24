"""The steward's energy rules (23 Oct 2026; proposed, pending ratification): the reference
energy, the energy fed, MBW minimums at the energy fed and MBW maximums at the reference
energy, the energy factor on rows with no MBW minimum, the optional optimal body weight, and
the floor of 10% of the reference. The template's own rules stay for the parity check
(limits.Request template_rules; docs/parity-21OCT26b.md).

The steward's decisions these tests hold (23 Oct 2026):
- the minimums rise so that the daily amount of each nutrient stays what the standard
  expected at the current body weight; maximums do not change per Mcal;
- the reference is the standard's own basis: NRC's average adult dog (130 kcal x kg BW^0.75)
  for NRC and AAFCO dogs, NRC's lean adult cat (100 kcal x kg BW^0.67) for NRC and AAFCO
  cats, FEDIAF's stated MER, else the requirement's own equation; the adult types set only
  the energy fed;
- an entered intake is the energy fed (a restriction entered with it says how far below the
  need it is), and an intake below the reference raises the minimums of rows with no MBW
  minimum;
- an optimal body weight means the energy at that weight is fed (cats: NRC's lean equation);
- an energy fed below 10% of the reference is rejected.

Run: nice -n 10 python3 -I -B tests/test_phase5_energy.py
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import schema_check  # noqa: E402
from oan import caveats, energy, limits, result  # noqa: E402

D = result.Data(os.path.join(ROOT, "data"))
SCHEMA = json.load(open(os.path.join(ROOT, "docs", "result.schema.json"), encoding="utf-8"))
DOG = dict(zip(("none", "inactive", "older", "average", "young", "terriers", "great-danes"),
               energy.dog_type_labels(D.tables)))
CAT = dict(zip(("none", "overweight", "lean"), energy.cat_type_labels(D.tables)))
PROTEIN_DOG = 3.28  # NRC 2006 adult dog protein RA, g/kg BW^0.75 a day
TOL = 1e-12


def request(rid, entries=None, template_rules=False, **facts):
    return limits.Request(D.tables, rid, facts, entries or {}, template_rules=template_rules)


def run(rid, entries=None, **animal):
    return result.check(D, {"requirement": rid, "animal": animal, "entries": entries or {}})


def nutrient(res, nid):
    return next(n for n in res["nutrients"] if n["id"] == nid)


class Close(unittest.TestCase):
    def close(self, a, b):
        self.assertAlmostEqual(a / b, 1.0, delta=TOL, msg="%r != %r" % (a, b))


class ReferenceEnergy(Close):
    def test_standards_basis_not_the_type(self):
        r = request("nrc-dog-adult", body_weight_kg=30.0, adult_dog_type=DOG["inactive"])
        self.assertEqual(r.energy_reference.kcal, 130 * 30 ** 0.75)
        self.assertEqual(r.energy_fed.kcal, 95 * 30 ** 0.75)
        r = request("aafco-dog-adult", body_weight_kg=30.0)
        self.assertEqual(r.energy_reference.kcal, 130 * 30 ** 0.75)
        self.assertEqual(r.energy_fed.reason, "adult-dog-type-needed")
        r = request("aafco-cat-adult", body_weight_kg=6.0, adult_cat_type=CAT["overweight"])
        self.assertEqual(r.energy_reference.kcal, 100 * 6 ** 0.67)
        self.assertEqual(r.energy_fed.kcal, 130 * 6 ** 0.4)
        r = request("fediaf-dog-adult-mer95", body_weight_kg=30.0)
        self.assertEqual(r.energy_reference.kcal, r.energy_fed.kcal)
        self.assertEqual(r.energy_reference.kcal, 95 * 30 ** 0.75)

    def test_life_stage_equation_without_the_type(self):
        facts = dict(body_weight_kg=30.0, life_stage="Gestation: week 5 to birth",
                     adult_dog_type=DOG["inactive"])
        r = request("nrc-dog-gestation-lactation", **facts)
        self.assertEqual(r.energy_reference.kcal, 130 * 30 ** 0.75 + 26 * 30)
        self.assertEqual(r.energy_fed.kcal, 95 * 30 ** 0.75 + 26 * 30)
        r = request("nrc-puppy-4-14-wk", body_weight_kg=5.0, mature_weight_kg=30.0)
        self.assertEqual(r.energy_reference, r.energy_requirement)

    def test_basis_text(self):
        f = run("aafco-dog-adult", body_weight_kg=30.0, adult_dog_type=DOG["average"])["factors"]
        self.assertIn("130 kcal x kg BW^0.75", f["reference_energy_basis"])
        self.assertIn("AAFCO states no energy basis", f["reference_energy_basis"])
        f = run("nrc-cat-adult", body_weight_kg=4.0, adult_cat_type=CAT["lean"])["factors"]
        self.assertIn("NRC's lean adult cat energy, 100 kcal x kg BW^0.67",
                      f["reference_energy_basis"])
        f = run("fediaf-cat-adult-mer75", body_weight_kg=4.0)["factors"]
        self.assertIn("75 kcal x kg BW^0.67", f["reference_energy_basis"])
        f = run("nrc-puppy-4-14-wk", body_weight_kg=5.0, mature_weight_kg=30.0)["factors"]
        self.assertEqual(f["reference_energy_basis"], caveats.REFERENCE_BASIS["life-stage"])
        self.assertEqual(f["energy_rules"], caveats.ENERGY_RULES_TEXT)


class MBWRowsAtTheEnergyFed(Close):
    """Item 1: the restriction reaches the MBW minimums; the daily amount stays the need."""

    def daily(self, r, nid="protein-mbw"):
        return r.minimum(nid) * r.energy_fed.kcal / 1000

    def test_restriction_on_the_equation(self):
        need = PROTEIN_DOG * 30 ** 0.75
        for kind in ("inactive", "average", "young"):
            r = request("nrc-dog-adult", body_weight_kg=30.0, adult_dog_type=DOG[kind],
                        caloric_restriction_percent=20)
            self.close(self.daily(r), need)
            self.close(r.energy_fed.kcal, r.energy_requirement.kcal * 0.8)
        # The template's rules convert at the energy before the cut: 80% of the need.
        t = request("nrc-dog-adult", template_rules=True, body_weight_kg=30.0,
                    adult_dog_type=DOG["inactive"], caloric_restriction_percent=20)
        self.close(t.minimum("protein-mbw") * t.energy.kcal * 0.8 / 1000, need * 0.8)

    def test_intake_is_the_energy_fed(self):
        r = request("nrc-dog-adult", body_weight_kg=30.0, adult_dog_type=DOG["average"],
                    energy_intake_kcal_per_day=1000.0, caloric_restriction_percent=10)
        self.assertEqual(r.energy_fed.kcal, 1000.0)
        self.close(self.daily(r), PROTEIN_DOG * 30 ** 0.75)

    def test_methionine_at_half_the_average_energy(self):
        # A 20 kg dog fed 529.6 kcal/day: 0.11 g methionine per kg BW^0.75 a day is 1.04 g.
        r = request("nrc-dog-adult", body_weight_kg=20.0, adult_dog_type=DOG["average"],
                    energy_intake_kcal_per_day=529.6)
        self.close(self.daily(r, "methionine-mbw"), 0.11 * 20 ** 0.75)

    def test_fat_mbw_not_raised(self):
        # As the per-Mcal fat row, the fat MBW minimum takes no restriction or optimal body
        # weight: it is converted at the energy used (steward, 23 Oct 2026).
        base = dict(body_weight_kg=20.0, adult_dog_type=DOG["inactive"])
        plain = request("nrc-dog-adult", **base)
        for v in (dict(caloric_restriction_percent=20), dict(optimal_body_weight_kg=15.0)):
            r = request("nrc-dog-adult", **dict(base, **v))
            t = request("nrc-dog-adult", template_rules=True, **dict(base, **v))
            self.assertEqual(r.minimum("fat-mbw"), plain.minimum("fat-mbw"), v)
            self.assertEqual(r.minimum("fat-mbw"), t.minimum("fat-mbw"), v)
            self.assertEqual(r.minimum("fat"), plain.minimum("fat"), v)
            self.assertGreater(r.minimum("protein-mbw"), plain.minimum("protein-mbw"), v)
        r = request("nrc-dog-adult", energy_intake_kcal_per_day=500.0, **base)
        self.assertEqual(r.mbw_energy("minimum", "fat-mbw").kcal, 500.0)
        res = run("nrc-dog-adult", caloric_restriction_percent=20,
                  entries={"fat-mbw": {"low": 20}}, **base)
        text = nutrient(res, "fat-mbw")["mbw"]["text"]
        self.assertIn(caveats.MBW_MINIMUM_ENERGY["used"], text)


class MaximumsPerMcal(Close):
    """MBW maximums at the reference energy: never moved by a restriction, an intake, the
    type or an optimal body weight (steward, 23 Oct 2026)."""

    def test_unchanged(self):
        base = dict(body_weight_kg=30.0, adult_dog_type=DOG["average"])
        ref = request("nrc-dog-adult", **base)
        variants = [dict(caloric_restriction_percent=20),
                    dict(energy_intake_kcal_per_day=1000.0),
                    dict(adult_dog_type=DOG["inactive"]), dict(optimal_body_weight_kg=22.0)]
        for v in variants:
            r = request("nrc-dog-adult", **dict(base, **v))
            for nid in ("fat-mbw", "linoleic-acid-mbw", "vitamin-d-mbw", "sodium-mbw"):
                self.assertEqual(r.maximum(nid), ref.maximum(nid), (v, nid))
        # The reference energy cannot be computed (lactation after week 4): the intake.
        r = request("nrc-dog-gestation-lactation", body_weight_kg=30.0,
                    energy_intake_kcal_per_day=3000.0, life_stage="Lactation: bitch",
                    lactation_week=5, puppies_nursing=4)
        self.assertIsNone(r.energy_reference.kcal)
        self.assertEqual(r.mbw_energy("maximum").kcal, 3000.0)

    def test_per_mcal_rows_not_raised(self):
        r = request("aafco-dog-adult", body_weight_kg=30.0, adult_dog_type=DOG["inactive"],
                    caloric_restriction_percent=40)
        t = request("aafco-dog-adult", template_rules=True, body_weight_kg=30.0,
                    adult_dog_type=DOG["inactive"], caloric_restriction_percent=40)
        self.assertEqual(r.maximum("vitamin-a"), t.maximum("vitamin-a"))


class CholineMaximum(Close):
    """The choline maximum is at least 1.1 x the higher choline minimum (steward, 23 Oct
    2026)."""

    def test_raised_above_the_minimum(self):
        base = dict(body_weight_kg=20.0, adult_dog_type=DOG["inactive"])
        for r in (0, 10, 20):
            q = request("nrc-dog-adult", caloric_restriction_percent=r, **base)
            least = max(q.minimum("choline"), q.minimum("choline-mbw"))
            lim = q.limits("choline")
            self.close(lim.maximum, least * 1.1)
            self.assertEqual(lim.max_code, "TPL")
        q = request("nrc-puppy-14-wk-plus", body_weight_kg=20.0, mature_weight_kg=35.0,
                    caloric_restriction_percent=35)
        self.close(q.maximum("choline"), q.minimum("choline") * 1.1)

    def test_presumed_safe_maximum_otherwise(self):
        q = request("nrc-dog-adult", body_weight_kg=20.0, adult_dog_type=DOG["average"])
        lim = q.limits("choline")
        self.assertEqual((lim.maximum, lim.max_code), (500.0, "PSM"))
        t = request("nrc-dog-adult", template_rules=True, body_weight_kg=20.0,
                    adult_dog_type=DOG["inactive"], caloric_restriction_percent=20)
        self.assertEqual(t.maximum("choline"), 500.0)
        self.assertIsNone(request("nrc-cat-adult", body_weight_kg=4.0,
                                  adult_cat_type=CAT["lean"]).maximum("choline"))

    def test_not_excess(self):
        # Under the presumed safe maximum 540 would be excess; with the raised maximum it is
        # within the range, and a value above that maximum is not excess.
        facts = dict(body_weight_kg=20.0, adult_dog_type=DOG["inactive"],
                     caloric_restriction_percent=10)
        low = nutrient(run("nrc-dog-adult", {"choline": {"low": 540}}, **facts), "choline")
        self.assertEqual(low["max_provenance"], "template-set")
        self.assertEqual(low["low"]["comparison_to_max"], "not_above_max")
        high = nutrient(run("nrc-dog-adult", {"choline": {"low": 600}}, **facts), "choline")
        self.assertEqual(high["low"]["comparison_to_max"], "above_non_authoritative_max")
        self.assertNotEqual(high["low"]["verdict"], "excess")


class EnergyFactor(Close):
    """Rows with no MBW minimum: x the reference / the energy fed, at least 1 and at least the
    restriction's factor."""

    def test_aafco_types(self):
        ref = 130 * 30 ** 0.75
        for kind, fed in (("inactive", 95), ("older", 105), ("average", 130), ("young", 140)):
            r = request("aafco-dog-adult", body_weight_kg=30.0, adult_dog_type=DOG[kind])
            factor = max(1.0, ref / (fed * 30 ** 0.75))
            self.close(r.minimum("protein"), 45 * factor)
        r = request("aafco-dog-adult", body_weight_kg=30.0, adult_dog_type=DOG["young"],
                    caloric_restriction_percent=20)
        self.close(r.minimum("protein"), 45 * max(1.25, ref / (140 * 30 ** 0.75 * 0.8)))
        r = request("aafco-dog-adult", body_weight_kg=30.0, adult_dog_type=DOG["terriers"],
                    caloric_restriction_percent=20)
        self.close(r.minimum("protein"), 45 * 1.25)  # the restriction's factor is the floor

    def test_intake_below_the_reference(self):
        r = request("aafco-dog-adult", body_weight_kg=30.0, adult_dog_type=DOG["average"],
                    energy_intake_kcal_per_day=1000.0)
        self.close(r.minimum("protein"), 45 * (130 * 30 ** 0.75) / 1000)
        r = request("aafco-dog-adult", body_weight_kg=30.0, adult_dog_type=DOG["average"],
                    energy_intake_kcal_per_day=3000.0)
        self.assertEqual(r.minimum("protein"), 45.0)  # never lowered

    def test_rows_with_mbw_figures_keep_the_restriction_factor(self):
        r = request("nrc-dog-adult", body_weight_kg=30.0, adult_dog_type=DOG["inactive"],
                    energy_intake_kcal_per_day=1000.0, caloric_restriction_percent=20)
        self.close(r.minimum("protein"), 25 * 1.25)
        self.assertGreater(r.minimum("protein-mbw"), r.minimum("protein"))

    def test_type_not_chosen_counts_as_one(self):
        r = request("aafco-dog-adult", body_weight_kg=30.0)
        self.assertIsNone(r.energy_factor)
        self.assertEqual(r.minimum("protein"), 45.0)

    def test_puppy_calcium(self):
        facts = dict(body_weight_kg=8.0, mature_weight_kg=40.0, puppy_body_weight_kg=8.0)
        for extra in ({}, dict(caloric_restriction_percent=20),
                      dict(energy_intake_kcal_per_day=1200.0, caloric_restriction_percent=20)):
            s = request("nrc-puppy-4-14-wk", **dict(facts, **extra))
            t = request("nrc-puppy-4-14-wk", template_rules=True, **dict(facts, **extra))
            self.close(s.minimum("calcium-large-breed-puppy"),
                       t.minimum("calcium-large-breed-puppy"))
        s = request("nrc-puppy-4-14-wk", energy_intake_kcal_per_day=300.0,
                    **dict(facts, puppy_body_weight_kg=None))
        self.assertEqual(s.energy_factor, 1.0)
        self.assertEqual(s.minimum("calcium-large-breed-puppy"), 3.0)

    def test_adult_maintenance_only(self):
        # Growth, gestation and lactation keep their per-Mcal minimums at any intake; a
        # restriction still raises them (steward, 23 Oct 2026).
        for rid, facts in (("nrc-puppy-14-wk-plus", dict(body_weight_kg=20.0,
                                                          mature_weight_kg=35.0)),
                           ("aafco-dog-growth-large-breed", dict(
                               body_weight_kg=20.0, life_stage="Growth: 4 months to adult size")),
                           ("nrc-dog-gestation-lactation", dict(
                               body_weight_kg=20.0, life_stage="Gestation: week 5 to birth"))):
            eq = request(rid, **facts).energy_requirement.kcal
            r = request(rid, energy_intake_kcal_per_day=eq * 0.65, **facts)
            t = request(rid, template_rules=True, energy_intake_kcal_per_day=eq * 0.65, **facts)
            self.assertEqual(r.energy_factor, 1.0, rid)
            self.assertEqual(r.minimum("calcium"), t.minimum("calcium"), rid)
            r = request(rid, caloric_restriction_percent=20, **facts)
            self.close(r.minimum("calcium"), t.minimum("calcium") * 1.25)

    def test_template_rules_unchanged(self):
        t = request("aafco-dog-adult", template_rules=True, body_weight_kg=30.0,
                    adult_dog_type=DOG["inactive"])
        self.assertEqual(t.minimum("protein"), 45.0)
        self.assertEqual(t.energy_factor, 1.0)


class OptimalBodyWeight(Close):
    def test_dog(self):
        r = request("nrc-dog-adult", body_weight_kg=30.0, optimal_body_weight_kg=22.0,
                    adult_dog_type=DOG["average"])
        self.assertEqual(r.optimal_status, "used")
        self.assertEqual(r.energy_fed.kcal, 130 * 22 ** 0.75)
        self.close(r.minimum("protein-mbw") * r.energy_fed.kcal / 1000, PROTEIN_DOG * 30 ** 0.75)
        a = request("aafco-dog-adult", body_weight_kg=30.0, optimal_body_weight_kg=22.0,
                    adult_dog_type=DOG["average"], caloric_restriction_percent=20)
        self.close(a.energy_fed.kcal, 130 * 22 ** 0.75 * 0.8)
        self.close(a.minimum("protein"), 45 * (30 / 22) ** 0.75 / 0.8)

    def test_cat_lean_at_the_optimal_weight(self):
        r = request("nrc-cat-adult", body_weight_kg=6.0, optimal_body_weight_kg=4.5,
                    adult_cat_type=CAT["overweight"])
        self.assertEqual(r.energy_fed.kcal, 100 * 4.5 ** 0.67)

    def test_not_used(self):
        cases = [("nrc-dog-adult", dict(optimal_body_weight_kg=30.0), "not-below-current"),
                 ("nrc-dog-adult", dict(optimal_body_weight_kg=22.0,
                                        energy_intake_kcal_per_day=1000.0), "intake-entered"),
                 ("nrc-puppy-4-14-wk", dict(optimal_body_weight_kg=4.0, mature_weight_kg=30.0),
                  "not-adult")]
        for rid, extra, status in cases:
            r = request(rid, **dict(dict(body_weight_kg=30.0 if rid == "nrc-dog-adult" else 5.0,
                                         adult_dog_type=DOG["average"]), **extra))
            self.assertEqual(r.optimal_status, status)
            self.assertNotEqual(r.energy_fed.kcal, 130 * 22 ** 0.75)
        # No current body weight entered (steward, 24 Oct 2026).
        res = run("nrc-dog-adult", {}, optimal_body_weight_kg=22.0, adult_dog_type=DOG["average"])
        self.assertEqual(res["factors"]["optimal_body_weight"],
                         {"status": "no-current-weight",
                          "text": "Not used: no current body weight is entered."})
        self.assertEqual(schema_check.errors(res, SCHEMA), [])

    def test_result_and_inputs(self):
        res = run("nrc-dog-adult", {"energy": 1321, "protein-mbw": 40}, body_weight_kg=30.0,
                  optimal_body_weight_kg=22.0, adult_dog_type=DOG["average"])
        f = res["factors"]
        self.assertEqual(f["optimal_body_weight"]["status"], "used")
        self.assertEqual(f["energy_fed_is"], "the energy at the optimal body weight")
        self.assertIn(caveats.STATUS["energy-optimal-weight"],
                      nutrient(res, "energy")["low"]["status"])
        # A row with one limit names its energy, in whole kcal/day (steward, 24 Oct 2026):
        # 130 x 22^0.75 = 1320.6.
        self.assertIn("converted to g/Mcal at the energy fed (1321 kcal/day) and a current body "
                      "weight of 30 kg.", nutrient(res, "protein-mbw")["mbw"]["text"])
        self.assertEqual(schema_check.errors(res, SCHEMA), [])
        reads = {r["id"]: r["reads"] for r in result.list_requirements(D)["requirements"]}
        self.assertIn("optimal_body_weight_kg", reads["aafco-cat-adult"])
        self.assertNotIn("optimal_body_weight_kg", reads["nrc-puppy-4-14-wk"])
        facts = {f["name"]: f for f in result.describe_inputs(D)["animal_facts"]}
        self.assertEqual(facts["body_weight_kg"]["label"], "Current body weight (kg)")
        self.assertIn("at mating", facts["body_weight_kg"]["description"])


class FatAndRatios(Close):
    """The steward's rules of 24 Oct 2026: a caloric restriction never raises fat's minimum,
    also when it is entered with an intake; ratios do not change with a restriction or a low
    energy fed, as a ratio's numerator and denominator rise together."""

    def test_fat_with_an_intake_and_a_restriction(self):
        need = 130 * 30 ** 0.75
        fat = {}
        for name, extra in (("restriction", dict(caloric_restriction_percent=20)),
                            ("intake", dict(energy_intake_kcal_per_day=0.8 * need)),
                            ("both", dict(energy_intake_kcal_per_day=0.8 * need,
                                          caloric_restriction_percent=20))):
            r = request("nrc-dog-adult", body_weight_kg=30.0, adult_dog_type=DOG["average"],
                        **extra)
            fat[name] = r.minimum("fat-mbw")
            self.assertEqual(r.minimum("fat"), 13.8)
        # 1.8 g/kg BW^0.75 a day: at the need (the restriction, or the intake / (1 - 0.2)),
        # and at an intake entered alone, which is the dog's need.
        self.close(fat["restriction"], 1.8 * 1000 / 130)
        self.close(fat["both"], fat["restriction"])
        self.close(fat["intake"], 1.8 * 1000 / (130 * 0.8))
        res = run("nrc-dog-adult", {"fat-mbw": 20}, body_weight_kg=30.0,
                  adult_dog_type=DOG["average"], energy_intake_kcal_per_day=0.8 * need,
                  caloric_restriction_percent=20)
        self.close(nutrient(res, "fat-mbw")["mbw"]["minimum_energy_kcal_per_day"], need)
        # The template converts at the intake.
        t = request("nrc-dog-adult", template_rules=True, body_weight_kg=30.0,
                    adult_dog_type=DOG["average"], energy_intake_kcal_per_day=0.8 * need,
                    caloric_restriction_percent=20)
        self.close(t.minimum("fat-mbw"), fat["intake"])

    def test_ratios_do_not_change(self):
        rows = ("la-aa-to-ala-epa-dha-ratio", "la-aa-to-epa-dha-ratio", "ca-p-ratio")
        for rid, facts in (("nrc-dog-adult", dict(body_weight_kg=30.0,
                                                  adult_dog_type=DOG["inactive"])),
                           ("nrc-puppy-14-wk-plus", dict(body_weight_kg=10.0,
                                                         mature_weight_kg=30.0)),
                           ("fediaf-dog-early-growth-reproduction",
                            dict(body_weight_kg=5.0, mature_weight_kg=30.0))):
            base = request(rid, **facts)
            for extra in (dict(caloric_restriction_percent=30),
                          dict(energy_intake_kcal_per_day=base.energy.kcal * 0.6)):
                r = request(rid, **dict(facts, **extra))
                for nid in rows:
                    self.assertEqual((r.minimum(nid), r.maximum(nid)),
                                     (base.minimum(nid), base.maximum(nid)), (rid, extra, nid))
        # NRC puppies' Ca:P maximum: NRC's calcium SUL / the phosphorus minimum, 4.5 / 2.5.
        self.close(request("nrc-puppy-14-wk-plus", body_weight_kg=10.0, mature_weight_kg=30.0,
                           caloric_restriction_percent=30).maximum("ca-p-ratio"), 1.8)
        # The template's rules narrow them under a restriction (1.8 x 0.7).
        t = request("nrc-puppy-14-wk-plus", template_rules=True, body_weight_kg=10.0,
                    mature_weight_kg=30.0, caloric_restriction_percent=30)
        self.close(t.maximum("ca-p-ratio"), 1.8 * 0.7)

    def test_rules_text(self):
        self.assertIn("(fat's and the ratios' excepted)", caveats.ENERGY_RULES_TEXT)
        self.assertIn("the NRC dog choline maximum, NRC's large-breed puppy calcium row and the "
                      "carbohydrate maximum", caveats.ENERGY_RULES_TEXT)


class Floor(unittest.TestCase):
    """An energy fed below 10% of the reference is rejected."""

    def test_intake(self):
        res = run("nrc-dog-adult", {"protein": 30}, body_weight_kg=30.0,
                  adult_dog_type=DOG["average"], energy_intake_kcal_per_day=100.0)
        item = next(i for i in res["input_report"] if i["reason"] == "energy-fed-below-floor")
        self.assertEqual((item["input"], item["status"]),
                         ("animal.energy_intake_kcal_per_day", "rejected"))
        # Whole kcal/day (steward, 24 Oct 2026): 130 x 30^0.75 = 1666.4.
        self.assertEqual(item["text"], "Not used: the energy fed would be 100 kcal/day, below "
                         "10% of the reference energy (1666 kcal/day). Check the entry.")
        self.assertNotIn("energy_intake_kcal_per_day", res["inputs"]["normalized"]["animal"])
        self.assertEqual(res["factors"]["energy_fed_is"], "the requirement's energy")
        self.assertEqual(schema_check.errors(res, SCHEMA), [])
        at_floor = 0.1 * 130 * 30 ** 0.75
        res = run("nrc-dog-adult", {}, body_weight_kg=30.0, adult_dog_type=DOG["average"],
                  energy_intake_kcal_per_day=at_floor)
        self.assertFalse(any(i["reason"] == "energy-fed-below-floor"
                             for i in res["input_report"]))

    def test_optimal_weight(self):
        res = run("nrc-dog-adult", {}, body_weight_kg=30.0, adult_dog_type=DOG["average"],
                  optimal_body_weight_kg=0.1)
        item = next(i for i in res["input_report"] if i["reason"] == "energy-fed-below-floor")
        self.assertEqual(item["input"], "animal.optimal_body_weight_kg")
        self.assertIsNone(res["factors"]["optimal_body_weight"])


class RaisedMinimum(Close):
    """A standard's minimum raised for a caloric restriction or by the energy factor counts as
    the standard's for the verdict, but is never credited to the standard alone (steward, 24
    Oct 2026, after the AI-read test of release 0.5.0)."""

    CAT = {"body_weight_kg": 6.5, "caloric_restriction_percent": 25}

    def test_ai_read_case(self):
        # The AI-read test's case B: 120 g/Mcal is above AAFCO's 72.22 (65 x 4 / 3.6) and below
        # the raised 122.8; the status names the raise and the minimum before it.
        res = run("aafco-cat-adult", {"protein": 120, "energy-density": 3.6},
                  adult_cat_type=CAT["overweight"], **self.CAT)
        n = nutrient(res, "protein")
        raise_ = n["minimum_raise"]
        self.close(raise_["standard_minimum_before_raise"], 65 * 4 / 3.6)
        self.close(raise_["factor"], res["factors"]["energy_factor"])
        self.close(n["standard_minimum"], raise_["standard_minimum_before_raise"] *
                   raise_["factor"])
        self.assertEqual(raise_["reason"], limits.RAISE_ENERGY)
        self.assertEqual(n["low"]["verdict"], "deficient")
        status = n["low"]["status"]
        self.assertNotIn("Below the AAFCO minimum", status)
        self.assertTrue(status.startswith("Below 122.8 g/Mcal: the AAFCO minimum at this "
                                          "food's energy density, 72.22 g/Mcal, raised × 1.7 "
                                          "because the energy fed is below the reference "
                                          "energy"), status)
        self.assertTrue(status.endswith("only the raise makes it deficient."), status)
        self.assertIn("AAFCO's minimum at this food's energy density is 72.22 g/Mcal. This "
                      "checker raises it × 1.7 to 122.8 g/Mcal because the energy fed (206 "
                      "kcal/day) is below the reference energy (350 kcal/day)", raise_["text"])
        self.assertEqual(schema_check.errors(res, SCHEMA), [])

    def test_also_below_the_standard(self):
        res = run("aafco-cat-adult", {"protein": 70, "energy-density": 3.6},
                  adult_cat_type=CAT["overweight"], **self.CAT)
        status = nutrient(res, "protein")["low"]["status"]
        self.assertTrue(status.endswith("The value is also below the AAFCO minimum before the "
                                        "raise (72.22 g/Mcal)."), status)

    def test_restriction(self):
        # NRC's average adult dog: the need is the reference, so the restriction is the factor.
        res = run("nrc-dog-adult", {"linoleic-acid": 3.0}, body_weight_kg=20.0,
                  adult_dog_type=DOG["average"], caloric_restriction_percent=20)
        n = nutrient(res, "linoleic-acid")
        self.assertEqual(n["minimum_raise"]["reason"], limits.RAISE_RESTRICTION)
        self.close(n["minimum_raise"]["factor"], 1.25)
        self.assertEqual(n["low"]["status"].split(" (")[0],
                         "Below 3.5 g/Mcal: the NRC minimum, 2.8 g/Mcal, raised × 1.25 for the "
                         "caloric restriction of 20%")

    def test_not_raised(self):
        # No restriction or energy factor; an MBW row (the standard's daily amount); fat.
        res = run("nrc-dog-adult", {"linoleic-acid": 2.0, "protein-mbw": 20, "fat": 30},
                  body_weight_kg=20.0, adult_dog_type=DOG["average"])
        for nid in ("linoleic-acid", "protein-mbw", "fat"):
            self.assertIsNone(nutrient(res, nid)["minimum_raise"], nid)
        self.assertEqual(nutrient(res, "linoleic-acid")["low"]["status"],
                         caveats.STATUS["deficient"].replace("{standard}", "NRC"))
        res = run("nrc-dog-adult", {"protein-mbw": 20, "fat": 30}, body_weight_kg=20.0,
                  adult_dog_type=DOG["average"], caloric_restriction_percent=20)
        for nid in ("protein-mbw", "fat"):
            self.assertIsNone(nutrient(res, nid)["minimum_raise"], nid)

    def test_arginine_not_one_factor(self):
        # The protein increase does not scale: no factor, and no "x" in the texts.
        r = request("nrc-dog-adult", {"protein": {"low": 45.0}}, body_weight_kg=20.0,
                    adult_dog_type=DOG["average"], caloric_restriction_percent=20)
        raise_ = r.minimum_raise("arginine")
        self.assertIsNone(raise_.factor)
        self.assertLess(raise_.before, r.standard_minimum("arginine"))

    def test_aafco_open_minimum(self):
        res = run("aafco-cat-adult", {"linoleic-acid": 1.7, "energy-density": 3.6},
                  adult_cat_type=CAT["overweight"], **self.CAT)
        low = nutrient(res, "linoleic-acid")["low"]
        self.assertIsNone(low["verdict"])
        self.assertEqual(low["open_reason"], "ig-open-point-6-aafco-dry-matter")
        self.assertIn("raised × 1.7 because the energy fed is below the reference energy",
                      low["status"])
        self.assertTrue(low["status"].endswith("The value is not below the AAFCO minimum "
                                               "before the raise (1.556 g/Mcal)."))

    def test_template_rules(self):
        r = request("aafco-cat-adult", {"energy-density": {"low": 3.6}}, template_rules=True,
                    adult_cat_type=CAT["lean"], body_weight_kg=4.0,
                    caloric_restriction_percent=20)
        raise_ = r.minimum_raise("protein")
        self.close(raise_.before, 65 * 4 / 3.6)
        self.close(raise_.factor, 1.25)
        self.assertEqual(raise_.reason, limits.RAISE_RESTRICTION)


if __name__ == "__main__":
    unittest.main()
