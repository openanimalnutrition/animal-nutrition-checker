"""Daily energy: each requirement's energy minimum, and the energy the checker uses.

The equations are the standards' (each figure in data/energy.csv cites its table and page); the
rules are on the IG's band computation page ("Requirements per kg of metabolic body weight",
"Caloric restriction", "Energy rules proposed for the code version") and in
docs/changes-from-21OCT26b.md. Written in nutrition terms. Every figure the standards print is
read from data/energy.csv by its id (FIGURES below); the shape of each equation, and which
requirement uses which equation, is here. A requirement whose energy cannot be computed gets a
reason code instead of a number (REASONS); the code never produces the template's messages or
error codes.

The animal facts are the ones oan/inputs.py accepts, already normalised: None means not
entered. A blank number of puppies or lactation week counts as 0, as in the template; a
blank life stage counts as "None".
"""

import math
from collections import namedtuple

# The figures of data/energy.csv: id -> the unit the code reads it in ("" for a plain
# number: a multiplier, an exponent, a rate or a week factor).
FIGURES = {
    "nrc-dog-exponent": "",
    "nrc-dog-maintenance-inactive": "kcal/kg BW^0.75",
    "nrc-dog-maintenance-older": "kcal/kg BW^0.75",
    "nrc-dog-maintenance-average": "kcal/kg BW^0.75",
    "nrc-dog-maintenance-young": "kcal/kg BW^0.75",
    "nrc-dog-maintenance-terriers": "kcal/kg BW^0.75",
    "nrc-dog-maintenance-great-danes": "kcal/kg BW^0.75",
    "nrc-puppy-maintenance": "kcal/kg BW^0.75",
    "nrc-puppy-multiplier": "",
    "nrc-puppy-rate": "",
    "nrc-puppy-offset": "",
    "nrc-gestation-maintenance": "kcal/kg BW^0.75",
    "nrc-gestation-per-kg": "kcal/kg BW",
    "nrc-lactation-maintenance": "kcal/kg BW^0.75",
    "nrc-lactation-per-puppy-1-to-4": "kcal/kg BW",
    "nrc-lactation-per-puppy-5-to-8": "kcal/kg BW",
    "nrc-lactation-puppies-first-group": "puppies",
    "nrc-lactation-puppies-counted": "puppies",
    "nrc-lactation-week-1": "",
    "nrc-lactation-week-2": "",
    "nrc-lactation-week-3": "",
    "nrc-lactation-week-4": "",
    "nrc-cat-exponent": "",
    "nrc-cat-maintenance-overweight": "kcal/kg BW^0.4",
    "nrc-cat-maintenance-overweight-exponent": "",
    "nrc-cat-maintenance-lean": "kcal/kg BW^0.67",
    "nrc-kitten-maintenance": "kcal/kg BW^0.67",
    "nrc-kitten-multiplier": "",
    "nrc-kitten-rate": "",
    "nrc-kitten-offset": "",
    "nrc-queen-gestation": "kcal/kg BW^0.67",
    "nrc-queen-lactation-maintenance": "kcal/kg BW^0.67",
    "nrc-queen-lactation-kittens-under-3": "kcal/kg BW",
    "nrc-queen-lactation-kittens-3-to-4": "kcal/kg BW",
    "nrc-queen-lactation-kittens-over-4": "kcal/kg BW",
    "nrc-queen-lactation-week-1": "",
    "nrc-queen-lactation-week-2": "",
    "nrc-queen-lactation-week-3": "",
    "nrc-queen-lactation-week-4": "",
    "nrc-queen-lactation-week-5": "",
    "nrc-queen-lactation-week-6": "",
    "nrc-queen-lactation-week-7": "",
    "fediaf-dog-exponent": "",
    "fediaf-cat-exponent": "",
    "fediaf-puppy-constant": "kcal/kg BW^0.75",
    "fediaf-puppy-slope": "kcal/kg BW^0.75",
    "fediaf-gestation-maintenance": "kcal/kg BW^0.75",
    "fediaf-gestation-per-kg": "kcal/kg BW",
    "fediaf-lactation-maintenance": "kcal/kg BW^0.75",
    "fediaf-lactation-per-puppy-1-to-4": "kcal/kg BW",
    "fediaf-lactation-per-puppy-5-to-8": "kcal/kg BW",
    "fediaf-lactation-puppies-first-group": "puppies",
    "fediaf-lactation-puppies-counted": "puppies",
    "fediaf-lactation-week-1": "",
    "fediaf-lactation-week-2": "",
    "fediaf-lactation-week-3": "",
    "fediaf-lactation-week-4": "",
    "fediaf-queen-gestation": "kcal/kg BW^0.67",
    "fediaf-queen-lactation-maintenance": "kcal/kg BW^0.67",
    "fediaf-queen-lactation-kittens-under-3": "kcal/kg BW",
    "fediaf-queen-lactation-kittens-3-to-4": "kcal/kg BW",
    "fediaf-queen-lactation-kittens-over-4": "kcal/kg BW",
    "fediaf-queen-lactation-week-1": "",
    "fediaf-queen-lactation-week-2": "",
    "fediaf-queen-lactation-week-3": "",
    "fediaf-queen-lactation-week-4": "",
    "fediaf-queen-lactation-week-5": "",
    "fediaf-queen-lactation-week-6": "",
    "fediaf-queen-lactation-week-7": "",
    "avcn-rer": "kcal/kg BW^0.75",
    "avcn-rer-exponent": "",
    "avcn-puppy-to-4-months": "x RER",
    "avcn-puppy-to-adult-size": "x RER",
    "avcn-kitten-growth": "x RER",
    "energy-range-high": "x energy minimum",
}

