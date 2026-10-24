"""Independent model of the daily energy minimum (s02 row 4) after the energy batches 1 and 2.

Written as an independent check during the template's energy work (19 Oct 2026) and copied
here; phase 2 re-pointed its figures at a data folder's energy.csv (use(data) before energy()),
so the impact report can re-run it on changed data. Its structure is unchanged and independent
of oan/energy.py.

Written from the sources and from Sean's decisions (batches 1 and 2, 19 Oct 2026), not from the formula text:
  - AVCN 2nd ed. Box 3.1 (pp. 46-47): RER = 70 * BW^0.75; puppies 3 x RER weaning-4 months, then 2 x RER until adult
    size; kittens about 2.5 x RER.
  - 2006 NRC: Table 15-2 (p. 356) puppies; Table 15-4 (p. 359) dog types (the B4 list); Table 15-6 (p. 361) late
    gestation = maintenance + 26 x BW, from 4 weeks after mating; p. 37 individual maintenance; Table 15-7 (p. 361)
    lactation 145 x BW^0.75 + BW x (24n + 12m) x L, n = puppies 1-4, m = puppies 5-8, L weeks 1-4 = .75 .95 1.1 1.2;
    p. 38 no notable increase above 8 puppies, no estimate after week 4; Table 15-9 (p. 364) kittens; Table 15-11
    (p. 366) cat types; Table 15-13 (p. 368) queen lactation, L weeks 1-7 = .9 .9 1.2 1.2 1.1 1.0 .8; Table 15-14
    footnotes c, d (p. 369) queen gestation 140 x BW^0.67.
  - 2025 FEDIAF: VII-8b (p. 56) puppy [254.1 - 135.0 p] x BW^0.75; gestation 132 x BW^0.75 (+ 26 x BW last 5 weeks);
    lactation 145 x BW^0.75 + 24 n x BW x L (1-4 puppies), + [96 + 12 (n-4)] x BW x L (5-8); VII-10 (p. 57) queens.
  - Decisions: 1a B (one life-stage list in M3), 1b A (K3 = week, species L looked up), 1c B (one count, at most 8),
    1d B, 1e B (AM4), 2a A, 2b C, 2c B, 2d A, 2f B; batch 8c A (Sean, 19 Oct 2026: a growing animal's BW above its
    expected mature BW is an input error and shows a message under every growth equation that uses E3); batch 8g as
    batch-8.md lists it (pending): stages a selection does not cover give the life-stage message, worded 8g-5.
Inputs are given as Sheets would hold them: numbers, text, or None (blank). Standard library only.
"""
import math
import re

NONE, G1, G2 = "None", "Growth: weaning to 4 months", "Growth: 4 months to adult size"
P1, P2, LB = "Gestation: weeks 1-4", "Gestation: week 5 to birth", "Lactation: bitch"
Q1, Q2, Q3 = "<3 Kittens", "3-4 Kittens", ">4 Kittens"

MSG_STAGE = "Standards Sheet Needs A Life Stage This Selection Covers"
MSG_PUPPY = "Standards Sheet Needs Lactation Wk & Puppy #"
MSG_WK4 = "No NRC/FEDIAF Estimate After Lactation Wk 4: Use K4"
MSG_BW = "Expected Mature BW Must Be At Least Current BW"
MSG_KITTEN = "Standards Sheet Needs Lactation Wk & Kitten #"
MSG_E3 = "Expected Mature BW in Standards Sheet Needed"
MSG_DOG = "No Dog Type Selection on Standards Sheet"
MSG_CAT = "No Cat Type Selection on Standards Sheet"

# Filled from the data by use(): the B4 items -> NRC Table 15-4 kcal/kg BW^0.75, the D4
# items, the week factors and the kitten coefficients, by standard ("nrc" or "fediaf").
DOG_TYPE = {}
CAT_LEAN = CAT_OVER = None
L_BITCH, L_QUEEN, KITTEN_COEF = {}, {}, {}
F = {}
MER = {}


