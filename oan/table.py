"""The requirement table: load the standards CSV files and compute each limit.

Each limit cell holds the figure as the standard prints it, the unit it is printed in
(empty when that is the nutrient's own unit) and a rule from a closed list (RULES). The
code computes every value; no CSV cell holds an expression.

Figures:
  12.5        a plain decimal
  >5.5        printed as "greater than 5.5": the value is the converted figure plus
              GREATER_THAN_STEP, so a diet at the printed figure stays below it
  2|2.5       two figures, for a rule that chooses between them (see the rule)
  none        the standard sets no figure here
  (empty)     a derived cell: the rule computes it from other cells

Printed units are "<amount>/<basis>": amount g, mg, mcg or IU (mcg of vitamin D converts at
40 IU/mcg, mg of vitamin E at 1 IU/mg); basis 1000 kcal, 100 g DM,
kg DM, kg BW^0.75 or kg BW^0.67. A dry matter basis converts at 4,000 kcal ME per kg DM.
The conversion is exact in decimal and rounded once to a double, so a converted figure
equals the number the template typed.
"""

import csv
import os
from decimal import Decimal

GREATER_THAN_STEP = Decimal("0.000000001")

# rule name -> (kind, description). kind: "figure" (from a printed figure), "derived"
# (computes from other cells; the figure is empty), "pair" (two figures).
RULES = {
    "printed": ("figure", "the figure as printed, converted from its printed unit"),
    "template": ("figure", "a figure the template sets itself; its note says how"),
    "folic-acid-to-dfe": ("figure", "printed as folic acid: the figure / 0.6 gives DFE"),
    "mbw-from-per-mcal": ("derived", "the per-Mcal value x the requirement's MER / 1000"),
    "retinol-from-vitamin-a-iu": ("derived", "the vitamin A (IU) value of the same basis x 0.3"),
    "vitamin-a-iu-from-retinol": ("derived", "the retinol (mcg) value of the same basis / 0.3"),
    "la-aa-over-epa-dha": ("derived", "(LA max + AA max) / EPA+DHA min of the same requirement"),
    "fediaf-late-growth-by-mature-weight": (
        "pair",
        "the first figure if the expected mature body weight is above 0 and at most 15 kg, "
        "else the second (also when it is not entered)",
    ),
}

AMOUNTS_MCG = {"g": Decimal(1000000), "mg": Decimal(1000), "mcg": Decimal(1)}
VITAMIN_D_IU_PER_MCG = Decimal(40)
VITAMIN_D = ("vitamin-d", "vitamin-d-mbw")
# 1 IU of vitamin E = 1 mg all-rac-alpha-tocopheryl acetate (NRC 2006 table footnotes).
VITAMIN_E_IU_PER_MG = Decimal(1)
VITAMIN_E = ("vitamin-e", "vitamin-e-mbw")
# printed basis -> {nutrient basis: factor}
BASES = {
    "1000 kcal": {"per-mcal": Decimal(1)},
    "100 g DM": {"per-mcal": Decimal(10) / 4, "per-100g-dm": Decimal(1)},
    "kg DM": {"per-mcal": Decimal(1) / 4, "per-100g-dm": Decimal(1) / 10},
    "kg BW^0.75": {"per-mbw": Decimal(1)},
    "kg BW^0.67": {"per-mbw": Decimal(1)},
}
MBW_BASIS = {"canine": "kg BW^0.75", "feline": "kg BW^0.67"}

# Partners of the cross-nutrient rules, by nutrient id.
RETINOL_VITAMIN_A = {"retinol": "vitamin-a", "retinol-mbw": "vitamin-a-mbw"}
VITAMIN_A_RETINOL = {v: k for k, v in RETINOL_VITAMIN_A.items()}
LA_AA_EPA_DHA = ("linoleic-acid", "arachidonic-acid", "epa-dha")

NONE = "none"


class DataError(Exception):
    pass