# The adult dog and cat types, in the template's list order after the "not selected" item.
# Each type's label is in data/energy.csv and prints its figure (checked by the validator).
NOT_SELECTED_DOG = "Not selected or a dog"
NOT_SELECTED_CAT = "Not selected or a cat"
DOG_TYPES = (
    "nrc-dog-maintenance-inactive",
    "nrc-dog-maintenance-older",
    "nrc-dog-maintenance-average",
    "nrc-dog-maintenance-young",
    "nrc-dog-maintenance-terriers",
    "nrc-dog-maintenance-great-danes",
)
CAT_TYPES = ("nrc-cat-maintenance-overweight", "nrc-cat-maintenance-lean")
# The exponent each type's label prints.
TYPE_EXPONENTS = {fid: "nrc-dog-exponent" for fid in DOG_TYPES}
TYPE_EXPONENTS.update({
    "nrc-cat-maintenance-overweight": "nrc-cat-maintenance-overweight-exponent",
    "nrc-cat-maintenance-lean": "nrc-cat-exponent",
})

# Life stages (oan/inputs.py LIFE_STAGES).
NONE = "None"
GROWTH_TO_4_MONTHS = "Growth: weaning to 4 months"
GROWTH_TO_ADULT = "Growth: 4 months to adult size"
GESTATION_WEEKS_1_4 = "Gestation: weeks 1-4"
GESTATION_WEEK_5_ON = "Gestation: week 5 to birth"
LACTATION_BITCH = "Lactation: bitch"
KITTENS = {
    "<3 Kittens": "kittens-under-3",
    "3-4 Kittens": "kittens-3-to-4",
    ">4 Kittens": "kittens-over-4",
}
GROWTH = (NONE, GROWTH_TO_4_MONTHS, GROWTH_TO_ADULT)
GESTATION = (GESTATION_WEEKS_1_4, GESTATION_WEEK_5_ON)

BITCH_LACTATION_WEEKS = 4  # neither standard gives an estimate after week 4
QUEEN_LACTATION_WEEKS = 7

# Why a requirement's energy is not a number. The template shows a message instead; the
# wording for the checker's users is drafted with the caveats (plan, phase 5).
REASONS = (
    "body-weight-needed",
    "adult-dog-type-needed",
    "adult-cat-type-needed",
    "mature-weight-needed",
    "mature-weight-below-body-weight",
    "life-stage-not-covered",
    "lactation-week-and-puppies-needed",
    "no-estimate-after-lactation-week-4",
    "lactation-week-and-kittens-needed",
)