def use(data):
    """Read the figures of a loaded data folder (oan.table.load)."""
    global CAT_LEAN, CAT_OVER
    MER.clear()
    MER.update({r["name"]: float(r["mer_kcal_per_mbw"]) for r in data["requirements"]
                if r["mer_kcal_per_mbw"]})
    F.clear()
    F.update({fid: float(row["figure"]) for fid, row in data["energy"].items()})
    DOG_TYPE.clear()
    for fid, row in data["energy"].items():
        if fid.startswith("nrc-dog-maintenance-"):
            DOG_TYPE[row["label"]] = F[fid]
    CAT_LEAN = data["energy"]["nrc-cat-maintenance-lean"]["label"]
    CAT_OVER = data["energy"]["nrc-cat-maintenance-overweight"]["label"]
    for std in ("nrc", "fediaf"):
        L_BITCH[std] = {w: F["%s-lactation-week-%d" % (std, w)] for w in range(1, 5)}
        L_QUEEN[std] = {w: F["%s-queen-lactation-week-%d" % (std, w)] for w in range(1, 8)}
        KITTEN_COEF[std] = {Q1: F[std + "-queen-lactation-kittens-under-3"],
                            Q2: F[std + "-queen-lactation-kittens-3-to-4"],
                            Q3: F[std + "-queen-lactation-kittens-over-4"]}


def num(x):
    """What a formula reads from an input cell through N(): a number, else 0 (blank or text)."""
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else 0.0


def stage_of(m3):
    """The life stage as the formulas compare it (Sheets TRIM): spaces (U+0020 only) removed at both ends and every run
    of spaces inside reduced to one; other whitespace is kept. Blank counts as None."""
    s = "" if m3 is None else re.sub(" +", " ", str(m3).strip(" "))
    return NONE if s == "" else s


def same(a, b):
    return a.lower() == b.lower()        # Sheets compares text without case


def rer(bw):
    return F["avcn-rer"] * bw ** F["avcn-rer-exponent"]


def nrc_dog_maintenance(bw, b4):
    f = DOG_TYPE.get(b4)
    return MSG_DOG if f is None else f * bw ** F["nrc-dog-exponent"]


def nrc_cat_maintenance(bw, d4):
    if d4 == CAT_OVER:
        return F["nrc-cat-maintenance-overweight"] * bw ** F["nrc-cat-maintenance-overweight-exponent"]
    if d4 == CAT_LEAN:
        return F["nrc-cat-maintenance-lean"] * bw ** F["nrc-cat-exponent"]
    return MSG_CAT


def bitch_maintenance(bw, b4):
    """1e B: the B4 type's NRC maintenance when one is selected, else NRC's average 130 (Table 15-6)."""
    f = DOG_TYPE.get(b4)
    return (f if f is not None else F["nrc-gestation-maintenance"]) * bw ** F["nrc-dog-exponent"]


def nrc_late_gestation(bw, b4):
    return bitch_maintenance(bw, b4) + F["nrc-gestation-per-kg"] * bw   # Table 15-6; p. 37


def week(k3):
    """The week as a whole number, or None when missing (0, blank or text)."""
    w = num(k3)
    return None if w < 1 else w


def nrc_bitch_lactation(bw, g3, k3):
    p, w = num(g3), week(k3)
    if p < 1 or w is None:
        return MSG_PUPPY
    if w > 4:
        return MSG_WK4                                              # p. 38: no estimate after week 4
    k, cap = F["nrc-lactation-puppies-first-group"], F["nrc-lactation-puppies-counted"]
    n = min(p, k)                                                   # puppies 1-4
    m = max(0.0, min(p, cap) - k)                                   # puppies 5-8; none counted above 8 (p. 38)
    return (F["nrc-lactation-maintenance"] * bw ** F["nrc-dog-exponent"]
            + bw * (F["nrc-lactation-per-puppy-1-to-4"] * n + F["nrc-lactation-per-puppy-5-to-8"] * m)
            * L_BITCH["nrc"][int(w)])


