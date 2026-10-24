"""Independent model of the template's value rules on the Standards tab.

Written as an independent check during the template's 21OCT26 build (19-20 Oct 2026) and copied
here. Phase 3 gave it a data driver: use(data) reads the template's figures it needs
(data/template.csv: the vitamin D2 efficiency, the taurine default maximum, the MCT maximum)
and FEDIAF late growth's two pairs of figures, and table_from_data(data) builds the requirement
table it reads from a data folder (the values oan/table.py computes from the printed figures,
checked against the released table in phase 1a), so the impact report can re-run it on changed
data. Its rules are unchanged and independent of oan/limits.py; its original 8a/4d rules for
formula cells are not needed, because the data folder's derived cells arrive computed.

Not modelled (taken from the case's own outputs as data): G4 (the daily energy), C14
and C15 (arginine), C48/E48 (ALA MBW) and the AR sentences.
"""

import json
import os
import sys
from decimal import Decimal, ROUND_HALF_UP

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
import sheet_map  # noqa: E402
from oan import table as oan_table  # noqa: E402

NONE = "none"
VALUE_ERR = {"error": "#VALUE!"}
BANDS = ["Very Severely Restricted (<25% of Min)", "Severely Restricted (25 to <50% of Min)",
         "Moderately Restricted (50 to <75% of Min)", "Slightly Restricted (75 to <100% of Min)",
         "Lowest/Just Above Min (Min to <10% of Range)", "Lower (10 to <20% of Range)",
         "Low (20 to <30% of Range)", "Low Moderate (30 to <40% of Range)",
         "Mid Moderate (40 to <50% of Range)", "High Moderate (50 to <60% of Range)",
         "High (60 to <70% of Range)", "Higher (70 to <80% of Range)",
         "Near Highest (80 to <90% of Range)", "Highest (90% of Range or Greater)"]
NO_MIN = "No min requirement &/or no min amount entered to describe"
EDGE_COLS = ["Q", "S", "U", "W", "Y", "AA", "AC", "AE", "AG", "AI", "AK", "AM", "AO"]
EDGE_FRAC = {"Y": 0.1, "AA": 0.2, "AC": 0.3, "AE": 0.4, "AG": 0.5, "AI": 0.6, "AK": 0.7,
             "AM": 0.8, "AO": 0.9}
RAISED = {12, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 45, 51, 53, 61, 63, 67, 70,
          72, 74, 76, 78, 80, 82, 83, 85, 87, 89, 91, 92, 94, 96, 100, 102, 104, 106, 108, 110,
          112, 114, 116, 118, 120}
DOG_SELECTIONS = {"NRC RA Dog Maintenance", "AAFCO Dog Maintenance",
                  "FEDIAF Dog (MER 95 kcal/kg^0.75)", "FEDIAF Dog (MER 110 kcal/kg^0.75)",
                  "NRC RA Puppy 4-14 Wk Growth", "NRC RA Puppy 14 Wk+ Growth",
                  "AAFCO Dog Growth (Small & Medium) and Reproduction",
                  "AAFCO Large Breed Dog Growth",
                  "FEDIAF Dog Early Growth (< 14 wk) & Reproduction",
                  "FEDIAF Dog Late Growth (>/= 14 wk)",
                  "NRC RA Dog Late Gestation & Peak Lactation"}
NOT_MODELLED = {"G4", "C14", "C15", "C48", "E48"}
# The figures read from the data (use(data)).
FIG = {}
LATE_GROWTH = {}


def use(data):
    """Read the figures of a loaded data folder (oan.table.load)."""
    FIG.clear()
    FIG.update({fid: float(row["figure"]) for fid, row in data["template"].items()
                if row["kind"] == "figure"})
    rows = data["limits"]["fediaf-dog-late-growth"]
    for nid, bound, cell in (("calcium", "min", (52, "AE")), ("ca-p-ratio", "max", (56, "AF"))):
        figures, _ = oan_table.parse_figure(rows[nid][bound])
        LATE_GROWTH[cell] = tuple(float(f) for f in figures)


def split(a1):
    i = 0
    while a1[i].isalpha():
        i += 1
    return a1[:i], int(a1[i:])


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def N(v):
    """Sheets N(): a number is itself, TRUE 1, FALSE 0, anything else (blank, text) 0."""
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    return float(v) if is_num(v) else 0.0


def r7(x):
    """ROUND(x, 7) as Sheets does it (batch 8f): the 15-significant-digit decimal value, half
    away from zero."""
    return float(Decimal("%.15g" % x).quantize(Decimal("1e-7"), rounding=ROUND_HALF_UP))


def is_err(v):
    return isinstance(v, dict) and "error" in v


def same(e, a):
    if isinstance(e, bool) or isinstance(a, bool):
        return type(e) is type(a) and e == a
    if is_num(e) and is_num(a):
        return e == a or abs(e - a) <= 1e-12 * max(abs(e), abs(a))
    return e == a


