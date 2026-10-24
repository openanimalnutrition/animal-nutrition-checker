"""Independent model of the minimum rules of the template's formulas.

Written as an independent check during the template's 21OCT26 build (19-20 Oct 2026) and copied
here, its rules for 21OCT26 only (the 18OCT26 comparisons are left out). Phase 3 gave it a data
driver: use(data) reads the figures its rules use from data/template.csv (AAFCO's presumed
energy density, the large-breed puppy calcium figures, NRC's highest LA:ALA ratios, the EPA
share of adult cats, the carbohydrate energy factors), and build_model(data) builds the tables
it reads from a data folder (the values oan/table.py computes from the printed figures), so the
impact report can re-run it on changed data. Its rules are unchanged and independent of
oan/limits.py; it uses no formula text and no evaluator.

Values: float, str, bool, None (blank) or ("#ERR", code) for an error. The model checks, per
case, the cells of TARGETS; the energy (s02 row 4), C11 and C53 it reads are the case's own
values, as the original read them from the evaluator.
"""

import json
from decimal import Decimal, ROUND_HALF_UP

import sheet_map
import sheet_view

NA = ("#ERR", "#N/A")
VALUE = ("#ERR", "#VALUE!")
DIV0 = ("#ERR", "#DIV/0!")
NONE = "none"
C11_MSG = "Select A Requirement In O1"
AR_MSG = " W/ An AAFCO Dry Matter Adjustment: Min x "
FIG = {}
# The 47 per-Mcal minimums a restriction and the AAFCO factor raise (spec section 5.1).
RAISED = (12, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 45, 51, 53, 61, 63, 67, 70,
          72, 74, 76, 78, 80, 82, 83, 85, 87, 89, 91, 92, 94, 96, 100, 102, 104, 106, 108, 110,
          112, 114, 116, 118, 120)
TARGETS = ("AS1", "C43", "C11", "E124", "C66", "C47", "L58", "N58") + tuple(
    "C%d" % r for r in RAISED)
# The summary sentences that end with the AAFCO factor (spec section 11).
AR_SUFFIX_ROWS = RAISED + (14, 43, 47, 98)


def use(data):
    """Read the figures of a loaded data folder (oan.table.load)."""
    FIG.clear()
    FIG.update({fid: float(row["figure"]) for fid, row in data["template"].items()
                if row["kind"] == "figure"})


def is_err(v):
    return isinstance(v, tuple) and len(v) == 2 and v[0] == "#ERR"


def is_num(v):
    return isinstance(v, float)


def dec15(x):
    """The 15-significant-digit decimal value of a double: how Sheets' ROUND sees a number
    (batch 8f and its follow-up); TEXT is assumed to see it the same way."""
    return Decimal("%.15g" % x)