def fediaf_bitch_lactation(bw, g3, k3):
    p, w = num(g3), week(k3)
    if p < 1 or w is None:
        return MSG_PUPPY
    if w > 4:
        return MSG_WK4
    k, cap = F["fediaf-lactation-puppies-first-group"], F["fediaf-lactation-puppies-counted"]
    a, b = F["fediaf-lactation-per-puppy-1-to-4"], F["fediaf-lactation-per-puppy-5-to-8"]
    n = min(p, cap)                                                 # the template counts at most 8 (1c B)
    per_puppy_block = a * n if n <= k else a * k + b * (n - k)      # VII-8b as printed (96 = 24 x 4)
    return F["fediaf-lactation-maintenance"] * bw ** F["fediaf-dog-exponent"] + per_puppy_block * bw * L_BITCH["fediaf"][int(w)]


def queen_lactation(bw, stage, k3, std="nrc"):
    w = week(k3)
    if w is None or w > 7:
        return MSG_KITTEN
    for item, coef in KITTEN_COEF[std].items():
        if same(stage, item):
            return (F[std + "-queen-lactation-maintenance"] * bw ** F[std + "-cat-exponent"]
                    + coef * bw * L_QUEEN[std][int(w)])
    return MSG_KITTEN


def queen_gestation(bw, std="nrc"):
    return F[std + "-queen-gestation"] * bw ** F[std + "-cat-exponent"]


def growth_check(bw, e3):
    """The messages of every growth equation that uses the expected mature BW: E3 missing; BW above it (8c A)."""
    if num(e3) == 0:
        return MSG_E3
    if bw > num(e3):
        return MSG_BW                                               # a growing animal weighs less than its adult BW
    return None


def nrc_puppy(bw, e3):
    return growth_check(bw, e3) or F["nrc-puppy-maintenance"] * bw ** F["nrc-dog-exponent"] * F["nrc-puppy-multiplier"] * (
        math.exp(-F["nrc-puppy-rate"] * bw / num(e3)) - F["nrc-puppy-offset"])


def nrc_kitten(bw, e3):
    return growth_check(bw, e3) or F["nrc-kitten-maintenance"] * bw ** F["nrc-cat-exponent"] * F["nrc-kitten-multiplier"] * (
        math.exp(-F["nrc-kitten-rate"] * bw / num(e3)) - F["nrc-kitten-offset"])


def fediaf_puppy(bw, e3):
    return growth_check(bw, e3) or (F["fediaf-puppy-constant"] - F["fediaf-puppy-slope"] * bw / num(e3)) * bw ** F["fediaf-dog-exponent"]


def is_in(stage, *items):
    return any(same(stage, x) for x in items)