Energy = namedtuple("Energy", "kcal reason")  # kcal per day, or None with a reason


class _Animal:
    """The facts one energy equation reads, with the figures of the data folder."""

    def __init__(self, data, requirement, facts):
        self.figures = data["energy"]
        self.requirement = requirement
        self.bw = facts["body_weight_kg"]
        self.mature = facts.get("mature_weight_kg")
        self.puppies = facts.get("puppies_nursing") or 0
        self.week = int(facts.get("lactation_week") or 0)
        self.stage = facts.get("life_stage") or NONE
        self.dog_type = _type_id(data, DOG_TYPES, facts.get("adult_dog_type"))
        self.cat_type = _type_id(data, CAT_TYPES, facts.get("adult_cat_type"))

    def f(self, fid):
        return float(self.figures[fid]["figure"])

    def mbw(self, exponent_id):
        return self.bw ** self.f(exponent_id)


def _type_id(data, ids, label):
    for fid in ids:
        if data["energy"][fid]["label"] == label:
            return fid
    return None


def _value(kcal):
    return Energy(kcal, None)


def _reason(code):
    return Energy(None, code)


def dog_type_labels(data):
    """The adult dog type list, as the template orders it."""
    return (NOT_SELECTED_DOG,) + tuple(data["energy"][fid]["label"] for fid in DOG_TYPES)


def cat_type_labels(data):
    """The adult cat type list, as the template orders it."""
    return (NOT_SELECTED_CAT,) + tuple(data["energy"][fid]["label"] for fid in CAT_TYPES)


# The building blocks (spec section 2).

def _rer(a):
    return a.f("avcn-rer") * a.mbw("avcn-rer-exponent")


def _nrc_dog_maintenance(a):
    if a.dog_type is None:
        return _reason("adult-dog-type-needed")
    return _value(a.f(a.dog_type) * a.mbw("nrc-dog-exponent"))


def _nrc_cat_maintenance(a):
    if a.cat_type is None:
        return _reason("adult-cat-type-needed")
    return _value(a.f(a.cat_type) * a.mbw(TYPE_EXPONENTS[a.cat_type]))


def _bitch_maintenance(a):
    """The selected dog type's maintenance, else NRC's average for gestation (decision 1e B)."""
    factor = a.f(a.dog_type) if a.dog_type else a.f("nrc-gestation-maintenance")
    return factor * a.mbw("nrc-dog-exponent")


def _nrc_late_gestation(a):
    return _value(_bitch_maintenance(a) + a.f("nrc-gestation-per-kg") * a.bw)


def _bitch_lactation(a, std):
    """Maintenance during lactation + BW x (per-puppy figures x puppies) x the week's factor.
    The puppies count once: the first group (1-4) at the first figure, the rest up to the
    number counted (5-8) at the second."""
    if a.puppies < 1 or a.week < 1:
        return _reason("lactation-week-and-puppies-needed")
    if a.week > BITCH_LACTATION_WEEKS:
        return _reason("no-estimate-after-lactation-week-4")
    first = a.f(std + "-lactation-puppies-first-group")
    counted = a.f(std + "-lactation-puppies-counted")
    n = min(a.puppies, first)
    m = min(max(a.puppies - first, 0), counted - first)
    per_kg = a.f(std + "-lactation-per-puppy-1-to-4") * n + \
        a.f(std + "-lactation-per-puppy-5-to-8") * m
    week = a.f("%s-lactation-week-%d" % (std, a.week))
    return _value(a.f(std + "-lactation-maintenance") * a.mbw(std + "-dog-exponent")
                  + a.bw * per_kg * week)


def _queen_gestation(a, std):
    return _value(a.f(std + "-queen-gestation") * a.mbw(std + "-cat-exponent"))


