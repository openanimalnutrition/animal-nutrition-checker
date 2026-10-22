"""The 14 bands: which band of a row a value is in.

Written from the IG's band computation page ("The 14 bands", "Rows with no range"). The
band codes are the IG's nutrient-decile codes. Every band test and every comparison in the
"No range" check is made at 7 decimal places, rounded as the template rounds
(numbers.sheet_round); nothing else is rounded.
"""

from . import numbers

BANDS = (
    "below-min-lt25",
    "below-min-25-50",
    "below-min-50-75",
    "below-min-75-100",
    "range-d1",
    "range-d2",
    "range-d3",
    "range-d4",
    "range-d5",
    "range-d6",
    "range-d7",
    "range-d8",
    "range-d9",
    "range-d10",
)
NO_RANGE = "no-range"
BELOW_MIN_FRACTIONS = (0.25, 0.5, 0.75)
DECILE_FRACTIONS = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
PLACES = 7


def lower_edges(minimum, range_high):
    """The lower edges of bands 2 to 14, in order (band 1 is open below).

    minimum: the row's minimum, or None on a row with no minimum (its below-minimum edges
    and its base are then 0). range_high: the row's maximum, or its computed range high.
    Each decile edge is computed as the template does: range high minus base, times the
    fraction, plus base.
    """
    base = 0.0 if minimum is None else minimum
    return [base * f for f in BELOW_MIN_FRACTIONS] + [base] + [
        ((range_high - base) * f) + base for f in DECILE_FRACTIONS]


def _r(x):
    return numbers.sheet_round(x, PLACES)


def band(value, minimum, range_high, has_max):
    """The band code of a value, or NO_RANGE.

    "No range" when the row has no maximum, its range high is not above its base, and the
    row has no minimum or the value is at or above it. Otherwise the value is in the band
    before the first lower edge it is below, or in the top band.
    """
    base = 0.0 if minimum is None else minimum
    if (not has_max and _r(range_high) <= _r(base)
            and (minimum is None or _r(value) >= _r(minimum))):
        return NO_RANGE
    v = _r(value)
    for code, edge in zip(BANDS[1:], lower_edges(minimum, range_high)):
        if v < _r(edge):
            return BANDS[BANDS.index(code) - 1]
    return BANDS[-1]
