"""The requirement table: load the standards CSV files and compute each limit.

Each limit cell holds the figure as the standard prints it and a rule from a closed
list (RULES). The code computes every value; no CSV cell holds an expression.

Figures:
  12.5        a plain decimal
  >5.5        printed as "greater than 5.5": the value is the converted figure plus
              GREATER_THAN_STEP, added exactly in decimal and rounded once, so a diet
              at the printed figure stays below it
  2|2.5       two figures, for a rule that chooses between them (see the rule)
  none        the standard sets no figure here
  (empty)     a derived cell: the rule computes it from other cells
"""

import csv
import os
from decimal import Decimal

GREATER_THAN_STEP = Decimal("0.000000001")

# rule name -> (kind, description). kind: "figure" (converts a printed figure),
# "derived" (computes from other cells; the figure is empty), "pair" (two figures).
RULES = {
    "printed": ("figure", "the figure as printed, in the nutrient's unit"),
    "template": ("figure", "a figure the template sets itself; a note says how"),
    "per-4000-kcal": ("figure", "printed per 4,000 kcal (per kg DM at 4 kcal/g): figure / 4"),
    "vitamin-d-mcg": ("figure", "printed in mcg of vitamin D: figure x 40 IU/mcg"),
    "folic-acid-to-dfe": ("figure", "printed as folic acid: figure / 0.6 gives DFE"),
    "mbw-from-per-mcal": ("derived", "the per-Mcal sibling's value x the requirement's MER / 1000"),
    "retinol-from-vitamin-a-iu": ("derived", "the vitamin A (IU) value of the same basis x 0.3"),
    "vitamin-a-iu-from-retinol": ("derived", "the retinol (mcg) value of the same basis / 0.3"),
    "la-aa-over-epa-dha": ("derived", "(LA max + AA max) / EPA+DHA min of the same requirement"),
    "fediaf-late-growth-by-mature-weight": (
        "pair",
        "first figure if the expected mature body weight is above 0 and at most 15 kg, "
        "else the second (also when not entered)",
    ),
}

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
    """Load the data folder: nutrients, requirements, limits and notes."""
    nutrients = read_csv(os.path.join(data_dir, "nutrients.csv"))
    requirements = read_csv(os.path.join(data_dir, "requirements.csv"))
    notes = read_csv(os.path.join(data_dir, "notes.csv"))
    limits = {}
    for req in requirements:
        path = os.path.join(data_dir, "standards", req["edition"], req["id"] + ".csv")
        limits[req["id"]] = {row["nutrient"]: row for row in read_csv(path)}
    return {"nutrients": nutrients, "requirements": requirements, "limits": limits,
            "notes": notes}


def parse_figure(text):
    """(figures, greater_than) from a figure cell; figures is a tuple of floats,
    () for an empty (derived) cell, or None for "none"."""
    if text == NONE:
        return None, False
    if text == "":
        return (), False
    greater = text.startswith(">")
    if greater:
        text = text[1:]
    return tuple(float(part) for part in text.split("|")), greater


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
            result = None
        elif rule in ("printed", "template"):
            result = figures[0]
        elif rule == "per-4000-kcal":
            result = figures[0] / 4
        elif rule == "vitamin-d-mcg":
            result = figures[0] * 40
        elif rule == "folic-acid-to-dfe":
            result = figures[0] / 0.6
        elif rule == "mbw-from-per-mcal":
            result = value(nutrients[nutrient_id]["mbw_of"], bound, stack) * float(
                req["mer_kcal_per_mbw"]) / 1000
        elif rule == "retinol-from-vitamin-a-iu":
            result = value(RETINOL_VITAMIN_A[nutrient_id], bound, stack) * 0.3
        elif rule == "vitamin-a-iu-from-retinol":
            result = value(VITAMIN_A_RETINOL[nutrient_id], bound, stack) / 0.3
        elif rule == "la-aa-over-epa-dha":
            la, aa, epa_dha = LA_AA_EPA_DHA
            result = (value(la, "max", stack) + value(aa, "max", stack)) / value(
                epa_dha, "min", stack)
        elif rule == "fediaf-late-growth-by-mature-weight":
            small = mature_weight_kg is not None and 0 < mature_weight_kg <= 15
            result = figures[0] if small else figures[1]
        else:
            raise DataError("%s: %s %s has an unknown rule %r" % (
                requirement_id, nutrient_id, bound, rule))
        if greater:
            # The template typed these as decimals (5.500000001); adding in floats would
            # be one unit in the last place off for some of them.
            result = float(Decimal(repr(result)) + GREATER_THAN_STEP)
        done[key] = result
        return result

    return {nid: (value(nid, "min"), value(nid, "max")) for nid in rows}