class Model:
    def __init__(self, names_row2, table, s01_keys):
        """names_row2: [(column letter, text or None)] for s02 B2..AT2 in order (position 1 =
        B). table: {lower-case key: {column letter: value}} for the first s02 row (5..157) with
        that key in column B. s01_keys: {s01 row number: the column B text}."""
        self.row2 = names_row2
        self.table = table
        self.keys = s01_keys
        self.cols = [c for c, _ in names_row2]

    # ------------------------------------------------------------ selection
    def position(self, o1):
        """AX1: blank O1 (or empty text) -> None (NA()); else the first exact,
        case-insensitive match among E2:AT2 (positions 4 and up, counted from B); None for no
        match. Only text can match."""
        if not isinstance(o1, str) or o1 == "":
            return None
        for i, (c, name) in enumerate(self.row2):
            if i + 1 >= 4 and isinstance(name, str) and name != "" and name.lower() == o1.lower():
                return i + 1
        return None

    def value(self, row, k, plus=0):
        """VLOOKUP(s01 B<row>, s02 B5:AT157, k + plus, FALSE)."""
        if k is None:
            return NA
        key = self.keys[row].lower()
        col = self.cols[k - 1 + plus]
        if key not in self.table:
            return NA
        return self.table[key][col]

    # ------------------------------------------------------------ factors
    @staticmethod
    def restriction(g10):
        """Item 15: 1/(1-(G10/100)) when G10 holds a number above 0; otherwise 1."""
        if is_num(g10) and g10 > 0:
            d = 1 - (g10 / 100)
            return DIV0 if d == 0 else 1 / d
        return 1.0

    @staticmethod
    def raised(g10):
        return is_num(g10) and g10 > 0

    def aafco(self, o1, g130):
        """3a A (D1): 4/G130 when the selection is an AAFCO requirement and G130 is a number
        in (0, 4); else 1; an error (#N/A) when O1 matches no requirement."""
        if self.position(o1) is None:
            return NA
        presumed = FIG["aafco-energy-density"]
        if o1[:5].lower() == "aafco" and is_num(g130) and 0 < g130 < presumed:
            return presumed / g130
        return 1.0

    # ------------------------------------------------------------ the minimum rules
    def min_raised_new(self, row, o1, g10, g130):
        """The 48 minimums raised by G10 (47 in column C and the arginine base AS1); the
        raised branch tests the looked-up value (finding 6)."""
        k = self.position(o1)
        a = self.aafco(o1, g130)
        if is_err(a):
            return a
        v = self.value(row, k)
        if self.raised(g10) or a != 1:
            f = self.restriction(g10)
            if not is_num(v):
                return v
            return f if is_err(f) else (a * f) * v
        return v

    def fat_new(self, row, o1, g130):
        """3b C: the fat min takes only the AAFCO factor."""
        k = self.position(o1)
        a = self.aafco(o1, g130)
        if is_err(a):
            return a
        v = self.value(row, k)
        if a != 1:
            return a * v if is_num(v) else v
        return v

    def c66(self, o1, g10, g65, k4, c11):
        """Row 66, NRC 4-14 wk puppies of large expected size: 3 g/Mcal, or 0.54 g Ca/kg BW
        (G65) converted with the row 11 energy, each raised for G10 (the BW part only without
        an intake in K4)."""
        if not (isinstance(o1, str) and o1.lower() == "nrc ra puppy 4-14 wk growth"):
            return NONE
        f = self.restriction(g10)
        if is_err(f):
            return f
        three = FIG["large-breed-puppy-calcium-min"] * f
        if is_num(g65) and g65 > 0:
            if not is_num(c11):
                return c11 if is_err(c11) else VALUE
            k4f = 1.0 if (is_num(k4) and k4 > 0) else f
            per_kg = FIG["large-breed-puppy-calcium-per-kg-body-weight"]
            return max(three, ((per_kg * g65) / (c11 / 1000)) * k4f)
        return three

    def c47(self, o1, g10, g130, la):
        """Item 11 (+3a): the ALA min, raised like the other mins, then floored by LA min / 16
        under the NRC puppy and bitch selections and by LA min / 26 under NRC RA Dog
        Maintenance."""
        k = self.position(o1)
        if k is None:
            return NA
        x = self.value(47, k)
        a = self.aafco(o1, g130)
        if is_err(a):
            return a
        if self.raised(g10) or a != 1:
            f = self.restriction(g10)
            r = x if not is_num(x) else (f if is_err(f) else (a * f) * x)
        else:
            r = x
        if is_err(r):
            return r
        if is_err(la):
            return la
        n_la = la if is_num(la) else 0.0
        if k in (20, 22, 38) and n_la > 0:
            high = FIG["la-ala-ratio-high-growth-reproduction"]
            return VALUE if isinstance(r, str) else max(r, n_la / high)
        if k == 4 and n_la > 0:
            return VALUE if isinstance(r, str) else max(r, n_la / FIG["la-ala-ratio-high-adult"])
        return r

    def c11(self, o1, k4, energy):
        """C11: the message when O1 is blank or no requirement name; else K4 when it holds a
        number above 0, else the requirement's energy (s02 row 4)."""
        if self.position(o1) is None:
            return C11_MSG
        if is_num(k4) and k4 > 0:
            return k4
        return energy

    def e124(self, o1, g10, g130):
        """E124: the requirement's carbohydrate max; when it is 'none', (1000 - (C12 x 4 +
        C43 x 9)) / 4 from the protein and fat mins, floored at 0 (8e A)."""
        k = self.position(o1)
        if k is None:
            return NA
        v = self.value(124, k, 1)
        c12, c43 = self.min_raised_new(12, o1, g10, g130), self.fat_new(43, o1, g130)
        if v != NONE:
            return v
        for x in (c12, c43):
            if is_err(x):
                return x
            if not is_num(x):
                return VALUE
        calc = (1000 - ((c12 * FIG["carbohydrate-max-protein-energy"]) +
                        (c43 * FIG["carbohydrate-max-fat-energy"]))) / \
            FIG["carbohydrate-max-carbohydrate-energy"]
        return max(0.0, calc)

    @staticmethod
    def text3(x):
        """TEXT(x, "0.000"): 3 decimals of the 15-digit decimal value, half away from zero
        (assumed, as in the evaluator)."""
        d = dec15(x).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        return ("-" if x < 0 else "") + format(abs(d), "f")

    def ar_suffix(self, o1, g130, c_value):
        """The suffix a factored row's sentence ends with: when the AAFCO factor is a number
        other than 1 and the row's min is a number."""
        a = self.aafco(o1, g130)
        if is_err(a) or not is_num(c_value) or a == 1:
            return ""
        return AR_MSG + self.text3(a)

    @staticmethod
    def round7(x):
        """ROUND(x, 7): the 15-digit decimal value rounded half away from zero."""
        if x == 0:
            return 0.0
        return float(dec15(x).quantize(Decimal("1e-7"), rounding=ROUND_HALF_UP))

    def row58(self, o1, epa_dha, epa, c53):
        """The NRC adult cat EPA share check, and the DHA min check (3e C)."""
        if not (isinstance(o1, str) and o1.lower() == "nrc ra cat maintenance"):
            return "Not applicable"
        t = 0.0 if epa_dha is None else epa_dha
        e = 0.0 if epa is None else epa
        if t <= 0 and e <= 0:
            return "OK"
        if t >= 0 and (e <= 0 or t * FIG["epa-share-max-dha-only"] < e):
            return "Outside NRC >0-20% of EPA + DHA = EPA"
        if is_num(c53) and self.round7(t - e) < self.round7(c53):
            return "DHA (EPA + DHA minus EPA) below NRC min"
        return "OK"


