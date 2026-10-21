"""Find the printed source (table and page) of every figure in a data folder.

For each figure, the finder looks in the nutrient's row on the requirement's table pages in
the text of the standard (FEDIAF and AAFCO; NRC's tables are scanned sideways and are
placed from the page images, see NRC_PAGES). A figure is placed only when its number is
printed in that row; the scaling that matched is recorded (for example a FEDIAF legal
maximum printed per 100 g DM that the template typed per kg DM). Nothing is guessed:
unplaced figures are listed for the steward.

Usage: python3 -I -B tools/find_sources.py DATA_DIR TEXT_DIR TRANSCRIPTIONS_DIR OUT_JSON
"""

import json
import os
import re
import sys
from decimal import Decimal, InvalidOperation

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from oan import table  # noqa: E402

FEDIAF_TEXT = "FEDIAF-Nutritional-Guidelines_2025-ONLINE.txt"
AAFCO_TEXT = "2026_AAFCO_Reqts_OCR.txt"

# requirement id -> [(table label, pdf page)] searched in order; FEDIAF printed page = pdf page.
FEDIAF_DOG = [("Table III-3b", 16), ("Table III-3a", 15)]
FEDIAF_CAT = [("Table III-4b", 19), ("Table III-4a", 18)]
FEDIAF_TABLES = {
    "fediaf-dog-adult-mer95": FEDIAF_DOG, "fediaf-dog-adult-mer110": FEDIAF_DOG,
    "fediaf-dog-early-growth-reproduction": FEDIAF_DOG, "fediaf-dog-late-growth": FEDIAF_DOG,
    "fediaf-cat-adult-mer75": FEDIAF_CAT, "fediaf-cat-adult-mer100": FEDIAF_CAT,
    "fediaf-cat-growth": FEDIAF_CAT, "fediaf-cat-reproduction": FEDIAF_CAT,
}

# nutrient id (per-Mcal row) -> regex for the row label in the FEDIAF tables.
FEDIAF_LABELS = {
    "protein": r"Protein\*?", "arginine": r"Arginine\*?", "histidine": r"Histidine",
    "isoleucine": r"Isoleucine", "leucine": r"Leucine", "lysine": r"Lysine\*?",
    "methionine": r"Methionine\*?(?!\s*\+)", "methionine-cystine": r"Methionine \+ cystine\*?",
    "phenylalanine": r"Phenylalanine(?!\s*\+)", "phenylalanine-tyrosine":
    r"Phenylalanine \+ tyrosine\*?", "threonine": r"Threonine", "tryptophan": r"Tryptophan",
    "valine": r"Valine", "taurine": r"Taurine.*dry", "taurine-wet": r"Taurine.*(wet|canned)",
    "fat": r"Fat\*?", "linoleic-acid": r"Linoleic acid", "arachidonic-acid":
    r"Arachidonic acid", "alpha-linolenic-acid": r"Alpha-linolenic acid", "epa-dha":
    r"EPA \+ DHA", "calcium": r"Calcium\*?", "phosphorus": r"Phosphorus\*?",
    "ca-p-ratio": r"Ca / P ratio", "potassium": r"Potassium", "sodium": r"Sodium\*?",
    "chloride": r"Chloride", "magnesium": r"Magnesium", "copper": r"Copper\*?",
    "iodine": r"Iodine\*?", "iron": r"Iron\*?", "manganese": r"Manganese",
    "selenium": r"Selenium\*? \(dry", "selenium-wet": r"Selenium\*? \(wet", "zinc": r"Zinc\*?",
    "vitamin-a": r"Vitamin A\*?", "vitamin-d": r"Vitamin D\*?", "vitamin-e": r"Vitamin E\*?",
    "thiamine": r"Vitamin B1 ", "riboflavin": r"Vitamin B2 ", "pantothenic-acid":
    r"Vitamin B5 ", "pyridoxine": r"Vitamin B6 ", "cobalamin": r"Vitamin B12 ",
    "niacin": r"Vitamin B3 ", "folate": r"Vitamin B9 ", "biotin": r"Vitamin B7 ",
    "choline": r"Choline", "vitamin-k1": r"Vitamin K\*?",
}

