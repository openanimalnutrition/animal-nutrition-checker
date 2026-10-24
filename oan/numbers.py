"""Number handling, in one place: the template's (Google Sheets') number rules.

The rules are those of the template's spreadsheet application, as the steward checked them on
19 Oct 2026 (the IG's band computation page, "Comparing at 7 decimal places" and open point 8):

- Arithmetic is IEEE 754 double precision (Python floats), in the order the specifications
  write it. Nothing is rounded except by sheet_round() and the text functions below.
- ROUND rounds the number's 15-significant-digit decimal value, half away from zero, for
  negative numbers too: ROUND(1.005, 2) is 1.01 and ROUND(0.145*3, 2) is 0.44. It does not
  round the stored binary value (Python's round() does) or the shortest decimal that reads
  back as the number (repr).
- A number turned into text has 15 significant digits; whole numbers are written plainly.
- Numbers compare within a relative 1e-12 (close()); everything else matches exactly.

Assumed, not checked in Sheets (each marked where it is used):
- an exact tie at the 15th significant digit goes to even, as "%.15g" does;
- number-to-text writes an exponent as "1.5E-07" or "1.5E+20";
- TEXT(x, "0.000") and TEXT(x, "0.00%") round like ROUND.

The four empty states are kept apart. In a sheet value: None is a blank cell, "" is empty
text, 0.0 is the number zero and "none" is the text the template writes where a standard
sets no figure. In the core: None is "not entered" and a limit with no figure is None
(oan/table.py); a zero entry is the number 0.0, never "not entered".

Input numbers (as_input_number) must be real numbers: true/false (Python counts True as 1),
NaN and Infinity (Python's JSON reader accepts both) and numbers of 1e15 or more are
rejected, and so is text, even numeric text ("15").
"""

import math
from decimal import ROUND_HALF_UP, Context, Decimal

REL_TOL = 1e-12
INPUT_LIMIT = 1e15
NONE = "none"

# Precision for rounding a 15-digit value: at most 309 integer digits plus the places kept.
_PLACES_LIMIT = 400
_CONTEXT = Context(prec=1000, rounding=ROUND_HALF_UP)


def is_number(v):
    """True for an int or float that is finite and not true/false."""
    return type(v) in (int, float) and math.isfinite(v)


def as_input_number(v):
    """(number as a float, None) for an accepted input number, else (None, reason)."""
    if isinstance(v, bool):
        return None, "true/false is not a number"
    if isinstance(v, str):
        return None, "text is not a number (write 15, not \"15\")"
    if type(v) not in (int, float):
        return None, "not a number"
    if not math.isfinite(v):
        return None, "not a finite number"
    if abs(v) >= INPUT_LIMIT:
        return None, "too large (1e15 or more)"
    return float(v), None


def decimal15(x):
    """x's 15-significant-digit decimal value (an exact tie at the 15th digit goes to even:
    assumed)."""
    return Decimal("%.15g" % x)


def sheet_round(x, places=0):
    """Sheets' ROUND(x, places): the 15-significant-digit value of x rounded half away from
    zero to 'places' decimals (negative places round to tens, hundreds, ...)."""
    if x == 0 or not math.isfinite(x):
        return x
    places = max(-_PLACES_LIMIT, min(_PLACES_LIMIT, int(places)))
    value = decimal15(x)
    if -places <= value.as_tuple().exponent:
        return float(value)
    return float(value.quantize(Decimal(1).scaleb(-places), context=_CONTEXT))


def to_text(x):
    """A number as text, as Sheets writes it in its default format: whole numbers plainly,
    others with 15 significant digits. The exponent form ("1.5E-07") is assumed."""
    if not math.isfinite(x):
        raise ValueError("a non-finite number has no text form: %r" % x)
    if x == int(x) and abs(x) < INPUT_LIMIT:
        return "%d" % x
    text = "%.15g" % x
    if "e" in text:
        mantissa, exponent = text.split("e")
        exponent = int(exponent)
        return "%sE%s%02d" % (mantissa, "-" if exponent < 0 else "+", abs(exponent))
    return text


def format_fixed(x, decimals, percent=False):
    """TEXT(x, "0.000") (decimals 3) or TEXT(x, "0.00%") (decimals 2, percent): the
    15-significant-digit value (times 100 for a percent), rounded half away from zero to
    'decimals' places (assumed to round like ROUND). A negative number that rounds to zero
    keeps its minus sign ("-0.00"): assumed."""
    if not math.isfinite(x):
        raise ValueError("a non-finite number has no text form: %r" % x)
    value = decimal15(x) * 100 if percent else decimal15(x)
    rounded = abs(value).quantize(Decimal(1).scaleb(-decimals), context=_CONTEXT)
    return ("-" if x < 0 else "") + format(rounded, "f") + ("%" if percent else "")


def close(a, b):
    """True when two numbers are equal within a relative 1e-12 (exactly equal for zero)."""
    return a == b or math.isclose(a, b, rel_tol=REL_TOL, abs_tol=0.0)