# ---------------------------------------------------------------- the data driver

def build_model(data, mature_weight_kg=None):
    """The model on a data folder: s02 row 2's names, the keyed rows (first row of each key)
    and the Standards tab's column B, from the data (oan/table.py) through the test cell map."""
    view = sheet_view.TableView(data, mature_weight_kg)
    names = {}
    for rid, (min_col, _, _) in sheet_map.REQUIREMENT_COLUMNS.items():
        names[min_col] = view.names[rid]
    row2 = [(c, names.get(c, "Requirement Name:" if c == "D" else None))
            for c in _columns("B", "AT")]
    table = {}
    for nid, r in sorted(sheet_map.NUTRIENT_ROWS.items(), key=lambda kv: kv[1]):
        key = view.nutrients[nid]["name"].lower()
        if key in table:
            continue
        cells = {}
        for col in _columns("E", "AT"):
            v, _ = view.cell("s02!%s%d" % (col, r))
            cells[col] = v
        table[key] = cells
    keys = {r: sheet_map.S01_LABELS.get(r, view.nutrients[nid]["name"])
            for r, nid in sheet_map.S01_ROWS.items()}
    keys.update({r: data["template"][nid]["name"] for r, nid in sheet_map.TEMPLATE_ROWS.items()})
    return Model(row2, table, keys)


def _columns(first, last):
    out, n = [], sheet_view._column_number(first)
    while True:
        col = _letters(n)
        out.append(col)
        if col == last:
            return out
        n += 1


def _letters(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _jv(v):
    """Model value -> vector encoding."""
    if is_err(v):
        return {"error": v[1]}
    return v


def _from_vector(v):
    if isinstance(v, dict):
        return ("#ERR", v["error"])
    return v


def expect(m, inp, known, t):
    """The model's value of target cell t for one case; known: the case's own values."""
    o1, g10, g130 = inp.get("O1"), inp.get("G10"), inp.get("G130")
    if t == "AS1":
        return m.min_raised_new(14, o1, g10, g130)
    if t == "C43":
        return m.fat_new(43, o1, g130)
    if t == "C11":
        return m.c11(o1, inp.get("K4"), _from_vector(known["G4"]))
    if t == "E124":
        return m.e124(o1, g10, g130)
    if t == "C66":
        return m.c66(o1, g10, inp.get("G65"), inp.get("K4"), _from_vector(known["C11"]))
    if t == "C47":
        return m.c47(o1, g10, g130, m.min_raised_new(45, o1, g10, g130))
    if t in ("L58", "N58"):
        tt, e = (inp.get("G53"), inp.get("G55")) if t == "L58" else (inp.get("I53"), inp.get("I55"))
        return m.row58(o1, tt, e, _from_vector(known["C53"]))
    return m.min_raised_new(int(t[1:]), o1, g10, g130)


def same(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return a == b or abs(a - b) <= 1e-12 * max(abs(a), abs(b))
    return type(a) is type(b) and a == b


def run(data, cases, cells):
    """(values checked, [(case id, cell, expected, model)], cases skipped) over the formulas
    cases: every target cell, and the AAFCO factor suffix of each summary sentence given.
    Skipped as in the original: the wildcard group and an O1 matching no requirement."""
    use(data)
    models = {}
    checked, bad, skipped = 0, [], 0
    for case in cases:
        inp = case["inputs"]
        if case["group"] == "selection-wildcard":
            skipped += 1
            continue
        e3 = inp.get("E3")
        e3 = e3 if isinstance(e3, float) else None
        if e3 not in models:
            models[e3] = build_model(data, e3)
        m = models[e3]
        if m.position(inp.get("O1")) is None:
            skipped += 1
            continue
        known = dict(zip(cells, case["values"]))
        for t in TARGETS:
            checked += 1
            try:
                got = _jv(expect(m, inp, known, t))
            except Exception as ex:  # a model or driver defect: a mismatch, never hidden
                got = "#MODEL %r" % ex
            if not same(known[t], got):
                bad.append((case["id"], t, known[t], got))
        for ref, sentence in (case.get("descriptors") or {}).items():
            row = int(ref[2:]) if ref.startswith("AR") else None
            if row not in AR_SUFFIX_ROWS or not isinstance(sentence, str):
                continue
            checked += 1
            suffix = m.ar_suffix(inp.get("O1"), inp.get("G130"),
                                 _from_vector(known.get("C%d" % row)))
            if (suffix and not sentence.endswith(suffix)) or (not suffix and AR_MSG in sentence):
                bad.append((case["id"], ref, sentence, "suffix %r" % suffix))
    return checked, bad, skipped


def load(path):
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    return doc["cases"], doc["cells"]