NUMBER = re.compile(r"(?<![\d.])(\d{1,3}(?: \d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)")
AMOUNTS = ["g", "mg", "mcg", "IU"]
FEDIAF_FOOTNOTES = ("Footnotes to Tables III-3 and III-4", 21)
# The adult per-MBW minimums (one column per species for both MERs).
FEDIAF_MBW = ("Table VII-11", 58)
NATURAL_BASIS = {"per-mcal": "1000 kcal", "per-100g-dm": "100 g DM"}


def tokens_in(text):
    """[(printed text without spaces, Decimal)] for every number in text."""
    out = []
    for m in NUMBER.finditer(text):
        t = m.group(1).replace(" ", "")
        try:
            out.append((t, Decimal(t)))
        except InvalidOperation:
            pass
    return out


def row_blocks(page_text, labels):
    """{nutrient id: text of its row block} on one table page. A block runs from the line
    after the previous label to the line before the next label, so it includes entries of
    the maximum column printed above or below the label line."""
    lines = page_text.splitlines()
    hits = []
    for i, line in enumerate(lines):
        head = line.strip()
        for nid, pattern in labels.items():
            if re.match(pattern, head, re.I):
                hits.append((i, nid))
                break
    blocks = {}
    for k, (i, nid) in enumerate(hits):
        start = hits[k - 1][0] + 1 if k else max(0, i - 3)
        end = hits[k + 1][0] if k + 1 < len(hits) else min(len(lines), i + 4)
        blocks.setdefault(nid, "\n".join(lines[start:end]))
    return blocks


def natural(unit, nutrient, species):
    if unit == "":
        return True
    amount, _, basis = unit.partition("/")
    want = NATURAL_BASIS.get(nutrient["basis"]) or table.MBW_BASIS[species]
    return amount == nutrient["amount"] and basis == want


def match(bases, tokens, units, nutrient, species):
    """(printed texts, unit) when every base value is printed among tokens in one unit."""
    for unit in units:
        try:
            factor = table.unit_factor(unit, nutrient, species)
        except table.DataError:
            continue
        found = []
        for base in bases:
            hit = next((t for t, d in tokens if d * factor == base), None)
            if hit is None:
                break
            found.append(hit)
        if len(found) == len(bases):
            return found, ("" if natural(unit, nutrient, species) else unit)
    return None



# NRC 2006: the tables are scanned sideways, so the finder reads an independent transcription
# made from the page images (kept private with the scans). requirement id -> (table, pages,
# section of the amino acid rows).
NRC_TABLES = {
    "nrc-dog-adult": ("Table 15-5", None), "nrc-puppy-4-14-wk": ("Table 15-3", "4-14 wk"),
    "nrc-puppy-14-wk-plus": ("Table 15-3", "14+ wk"),
    "nrc-dog-gestation-lactation": ("Table 15-8", None), "nrc-kitten": ("Table 15-10", None),
    "nrc-cat-adult": ("Table 15-12", None), "nrc-cat-late-gestation": ("Table 15-14", "gestation"),
    "nrc-cat-peak-lactation": ("Table 15-14", "lactation"),
}
NRC_LABELS = {
    "Crude Protein": ["protein", "protein-dm"], "Arginine": ["arginine"], "Histidine": ["histidine"],
    "Isoleucine": ["isoleucine"], "Methionine": ["methionine"],
    "Methionine & Cystine": ["methionine-cystine"], "Leucine": ["leucine"], "Lysine": ["lysine"],
    "Phenylalanine": ["phenylalanine"], "Phenylalanine & Tyrosine": ["phenylalanine-tyrosine"],
    "Threonine": ["threonine"], "Tryptophan": ["tryptophan"], "Valine": ["valine"],
    "Taurine": ["taurine", "taurine-wet"], "Total Fat": ["fat"], "Linoleic Acid": ["linoleic-acid"],
    "α-Linolenic Acid": ["alpha-linolenic-acid"], "Arachidonic Acid": ["arachidonic-acid"],
    "Eicosapentaenoic & Docosahexaenoic Acid": ["epa-dha"], "Calcium": ["calcium"],
    "Phosphorus": ["phosphorus"], "Magnesium": ["magnesium"], "Sodium": ["sodium"],
    "Potassium": ["potassium"], "Chloride": ["chloride"], "Iron": ["iron"],
    "Copper": ["copper", "copper-wet"], "Zinc": ["zinc"], "Manganese": ["manganese"],
    "Selenium": ["selenium", "selenium-wet"], "Iodine": ["iodine"], "Vitamin A": ["retinol"],
    "Cholecalciferol": ["vitamin-d"], "Vitamin E": ["vitamin-e"], "Vitamin K": ["vitamin-k1"],
    "Thiamin": ["thiamine"], "Riboflavin": ["riboflavin"], "Pyridoxine": ["pyridoxine"],
    "Niacin": ["niacin"], "Pantothenic Acid": ["pantothenic-acid"], "Cobalamin": ["cobalamin"],
    "Folic Acid": ["folate"], "Biotin": ["biotin"], "Choline": ["choline"],
    "Glutamic Acid": ["glutamic-acid"],
}
NRC_FOOTNOTE_TAURINE = ["taurine", "taurine-wet"]
GROUP_ORDER = {"min": ["RA", "AI", "MR", "FN", "SUL"], "max": ["SUL", "RA", "AI", "MR", "FN"]}