def energy(selection, inp):
    """The energy minimum (kcal/day) or message of a selection, from the inputs B3, E3, G3, K3, M3, B4, D4."""
    bw = num(inp.get("B3"))
    e3, g3, k3, b4, d4 = inp.get("E3"), inp.get("G3"), inp.get("K3"), inp.get("B4"), inp.get("D4")
    st = stage_of(inp.get("M3"))
    if selection in ("NRC RA Dog Maintenance", "AAFCO Dog Maintenance"):
        return nrc_dog_maintenance(bw, b4)
    if selection == "FEDIAF Dog (MER 95 kcal/kg^0.75)":
        return MER[selection] * bw ** F["fediaf-dog-exponent"]
    if selection == "FEDIAF Dog (MER 110 kcal/kg^0.75)":
        return MER[selection] * bw ** F["fediaf-dog-exponent"]
    if selection in ("NRC RA Cat Maintenance", "AAFCO Cat Maintenance"):
        return nrc_cat_maintenance(bw, d4)
    if selection == "FEDIAF Cat (MER 75 kcal/kg^0.67)":
        return MER[selection] * bw ** F["fediaf-cat-exponent"]
    if selection == "FEDIAF Cat (MER 100 kcal/kg^0.67)":
        return MER[selection] * bw ** F["fediaf-cat-exponent"]
    if selection in ("NRC RA Puppy 4-14 Wk Growth", "NRC RA Puppy 14 Wk+ Growth"):
        return nrc_puppy(bw, e3)
    if selection == "AAFCO Dog Growth (Small & Medium) and Reproduction":
        if is_in(st, G1):
            return F["avcn-puppy-to-4-months"] * rer(bw)
        if is_in(st, G2):
            return F["avcn-puppy-to-adult-size"] * rer(bw)
        if is_in(st, P1):
            return bitch_maintenance(bw, b4)          # NRC: the added gestation energy starts 4 weeks after mating
        if is_in(st, P2):
            return nrc_late_gestation(bw, b4)
        if is_in(st, LB):
            return nrc_bitch_lactation(bw, g3, k3)
        return MSG_STAGE
    if selection == "AAFCO Large Breed Dog Growth":
        if is_in(st, G1):
            return F["avcn-puppy-to-4-months"] * rer(bw)
        if is_in(st, G2):
            return F["avcn-puppy-to-adult-size"] * rer(bw)
        return MSG_STAGE
    if selection == "FEDIAF Dog Early Growth (< 14 wk) & Reproduction":
        if is_in(st, NONE, G1, G2):
            return fediaf_puppy(bw, e3)
        if is_in(st, P1):
            return F["fediaf-gestation-maintenance"] * bw ** F["fediaf-dog-exponent"]
        if is_in(st, P2):
            return F["fediaf-gestation-maintenance"] * bw ** F["fediaf-dog-exponent"] + F["fediaf-gestation-per-kg"] * bw
        if is_in(st, LB):
            return fediaf_bitch_lactation(bw, g3, k3)
        return MSG_STAGE
    if selection == "FEDIAF Dog Late Growth (>/= 14 wk)":
        return fediaf_puppy(bw, e3)
    if selection in ("NRC RA Kitten Growth", "FEDIAF Cat Growth"):
        return nrc_kitten(bw, e3)
    if selection == "AAFCO Cat Growth and Reproduction":
        if is_in(st, NONE, G1, G2):
            return F["avcn-kitten-growth"] * rer(bw)
        if is_in(st, P1, P2):
            return queen_gestation(bw)
        if is_in(st, Q1, Q2, Q3):
            return queen_lactation(bw, st, k3)
        return MSG_STAGE
    if selection == "NRC RA Dog Late Gestation & Peak Lactation":
        if is_in(st, NONE, P2):
            return nrc_late_gestation(bw, b4)
        if is_in(st, LB):
            return nrc_bitch_lactation(bw, g3, k3)
        return MSG_STAGE
    if selection == "NRC RA Cat Late Gestation":
        return queen_gestation(bw)
    if selection == "NRC RA Cat Peak Lactation":
        return queen_lactation(bw, st, k3)
    if selection == "FEDIAF Cat Reproduction":
        if is_in(st, P1, P2):
            return queen_gestation(bw, "fediaf")                    # FEDIAF VII-10 gestation
        return queen_lactation(bw, st, k3, "fediaf")
    raise KeyError(selection)


def energy_row(selection, inp, k4=None):
    """What the Standards tab shows: G4 (the selection's value), C11 (an intake above 0 in K4 wins), and whether the
    1f C rule highlights C11 (anything that is not a number)."""
    g4 = energy(selection, inp)
    c11 = float(k4) if isinstance(k4, (int, float)) and not isinstance(k4, bool) and k4 > 0 else g4
    return {"G4": g4, "C11": c11, "C11_highlighted": not isinstance(c11, float)}
