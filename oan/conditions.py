"""The conditions of a result: the template's ten known limitations (data/limitations.csv), as
fixed conditions on the nutrients they affect (data/conditions.csv).

A condition names a fact this checker does not take as an input, on which a result depends.
In this version the conditions are fixed: they attach by requirement, row and the closed
cases in WHEN, not by the value entered. Later inputs (age, breed, additive or intrinsic
source, ...) are to turn them into answers (plan, phase 7).
"""

from . import limits, numbers

# A condition's "when", from a closed list (also checked by the validator). "range-high-type:"
# takes a type code of the range high (a template code, TPL or K).
WHEN = (
    "always",
    "mbw-row",
    "mature-weight-over-15-or-not-entered",
    "energy-density-not-entered",
    "aafco-factor-above-1",
    "aafco-maximum-factor-above-1",
    "default-minimum",
    "protein-not-entered",
    "moisture-rows-differ",
    "moisture-rows-same",
)
# A row for foods of 12% moisture or less and its row for wetter foods (steward, 24 Oct 2026:
# say on each row which foods it is for, and whether the two differ under the requirement).
MOISTURE_TWINS = {"taurine": "taurine-wet", "taurine-mbw": "taurine-wet-mbw",
                  "copper": "copper-wet", "selenium": "selenium-wet"}
MOISTURE_TWINS.update({wet: dry for dry, wet in list(MOISTURE_TWINS.items())})
RANGE_HIGH_TYPE = "range-high-type:"


def valid_when(text):
    return text in WHEN or (text.startswith(RANGE_HIGH_TYPE) and len(text) >
                            len(RANGE_HIGH_TYPE))


def applies_to(text, requirement):
    """A condition's applies_to: "*", a species, a standard or requirement ids."""
    tokens = text.split()
    if "*" in tokens:
        return True
    return requirement is not None and (
        requirement["id"] in tokens or requirement["species"] in tokens or
        requirement["standard"] in tokens)


def _when(text, request, nid, lim):
    if text == "always":
        return True
    if text == "mbw-row":
        return nid.endswith("-mbw")
    if text == "mature-weight-over-15-or-not-entered":
        mw = request.facts.get("mature_weight_kg")
        return not (mw is not None and 0 < mw <= 15)
    if text == "energy-density-not-entered":
        return request.low("energy-density") is None and request.aafco_raises(nid)
    if text in ("aafco-factor-above-1", "aafco-maximum-factor-above-1"):
        f = request.aafco_factor
        if not (limits.number(f) and f > 1):
            return False
        return text == "aafco-factor-above-1" or lim.max_code == "AAFCO"
    if text == "default-minimum":
        return request.std(nid, "min") is None
    if text in ("moisture-rows-differ", "moisture-rows-same"):
        twin = MOISTURE_TWINS[nid]
        same = all(request.std(nid, b) == request.std(twin, b) for b in ("min", "max"))
        return same == (text == "moisture-rows-same")
    if text == "protein-not-entered":
        # The arginine minimum's protein increase reads the protein entered as low.
        protein = "protein-mbw" if nid.endswith("-mbw") else "protein"
        return request.low(protein) is None and \
            any(request.applies(f) for f in limits.ARGININE_PER_PROTEIN)
    if text.startswith(RANGE_HIGH_TYPE):
        return lim.max_code == text[len(RANGE_HIGH_TYPE):]
    raise ValueError("unknown condition case %r" % text)


def _fill(text, lim, k):
    if "{k}" in text:
        text = text.replace("{k}", numbers.to_text(k))
    for name in ("minimum", "maximum"):
        key = "{%s}" % name
        if key in text:
            text = text.replace(key, numbers.to_text(getattr(lim, name)))
    return text


def for_nutrient(data, request, nid, lim, k):
    """The conditions on one nutrient's result: [{id, limitation, depends_on, notes}]; none
    when no requirement is chosen, the limits are unavailable (lim None) or the row has no
    limit under the requirement. k: the row's multiplier K, for a K range high's text."""
    if request.requirement is None or lim is None:
        return []
    if lim.minimum is None and lim.maximum is None:
        return []
    out = []
    for row in data["conditions"]:
        if nid not in row["nutrients"].split() and row["nutrients"] != "*":
            continue
        if not applies_to(row["applies_to"], request.requirement):
            continue
        if not _when(row["when"], request, nid, lim):
            continue
        # A condition outside the template's ten known limitations has no item (steward, 24
        # Oct 2026: the cat vitamin D form and the arginine protein conditions).
        out.append({"id": row["id"], "limitation": int(row["item"]) if row["item"] else None,
                    "depends_on": _fill(row["depends_on"], lim, k),
                    "notes": row["notes"].split()})
    return out


def open_minimum(data, request, nid):
    """The open-minimums.csv row that leaves this nutrient's minimum without a verdict in this
    request, or None."""
    if request.requirement is None:
        return None
    for row in data["open_minimums"]:
        if row["requirement"] == request.requirement["id"] and row["nutrient"] == nid and \
                _when(row["when"], request, nid, None):
            return row
    return None
