"""The input rules: what the checker accepts, in nutrition terms.

These are the template's input rules (ai1/README.md, "Inputs and their allowed ranges"). A
value outside its rule is rejected with a reason and never computed with (Sean, 21 Oct 2026,
decision 1 A). None means "not entered": it is never rejected here, and whether a requirement
needs the value is decided where the value is used.

The template reads a life stage with TRIM and compares it without case, so a life stage typed
with other capitals or extra spaces is accepted and normalised to its list item. Every other
listed text (the requirement, the adult dog and cat types) must match its item exactly.
"""

import string
from collections import namedtuple

from . import numbers

LIFE_STAGES = (
    "None",
    "Growth: weaning to 4 months",
    "Growth: 4 months to adult size",
    "Gestation: weeks 1-4",
    "Gestation: week 5 to birth",
    "Lactation: bitch",
    "<3 Kittens",
    "3-4 Kittens",
    ">4 Kittens",
)
ADULT_DOG_TYPES = (
    "Not selected or a dog",
    "Inactive (95 * kg BW^0.75)",
    "Older laboratory/active OR Laboratory Newfoundlands (105 * kg BW^0.75)",
    "Average laboratory or active (130 * kg BW^0.75)",
    "Young laboratory/active (140 * kg BW^0.75)",
    "Laboratory/active terriers (180 * kg BW^0.75)",
    "Laboratory/active Great Danes (200 * kg BW^0.75)",
)
ADULT_CAT_TYPES = (
    "Not selected or a cat",
    "Overweight domestic (130 * BW^0.4)",
    "Lean domestic (100 * kgBW^0.67)",
)

# field -> (kind, rule). kinds: "number" (low, high), "whole" (low, high), "restriction",
# "list" (items), "life-stage", "requirement".
FACTS = {
    "requirement": ("requirement", None),
    "body_weight_kg": ("number", (0.05, 150)),
    "mature_weight_kg": ("number", (0.5, 150)),
    "puppies_nursing": ("whole", (0, 20)),
    "lactation_week": ("whole", (0, 7)),
    "life_stage": ("life-stage", LIFE_STAGES),
    "adult_dog_type": ("list", ADULT_DOG_TYPES),
    "adult_cat_type": ("list", ADULT_CAT_TYPES),
    "energy_intake_kcal_per_day": ("number", (10, 30000)),
    "caloric_restriction_percent": ("restriction", (1, 55)),
    # Used only for the calcium maximum of NRC puppies 4-14 weeks of a large expected size.
    "puppy_body_weight_kg": ("number", (0.5, 50)),
}
# Entries (low or high) with a range of their own; any other entry is any number.
ENTRY_RANGES = {"energy-density": (2, 9)}

Verdict = namedtuple("Verdict", "status value reason")  # status: accept, reject or empty

_ASCII_LOWER = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)


def _accept(value):
    return Verdict("accept", value, None)


def _reject(reason):
    return Verdict("reject", None, reason)


def _in_range(x, low, high, unit=""):
    if low <= x <= high:
        return _accept(x)
    return _reject("outside %s to %s%s" % (numbers.to_text(low), numbers.to_text(high), unit))


def trim(text):
    """Sheets' TRIM: drops leading and trailing spaces and makes inner runs of spaces one.
    Only the space character counts (assumed for tabs and no-break spaces)."""
    return " ".join(part for part in text.split(" ") if part)


def fold(text):
    """Text for a comparison without case: ASCII letters only, as the template compares."""
    return text.translate(_ASCII_LOWER)


def check_fact(field, value, data):
    """The Verdict for one animal fact or selection."""
    if field not in FACTS:
        return _reject("unknown input %r" % field)
    if value is None:
        return Verdict("empty", None, None)
    kind, rule = FACTS[field]
    if kind == "requirement":
        names = [r["name"] for r in data["requirements"]]
        if isinstance(value, str) and value in names:
            return _accept(value)
        return _reject("not one of the %d requirement names" % len(names))
    if kind == "list":
        if isinstance(value, str) and value in rule:
            return _accept(value)
        return _reject("not one of the %d listed items" % len(rule))
    if kind == "life-stage":
        if isinstance(value, str):
            wanted = fold(trim(value))
            for item in rule:
                if fold(item) == wanted:
                    return _accept(item)
        return _reject("not one of the %d life stages" % len(rule))
    x, reason = numbers.as_input_number(value)
    if reason:
        return _reject(reason)
    if kind == "whole" and x != int(x):
        return _reject("not a whole number")
    if kind == "restriction":
        # 0 means no restriction (a 0 typed as 0% is the number 0); 25 means 25%.
        if x == 0:
            return _accept(x)
        return _in_range(x, rule[0], rule[1], " (or 0 for none)")
    return _in_range(x, *rule)


def check_entry(nutrient_id, value, data):
    """The Verdict for one entry (low or high) of a nutrient."""
    nutrient = next((n for n in data["nutrients"] if n["id"] == nutrient_id), None)
    if nutrient is None:
        return _reject("unknown nutrient %r" % nutrient_id)
    if nutrient["enterable"] != "yes":
        return _reject("%s is not entered; it is computed" % nutrient_id)
    if value is None:
        return Verdict("empty", None, None)
    x, reason = numbers.as_input_number(value)
    if reason:
        return _reject(reason)
    if nutrient_id in ENTRY_RANGES:
        return _in_range(x, *ENTRY_RANGES[nutrient_id])
    return _accept(x)