def read_transcription(path):
    """[(table, page, BW exponent, section, label, amount unit, group, [DM, ME, BW])]."""
    rows = []
    table_name = page = exponent = None
    section = "all"
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("@@"):
            section = line[2:].strip()
            continue
        if line.startswith("@"):
            table_name, page, exponent = [x.strip() for x in line[1:].split("|")]
            page = int(page)
            section = "all"
            continue
        label, unit, groups = [x.strip() for x in line.split("|")]
        for part in groups.split(";"):
            group, values = part.split(":")
            rows.append((table_name, page, exponent, section, label, unit, group.strip(),
                         values.split()))
    return rows


def nrc_sources(data, nutrients, transcription, results, unplaced):
    rows = read_transcription(transcription)
    for req in data["requirements"]:
        if req["standard"] != "NRC":
            continue
        table_name, section = NRC_TABLES[req["id"]]
        species = req["species"]
        for nid, r in data["limits"][req["id"]].items():
            nutrient = nutrients[nid]
            is_mbw = nid.endswith("-mbw")
            base_id = nid[:-4] if is_mbw else nid
            for bound in ("min", "max"):
                text = r[bound]
                if text in ("none", ""):
                    continue
                key = "%s/%s/%s" % (req["id"], nid, bound)
                figures, greater = table.parse_figure(text)
                factor = table.unit_factor(r[bound + "_unit"], nutrient, species)
                base = figures[0] * factor
                hits = []
                for (tname, page, exponent, sec, label, amount, group, values) in rows:
                    if tname != table_name or sec not in ("all", section):
                        continue
                    if label.startswith("Taurine (footnote"):
                        ids = NRC_FOOTNOTE_TAURINE
                    else:
                        ids = NRC_LABELS.get(label, [])
                    if base_id not in ids:
                        continue
                    if is_mbw:
                        columns = [(2, amount + "/kg BW^" + exponent)]
                    else:
                        columns = [(1, amount + "/1000 kcal"), (0, amount + "/kg DM")]
                    for index, unit in columns:
                        if index >= len(values) or values[index] == "-":
                            continue
                        printed = values[index]
                        printed_gt = printed.startswith(">") and not printed.startswith(">=")
                        number = printed.lstrip(">=")
                        try:
                            f = table.unit_factor(unit, nutrient, species)
                        except table.DataError:
                            continue
                        if Decimal(number) * f == base:
                            hits.append((group, index, page, label, number, unit, printed_gt,
                                         printed))
                if not hits:
                    unplaced.append((key, text, r[bound + "_unit"], r[bound + "_rule"],
                                     "not in the transcribed %s rows" % table_name))
                    continue
                order = GROUP_ORDER[bound]
                hits.sort(key=lambda h: (order.index(h[0]) if h[0] in order else 9, h[1] != 1))
                group, index, page, label, number, unit, printed_gt, printed = hits[0]
                column = ["kg DM", "1,000 kcal", "kg BW"][index]
                src = "%s, p. %d" % (table_name, page)
                if group == "FN":
                    src += ", footnote (%s)" % label.split(":", 1)[1].rstrip(")").strip()
                entry = {"source": src, "how": "transcription", "group": group,
                         "column": column, "printed": [printed],
                         "figure": (">" if greater else "") + number,
                         "unit": "" if natural(unit, nutrient, species) else unit}
                expected = "SUL" if bound == "max" else "RA"
                flags = []
                if group != expected:
                    flags.append("found in the %s columns, not %s" % (group, expected))
                if printed_gt != greater:
                    flags.append("printed %r but the figure is %r" % (printed, text))
                if flags:
                    entry["flags"] = flags
                results[key] = entry


