"""The Result: what the checker returns, as one JSON object (schema "oan-check-result/2",
docs/result.schema.json).

check() is the only path from a request to a result; the GUI and the MCP server only render
what it returns, and to_json() gives the one byte form both serve. The caveats come first in
every result, from every tool. The output has no timestamps: the same request gives the same
bytes.

A request is a JSON object:
  requirement  a requirement's name (as in the template's list) or id
  animal       the animal facts, by the names in oan/inputs.py FACTS
  entries      {nutrient id: {"low": number, "high": number}}, at least one of the two, or a
               bare number, placed by the template's heading rule "(If No Req't Min, Put In
               Range)": low on a row with a minimum, high on a row without one
  subject      "diet" (the default) or "requirement range": a label only (decision 2)
A request that is not of this shape raises RequestError. A value outside its input rule is
rejected in the input report and never computed with.

Numbers are shown as the checker compares them (steward, 25 Oct 2026, after the AI-read test of
release 0.6.0 with new cases: "150.000000001" and "45.00000000000001" read as bugs): a limit
at 7 decimal places, as every band test and comparison rounds it (oan/bands.py), which also
shows a figure printed as "greater than" as printed (table.GREATER_THAN_STEP is far below 7
places); every other number at 15 significant digits.
"""

from decimal import Decimal

from . import (bands, caveats, conditions, energy, inputs, interpret, limits, numbers,
               outcomes, release, table)

SCHEMA = "oan-check-result/2"
CODE_RELEASE = "0.9.0"
SUBJECTS = ("diet", "requirement range")
REQUEST_FIELDS = ("requirement", "animal", "entries", "subject")
ENERGY_NAME, ENERGY_UNIT = "Energy", "kcal/day"
# The energy reasons that a missing animal fact causes, and the facts each names.
MISSING_FACTS = {
    "body-weight-needed": ("body_weight_kg",),
    "adult-dog-type-needed": ("adult_dog_type",),
    "adult-cat-type-needed": ("adult_cat_type",),
    "mature-weight-needed": ("mature_weight_kg",),
    "life-stage-not-covered": ("life_stage",),
    "lactation-week-and-puppies-needed": ("lactation_week", "puppies_nursing"),
    "lactation-week-and-kittens-needed": ("lactation_week", "life_stage"),
    "no-estimate-after-lactation-week-4": ("energy_intake_kcal_per_day",),
    "requirement-needed": ("requirement",),
}


class RequestError(ValueError):
    """A request that is not of the request's shape (not a value outside an input rule)."""


class Data:
    """A loaded data folder with its release, for any number of requests."""

    def __init__(self, data_dir):
        self.dir = data_dir
        self.tables = table.load(data_dir)
        rel = release.read_release(data_dir)
        self.version = rel["data_version"]
        self.sha256 = rel["content_sha256"]
        self.notes = {n["id"]: n for n in self.tables["notes"]}
        self.limitations = {int(r["item"]): r for r in self.tables["limitations"]}