def _queen_lactation(a, std):
    if a.week < 1 or a.week > QUEEN_LACTATION_WEEKS:
        return _reason("lactation-week-and-kittens-needed")
    kittens = KITTENS.get(a.stage)
    if kittens is None:
        return _reason("lactation-week-and-kittens-needed")
    return _value(a.f(std + "-queen-lactation-maintenance") * a.mbw(std + "-cat-exponent")
                  + a.f("%s-queen-lactation-%s" % (std, kittens)) * a.bw
                  * a.f("%s-queen-lactation-week-%d" % (std, a.week)))


def _growth_check(a):
    """A growth equation needs the expected mature BW, and a growing animal weighs less than
    it (batch 8c A); BW equal to it computes."""
    if a.mature is None:
        return _reason("mature-weight-needed")
    if a.bw > a.mature:
        return _reason("mature-weight-below-body-weight")
    return None


def _nrc_puppy(a):
    return _growth_check(a) or _value(
        a.f("nrc-puppy-maintenance") * a.mbw("nrc-dog-exponent") * a.f("nrc-puppy-multiplier")
        * (math.exp(-a.f("nrc-puppy-rate") * (a.bw / a.mature)) - a.f("nrc-puppy-offset")))


def _nrc_kitten(a):
    return _growth_check(a) or _value(
        a.f("nrc-kitten-maintenance") * a.mbw("nrc-cat-exponent") * a.f("nrc-kitten-multiplier")
        * (math.exp(-a.f("nrc-kitten-rate") * (a.bw / a.mature)) - a.f("nrc-kitten-offset")))


def _fediaf_puppy(a):
    return _growth_check(a) or _value(
        (a.f("fediaf-puppy-constant") - a.f("fediaf-puppy-slope") * (a.bw / a.mature))
        * a.mbw("fediaf-dog-exponent"))


# The rules of the requirements (spec section 4). The first matching life stage wins; a stage
# a rule does not cover gives life-stage-not-covered.

def _fediaf_adult(a):
    exponent = "fediaf-dog-exponent" if a.requirement["species"] == "canine" else \
        "fediaf-cat-exponent"
    return _value(float(a.requirement["mer_kcal_per_mbw"]) * a.mbw(exponent))


def _aafco_dog_growth_reproduction(a):
    """AVCN Box 3.1 for growth; NRC for reproduction (the template's rule, notes n039)."""
    if a.stage == GROWTH_TO_4_MONTHS:
        return _value(a.f("avcn-puppy-to-4-months") * _rer(a))
    if a.stage == GROWTH_TO_ADULT:
        return _value(a.f("avcn-puppy-to-adult-size") * _rer(a))
    if a.stage == GESTATION_WEEKS_1_4:
        return _value(_bitch_maintenance(a))
    if a.stage in (GESTATION_WEEK_5_ON, LACTATION_BITCH):
        return _nrc_dog_gestation_lactation(a)
    return _reason("life-stage-not-covered")


def _aafco_dog_growth_large_breed(a):
    if a.stage == GROWTH_TO_4_MONTHS:
        return _value(a.f("avcn-puppy-to-4-months") * _rer(a))
    if a.stage == GROWTH_TO_ADULT:
        return _value(a.f("avcn-puppy-to-adult-size") * _rer(a))
    return _reason("life-stage-not-covered")


def _fediaf_dog_early_growth_reproduction(a):
    if a.stage in GROWTH:
        return _fediaf_puppy(a)
    gestation = a.f("fediaf-gestation-maintenance") * a.mbw("fediaf-dog-exponent")
    if a.stage == GESTATION_WEEKS_1_4:
        return _value(gestation)
    if a.stage == GESTATION_WEEK_5_ON:
        return _value(gestation + a.f("fediaf-gestation-per-kg") * a.bw)
    if a.stage == LACTATION_BITCH:
        return _bitch_lactation(a, "fediaf")
    return _reason("life-stage-not-covered")


def _nrc_dog_gestation_lactation(a):
    if a.stage in (NONE, GESTATION_WEEK_5_ON):
        return _nrc_late_gestation(a)
    if a.stage == LACTATION_BITCH:
        return _bitch_lactation(a, "nrc")
    return _reason("life-stage-not-covered")


