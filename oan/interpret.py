"""The adequacy interpretation of one entry: its verdict, how it compares with the minimum and
the range high, the open point that leaves it without a verdict, and its status line.

Written from the IG's band computation page ("Bands and the adequacy interpretation",
"Maximum types") with the steward's answers of 22 Oct 2026 to its open points 6 and 7:
- `deficient` below the part of the minimum the applied standard sets
  (limits.Request.standard_minimum); below a minimum the template sets itself there is no
  verdict, and open point 6 is named;
- `excess` above an authoritative range high, and not below the standard's minimum; above any
  other range high the value is not excess;
- both tests compare at 7 decimal places, rounded as the template rounds, so a verdict always
  agrees with the band (open point 7).
`adequate` is never given: the band says where a value is (plan, "Result"). Every verdict is
proposed, pending ratification.
"""

from . import bands, caveats, limits, numbers, outcomes

DEFICIENT = "deficient"
EXCESS = "excess"

# comparison_to_min
BELOW_MIN = "below_min"
BELOW_TEMPLATE_MIN = "below_template_min"
AT_OR_ABOVE_MIN = "at_or_above_min"
# comparison_to_max
ABOVE_MAX = "above_max"
ABOVE_NON_AUTHORITATIVE_MAX = "above_non_authoritative_max"
NOT_ABOVE_MAX = "not_above_max"

# open_reason
OPEN_POINT_6 = "ig-open-point-6"
OPEN_POINT_6_AAFCO = "ig-open-point-6-aafco-dry-matter"
OPEN_POINT_3 = "ig-open-point-3"


def _r(x):
    return numbers.sheet_round(x, bands.PLACES)


def kind(code, provenance):
    if code == "AAFCO" and provenance == "conditional":
        return caveats.AAFCO_CONDITIONAL_KIND
    return caveats.KINDS.get(code, "")


def entry(value, outcome, lim, standard_minimum, provenance, open_minimum, standard, k,
          reason_text, energy_row=False, restricted=False, optimal_weight=False):
    """The interpretation of one entry, as a dict in the Result's order.

    value: the entry (a number); outcome: outcomes.Outcome; lim: limits.Limits;
    standard_minimum: limits.Request.standard_minimum; provenance: the range high's
    maxProvenance; open_minimum: the open-minimums.csv row that applies, or None; standard:
    the requirement's standard (NRC, AAFCO, FEDIAF); k: the multiplier of a K range high;
    reason_text: the plain words of an unavailable outcome's reason; energy_row: the energy
    row, whose minimum is an estimate; restricted: a caloric restriction is entered;
    optimal_weight: the energy fed is the energy at the optimal body weight."""
    out = {"value": value, "outcome": outcome.code, "outcome_reason": outcome.reason,
           "comparison_to_min": None, "comparison_to_max": None, "verdict": None,
           "verdict_status": caveats.VERDICT_STATUS, "open_reason": None, "status": None}
    if outcome.code in (outcomes.UNAVAILABLE, outcomes.NOT_BANDED, outcomes.NOT_ENTERED):
        if outcome.code == outcomes.UNAVAILABLE:
            out["status"] = reason_text if reason_text.startswith("Not computed") else \
                caveats.STATUS["unavailable"].replace("{reason}", reason_text)
        return out
    v = _r(value)
    minimum = lim.minimum
    below_min = limits.number(minimum) and v < _r(minimum)
    below_standard = limits.number(standard_minimum) and v < _r(standard_minimum)
    below_open = below_standard and open_minimum is not None
    if below_open:
        below_standard = False
    # A range high exists where a maximum does, or where it is the minimum times K; a row
    # with neither limit (or "No range") has none to compare with.
    has_range_high = lim.range_high is not None and outcome.code != outcomes.NO_RANGE and (
        lim.maximum is not None or limits.number(minimum))
    above = has_range_high and v > _r(lim.range_high)

    if limits.number(minimum):
        out["comparison_to_min"] = BELOW_MIN if below_standard or below_open else \
            BELOW_TEMPLATE_MIN if below_min else AT_OR_ABOVE_MIN
    if has_range_high:
        out["comparison_to_max"] = (ABOVE_MAX if provenance == "authoritative" else
                                    ABOVE_NON_AUTHORITATIVE_MAX) if above else NOT_ABOVE_MAX

    lines = []
    if below_standard:
        out["verdict"] = DEFICIENT
        lines.append(caveats.STATUS["deficient"].replace("{standard}", standard))
    elif below_open:
        out["open_reason"] = OPEN_POINT_6_AAFCO
        lines.append(caveats.STATUS["below-aafco-open-minimum"])
    elif below_min:
        out["open_reason"] = OPEN_POINT_6
        if energy_row:
            lines.append(caveats.STATUS["energy-below-estimate"])
            if optimal_weight:
                lines.append(caveats.STATUS["energy-optimal-weight"])
            if restricted:
                lines.append(caveats.STATUS["energy-restriction"])
        else:
            lines.append(caveats.STATUS["below-template-minimum"])
    elif minimum is None and outcome.code in bands.BANDS[:4]:
        out["open_reason"] = OPEN_POINT_3
        lines.append(caveats.STATUS["below-zero-no-minimum"])

    if above:
        text_kind = kind(lim.max_code, provenance)
        if provenance == "authoritative" and not below_standard:
            out["verdict"] = EXCESS
            lines.append(caveats.STATUS["excess"].replace("{kind}", text_kind))
        elif lines:
            if text_kind:
                lines.append(caveats.STATUS["also-above"].replace("{kind}", text_kind))
        elif provenance == "conditional":
            lines.append(caveats.STATUS["above-conditional"].replace("{kind}", text_kind))
        elif provenance == "template-set":
            lines.append(caveats.STATUS["above-template-set"])
        else:
            lines.append(caveats.STATUS["above-derived-provisional"].replace(
                "{k}", numbers.to_text(k) if k is not None else "K"))
    if not lines:
        if outcome.code == outcomes.NO_MINIMUM:
            lines.append(caveats.STATUS["no-minimum"])
        elif outcome.code == outcomes.NO_RANGE:
            lines.append(caveats.STATUS["no-range"])
        else:
            lines.append(caveats.STATUS["within"])
    out["status"] = " ".join(lines)
    return out