def to_json(result):
    """The one byte form of a result, for the GUI's download and the MCP's text block: compact,
    with no indentation (steward, 25 Oct 2026, after the real-client test of release 0.8.0: a
    321 KB result, a quarter of it indentation, went to a file the model read with its own code,
    not to the model)."""
    import json
    return json.dumps(result, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"


def _envelope(data, tool):
    return {"schema": SCHEMA, "caveats": caveats.caveats(data.version), "tool": tool,
            "code_release": CODE_RELEASE, "data_version": data.version,
            "data_sha256": data.sha256, "template_version": caveats.TEMPLATE_VERSION,
            "verdict_status": caveats.VERDICT_STATUS, "verdict_text": caveats.VERDICT_TEXT}


def _reason_text(code):
    return caveats.REASONS.get(code, code)


def _dedupe(ids):
    out = []
    for i in ids:
        if i and i not in out:
            out.append(i)
    return out


# Requests.

def _requirement(data, value):
    """(requirements.csv row or None, input report item or None)."""
    reqs = data.tables["requirements"]
    if value is None:
        return None, {"input": "requirement", "status": "missing",
                      "reason": "requirement-needed",
                      "text": _reason_text("requirement-needed")}
    row = next((r for r in reqs if isinstance(value, str) and value in (r["name"], r["id"])),
               None)
    if row is None:
        return None, {"input": "requirement", "status": "rejected",
                      "reason": "not one of the %d requirement names or ids" % len(reqs),
                      "text": "Choose one of the requirements (list_requirements)."}
    return row, None


def _parse(data, request):
    """(requirement row, facts, raw entries {id: {side: value}}, subject, report)."""
    if not isinstance(request, dict):
        raise RequestError("the request must be a JSON object")
    unknown = sorted(k for k in request if k not in REQUEST_FIELDS)
    if unknown:
        raise RequestError("unknown request fields: %s (the fields are %s)" % (
            ", ".join(unknown), ", ".join(REQUEST_FIELDS)))
    report = []
    req, item = _requirement(data, request.get("requirement"))
    if item:
        report.append(item)
    animal = request.get("animal", {})
    if not isinstance(animal, dict):
        raise RequestError("animal must be an object of animal facts")
    facts = {}
    for field, value in animal.items():
        if field == "requirement" or field not in inputs.FACTS:
            raise RequestError("unknown animal fact %r (describe_inputs lists them)" % field)
        verdict = inputs.check_fact(field, value, data.tables)
        if verdict.status == "reject":
            report.append({"input": "animal." + field, "status": "rejected",
                           "reason": verdict.reason, "text": "Not used: %s." % verdict.reason})
        elif verdict.status == "accept":
            facts[field] = verdict.value
    entries = request.get("entries", {})
    if not isinstance(entries, dict):
        raise RequestError("entries must be an object: {nutrient id: {low, high} or a number}")
    raw = {}
    for nid, value in entries.items():
        if isinstance(value, dict):
            extra = sorted(k for k in value if k not in ("low", "high"))
            if extra:
                raise RequestError("entries.%s: only low and high are allowed" % nid)
            if value.get("low") is None and value.get("high") is None:
                raise RequestError("entries.%s: give low, high or both" % nid)
            raw[nid] = {"low": value.get("low"), "high": value.get("high"), "bare": False}
        elif value is None:
            raise RequestError("entries.%s: give a number, or low and/or high" % nid)
        else:
            raw[nid] = {"low": value, "high": None, "bare": True}
    subject = request.get("subject", "diet")
    if subject not in SUBJECTS:
        raise RequestError("subject must be one of: %s" % ", ".join(SUBJECTS))
    return req, facts, raw, subject, report


def _accept_entries(data, raw, report):
    """Each entry through its input rule: {id: {"low": x, "high": y}}, bare marked."""
    out, bare = {}, set()
    for nid, sides in raw.items():
        accepted = {}
        for side in ("low", "high"):
            if sides[side] is None:
                continue
            verdict = inputs.check_entry(nid, sides[side], data.tables)
            if verdict.status == "reject":
                where = "entries.%s" % nid if sides["bare"] else "entries.%s.%s" % (nid, side)
                report.append({"input": where, "status": "rejected", "reason": verdict.reason,
                               "text": "Not used: %s." % verdict.reason})
            elif verdict.status == "accept":
                accepted[side] = verdict.value
        if accepted:
            out[nid] = accepted
            if sides["bare"]:
                bare.add(nid)
    return out, bare


def _below_zero(data, entries, report):
    """A warning on each entry below 0, as entered (before a value is copied to a twin row):
    not physically possible (steward, 25 Oct 2026). Verdicts are unchanged."""
    for nid in sorted(entries):
        if any(v < 0 for v in entries[nid].values()):
            name = _row_info(data, nid)[0].split(" (")[0].split(",")[0].strip()
            report.append({"input": "entries." + nid, "status": "warning",
                           "reason": "below-zero",
                           "text": caveats.fill(caveats.BELOW_ZERO_ENTRY, {"name": name})})


class _Check:
    """One request's limits, the energy row's and every nutrient's."""

    def __init__(self, data, req, facts, entries):
        self.data = data
        self.req = req
        self.request = limits.Request(data.tables, req["id"] if req else None, facts, entries)

    def energy_limits(self):
        kcal = self.request.energy.kcal
        if kcal is None:
            reason = self.request.energy.reason
            return limits.Limits(limits.Unavailable(reason), None, None, None), None
        return limits.Limits(kcal, None, energy.range_high(self.data.tables, kcal),
                             limits.NO_MAXIMUM), \
            float(self.data.tables["energy"]["energy-range-high"]["figure"])

    def limits_of(self, nid):
        if nid == inputs.ENERGY_ENTRY:
            return self.energy_limits()
        return self.request.limits(nid), self.request.multiplier(nid)


def _place_bare(check, entries, bare, report):
    """A bare number goes under low on a row with a minimum, else under high."""
    for nid in sorted(bare):
        lim, _ = check.limits_of(nid)
        if lim.minimum is None:
            entries[nid] = {"high": entries[nid]["low"]}
            report.append({"input": "entries." + nid, "status": "defaulted",
                           "reason": "placed-high",
                           "text": "A single value on a row with no minimum is taken as the "
                                   "high entry (the template's heading rule)."})
        else:
            report.append({"input": "entries." + nid, "status": "defaulted",
                           "reason": "placed-low",
                           "text": "A single value on a row with a minimum is taken as the low "
                                   "entry (the template's heading rule)."})


def _twin_entries(data, check, entries, bare, report):
    """A value entered on one of a nutrient's per-Mcal and MBW rows is also checked on the other
    when that one is not entered and has a limit under the requirement: both rows take the
    diet's per-Mcal value (steward, 24 Oct 2026, after the AI-read test of release 0.5.1: an
    entry on the per-Mcal row alone missed the energy-fed check on the MBW row). A single
    value is placed on the other row by the heading rule."""
    rows = {n["id"]: n for n in data.tables["nutrients"]}
    twins = {}
    for n in rows.values():
        if n["basis"] == "per-mbw" and n["mbw_of"] and n["enterable"] == "yes":
            twins[n["mbw_of"]] = n["id"]
            twins[n["id"]] = n["mbw_of"]
    for nid in sorted(entries):
        twin = twins.get(nid)
        if twin is None or twin in entries:
            continue
        lim, _ = check.limits_of(twin)
        if lim.minimum is None and lim.maximum is None:
            continue
        sides = entries[nid]
        if nid in bare:
            value = next(iter(sides.values()))
            entries[twin] = {"high" if lim.minimum is None else "low": value}
        else:
            entries[twin] = dict(sides)
        shown = " to ".join(numbers.to_text(sides[s]) for s in ("low", "high") if s in sides)
        per_mcal = twin if rows[nid]["basis"] == "per-mbw" else nid
        report.append({"input": "entries." + twin, "status": "defaulted",
                       "reason": "checked-with-twin",
                       "text": caveats.fill(caveats.TWIN_ENTRY_TEXT, {
                           "source": nid, "value": shown, "unit": rows[per_mcal]["unit"]})})


def _mbw_rows_not_shown(data, check, entries, report):
    """An MBW row the requirement sets no limits on, entered with the same value as its per-Mcal
    row (entered, or checked with it), is not shown as a row: one input-report line names them
    all (steward, 25 Oct 2026, after the real-client test of release 0.8.0, where 38 such rows,
    each "No range", took a result to 321 KB). Its heading-rule line goes with it."""
    if check.request.requirement is None:
        return
    folded = []
    for n in data.tables["nutrients"]:
        nid, twin = n["id"], n["mbw_of"]
        if n["basis"] != "per-mbw" or not twin or nid not in entries or twin not in entries:
            continue
        lim, _ = check.limits_of(nid)
        if lim.minimum is not None or lim.maximum is not None:
            continue
        if sorted(entries[nid].values()) != sorted(entries[twin].values()):
            continue
        del entries[nid]
        folded.append(nid)
    if not folded:
        return
    gone = {"entries." + nid for nid in folded}
    report[:] = [r for r in report
                 if not (r["input"] in gone and r["reason"] in ("placed-low", "placed-high"))]
    report.append({"input": "entries", "status": "defaulted", "reason": "mbw-rows-not-shown",
                   "text": caveats.fill(caveats.MBW_ROWS_NOT_SHOWN, {
                       "requirement": check.request.requirement["name"],
                       "ids": ", ".join(folded)})})


def _computed_ratios(check, entries, report):
    """Rule 13 (steward, 25 Oct 2026): a ratio a standard sets for the requirement, not entered
    while every part of it is, is computed from the parts and checked as an entry: a part entered
    as one value counts on both sides, ranges give the lowest and highest ratios they allow (the
    numerator's low over the denominator's high, and the reverse; steward, 25 Oct 2026, as for
    the advice checks), and a part not entered is never 0. An entered ratio is checked as
    entered, with a warning when its parts, all single values, cannot give it: when no ratio the
    parts allow within their rounding comes within the entered value's rounding (each to its
    decimal places, at least one; steward, 25 Oct 2026, after the real-client test of release
    0.8.0, where 0.50 ÷ 0.62 = 0.8065 entered with parts rounded to 1.299 and 1.61 was warned
    as differing from 0.8068)."""
    request = check.request
    if request.requirement is None:
        return
    for nid, (top, bottom) in limits.RATIO_PARTS.items():
        parts = top + bottom
        if not all(p in entries for p in parts):
            continue
        single = all(len(entries[p]) == 1 for p in parts)
        values, sums = _ratio_values(entries, top, bottom, single)
        if values is None:
            continue  # a part below 0 or a denominator of 0: _ratios_not_entered says so
        fill = {"parts": _ratio_parts(parts), "sums": " and ".join(sums),
                "ratio": caveats.RATIO_NAMES[nid], "requirement": request.requirement["name"],
                "pairing": "" if single else caveats.RATIO_PAIRING}
        if nid in entries:
            if single and len(entries[nid]) == 1:
                entered = next(iter(entries[nid].values()))
                text = numbers.to_text(entered)
                if not _ratio_within_rounding(entries, top, bottom, entered):
                    report.append({"input": "entries." + nid, "status": "warning",
                                   "reason": "ratio-differs-from-parts",
                                   "text": caveats.fill(caveats.RATIO_DIFFERS,
                                                        dict(fill, entered=text))})
            continue
        if not any(limits.number(request.std(nid, b)) for b in ("min", "max")):
            continue  # not a standard's ratio: _ratios_not_entered says so
        if single:
            lim, _ = check.limits_of(nid)
            entries[nid] = {"high" if lim.minimum is None else "low": values["low"]}
        else:
            low, high = sorted((values["low"], values["high"]))
            entries[nid] = {"low": low, "high": high}
        report.append({"input": "entries." + nid, "status": "defaulted",
                       "reason": "ratio-computed",
                       "text": caveats.fill(caveats.RATIO_COMPUTED, fill)})


def _rounding_span(value):
    """(low, high) a value as entered stands for, to its last decimal place (at least one), in
    decimal arithmetic: an entry of 1.61 stands for 1.605 to 1.615, and 2 for 1.95 to 2.05."""
    d = Decimal(numbers.to_text(value))
    half = Decimal("0.5").scaleb(-max(1, -d.as_tuple().exponent))
    return d - half, d + half


def _ratio_within_rounding(entries, top, bottom, entered):
    """Whether an entered ratio and the ratios its parts (single values) allow within their
    rounding overlap, each value to its decimal places (_rounding_span)."""
    def span(parts):
        spans = [_rounding_span(next(iter(entries[p].values()))) for p in parts]
        return sum(s[0] for s in spans), sum(s[1] for s in spans)
    (t_low, t_high), (b_low, b_high) = span(top), span(bottom)
    e_low, e_high = _rounding_span(entered)
    return e_high >= t_low / b_high and (b_low <= 0 or e_low <= t_high / b_low)


def _ratio_parts_entered(entries, parts, side):
    return [next(iter(entries[p].values())) if len(entries[p]) == 1 else entries[p][side]
            for p in parts]


def _ratio_problem(entries, top, bottom):
    """Why a ratio cannot be computed from its parts entered: ("below-zero", the first part
    below 0), ("zero-denominator", None), or None. A numerator of 0 gives a ratio of 0."""
    sides = ("low", "high")
    for p in top + bottom:
        if any(v < 0 for v in entries[p].values()):
            return "below-zero", p
    if any(sum(_ratio_parts_entered(entries, bottom, side)) == 0 for side in sides):
        return "zero-denominator", None
    return None


def _ratio_values(entries, top, bottom, single):
    """A ratio from its parts entered, {side: value}, and the sums as text; (None, None) when it
    cannot be computed (_ratio_problem)."""
    if _ratio_problem(entries, top, bottom) is not None:
        return None, None
    values, sums = {}, []
    for side in ("low",) if single else ("low", "high"):
        other = "high" if side == "low" else "low"
        t, b = _ratio_parts_entered(entries, top, side), _ratio_parts_entered(entries, bottom,
                                                                              other)
        values[side] = sum(t) / sum(b)
        sums.append("%s ÷ %s = %s" % (_ratio_sum(t), _ratio_sum(b),
                                      numbers.to_display(values[side])))
    return values, sums


def _ratio_sum(values):
    texts = [numbers.to_text(v) for v in values]
    return texts[0] if len(texts) == 1 else "(%s)" % " + ".join(texts)


def _ratio_parts(parts):
    names = [caveats.RATIO_PART_NAMES[p] for p in parts]
    return names[0] if len(names) == 1 else "%s and %s" % (", ".join(names[:-1]), names[-1])


def _row_info(data, nid):
    """(name, unit, basis, ig_code, notes) of a nutrient, a template row or the energy row."""
    if nid == inputs.ENERGY_ENTRY:
        row = data.tables["energy"]["energy-range-high"]
        scoped = [n["id"] for n in data.tables["notes"] if n["scope"] == "energy"]
        return ENERGY_NAME, ENERGY_UNIT, "per-day", None, scoped + row["notes"].split()
    n = next((x for x in data.tables["nutrients"] if x["id"] == nid), None)
    if n is not None:
        unit = n["unit"]
        if n["basis"] == "per-mbw":
            # Entries and limits are per Mcal (the template's column D names the requirement's
            # basis instead, which reads as the entry's unit).
            unit = next(x["unit"] for x in data.tables["nutrients"] if x["id"] == n["mbw_of"])
        return n["name"], unit, n["basis"], n["ig_code"] or None, n["notes"].split()
    t = data.tables["template"][nid]
    return t["name"], t["unit"], "per-mbw" if nid.endswith("-mbw") else "per-mcal", None, \
        t["notes"].split()


def _number_or_none(x):
    return x if limits.number(x) else None


def _limit(x):
    """A limit as the checker compares it: at 7 decimal places (bands.PLACES); None for none
    or a limit not computed."""
    return numbers.sheet_round(x, bands.PLACES) if limits.number(x) else None


def _shown(value):
    """The result with every float at 15 significant digits (a limit is already at 7 places)."""
    if isinstance(value, float):
        return float("%.15g" % value)
    if isinstance(value, dict):
        return {k: _shown(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_shown(v) for v in value]
    return value


def _minimum_text(request, nid):
    """What a minimum of this checker's own is (caveats.MINIMUM_TEXT), or None."""
    own = request.own_minimum(nid) if request.requirement is not None else None
    if own is None:
        return None
    kind, notes = own
    how = caveats.OWN_MINIMUM_HOW[kind]
    if kind == "vitamin-d2":
        how = caveats.fill(how, {"efficiency": numbers.to_text(
            request.figure("vitamin-d2-per-vitamin-d"))})
    if notes:
        how += caveats.fill(caveats.MINIMUM_NOTES, {"notes": ", ".join(_dedupe(notes))})
    return caveats.fill(caveats.MINIMUM_TEXT, {"how": how})


def _computed_max_text(request, nid, code):
    """The two range highs computed from a minimum where it replaces NRC's figure
    (caveats.COMPUTED_MAX_TEXTS), or None."""
    if code != limits.COMPUTED or nid not in caveats.COMPUTED_MAX_TEXTS:
        return None
    if nid == "choline":
        factor, figure = limits.CHOLINE_MAX_OVER_MIN, request.std("choline", "max")
    else:
        factor = request.figure("large-breed-puppy-calcium-max-over-min")
        figure = request.figure("large-breed-puppy-calcium-max")
    return caveats.fill(caveats.COMPUTED_MAX_TEXTS[nid], {
        "factor": numbers.to_text(factor), "figure": numbers.to_text(_limit(figure))})


# Maximum types that are a standard's own figure (not the template's estimate or calculation).
STANDARD_MAXIMUM_TYPES = {code for code, kind in limits.PROVENANCE.items()
                          if kind in ("authoritative", "conditional")}


def _requirement_maximum(data, request, nid, lim):
    """Whether the requirement sets a maximum of its own for this nutrient, per Mcal or per kg
    BW^n (its per-Mcal row and its MBW row together), and if not a line saying so; where it
    sets one on the nutrient's other row only, a line naming that row (steward, 24 Oct 2026).
    A template row: set when its maximum is a standard's. None for the energy row or with no
    requirement."""
    nutrients = {n["id"]: n for n in data.tables["nutrients"]}
    if request.requirement is None or nid == inputs.ENERGY_ENTRY:
        return None
    if nid not in nutrients:
        code = lim.max_code if lim is not None else None
        return {"set": True, "text": None} if code in STANDARD_MAXIMUM_TYPES else None
    first = nutrients[nid]["mbw_of"] or nid
    family = [first] + [m for m, n in nutrients.items() if n["mbw_of"] == first]
    rows = data.tables["limits"][request.requirement["id"]]
    name = nutrients[first]["name"].split(" (For")[0].split(",")[0].strip()
    # In a sentence: "protein", but a chemical symbol stays as it is ("Ca : P ratio").
    if len(name.split(" ")[0]) > 2 and name[1].islower():
        name = name[0].lower() + name[1:]
    holders = [m for m in family if m in rows and rows[m]["max_type"] in STANDARD_MAXIMUM_TYPES]
    if holders:
        if nid in holders:
            return {"set": True, "text": None}
        other = holders[0]
        return {"set": True, "text": caveats.MAXIMUM_ON_OTHER_ROW.format(
            requirement=request.requirement["name"], nutrient=name,
            basis="MBW" if nutrients[other]["basis"] == "per-mbw" else "per Mcal", row=other)}
    basis = ""
    if nutrients[first]["basis"] == "per-mcal":
        has_mbw = any(rows[m]["min"] not in ("none", "") or rows[m]["max"] not in ("none", "")
                      for m in family[1:] if m in rows)
        basis = ", per Mcal" + (" or per kg %s" % table.MBW_BASIS[
            request.requirement["species"]].split(" ", 1)[1] if has_mbw else "")
    return {"set": False, "text": caveats.NO_MAXIMUM_TEXT.format(
        requirement=request.requirement["name"], nutrient=name, basis=basis)}


def _mbw(data, request, nid, lim, unit):
    """An MBW row's conversion: the requirement per kg BW^n a day, the energy and body weight
    it was converted with, and a line saying so; None on other rows or when not computed."""
    if not nid.endswith("-mbw") or request.requirement is None or lim is None:
        return None
    bounds = [b for b in ("minimum", "maximum") if limits.number(getattr(lim, b))]
    factors = {b: request.mbw_factor(b, nid) for b in bounds}
    if not bounds or not all(limits.number(f) for f in factors.values()):
        return None
    n = next((x for x in data.tables["nutrients"] if x["id"] == nid), None)
    amount = n["amount"] if n is not None else "IU"
    mbw_unit = "%s/%s" % (amount, table.MBW_BASIS[request.requirement["species"]])
    per = {"minimum": None, "maximum": None}
    for bound in bounds:
        per[bound] = _limit(getattr(lim, bound) / factors[bound])
    figures = ", ".join("%s %s %s (%s %s)" % (
        bound, numbers.to_text(per[bound]), mbw_unit, numbers.to_text(_limit(getattr(lim, bound))),
        unit) for bound in bounds)
    kcal = {b: request.mbw_energy(b, nid).kcal for b in bounds}
    bw = request.facts["body_weight_kg"]
    fill = {"mbw_unit": mbw_unit.split("/", 1)[1], "figures": figures, "unit": unit,
            "bw": numbers.to_text(bw)}
    which = "used" if nid in limits.MBW_NOT_RAISED and \
        kcal.get("minimum") != request.energy_fed.kcal else "fed"
    if len(set(kcal.values())) == 1:
        # One limit: its energy is named (steward, 24 Oct 2026).
        if bounds == ["minimum"]:
            name = caveats.MBW_MINIMUM_ENERGY[which]
        elif bounds == ["maximum"] and request.energy_reference.kcal is not None:
            name = caveats.MBW_MAXIMUM_ENERGY
        else:
            name = None
        kcal_text = _kcal_text(kcal[bounds[0]])
        energy_text = caveats.MBW_ENERGY.format(kcal=kcal_text) if name is None else \
            caveats.MBW_ENERGY_NAMED.format(name=name, kcal=kcal_text)
        text = caveats.MBW_TEXT.format(energy=energy_text, **fill)
    else:
        text = caveats.MBW_TEXT_TWO_ENERGIES.format(
            minimum_energy=caveats.MBW_MINIMUM_ENERGY[which],
            minimum_kcal=_kcal_text(kcal["minimum"]), ref=_kcal_text(kcal["maximum"]), **fill)
    return {"unit": mbw_unit, "minimum": per["minimum"], "maximum": per["maximum"],
            "minimum_energy_kcal_per_day": kcal.get("minimum"),
            "maximum_energy_kcal_per_day": kcal.get("maximum"),
            "body_weight_kg": bw, "text": text}


def _minimum_raise(request, nid, standard_min, unit):
    """The result's minimum_raise and the status texts' fill-ins, or None when this checker
    does not raise the standard's minimum (limits.Request.minimum_raise)."""
    r = request.minimum_raise(nid)
    if r is None:
        return None
    standard = request.requirement["standard"]
    restriction = request.facts.get("caloric_restriction_percent")
    fed, ref = request.energy_fed.kcal, request.energy_reference.kcal
    values = {"standard": standard,
              "restriction": numbers.to_display(restriction) if restriction else "",
              "fed": _kcal_text(fed) if fed else "", "ref": _kcal_text(ref) if ref else ""}
    a = request.aafco_factor
    fill = {"minimum": numbers.to_display(standard_min),
            "before": numbers.to_display(r.before), "unit": unit,
            "factor": "" if r.factor is None else caveats.fill(
                caveats.RAISE_FACTOR, {"factor": numbers.to_display(r.factor)}),
            "for_food": caveats.RAISE_FOR_FOOD if limits.number(a) and a > 1 else ""}
    supplies = "" if r.factor is None else caveats.fill(caveats.RAISE_SUPPLIES[r.reason], values)
    text = caveats.fill(caveats.MINIMUM_RAISE_TEXT, dict(
        fill, standard=standard, why=caveats.fill(caveats.RAISE_WHY_LONG[r.reason], values),
        supplies=supplies))
    return {"field": {"standard_minimum_before_raise": _limit(r.before), "factor": r.factor,
                      "reason": r.reason, "text": text},
            "fill": dict(fill, why=caveats.fill(caveats.RAISE_WHY[r.reason], values))}


def _max_type_text(code, k, provenance):
    """The kind of a range high in words (steward, 24 Oct 2026: the codes were not explained)."""
    if code is None:
        return None
    if code in caveats.MAX_TYPE_TEXTS:
        return caveats.fill(caveats.MAX_TYPE_TEXTS[code],
                            {"k": numbers.to_text(k) if k is not None else "K"})
    return interpret.kind(code, provenance) or None


def _kcal_text(kcal):
    """kcal/day in a sentence: a whole number (steward, 24 Oct 2026); the result's
    *_kcal_per_day fields keep the full figure."""
    return numbers.to_text(numbers.sheet_round(kcal, 0))


def _nutrient(data, check, nid, entries):
    request = check.request
    lim, k = check.limits_of(nid)
    name, unit, basis, ig_code, notes = _row_info(data, nid)
    unavailable = next((x for x in (lim.minimum, lim.maximum) if limits.unavailable(x)), None)
    if nid == inputs.ENERGY_ENTRY or limits.unavailable(lim.minimum):
        standard_min = None if not limits.unavailable(lim.minimum) else lim.minimum
    else:
        standard_min = request.standard_minimum(nid)
    provenance = limits.provenance(lim.max_code, request.aafco_factor, request.template_rules) \
        if lim.max_code else None
    if request.requirement is not None and nid in request.data["limits"].get(
            request.requirement["id"], {}):
        row = request.data["limits"][request.requirement["id"]][nid]
        notes = notes + row["min_notes"].split() + row["max_notes"].split()
    for fid in (limits.FIXED_MINIMUMS.get(nid), limits.FIXED_MAXIMUMS.get(nid),
                limits.DEFAULT_MINIMUMS.get(nid)):
        if fid:
            notes = notes + data.tables["template"][fid]["notes"].split()
    open_row = conditions.open_minimum(data.tables, request, nid) \
        if nid != inputs.ENERGY_ENTRY else None
    raise_ = _minimum_raise(request, nid, standard_min, unit) \
        if nid != inputs.ENERGY_ENTRY else None
    standard = request.requirement["standard"] if request.requirement else ""
    # A row with neither a minimum nor a maximum has no range high: the template's is the
    # minimum (none, read as 0) times K, which an AI reader took for a limit of 0 (steward,
    # 22 Oct 2026). The bands still use the template's 0 (oan/outcomes.py).
    no_limits = lim.minimum is None and lim.maximum is None
    out = {"id": nid, "name": name, "unit": unit, "basis": basis, "ig_code": ig_code,
           "minimum": _limit(lim.minimum),
           "verdict_minimum": _limit(standard_min),
           "minimum_text": None if nid == inputs.ENERGY_ENTRY else _minimum_text(request, nid),
           "minimum_raise": None if raise_ is None else raise_["field"],
           "maximum": _limit(lim.maximum),
           "range_high": None if no_limits else _limit(lim.range_high),
           "max_type": None if no_limits else lim.max_code,
           "max_provenance": None if no_limits else provenance,
           "max_type_text": None if no_limits else (
               _computed_max_text(request, nid, lim.max_code) or
               _max_type_text(lim.max_code, k, provenance)),
           "limits_unavailable": None if unavailable is None else {
               "reason": unavailable.reason, "text": _reason_text(unavailable.reason)},
           "mbw": _mbw(data, request, nid, None if unavailable else lim, unit),
           "requirement_maximum": _requirement_maximum(data, request, nid, lim),
           "entry": None, "low": None, "high": None, "summary": None, "other_row": None}
    if open_row is not None:
        notes = notes + open_row["notes"].split()
    given = entries.get(nid, {})
    described = {}
    for side in ("low", "high"):
        value = given.get(side)
        if value is None:
            continue
        if nid == inputs.ENERGY_ENTRY:
            outcome = _energy_outcome(value, lim)
        else:
            outcome = outcomes.describe(value, side, lim)
        reason_text = _reason_text(outcome.reason) if outcome.reason else ""
        described[side] = interpret.entry(
            value, outcome, lim, standard_min, provenance, open_row, standard, k, reason_text,
            energy_row=nid == inputs.ENERGY_ENTRY, restricted=request.restricted,
            optimal_weight=request.optimal_status == "used",
            minimum_raise=None if raise_ is None else {
                "before": raise_["field"]["standard_minimum_before_raise"],
                "fill": raise_["fill"]})
        no_max = out["requirement_maximum"]
        if no_max and not no_max["set"] and \
                described[side]["comparison_to_max"] in (interpret.ABOVE_NON_AUTHORITATIVE_MAX,
                                                         interpret.ABOVE_RANGE_HIGH):
            described[side]["status"] += " " + no_max["text"]
    # One value is the entry, with the template column it is in; low and high are the two
    # ends of a range (steward, 24 Oct 2026, after the AI-read tests: a single value in a
    # "low" slot read as a judgment of it).
    if len(described) == 1:
        side, out["entry"] = next(iter(described.items()))
        out["entry"]["placed"] = side
    elif described:
        out["low"], out["high"] = described["low"], described["high"]
        out["summary"] = "%s to %s" % (out["low"]["outcome"], out["high"]["outcome"])
    out["conditions"] = conditions.for_nutrient(data.tables, request, nid,
                                                None if unavailable else lim, k)
    for c in out["conditions"]:
        notes = notes + c["notes"]
    out["notes"] = _dedupe(notes)
    return out


def _other_rows(data, nutrients):
    """On each of a nutrient's per-Mcal and MBW rows checked together, the other's verdict
    (steward, 24 Oct 2026: the two rows gave different results for one value, and neither
    named the other)."""
    basis = {n["id"]: n["basis"] for n in data.tables["nutrients"]}
    twin = {}
    for n in data.tables["nutrients"]:
        if n["basis"] == "per-mbw" and n["mbw_of"]:
            twin[n["id"]], twin[n["mbw_of"]] = n["mbw_of"], n["id"]
    by_id = {n["id"]: n for n in nutrients}
    for n in nutrients:
        other = by_id.get(twin.get(n["id"]))
        if other is None:
            continue
        verdicts = []
        for side in ("entry", "low", "high"):
            v = other[side] and other[side]["verdict"]
            if v and v not in verdicts:
                verdicts.append(v)
        n["other_row"] = {"id": other["id"], "verdicts": verdicts,
                          "text": caveats.fill(caveats.OTHER_ROW_TEXT, {
                              "basis": "MBW" if basis[other["id"]] == "per-mbw" else "per-Mcal",
                              "row": other["id"],
                              "verdict": " and ".join(verdicts) or "no verdict"})}


def _energy_outcome(value, lim):
    if limits.unavailable(lim.minimum):
        return outcomes.Outcome(outcomes.UNAVAILABLE, lim.minimum.reason)
    from . import bands
    return outcomes.Outcome(bands.band(value, lim.minimum, lim.range_high, has_max=False),
                            None)


def _percent(x):
    return numbers.to_text(numbers.sheet_round(x * 100, 7))


def _checks(data, check, entries):
    """NRC's text checks that apply, when one of the nutrients they read is entered."""
    request = check.request
    if request.requirement is None:
        return []
    out = []
    for cid, sides in outcomes.checks(request).items():
        nids = outcomes.reads(cid)
        if not any(n in entries for n in nids):
            continue
        figures = sides["low"].figures
        fill = {}
        if cid == "la-ala-ratio":
            fill = {"{low}": numbers.to_text(figures["la-ala-ratio-low"]),
                    "{high}": numbers.to_text(next(
                        v for f, v in figures.items() if f in limits.LA_ALA_HIGH))}
        elif cid == "epa-share-range":
            fill = {"{low}": _percent(figures["epa-share-range-low"]),
                    "{high}": _percent(figures["epa-share-range-high"])}
        else:
            fill = {"{x}": _percent(figures[cid])}
        item = {"id": cid, "status": caveats.CHECK_STATUS, "reads": list(nids),
                "figures": figures, "entry": None}
        for side in ("low", "high"):
            missing = [n for n in nids if outcomes.check_entry(request, n, side) is None]
            if len(missing) == len(nids):
                item[side] = {"result": "not-entered", "text": None}
                continue
            if missing:
                # A nutrient the check needs is not entered: not checked (steward, 24 Oct 2026).
                item[side] = {"result": outcomes.NOT_ENTERED, "text": caveats.fill(
                    caveats.CHECK_NOT_ENTERED["la-ala-ratio" if cid == "la-ala-ratio" else
                                              "epa"],
                    {"missing": " and ".join(caveats.CHECK_NAMES[n] for n in missing)})}
                continue
            result = sides[side].result
            text = caveats.CHECKS.get((cid, result))
            for key, value in fill.items():
                text = text.replace(key, value) if text else text
            item[side] = {"result": result, "text": text}
        # Every nutrient read entered as one value: one result, as for the nutrients' entry.
        if all(len(entries[n]) == 1 for n in nids if n in entries):
            item["entry"], item["low"], item["high"] = item["low"], None, None
        item["caveat"] = None
        if cid == "epa-share-max-dha-only" and not limits.number(request.minimum("epa-dha")):
            item["caveat"] = caveats.DHA_NOT_COMPARED
        notes = []
        for fid in figures:
            notes += data.tables["template"][fid]["notes"].split()
        item["notes"] = _dedupe(notes)
        out.append(item)
    return out


def _factors(check):
    request = check.request
    facts = request.facts
    need = request.energy_requirement
    used = request.energy
    shortfall = request.intake_shortfall if request.requirement is not None else None
    ref, fed = request.energy_reference, request.energy_fed
    return {
        "caloric_restriction_percent": facts.get("caloric_restriction_percent"),
        "restriction_factor": request.restriction_factor,
        "aafco_dry_matter_factor": _number_or_none(request.aafco_factor),
        "energy_requirement_kcal_per_day": need.kcal,
        "energy_used_kcal_per_day": used.kcal,
        "energy_used_is": None if used.kcal is None else (
            "the intake entered" if facts.get("energy_intake_kcal_per_day") is not None
            else "the requirement's energy"),
        "energy_reason": None if used.kcal is not None else {
            "reason": used.reason, "text": _reason_text(used.reason)},
        "intake_shortfall": shortfall,
        "reference_energy_kcal_per_day": ref.kcal,
        "reference_energy_basis": _reference_basis_text(check),
        "energy_fed_kcal_per_day": fed.kcal,
        "energy_fed_is": _energy_fed_is(request),
        "energy_factor": request.energy_factor if request.requirement is not None else None,
        "optimal_body_weight": None if request.optimal_status is None else {
            "status": request.optimal_status,
            "text": caveats.OPTIMAL_WEIGHT_STATUS[request.optimal_status]},
        "energies_text": caveats.ENERGIES_TEXT,
        "body_weight_text": caveats.BODY_WEIGHT_TEXT if request.requirement is not None
        else None,
        "energy_rules": caveats.ENERGY_RULES_TEXT,
    }


def _reference_basis_text(check):
    """The reference energy's basis in words (steward, 23 Oct 2026: the notation of what the
    reference is and what it determines)."""
    req = check.req
    if req is None:
        return None
    basis = energy.reference_basis(check.data.tables, req["id"])
    if basis is None:
        return caveats.REFERENCE_BASIS["life-stage"]
    standard, figure, exponent = basis
    key = standard if standard == req["standard"] else "%s-for-%s" % (standard, req["standard"])
    dog = req["species"] == "canine"
    text = caveats.REFERENCE_BASIS[key].format(
        figure=numbers.to_text(figure), exponent=numbers.to_text(exponent),
        species="dog" if dog else "cat", who="average adult dog" if dog else "lean adult cat")
    return text if dog else text + " " + caveats.CAT_REFERENCE_TEXT


# The energy fed may not be below this share of the reference energy (steward, 23 Oct 2026).
ENERGY_FED_FLOOR = 0.10


def _guard_energy_fed(data, req, facts, report):
    """Rejects the input that puts the energy fed below ENERGY_FED_FLOOR of the reference: the
    intake when one is entered, else the optimal body weight, else the restriction."""
    if req is None:
        return
    for _ in range(3):
        r = limits.Request(data.tables, req["id"], facts, {})
        ref, fed = r.energy_reference.kcal, r.energy_fed.kcal
        if ref is None or fed is None or fed >= ENERGY_FED_FLOOR * ref:
            return
        if facts.get("energy_intake_kcal_per_day") is not None:
            field = "energy_intake_kcal_per_day"
        elif r.optimal_status == "used":
            field = "optimal_body_weight_kg"
        else:
            field = "caloric_restriction_percent"
        facts.pop(field)
        report.append({"input": "animal." + field, "status": "rejected",
                       "reason": "energy-fed-below-floor",
                       "text": caveats.ENERGY_FED_FLOOR_TEXT.format(
                           fed=_kcal_text(fed), ref=_kcal_text(ref),
                           floor=numbers.to_text(ENERGY_FED_FLOOR * 100))})


def _energy_fed_is(request):
    if request.energy_fed.kcal is None:
        return None
    if request.facts.get("energy_intake_kcal_per_day") is not None:
        return "the intake entered"
    base = "the energy at the optimal body weight" if request.optimal_status == "used" \
        else "the requirement's energy"
    return base + (" less the restriction" if request.restricted else "")


def _missing(report, nutrients):
    """Missing animal facts that leave an entered nutrient without limits."""
    reasons = set()
    for n in nutrients:
        for side in ("entry", "low", "high"):
            e = n.get(side)
            if e and e["outcome"] == outcomes.UNAVAILABLE and e["outcome_reason"]:
                reasons.add(e["outcome_reason"])
    for reason in sorted(reasons):
        for fact in MISSING_FACTS.get(reason, ()):
            item = {"input": fact if fact == "requirement" else "animal." + fact,
                    "status": "missing", "reason": reason, "text": _reason_text(reason)}
            if not any(r["input"] == item["input"] and r["status"] == "missing"
                       for r in report):
                report.append(item)


def _ratios_not_entered(check, entries, report):
    """A ratio row not entered or computed while every part of it is entered: not checked, and
    why (caveats.RATIO_NOT_ENTERED): a ratio the standard does not set is not computed (rule
    13), the requirement sets no range for it, a part entered is below 0, or a denominator
    entered is 0."""
    request = check.request
    if request.requirement is None:
        return
    for nid, (top, bottom) in limits.RATIO_PARTS.items():
        if nid in entries or not all(p in entries for p in top + bottom):
            continue
        lim, _ = check.limits_of(nid)
        fill = {"ratio": caveats.RATIO_NAMES[nid], "requirement": request.requirement["name"],
                "denominator": " + ".join(caveats.RATIO_PART_NAMES[p] for p in bottom)}
        if not (limits.number(lim.minimum) or limits.number(lim.maximum)):
            why = "no-range"
        elif any(limits.number(request.std(nid, b)) for b in ("min", "max")):
            why, part = _ratio_problem(entries, top, bottom)
            fill["part"] = caveats.RATIO_PART_NAMES.get(part, "")
        else:
            why = "not-a-standards-ratio"
        report.append({"input": "entries." + nid, "status": "warning",
                       "reason": "ratio-not-entered",
                       "text": caveats.fill(caveats.RATIO_NOT_ENTERED[why], fill)})


def _requirement_block(req, requested):
    if req is None:
        return {"requested": requested, "id": None, "name": None, "standard": None,
                "edition": None, "species": None, "life_stage": None}
    return {"requested": requested, "id": req["id"], "name": req["name"],
            "standard": req["standard"], "edition": req["edition"],
            "species": req["species"], "life_stage": req["life_stage"]}


def _root_notes(data, req):
    general = [n["id"] for n in data.tables["notes"] if n["scope"] == "table"]
    out = {"file": "data/notes.csv", "text": caveats.NOTES_TEXT, "general": general,
           "requirement": []}
    if req is not None:
        out["requirement"] = _dedupe(req["notes"].split() + req["energy_notes"].split())
    return out


def _limitations(data, nutrients):
    items = sorted({c["limitation"] for n in nutrients for c in n["conditions"]
                    if c["limitation"] is not None})
    return [{"item": i, "text": data.limitations[i]["text"],
             "notes": data.limitations[i]["notes"].split()} for i in items]


def check(data, request):
    """The Result of check_diet for a request (a dict, as parsed from JSON)."""
    req, facts, raw, subject, report = _parse(data, request)
    _guard_energy_fed(data, req, facts, report)
    entries, bare = _accept_entries(data, raw, report)
    _below_zero(data, entries, report)
    c = _Check(data, req, facts, {})
    _place_bare(c, entries, bare, report)
    _twin_entries(data, c, entries, bare, report)
    _mbw_rows_not_shown(data, c, entries, report)
    _computed_ratios(c, entries, report)
    if "puppy_body_weight_kg" in facts:
        report.append({"input": "animal.puppy_body_weight_kg", "status": "warning",
                       "reason": "not-used", "text": caveats.PUPPY_BODY_WEIGHT_NOT_USED})
    c = _Check(data, req, facts, entries)
    for nid, sides in entries.items():
        if "low" in sides and "high" in sides and sides["low"] > sides["high"]:
            report.append({"input": "entries." + nid, "status": "warning",
                           "reason": "low-above-high",
                           "text": "The low entry is above the high entry; each is described "
                                   "as entered."})
    order = [inputs.ENERGY_ENTRY] + limits.nutrient_ids(data.tables)
    nutrients = [_nutrient(data, c, nid, entries) for nid in order if nid in entries]
    _other_rows(data, nutrients)
    _computed_ratio_status(nutrients, report)
    _missing(report, nutrients)
    _ratios_not_entered(c, entries, report)
    out = _envelope(data, "check_diet")
    out.update({
        "requirement": _requirement_block(req, request.get("requirement")),
        "subject": subject,
        "inputs": {"submitted": request,
                   "normalized": {"requirement": req["id"] if req else None,
                                  "animal": facts, "entries": entries, "subject": subject}},
        "input_report": report,
        "factors": _factors(c),
        "entries_text": caveats.ENTRIES_RESULT_TEXT,
        "outcomes_text": caveats.OUTCOMES_TEXT,
        "nutrients": nutrients,
        "checks": _checks(data, c, entries),
        "limitations": _limitations(data, nutrients),
        "notes": _root_notes(data, req),
    })
    return _shown(out)


def _computed_ratio_status(nutrients, report):
    """A ratio computed from its parts (rule 13) says so on its own row's status too."""
    computed = {r["input"][len("entries."):] for r in report if r["reason"] == "ratio-computed"}
    for n in nutrients:
        if n["id"] in computed:
            for side in ("entry", "low", "high"):
                if n[side]:
                    n[side]["status"] += " " + caveats.RATIO_COMPUTED_STATUS


def get_limits(data, request):
    """Every nutrient's limits for a requirement and animal (no entries), in the envelope; with
    "nutrients" (ids), only those rows, each with its MBW row (a full get_limits is about
    150 KB; the live-call test of release 0.7.0)."""
    request = dict(request)
    if "entries" in request:
        raise RequestError("get_limits takes no entries; use check_diet")
    wanted = request.pop("nutrients", None)
    req, facts, _, subject, report = _parse(data, request)
    _guard_energy_fed(data, req, facts, report)
    c = _Check(data, req, facts, {})
    order = [inputs.ENERGY_ENTRY] + limits.nutrient_ids(data.tables)
    if wanted is not None:
        if not isinstance(wanted, list) or not wanted or \
                not all(isinstance(w, str) for w in wanted):
            raise RequestError("nutrients must be a list of nutrient ids (describe_inputs)")
        for w in wanted:
            if w not in order:
                reason = "unknown nutrient %r" % w
                report.append({"input": "nutrients." + w, "status": "rejected",
                               "reason": reason, "text": "Not used: %s." % reason})
        keep = set(wanted) | {w + "-mbw" for w in wanted}
        order = [nid for nid in order if nid in keep]
        if not order:
            raise RequestError("nutrients: no known nutrient id (describe_inputs lists them)")
        request["nutrients"] = wanted
    nutrients = [_nutrient(data, c, nid, {}) for nid in order]
    for n in nutrients:
        for side in ("entry", "low", "high", "summary", "other_row"):
            n.pop(side)
    out = _envelope(data, "get_limits")
    out.update({
        "requirement": _requirement_block(req, request.get("requirement")),
        "inputs": {"submitted": request,
                   "normalized": {"requirement": req["id"] if req else None,
                                  "animal": facts}},
        "input_report": report,
        "factors": _factors(c),
        "nutrients": nutrients,
        "limitations": _limitations(data, nutrients),
        "notes": _root_notes(data, req),
    })
    return _shown(out)


ALWAYS_READ = ("body_weight_kg", "energy_intake_kcal_per_day", "caloric_restriction_percent")
PROBED = ("mature_weight_kg", "adult_dog_type", "adult_cat_type", "life_stage",
          "lactation_week", "puppies_nursing")


def facts_read(data, rid):
    """The animal facts a requirement reads: those that change its energy (or the reason it
    has none) when left out, found by trying each life stage; the puppy body weight where the
    large-breed puppy calcium row applies; the expected mature body weight where a rule
    chooses a figure by it."""
    tables = data.tables
    req = next(r for r in tables["requirements"] if r["id"] == rid)
    full = {"body_weight_kg": 10.0 if req["species"] == "canine" else 4.0,
            "mature_weight_kg": 30.0 if req["species"] == "canine" else 5.0,
            "adult_dog_type": energy.dog_type_labels(tables)[3],
            "adult_cat_type": energy.cat_type_labels(tables)[2],
            "lactation_week": 3, "puppies_nursing": 4}
    read = set(ALWAYS_READ)
    for stage in inputs.LIFE_STAGES:
        facts = dict(full, life_stage=stage)
        whole = energy.requirement_energy(tables, rid, facts)
        for f in PROBED:
            less = dict(facts)
            less.pop(f)
            if energy.requirement_energy(tables, rid, less) != whole:
                read.add(f)
    if energy.RULES[rid] in energy.ADULT_RULES:
        read.add("optimal_body_weight_kg")
    if any(row["min_rule"] == "fediaf-late-growth-by-mature-weight" or
           row["max_rule"] == "fediaf-late-growth-by-mature-weight"
           for row in tables["limits"][rid].values()):
        read.add("mature_weight_kg")
    return [f for f in inputs.FACTS if f in read]


MAX_NOTE_IDS = 50


def get_notes(data, request):
    """The texts of notes, by id (at most MAX_NOTE_IDS), with the tab and cell of the template
    each comes from or was adapted from, in the envelope."""
    if not isinstance(request, dict) or set(request) != {"ids"} or \
            not isinstance(request["ids"], list):
        raise RequestError('get_notes takes {"ids": [note ids]}')
    ids = request["ids"]
    if not ids or len(ids) > MAX_NOTE_IDS:
        raise RequestError("give 1 to %d note ids" % MAX_NOTE_IDS)
    unknown = [i for i in ids if not isinstance(i, str) or i not in data.notes]
    if unknown:
        raise RequestError("unknown note ids: %s" % ", ".join(map(str, unknown[:10])))
    out = _envelope(data, "get_notes")
    out["note_texts"] = [{"id": i, "text": data.notes[i]["text"],
                          "origin": data.notes[i]["origin"]} for i in _dedupe(ids)]
    return out


def list_requirements(data):
    out = _envelope(data, "list_requirements")
    out["requirements"] = [
        {"id": r["id"], "name": r["name"], "standard": r["standard"], "edition": r["edition"],
         "species": r["species"], "life_stage": r["life_stage"],
         "reads": facts_read(data, r["id"])}
        for r in data.tables["requirements"]]
    return out


def describe_inputs(data):
    facts = []
    for name, (kind, rule) in inputs.FACTS.items():
        if name == "requirement":
            continue
        item = {"name": name, "kind": kind}
        if name in caveats.FACT_TEXTS:
            item["label"], item["description"] = caveats.FACT_TEXTS[name]
        if kind in ("number", "whole", "restriction"):
            item["range"] = list(rule)
        elif kind == "life-stage":
            item["items"] = list(rule)
        elif kind == "list":
            item["items"] = list(rule(data.tables))
        facts.append(item)
    entries = [{"id": inputs.ENERGY_ENTRY, "name": ENERGY_NAME, "unit": ENERGY_UNIT,
                "description": caveats.ENERGY_ENTRY_TEXT}]
    for nid in limits.nutrient_ids(data.tables):
        name, unit, basis, ig_code, _ = _row_info(data, nid)
        item = {"id": nid, "name": name, "unit": unit, "basis": basis}
        texts = [caveats.MBW_ENTRY_TEXT] if nid.endswith("-mbw") else []
        own = caveats.ENTRY_TEXTS.get(nid[:-len("-mbw")] if nid.endswith("-mbw") else nid)
        if own:
            texts.append(own)
        if texts:
            item["description"] = " ".join(texts)
        if nid in inputs.ENTRY_RANGES:
            item["range"] = list(inputs.ENTRY_RANGES[nid])
        entries.append(item)
    out = _envelope(data, "describe_inputs")
    out.update({
        "request": {
            "requirement": "a requirement's name or id (list_requirements)",
            "animal": "the animal facts below, by name; only those the requirement reads are "
                      "used",
            "entries": caveats.UNITS_TEXT + " {nutrient id: {\"low\": number, \"high\": "
                       "number}} with at least one, or a bare number: low on a row with a "
                       "minimum, high on a row without one. " + caveats.ENTRIES_TEXT,
            "subject": "diet (default) or requirement range: a label only",
        },
        "animal_facts": facts,
        "entries": entries,
    })
    return out