def _aafco_cat_growth_reproduction(a):
    """AVCN Box 3.1 for growth; NRC for reproduction (the template's rule, notes n045)."""
    if a.stage in GROWTH:
        return _value(a.f("avcn-kitten-growth") * _rer(a))
    if a.stage in GESTATION:
        return _queen_gestation(a, "nrc")
    if a.stage in KITTENS:
        return _queen_lactation(a, "nrc")
    return _reason("life-stage-not-covered")


def _fediaf_cat_reproduction(a):
    if a.stage in GESTATION:
        return _queen_gestation(a, "fediaf")
    return _queen_lactation(a, "fediaf")


# requirement id -> its energy rule. A new requirement needs a line here (the validator
# reports one without).
RULES = {
    "nrc-dog-adult": _nrc_dog_maintenance,
    "aafco-dog-adult": _nrc_dog_maintenance,  # AAFCO sets no energy requirement (n029)
    "fediaf-dog-adult-mer95": _fediaf_adult,
    "fediaf-dog-adult-mer110": _fediaf_adult,
    "nrc-cat-adult": _nrc_cat_maintenance,
    "aafco-cat-adult": _nrc_cat_maintenance,  # n033
    "fediaf-cat-adult-mer75": _fediaf_adult,
    "fediaf-cat-adult-mer100": _fediaf_adult,
    "nrc-puppy-4-14-wk": _nrc_puppy,
    "nrc-puppy-14-wk-plus": _nrc_puppy,
    "aafco-dog-growth-reproduction": _aafco_dog_growth_reproduction,
    "aafco-dog-growth-large-breed": _aafco_dog_growth_large_breed,
    "fediaf-dog-early-growth-reproduction": _fediaf_dog_early_growth_reproduction,
    "fediaf-dog-late-growth": _fediaf_puppy,
    "nrc-kitten": _nrc_kitten,
    "aafco-cat-growth-reproduction": _aafco_cat_growth_reproduction,
    "fediaf-cat-growth": _nrc_kitten,  # FEDIAF prints kitten energy as times MER (n046)
    "nrc-dog-gestation-lactation": _nrc_dog_gestation_lactation,
    "nrc-cat-late-gestation": lambda a: _queen_gestation(a, "nrc"),
    "nrc-cat-peak-lactation": lambda a: _queen_lactation(a, "nrc"),
    "fediaf-cat-reproduction": _fediaf_cat_reproduction,
}


def requirement_energy(data, requirement_id, facts):
    """The requirement's daily energy minimum (kcal) for the animal, or the reason it has
    none. facts: the accepted animal facts by input name (oan/inputs.py)."""
    if facts.get("body_weight_kg") is None:
        return _reason("body-weight-needed")
    requirement = next(r for r in data["requirements"] if r["id"] == requirement_id)
    return RULES[requirement_id](_Animal(data, requirement, facts))


def energy_used(requirement, intake_kcal):
    """The energy the checker uses: the animal's known intake when one is entered (it takes
    the place of the requirement's energy, whatever that is), else the requirement's."""
    if intake_kcal is not None:
        return _value(intake_kcal)
    return requirement


# The steward's energy rules (23 Oct 2026; proposed, pending ratification). The template's
# own rules use energy_used() alone (oan/limits.py, template_rules).
#
# The reference energy is the energy a standard's per-Mcal figures assume, at the current
# body weight: what "below what the standard expected" is measured against. The adult dog
# and cat types never set it: NRC's adult dog average for NRC and AAFCO dogs, NRC's lean
# adult cat for NRC and AAFCO cats (AAFCO states no energy basis), FEDIAF's stated MER; any
# other requirement, the equation this checker uses for its life stage (the energy row's: for
# AAFCO growth, AVCN Box 3.1; for FEDIAF Cat Growth, NRC's kitten equation), with no adult type.
REFERENCE_FIGURES = {
    _nrc_dog_maintenance: ("nrc-dog-maintenance-average", "nrc-dog-exponent"),
    _nrc_cat_maintenance: ("nrc-cat-maintenance-lean", "nrc-cat-exponent"),
}
# The adult maintenance rules: the only ones an optimal body weight applies to.
ADULT_RULES = (_nrc_dog_maintenance, _nrc_cat_maintenance, _fediaf_adult)