def table_from_data(data):
    """The requirement table the model reads, built from a data folder: the 21 selections
    with their MIN and MAX columns, each keyed row's cells, and the Standards tab's keys and
    multipliers K."""
    names = {r["id"]: r["name"] for r in data["requirements"]}
    selections = [{"name": names[rid], "min_col": cols[0], "max_col": cols[1]}
                  for rid, cols in sheet_map.REQUIREMENT_COLUMNS.items()]
    nutrients = {n["id"]: n for n in data["nutrients"]}
    computed = {rid: oan_table.compute_limits(data, rid) for rid in names}
    rows = []
    for nid, r in sheet_map.NUTRIENT_ROWS.items():
        cells = {}
        for rid, (min_col, max_col, _) in sheet_map.REQUIREMENT_COLUMNS.items():
            low, high = computed[rid][nid]
            cells[min_col] = NONE if low is None else low
            cells[max_col] = NONE if high is None else high
        rows.append({"row": r, "key": nutrients[nid]["name"], "unit": nutrients[nid]["unit"],
                     "cells": cells})
    s01 = []
    for r, nid in list(sheet_map.S01_ROWS.items()) + list(sheet_map.TEMPLATE_ROWS.items()):
        row = nutrients.get(nid) or data["template"][nid]
        try:
            k = float(row["k"])
        except ValueError:
            k = None
        s01.append({"row": r, "key": sheet_map.S01_LABELS.get(r, row["name"]), "K": k})
    return {"selections": selections, "rows": rows, "s01_rows": s01}


