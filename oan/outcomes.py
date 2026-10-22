"""What the checker says about each entry: a band, or another outcome; and NRC's text checks.

Written from the IG's band computation page ("Rows with no minimum", "Rows with no range",
"Outcomes other than a band") and the formulas specification (section 7, row 58). The
outcome codes other than the 14 bands are the code's own (plan, Result: they fill IG open
point 1 in the code's vocabulary). Verdicts (deficient, excess) are not decided here.

The text checks are NRC's advice on fatty acids, which the template checks as text: the
LA:ALA ratio (NRC dog requirements), and EPA's share of EPA + DHA (NRC requirements), with
NRC adult cats' DHA minimum. Their figures and the requirements they apply to are in
data/template.csv; each check reads the low entries together, and the high entries
together, as the template does.
"""

from collections import namedtuple

from . import bands, limits, numbers

NOT_ENTERED = "not-entered"
NO_MINIMUM = "no-minimum"
NO_RANGE = bands.NO_RANGE
UNAVAILABLE = "unavailable"
NOT_BANDED = "not-banded"

Outcome = namedtuple("Outcome", "code reason")  # reason: why the outcome is unavailable


def describe(value, side, lim):
    """The Outcome of one entry (side "low" or "high") against a nutrient's Limits.

    The order is the template's: nothing entered; a row that is not banded (EPA alone);
    under low, a row with no minimum (a value of 0 or more is not described); an unavailable
    limit; "No range"; the band.
    """
    if value is None:
        return Outcome(NOT_ENTERED, None)
    if lim.range_high is None and not limits.unavailable(lim.minimum) and \
            not limits.unavailable(lim.maximum):
        return Outcome(NOT_BANDED, None)  # EPA alone: entered for the EPA share checks only
    if side == "low":
        if limits.unavailable(lim.minimum):
            return Outcome(UNAVAILABLE, lim.minimum.reason)
        if lim.minimum is None and value >= 0:
            return Outcome(NO_MINIMUM, None)
    for x in (lim.minimum, lim.maximum):
        if limits.unavailable(x):
            return Outcome(UNAVAILABLE, x.reason)
    return Outcome(bands.band(value, lim.minimum, lim.range_high, lim.maximum is not None),
                   None)


# Text check results.
OK = "ok"
OUTSIDE = "outside"
ABOVE_MAXIMUM = "above-maximum"
DHA_BELOW_MINIMUM = "dha-below-minimum"

# check id -> its figures (data/template.csv); a check applies when its figures do.
CHECKS = {
    "la-ala-ratio": ("la-ala-ratio-low", limits.LA_ALA_HIGH),
    "epa-share-max": ("epa-share-max",),
    "epa-share-range": ("epa-share-range-low", "epa-share-range-high"),
    "epa-share-max-dha-only": ("epa-share-max-dha-only",),
}

# A check's result for one side: the result code and the figures it used, by id.
Check = namedtuple("Check", "result figures")


def _entry(request, nid, side):
    """An entry for a text check: nothing entered counts as 0, as in the template."""
    value = request.entries.get(nid, {}).get(side)
    return 0.0 if value is None else value


def _la_ala(la, ala, low, high):
    if la <= 0 and ala <= 0:
        return OK
    if la > 0 and ala <= 0:
        return OUTSIDE
    ratio = la / ala
    return OUTSIDE if ratio < low or ratio > high else OK


def _epa_share_max(total, epa, high):
    if total <= 0 and epa <= 0:
        return OK
    if epa == 0:
        return OK
    return ABOVE_MAXIMUM if epa > (high * total) else OK


def _epa_share_range(total, epa, low, high):
    if total <= 0 and epa <= 0:
        return OK
    return OUTSIDE if (total * low) > epa or (total * high) < epa else OK


def _epa_share_max_dha_only(total, epa, high, dha_minimum):
    """EPA included but at most a share of EPA + DHA; then DHA (EPA + DHA minus EPA) at
    least the EPA + DHA minimum, compared at 7 decimal places (spec section 7)."""
    if total <= 0 and epa <= 0:
        return OK
    if total >= 0 and (epa <= 0 or (total * high) < epa):
        return OUTSIDE
    if limits.number(dha_minimum) and \
            numbers.sheet_round(total - epa, 7) < numbers.sheet_round(dha_minimum, 7):
        return DHA_BELOW_MINIMUM
    return OK


def checks(request):
    """{check id: {"low": Check, "high": Check}} for the checks that apply to the request's
    requirement."""
    out = {}
    for cid, (first, *rest) in CHECKS.items():
        if not request.applies(first):
            continue
        figures = {first: request.figure(first)}
        for fid in rest:
            if isinstance(fid, tuple):
                fid = next(f for f in fid if request.applies(f))
            figures[fid] = request.figure(fid)
        out[cid] = {side: Check(_check(cid, request, side, figures), figures)
                    for side in ("low", "high")}
    return out


def _check(cid, request, side, figures):
    if cid == "la-ala-ratio":
        low = figures["la-ala-ratio-low"]
        high = next(v for k, v in figures.items() if k in limits.LA_ALA_HIGH)
        return _la_ala(_entry(request, "linoleic-acid", side),
                       _entry(request, "alpha-linolenic-acid", side), low, high)
    total, epa = _entry(request, "epa-dha", side), _entry(request, "epa", side)
    if cid == "epa-share-max":
        return _epa_share_max(total, epa, figures["epa-share-max"])
    if cid == "epa-share-range":
        return _epa_share_range(total, epa, figures["epa-share-range-low"],
                                figures["epa-share-range-high"])
    return _epa_share_max_dha_only(total, epa, figures["epa-share-max-dha-only"],
                                   request.minimum("epa-dha"))