# AAFCO 2026: the calorie-basis tables, read from the page images (the OCR text is too noisy).
# requirement id -> (table, column: 0 growth and reproduction, 1 adult maintenance).
AAFCO_TABLES = {
    "aafco-dog-adult": ("Dog Food Nutrient Profiles", 1),
    "aafco-dog-growth-reproduction": ("Dog Food Nutrient Profiles", 0),
    "aafco-dog-growth-large-breed": ("Dog Food Nutrient Profiles", 0),
    "aafco-cat-adult": ("Cat Food Nutrient Profiles", 1),
    "aafco-cat-growth-reproduction": ("Cat Food Nutrient Profiles", 0),
}
AAFCO_LABELS = {
    "Crude protein": ["protein", "protein-dm"], "Arginine": ["arginine"],
    "Histidine": ["histidine"], "Isoleucine": ["isoleucine"], "Leucine": ["leucine"],
    "Lysine": ["lysine"], "Methionine": ["methionine"], "Methionine-cystine": ["methionine-cystine"],
    "Phenylalanine": ["phenylalanine"], "Phenylalanine-tyrosine": ["phenylalanine-tyrosine"],
    "Threonine": ["threonine"], "Tryptophan": ["tryptophan"], "Valine": ["valine"],
    "Crude fat": ["fat"], "Linoleic acid": ["linoleic-acid"],
    "alpha-Linolenic acid": ["alpha-linolenic-acid"], "Arachidonic acid": ["arachidonic-acid"],
    "Eicosapentaenoic + Docosahexaenoic acid": ["epa-dha"],
    "(Linoleic + Arachidonic):(alpha-Linolenic + Eicosapentaenoic + Docosahexaenoic) acid ratio":
    ["la-aa-to-ala-epa-dha-ratio"],
    "Calcium": ["calcium"], "Calcium (footnote d, in parentheses)": ["calcium"],
    "Phosphorus": ["phosphorus"], "Ca:P ratio": ["ca-p-ratio"], "Potassium": ["potassium"],
    "Sodium": ["sodium"], "Chloride": ["chloride"], "Magnesium": ["magnesium"],
    "Iron": ["iron"], "Copper": ["copper", "copper-wet"], "Copper (extruded)": ["copper"],
    "Copper (canned)": ["copper-wet"], "Manganese": ["manganese"], "Zinc": ["zinc"],
    "Iodine": ["iodine"], "Selenium": ["selenium", "selenium-wet"], "Vitamin A": ["vitamin-a"],
    "Vitamin D": ["vitamin-d"], "Vitamin E": ["vitamin-e"], "Vitamin K": ["vitamin-k1"],
    "Thiamine": ["thiamine"], "Riboflavin": ["riboflavin"],
    "Pantothenic acid": ["pantothenic-acid"], "Niacin": ["niacin"],
    "Pyridoxine": ["pyridoxine"], "Folic acid": ["folate"], "Biotin": ["biotin"],
    "Vitamin B12": ["cobalamin"], "Choline": ["choline"], "Taurine (extruded)": ["taurine"],
    "Taurine (canned)": ["taurine-wet"],
}