def read_csv(path):
    """Rows of a CSV file as dicts. UTF-8 with an optional byte-order mark."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load(data_dir):
    """Load the data folder: nutrients, requirements, limits, energy figures, the template's
    own figures and rows, and notes."""
    nutrients = read_csv(os.path.join(data_dir, "nutrients.csv"))
    requirements = read_csv(os.path.join(data_dir, "requirements.csv"))
    notes = read_csv(os.path.join(data_dir, "notes.csv"))
    limits = {}
    for req in requirements:
        path = os.path.join(data_dir, "standards", req["edition"], req["id"] + ".csv")
        limits[req["id"]] = {row["nutrient"]: row for row in read_csv(path)}
    energy = {row["id"]: row for row in read_csv(os.path.join(data_dir, "energy.csv"))}
    template = {row["id"]: row for row in read_csv(os.path.join(data_dir, "template.csv"))}
    return {"nutrients": nutrients, "requirements": requirements, "limits": limits,
            "energy": energy, "template": template, "notes": notes}


def parse_figure(text):
    """(figures, greater_than) from a figure cell; figures is a tuple of Decimals,
    () for an empty (derived) cell, or None for "none"."""
    if text == NONE:
        return None, False
    if text == "":
        return (), False
    greater = text.startswith(">")
    if greater:
        text = text[1:]
    return tuple(Decimal(part) for part in text.split("|")), greater


def unit_factor(unit, nutrient, species):
    """The exact factor from a printed unit to the nutrient's unit (1 for an empty unit)."""
    if unit == "":
        return Decimal(1)
    amount, sep, basis = unit.partition("/")
    if not sep or basis not in BASES:
        raise DataError("unknown printed unit %r" % unit)
    if basis.startswith("kg BW") and basis != MBW_BASIS[species]:
        raise DataError("%r is not the %s metabolic body weight basis" % (unit, species))
    to_basis = BASES[basis].get(nutrient["basis"])
    if to_basis is None:
        raise DataError("%r does not convert to %s's basis (%s)" % (
            unit, nutrient["id"], nutrient["basis"]))
    target = nutrient["amount"]
    if amount == target:
        to_amount = Decimal(1)
    elif amount in AMOUNTS_MCG and target in AMOUNTS_MCG:
        to_amount = AMOUNTS_MCG[amount] / AMOUNTS_MCG[target]
    elif amount == "mcg" and target == "IU" and nutrient["id"] in VITAMIN_D:
        to_amount = VITAMIN_D_IU_PER_MCG
    elif amount == "mg" and target == "IU" and nutrient["id"] in VITAMIN_E:
        to_amount = VITAMIN_E_IU_PER_MG
    else:
        raise DataError("%r does not convert to %s's amount unit (%s)" % (
            unit, nutrient["id"], target))
    return to_amount * to_basis


def compute_limits(data, requirement_id, mature_weight_kg=None):
    """{nutrient id: (min, max)} for one requirement; each is a float or None ("none").

    mature_weight_kg: the expected mature body weight, or None when not entered.
    """
    req = next(r for r in data["requirements"] if r["id"] == requirement_id)
    rows = data["limits"][requirement_id]
    nutrients = {n["id"]: n for n in data["nutrients"]}
    done = {}

    def value(nutrient_id, bound, stack=()):
        key = (nutrient_id, bound)
        if key in done:
            return done[key]
        if key in stack:
            raise DataError("%s: the rules of %s %s refer to themselves" % (
                requirement_id, nutrient_id, bound))
        stack = stack + (key,)
        row = rows[nutrient_id]
        rule = row[bound + "_rule"]
        figures, greater = parse_figure(row[bound])
        if figures is None:
            done[key] = None
            return None
        kind = RULES.get(rule, ("unknown",))[0]
        if kind in ("figure", "pair"):
            if kind == "pair":
                small = mature_weight_kg is not None and 0 < mature_weight_kg <= 15
                figure = figures[0] if small else figures[1]
            else:
                figure = figures[0]
            exact = figure * unit_factor(row[bound + "_unit"], nutrients[nutrient_id],
                                         req["species"])
            if greater:
                exact += GREATER_THAN_STEP
            result = float(exact)
            if rule == "folic-acid-to-dfe":
                result = result / 0.6
        elif rule == "mbw-from-per-mcal":
            result = needed(nutrients[nutrient_id]["mbw_of"], bound, key, rule, stack) * \
                float(req["mer_kcal_per_mbw"]) / 1000
        elif rule == "retinol-from-vitamin-a-iu":
            result = needed(RETINOL_VITAMIN_A[nutrient_id], bound, key, rule, stack) * 0.3
        elif rule == "vitamin-a-iu-from-retinol":
            result = needed(VITAMIN_A_RETINOL[nutrient_id], bound, key, rule, stack) / 0.3
        elif rule == "la-aa-over-epa-dha":
            la, aa, epa_dha = LA_AA_EPA_DHA
            result = (needed(la, "max", key, rule, stack) +
                      needed(aa, "max", key, rule, stack)) / \
                needed(epa_dha, "min", key, rule, stack)
        else:
            raise DataError("%s: %s %s has an unknown rule %r" % (
                requirement_id, nutrient_id, bound, rule))
        done[key] = result
        return result

    def needed(nutrient_id, bound, of, rule, stack):
        """A value a rule computes from: a number, never none."""
        v = value(nutrient_id, bound, stack)
        if v is None:
            raise DataError("%s: %s %s is computed by the rule %s from %s %s, which is "
                            "none; give %s %s a figure, or the rule's value its own figure" % (
                                requirement_id, of[0], of[1], rule, nutrient_id, bound,
                                nutrient_id, bound))
        return v

    return {nid: (value(nid, "min"), value(nid, "max")) for nid in rows}