def reference_energy(data, requirement_id, facts):
    """The requirement's reference energy (kcal a day) at the current body weight, or the
    reason it has none."""
    if facts.get("body_weight_kg") is None:
        return _reason("body-weight-needed")
    requirement = next(r for r in data["requirements"] if r["id"] == requirement_id)
    rule = RULES[requirement_id]
    a = _Animal(data, requirement, facts)
    if rule in REFERENCE_FIGURES:
        figure, exponent = REFERENCE_FIGURES[rule]
        return _value(a.f(figure) * a.mbw(exponent))
    a.dog_type = a.cat_type = None
    return rule(a)


def reference_basis(data, requirement_id):
    """(the standard whose basis is used, its figure in kcal per kg BW^n, n), or None where the
    reference is the equation this checker uses for the life stage."""
    requirement = next(r for r in data["requirements"] if r["id"] == requirement_id)
    rule = RULES[requirement_id]
    if rule in REFERENCE_FIGURES:
        figure, exponent = REFERENCE_FIGURES[rule]
        return ("NRC", float(data["energy"][figure]["figure"]),
                float(data["energy"][exponent]["figure"]))
    if rule is _fediaf_adult:
        exponent = "fediaf-dog-exponent" if requirement["species"] == "canine" else \
            "fediaf-cat-exponent"
        return ("FEDIAF", float(requirement["mer_kcal_per_mbw"]),
                float(data["energy"][exponent]["figure"]))
    return None


def optimal_weight_status(requirement_id, facts):
    """Whether an entered optimal body weight is used: None when none is entered, else "used",
    "not-adult" (the requirement is not adult maintenance), "intake-entered" (the intake is
    the energy fed), "no-current-weight" (no current body weight is entered) or
    "not-below-current" (at or above the current body weight)."""
    optimal, current = facts.get("optimal_body_weight_kg"), facts.get("body_weight_kg")
    if optimal is None:
        return None
    if RULES[requirement_id] not in ADULT_RULES:
        return "not-adult"
    if facts.get("energy_intake_kcal_per_day") is not None:
        return "intake-entered"
    if current is None:
        return "no-current-weight"
    if not optimal < current:
        return "not-below-current"
    return "used"


def optimal_weight_energy(data, requirement_id, facts):
    """The requirement's maintenance energy at the optimal body weight; for NRC and AAFCO
    cats, NRC's lean equation whichever cat type is chosen (a cat at its optimal weight is
    lean; steward, 23 Oct 2026)."""
    requirement = next(r for r in data["requirements"] if r["id"] == requirement_id)
    rule = RULES[requirement_id]
    a = _Animal(data, requirement, dict(facts, body_weight_kg=facts["optimal_body_weight_kg"]))
    if rule is _nrc_cat_maintenance:
        return _value(a.f("nrc-cat-maintenance-lean") * a.mbw("nrc-cat-exponent"))
    return rule(a)


def energy_fed(data, requirement_id, facts, requirement):
    """The energy the animal is fed: the intake when one is entered (a restriction entered
    with it says how far below the need that intake is); else the requirement's energy, at
    the optimal body weight when that is used, less the restriction.

    requirement: the requirement's energy at the current body weight (requirement_energy)."""
    intake = facts.get("energy_intake_kcal_per_day")
    if intake is not None:
        return _value(intake)
    base = requirement
    if optimal_weight_status(requirement_id, facts) == "used":
        base = optimal_weight_energy(data, requirement_id, facts)
    restriction = facts.get("caloric_restriction_percent") or 0
    if base.kcal is None or not restriction > 0:
        return base
    return _value(base.kcal * (1 - restriction / 100))


def range_high(data, energy_kcal):
    """The top of the energy row's range: the energy used x the template's factor."""
    return energy_kcal * float(data["energy"]["energy-range-high"]["figure"])