class Model:
    def __init__(self, table):
        self.sel = [s["name"] for s in table["selections"]]
        self.selinfo = {s["name"].lower(): s for s in table["selections"]}
        self.rows = {r["row"]: r for r in table["rows"]}
        self.first_row = {}
        for r in sorted(self.rows):
            k = self.rows[r]["key"]
            if isinstance(k, str) and k and k.lower() not in self.first_row:
                self.first_row[k.lower()] = r
        self.s01 = {r["row"]: r for r in table["s01_rows"]}

    # ------------------------------------------------------------ the table
    def cell(self, r, col, inp):
        """A requirement-table cell; 5f's two cells follow E3 (spec-values section 6)."""
        if (r, col) in LATE_GROWTH:
            e3 = N(inp.get("E3"))
            small, other = LATE_GROWTH[(r, col)]
            return small if 0 < e3 <= 15 else other
        if col == "B":
            return self.rows[r]["key"]
        if col == "C":
            return self.rows[r]["unit"]
        return self.rows[r]["cells"].get(col)

    def k(self, o1):
        s = self.selinfo.get(o1.lower()) if isinstance(o1, str) and o1 else None
        return s

    def value(self, key, which, inp):
        s = self.k(inp.get("O1", "NRC RA Dog Maintenance"))
        r = self.first_row[key.lower()]
        return self.cell(r, s["min_col"] if which == "min" else s["max_col"], inp)

    # ------------------------------------------------------------ s01
    def factors(self, inp):
        o1 = inp.get("O1", "NRC RA Dog Maintenance")
        g10, g130 = inp.get("G10"), inp.get("G130")
        restricted = is_num(g10) and g10 > 0
        f = 1 / (1 - (g10 / 100)) if restricted else 1.0
        presumed = FIG["aafco-energy-density"]
        a = presumed / g130 if (o1[:5].upper() == "AAFCO" and is_num(g130) and
                                0 < g130 < presumed) else 1.0
        return restricted, f, a

    def c11(self, inp, known):
        k4 = inp.get("K4")
        return k4 if is_num(k4) and k4 > 0 else known["G4"]

    def mbw(self, v, inp, known):
        if v == NONE:
            return NONE
        o1 = inp.get("O1", "NRC RA Dog Maintenance")
        e = 0.75 if o1 in DOG_SELECTIONS else 0.67
        c11 = self.c11(inp, known)
        b3 = inp.get("B3", 15.0)
        if not is_num(c11):
            return VALUE_ERR
        return v * ((b3 ** e / c11) * 1000)

    def compute(self, inp, known, want):
        """Fill `known` with every modelled cell `want` needs (s01 refs as 'C63', s02 as
        's02!AE52')."""
        restricted, f, a = self.factors(inp)
        o1 = inp.get("O1", "NRC RA Dog Maintenance")

        def get(ref):
            if ref in known:
                return known[ref]
            v = calc(ref)
            known[ref] = v
            return v

        def key(r):
            return self.s01[r]["key"]

        def calc(ref):
            if ref.startswith("s02!"):
                col, r = split(ref[4:])
                return self.cell(r, col, inp)
            col, r = split(ref)
            if ref == "C11":
                return self.c11(inp, known)
            if ref == "N4":
                g4, k4 = known["G4"], inp.get("K4")
                ok = is_num(g4) and is_num(k4) and g4 > 0 and k4 > 0 and k4 < g4
                return (g4 - k4) / g4 if ok else ""
            if ref == "K69" or col == "K":
                return self.s01[r]["K"]
            is_mbw = isinstance(key(r), str) and key(r).endswith(" MBW")
            if col == "C":
                if r == 99:
                    if o1 in DOG_SELECTIONS:
                        return NONE
                    c97 = get("C97")
                    return NONE if c97 in ("", NONE) else c97 / FIG["vitamin-d2-per-vitamin-d"]
                v = self.value(key(r), "min", inp)
                if is_mbw:
                    return self.mbw(v, inp, known)
                if r in RAISED and (restricted or a != 1):
                    return (a * f) * v if is_num(v) else NONE
                return v
            if col == "E":
                if r in (39, 41):
                    if get("C38") == NONE:
                        return FIG["taurine-max-default"]
                    if get("C%d" % r) == NONE:
                        return NONE
                    return self.mbw(self.value(key(r), "max", inp), inp, known)
                if r == 62:
                    return FIG["mct-max"]
                if r == 99:
                    if o1 in DOG_SELECTIONS:
                        return NONE
                    e97 = get("E97")
                    return NONE if e97 in ("", NONE) else e97
                if r == 69:
                    v = self.value(key(r), "max", inp)
                    if is_num(v):
                        return v
                    e63, c67 = get("E63"), get("C67")
                    if is_num(e63) and is_num(c67):
                        return e63 / c67 if c67 > 0 else NONE
                    return NONE
                v = self.value(key(r), "max", inp)
                return self.mbw(v, inp, known) if is_mbw else v
            if col == "AP":
                e, c, kk = get("E%d" % r), get("C%d" % r), get("K%d" % r)
                if is_err(e):
                    return e
                if e in ("", NONE, None):
                    return (c if is_num(c) else 0.0) * (kk if is_num(kk) else 0.0)
                return 0.0 if e == 0 else e
            if col in EDGE_COLS:
                c, ap = get("C%d" % r), get("AP%d" % r)
                if is_err(c):
                    return c
                if col not in ("Q", "S", "U", "W") and is_err(ap):
                    return ap
                if col in ("Q", "S", "U"):
                    frac = {"Q": 0.25, "S": 0.5, "U": 0.75}[col]
                    return 0.0 if c == NONE else c * frac
                if col == "W":
                    return 0.0 if c in ("", NONE) else c
                base = c if c != NONE else 0.0
                return ((ap - base) * EDGE_FRAC[col]) + base
            if col in ("L", "N"):
                return self.describe(r, inp.get(("G" if col == "L" else "I") + str(r)),
                                     col == "L", get)
            raise KeyError(ref)

        for ref in want:
            get(ref)
        return known

    def describe(self, r, x, under_min, get):
        """The L (entry under Min, in G) or N (under Max, in I) text, in the order of
        band-computation.md 'Outcomes other than a band'. An error in a limit or an edge the
        test reaches gives that error (Sheets' AND and OR evaluate every argument)."""
        c, e = get("C%d" % r), get("E%d" % r)
        if isinstance(x, str) and x.lower() == "none":
            return "" if under_min else "none"
        if under_min:
            if is_err(c):
                return c
            if c in ("", NONE) and (x is None or isinstance(x, str) or (is_num(x) and x >= 0)):
                return NO_MIN
        if x is None or not is_num(x):
            return ""
        ap, w = get("AP%d" % r), get("W%d" % r)
        for v in (e, ap, w, c):
            if is_err(v):
                return v
        if e in ("", NONE) and r7(ap) <= r7(w) and (c in ("", NONE) or r7(x) >= r7(w)):
            return "No range"
        for i, col in enumerate(EDGE_COLS):
            edge = get("%s%d" % (col, r))
            if is_err(edge):
                return edge
            if r7(x) < r7(edge):
                return BANDS[i]
        return BANDS[-1]


def modelled(ref):
    if ref in NOT_MODELLED or ref.startswith("AR"):
        return False
    if ref.startswith("s02!"):
        return True
    if ref in ("C11", "N4"):
        return True
    col, r = split(ref)
    if not 12 <= r <= 129 or r == 58:
        return False   # the energy row, row 58's check and energy density are other rules
    return col in ("C", "E", "AP", "K", "L", "N") + tuple(EDGE_COLS)


def run(data, cases):
    """(values checked, [(case id, cell, expected, model)]) over the values cases (every
    group but 'table'), the model reading the data folder."""
    use(data)
    m = Model(table_from_data(data))
    checked, bad = 0, []
    for case in cases:
        if case["group"] == "table":
            continue
        inp = case["inputs"]
        expected = dict(case["outputs"])
        expected.update(case.get("descriptors", {}))
        known = {r: v for r, v in expected.items() if not modelled(r)}
        want = [r for r in expected if modelled(r)]
        try:
            got = m.compute(inp, dict(known), want)
        except Exception as ex:  # a model defect: reported, never hidden
            bad.append((case["id"], None, None, "model raised %r" % ex))
            continue
        for ref in want:
            checked += 1
            if not same(expected[ref], got[ref]):
                bad.append((case["id"], ref, expected[ref], got[ref]))
    return checked, bad


def load_cases(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["cases"]