def aafco_sources(data, nutrients, transcription, results, unplaced):
    pages = []
    current = None
    for line in open(transcription, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("@"):
            name, page = [x.strip() for x in line[1:].split("|")]
            current = (name, int(page))
            continue
        label, amount, values = [x.strip() for x in line.split("|")]
        pages.append((current[0], current[1], label, amount, values.split()))
    for req in data["requirements"]:
        if req["standard"] != "AAFCO":
            continue
        table_name, column = AAFCO_TABLES[req["id"]]
        species = req["species"]
        for nid, r in data["limits"][req["id"]].items():
            nutrient = nutrients[nid]
            for bound in ("min", "max"):
                text = r[bound]
                if text in ("none", ""):
                    continue
                key = "%s/%s/%s" % (req["id"], nid, bound)
                figures, greater = table.parse_figure(text)
                base = figures[0] * table.unit_factor(r[bound + "_unit"], nutrient, species)
                want = column if bound == "min" else 2
                hits = []
                for name, page, label, amount, values in pages:
                    if not name.startswith(table_name) or nid not in AAFCO_LABELS.get(label, []):
                        continue
                    if amount == "-":
                        unit = ""
                    elif amount == "%":
                        unit = "g/100 g DM"
                    else:
                        unit = amount + "/1000 kcal"
                    try:
                        f = table.unit_factor(unit, nutrient, species)
                    except table.DataError:
                        continue
                    for index, printed in enumerate(values):
                        if printed in ("-", "ND"):
                            continue
                        number = printed.split(":")[0]
                        if Decimal(number) * f == base:
                            hits.append((index != want, index, page, label, printed, number,
                                         unit, name))
                if not hits:
                    unplaced.append((key, text, r[bound + "_unit"], r[bound + "_rule"],
                                     "not in the transcribed %s rows" % table_name))
                    continue
                hits.sort()
                off, index, page, label, printed, number, unit, name = hits[0]
                src = "%s, p. %d" % (name, page)
                if "footnote" in label:
                    src += ", footnote d"
                entry = {"source": src, "how": "transcription", "printed": [printed],
                         "column": ["growth and reproduction", "adult maintenance",
                                    "maximum"][index],
                         "figure": (">" if greater else "") + number,
                         "unit": "" if natural(unit, nutrient, species) else unit}
                if off:
                    entry["flags"] = ["found in the %s column" % entry["column"]]
                results[key] = entry


# Figures the scans cannot show, recorded by hand with the reason.
MANUAL_SOURCES = {
    "nrc-cat-peak-lactation/valine/min": "3.0 g/1,000 kcal",
    "nrc-cat-peak-lactation/valine-mbw/min": "0.64 g/kg BW^0.67",
}


def manual_sources(results, unplaced):
    still = []
    for item in unplaced:
        if item[0] in MANUAL_SOURCES:
            results[item[0]] = {
                "source": "Table 15-14, p. 369", "how": "manual",
                "flags": ["the lactating valine row is cut off at the top edge of the private "
                          "NRC scan; the figure (%s) is as quoted in note n068 and is not "
                          "confirmed from the scan" % MANUAL_SOURCES[item[0]]]}
        else:
            still.append(item)
    unplaced[:] = still


def template_sources(data, nutrients, results, unplaced):
    """Second pass over unplaced figures: values the template sets itself. A figure is
    recorded as template-set only when a note on its cell says how it was made, or when it
    equals exactly the late-gestation computation NRC's footnote d describes."""
    notes = {n["id"]: n["text"] for n in data["notes"]}
    reqs = {r["id"]: r for r in data["requirements"]}
    still = []
    for item in unplaced:
        key = item[0]
        rid, nid, bound = key.split("/")
        r = data["limits"][rid][nid]
        cell_notes = r[bound + "_notes"].split()
        # "template" relabels a plain figure; a conversion rule (folic acid to DFE) stays.
        relabel = {"rule": "template"} if r[bound + "_rule"] == "printed" else {}
        if cell_notes:
            results[key] = dict(relabel, source="template-set, see note " + " ".join(
                cell_notes), how="note", flags=["template-set: check the note's derivation"])
            continue
        if rid == "nrc-cat-late-gestation" and nid.endswith("-mbw"):
            parent = nutrients[nid]["mbw_of"]
            pr = data["limits"][rid][parent]
            if pr[bound] not in ("none", ""):
                req = reqs[rid]
                pfig, _ = table.parse_figure(pr[bound])
                pbase = pfig[0] * table.unit_factor(pr[bound + "_unit"], nutrients[parent],
                                                    req["species"])
                figs, _ = table.parse_figure(r[bound])
                base = figs[0] * table.unit_factor(r[bound + "_unit"], nutrients[nid],
                                                   req["species"])
                if pbase * Decimal(140) / 1000 == base:
                    results[key] = dict(relabel, how="computed", source=(
                        "template-set from Table 15-14 footnote d, p. 369: the per-Mcal "
                        "value x 140/1000 (note %s)" % req["notes"].split()[0]))
                    continue
        still.append(item)
    unplaced[:] = still


def main(data_dir, text_dir, transcription_dir, out_path):
    fediaf_pages = open(os.path.join(text_dir, FEDIAF_TEXT), encoding="utf-8").read().split("\f")
    data = table.load(data_dir)
    nutrients = {n["id"]: n for n in data["nutrients"]}
    labels = FEDIAF_LABELS
    # rows printed once that the template uses for two of its nutrients
    shared_row = {"protein-dm": "protein", "copper-wet": "copper"}
    blocks_cache = {}
    results = {}
    unplaced = []
    for req in data["requirements"]:
        if req["standard"] != "FEDIAF":
            continue
        species = req["species"]
        rows = data["limits"][req["id"]]
        for nid, r in rows.items():
            nutrient = nutrients[nid]
            for bound in ("min", "max"):
                text = r[bound]
                if text in ("none", ""):
                    continue
                key = "%s/%s/%s" % (req["id"], nid, bound)
                figures, greater = table.parse_figure(text)
                factor = table.unit_factor(r[bound + "_unit"], nutrient, species)
                bases = [f * factor for f in figures]
                if nid.endswith("-mbw"):
                    label, page = FEDIAF_MBW
                    if page not in blocks_cache:
                        blocks_cache[page] = row_blocks(fediaf_pages[page - 1], labels)
                    block = blocks_cache[page].get(shared_row.get(nid[:-4], nid[:-4]))
                    m = block and match(bases, tokens_in(block), [
                        a + "/" + table.MBW_BASIS[species] for a in AMOUNTS], nutrient, species)
                    if m:
                        results[key] = {"source": "%s, p. %d" % (label, page), "how": "row",
                                        "printed": m[0], "unit": m[1],
                                        "figure": (">" if greater else "") + "|".join(m[0])}
                    else:
                        unplaced.append((key, text, r[bound + "_unit"], r[bound + "_rule"],
                                         "not printed in the row of Table VII-11"))
                    continue
                found = None
                for label, page in FEDIAF_TABLES[req["id"]]:
                    if page not in blocks_cache:
                        blocks_cache[page] = row_blocks(fediaf_pages[page - 1], labels)
                    block = blocks_cache[page].get(shared_row.get(nid, nid))
                    if block is None:
                        continue
                    if "1000 kcal" in (label + fediaf_pages[page - 1][:600]):
                        units = [a + "/1000 kcal" for a in AMOUNTS]
                    else:
                        units = [a + "/100 g DM" for a in AMOUNTS]
                    if nutrient["basis"] == "per-100g-dm":
                        units = [a + "/100 g DM" for a in AMOUNTS]
                    if nutrient["basis"] in ("ratio", "energy-density"):
                        units = [""]
                    m = match(bases, tokens_in(block), units, nutrient, species)
                    if m:
                        found = {"source": "%s, p. %d" % (label, page), "how": "row",
                                 "printed": m[0], "unit": m[1]}
                        break
                if not found:
                    label, page = FEDIAF_FOOTNOTES
                    m = match(bases, tokens_in(fediaf_pages[page - 1]),
                              [a + "/1000 kcal" for a in AMOUNTS], nutrient, species)
                    if m:
                        found = {"source": "%s, p. %d" % (label, page), "how": "page",
                                 "printed": m[0], "unit": m[1]}
                if found:
                    found["figure"] = (">" if greater else "") + "|".join(found["printed"])
                    results[key] = found
                else:
                    unplaced.append((key, text, r[bound + "_unit"], r[bound + "_rule"],
                                     "not printed in the row on the table pages"))
    nrc_sources(data, nutrients, os.path.join(transcription_dir, "nrc-2006.txt"), results,
                unplaced)
    aafco_sources(data, nutrients, os.path.join(transcription_dir, "aafco-2026.txt"), results,
                  unplaced)
    template_sources(data, nutrients, results, unplaced)
    manual_sources(results, unplaced)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"sources": results, "unplaced": unplaced}, f, indent=1, sort_keys=True)
    print("placed %d, unplaced %d" % (len(results), len(unplaced)))


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    main(*sys.argv[1:])
