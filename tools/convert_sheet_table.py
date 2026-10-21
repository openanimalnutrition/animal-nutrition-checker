"""One-time conversion of the DDS template's requirement table to the data/ CSV files.

Reads the table JSON (format oan-dds-requirements-table/1, candidate b04aa7ff, released as
Version 21OCT26b), the s02 cell notes of the 21OCT26b export, and the per-value sources
found by tools/find_sources.py. Writes data/. Every limit cell becomes the figure as the
standard prints it plus a named rule (oan/table.py RULES); formulas the converter does not
recognise stop the conversion.

Usage: python3 -I -B tools/convert_sheet_table.py TABLE_JSON NOTES_TXT SOURCES_JSON OUT_DATA_DIR
"""

import csv
import json
import os
import re
import sys
from decimal import Decimal

# s02 row -> nutrient id (row 7 is the second "Protein", per 100 g DM; lookups never reach it).
BASE_IDS = [
    (5, "protein"), (7, "protein-dm"), (8, "arginine"), (10, "histidine"),
    (12, "isoleucine"), (14, "leucine"), (16, "lysine"), (18, "methionine"),
    (20, "methionine-cystine"), (22, "phenylalanine"), (24, "phenylalanine-tyrosine"),
    (26, "threonine"), (28, "tryptophan"), (30, "valine"), (32, "taurine"),
    (34, "taurine-wet"), (36, "fat"), (38, "linoleic-acid"), (40, "alpha-linolenic-acid"),
    (42, "arachidonic-acid"), (44, "epa-dha"), (46, "la-aa-to-ala-epa-dha-ratio"),
    (48, "la-aa-to-epa-dha-ratio"), (50, "mct"), (52, "calcium"), (54, "phosphorus"),
    (56, "ca-p-ratio"), (58, "potassium"), (60, "sodium"), (62, "chloride"),
    (64, "magnesium"), (66, "iron"), (68, "copper"), (70, "copper-wet"), (72, "manganese"),
    (74, "zinc"), (76, "iodine"), (78, "selenium"), (80, "selenium-wet"), (82, "retinol"),
    (84, "vitamin-a"), (86, "vitamin-d"), (88, "vitamin-e"), (90, "vitamin-k1"),
    (92, "thiamine"), (94, "riboflavin"), (96, "pantothenic-acid"), (98, "niacin"),
    (100, "pyridoxine"), (102, "folate"), (104, "biotin"), (106, "cobalamin"),
    (108, "choline"), (110, "vitamin-c"), (111, "water"), (112, "carbohydrate"),
    (113, "fiber-total"), (114, "fiber-insoluble"), (115, "fiber-soluble"),
    (116, "oxalate"), (117, "purine"), (118, "energy-density"), (119, "glutamic-acid"),
]
IG_CODES = {"protein": "protein", "calcium": "calcium", "phosphorus": "phosphorus",
            "potassium": "potassium", "ca-p-ratio": "ca-p-ratio", "vitamin-d": "vitamin-d"}

# Selection name -> (id, standard, edition, species, life stages, MER kcal per kg MBW).
REQUIREMENTS = {
    "NRC RA Dog Maintenance": ("nrc-dog-adult", "NRC", "NRC-2006", "canine", "adult-maintenance", ""),
    "AAFCO Dog Maintenance": ("aafco-dog-adult", "AAFCO", "AAFCO-2026", "canine", "adult-maintenance", ""),
    "FEDIAF Dog (MER 95 kcal/kg^0.75)": ("fediaf-dog-adult-mer95", "FEDIAF", "FEDIAF-2025", "canine", "adult-maintenance", "95"),
    "FEDIAF Dog (MER 110 kcal/kg^0.75)": ("fediaf-dog-adult-mer110", "FEDIAF", "FEDIAF-2025", "canine", "adult-maintenance", "110"),
    "NRC RA Cat Maintenance": ("nrc-cat-adult", "NRC", "NRC-2006", "feline", "adult-maintenance", ""),
    "AAFCO Cat Maintenance": ("aafco-cat-adult", "AAFCO", "AAFCO-2026", "feline", "adult-maintenance", ""),
    "FEDIAF Cat (MER 75 kcal/kg^0.67)": ("fediaf-cat-adult-mer75", "FEDIAF", "FEDIAF-2025", "feline", "adult-maintenance", "75"),
    "FEDIAF Cat (MER 100 kcal/kg^0.67)": ("fediaf-cat-adult-mer100", "FEDIAF", "FEDIAF-2025", "feline", "adult-maintenance", "100"),
    "NRC RA Puppy 4-14 Wk Growth": ("nrc-puppy-4-14-wk", "NRC", "NRC-2006", "canine", "growth", ""),
    "NRC RA Puppy 14 Wk+ Growth": ("nrc-puppy-14-wk-plus", "NRC", "NRC-2006", "canine", "growth", ""),
    "AAFCO Dog Growth (Small & Medium) and Reproduction": ("aafco-dog-growth-reproduction", "AAFCO", "AAFCO-2026", "canine", "growth gestation-lactation", ""),
    "AAFCO Large Breed Dog Growth": ("aafco-dog-growth-large-breed", "AAFCO", "AAFCO-2026", "canine", "growth", ""),
    "FEDIAF Dog Early Growth (< 14 wk) & Reproduction": ("fediaf-dog-early-growth-reproduction", "FEDIAF", "FEDIAF-2025", "canine", "growth gestation-lactation", ""),
    "FEDIAF Dog Late Growth (>/= 14 wk)": ("fediaf-dog-late-growth", "FEDIAF", "FEDIAF-2025", "canine", "growth", ""),
    "NRC RA Kitten Growth": ("nrc-kitten", "NRC", "NRC-2006", "feline", "growth", ""),
    "AAFCO Cat Growth and Reproduction": ("aafco-cat-growth-reproduction", "AAFCO", "AAFCO-2026", "feline", "growth gestation-lactation", ""),
    "FEDIAF Cat Growth": ("fediaf-cat-growth", "FEDIAF", "FEDIAF-2025", "feline", "growth", ""),
    "NRC RA Dog Late Gestation & Peak Lactation": ("nrc-dog-gestation-lactation", "NRC", "NRC-2006", "canine", "gestation-lactation", ""),
    "NRC RA Cat Late Gestation": ("nrc-cat-late-gestation", "NRC", "NRC-2006", "feline", "gestation-lactation", ""),
    "NRC RA Cat Peak Lactation": ("nrc-cat-peak-lactation", "NRC", "NRC-2006", "feline", "gestation-lactation", ""),
    "FEDIAF Cat Reproduction": ("fediaf-cat-reproduction", "FEDIAF", "FEDIAF-2025", "feline", "gestation-lactation", ""),
}

NUM = r"(\d+(?:\.\d+)?)"
# formula -> (printed unit kind, rule, greater than). "kg DM": the template divided a
# figure printed per kg DM by 4 (4,000 kcal ME per kg DM); "vitamin-d-mcg": it multiplied
# a figure printed in mcg by 40 IU/mcg.
CONSTANT_RULES = [
    (re.compile(r"=\(%s/\(4\*1000\)\)\*1000" % NUM), "kg DM", "printed", False),
    (re.compile(r"=\(%s/4000\)\*1000" % NUM), "kg DM", "printed", False),
    (re.compile(r"=%s/4" % NUM), "kg DM", "printed", False),
    (re.compile(r"=%s/4\+0\.000000001" % NUM), "kg DM", "printed", True),
    (re.compile(r"=%s\*40" % NUM), "vitamin-d-mcg", "printed", False),
    (re.compile(r"=%s/0\.6" % NUM), "", "folic-acid-to-dfe", False),
]
MBW_BASIS = {"canine": "kg BW^0.75", "feline": "kg BW^0.67"}
LATE_GROWTH = re.compile(
    r"=IF\(AND\(N\('Standards \| Dyn Decile Sys Table'!\$E\$3\)>0,"
    r"N\('Standards \| Dyn Decile Sys Table'!\$E\$3\)<=15\),%s,%s\)" % (NUM, NUM))
REF = re.compile(r"=([A-Z]{1,2})(\d+)(\*\d+/1000|\*0\.3|/0\.3)")


def col_index(col):
    n = 0
    for ch in col:
        n = n * 26 + ord(ch) - 64
    return n


def plain(text):
    """A decimal string without exponent or trailing zeros."""
    d = Decimal(text)
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def typed_figure(value):
    """(figure text, greater_than) for a typed number; the template wrote a printed
    greater-than figure as the figure plus 0.000000001."""
    text = repr(float(value))
    if "e" in text:
        text = plain(text)
    m = re.fullmatch(r"(\d+)\.(\d{9})", text)
    if m and m.group(2).endswith("1"):
        base = Decimal(text) - Decimal("0.000000001")
        if base == base.quantize(Decimal("0.000001")):
            return plain(str(base)), True
    return plain(text), False


def convert_cell(cell, row_no, col, nutrient, sel, row_ids):
    """(figure text, printed unit, rule) for one limit cell."""
    nutrient_id = nutrient["id"]
    if cell is None:
        raise ValueError("blank limit cell %s%d" % (col, row_no))
    if cell == "none":
        return "none", "", "printed"
    if isinstance(cell, (int, float)) and not isinstance(cell, bool):
        figure, greater = typed_figure(cell)
        return (">" if greater else "") + figure, "", "printed"
    if not isinstance(cell, dict):
        raise ValueError("unexpected cell %s%d %r" % (col, row_no, cell))
    f = cell["formula"]
    for pattern, unit_kind, rule, greater in CONSTANT_RULES:
        m = pattern.fullmatch(f)
        if m:
            if unit_kind == "kg DM":
                if nutrient["basis"] != "per-mcal":
                    raise ValueError("per kg DM figure on a %s row %s%d" % (
                        nutrient["basis"], col, row_no))
                unit = nutrient["amount"] + "/kg DM"
            elif unit_kind == "vitamin-d-mcg":
                if nutrient["basis"] == "per-mcal":
                    unit = "mcg/1000 kcal"
                else:
                    unit = "mcg/" + MBW_BASIS[sel["species"]]
            else:
                unit = ""
            return (">" if greater else "") + plain(m.group(1)), unit, rule
    m = LATE_GROWTH.fullmatch(f)
    if m:
        return (plain(m.group(1)) + "|" + plain(m.group(2)), "",
                "fediaf-late-growth-by-mature-weight")
    if f == "=(N38+N42)/M44" and nutrient_id == "la-aa-to-epa-dha-ratio" and col == "N":
        return "", "", "la-aa-over-epa-dha"
    m = REF.fullmatch(f)
    if m and m.group(1) == col:
        ref_id = row_ids[int(m.group(2))]
        op = m.group(3)
        if op.startswith("*") and op.endswith("/1000"):
            mer = op[1:-5]
            if ref_id + "-mbw" != nutrient_id or mer != sel["mer"]:
                raise ValueError("MBW formula %s%d %s does not fit" % (col, row_no, f))
            return "", "", "mbw-from-per-mcal"
        if op == "*0.3" and ref_id.startswith("vitamin-a") and nutrient_id.startswith("retinol"):
            return "", "", "retinol-from-vitamin-a-iu"
        if op == "/0.3" and ref_id.startswith("retinol") and nutrient_id.startswith("vitamin-a"):
            return "", "", "vitamin-a-iu-from-retinol"
    raise ValueError("unrecognised formula %s%d %s" % (col, row_no, f))


def parse_notes(path):
    """{cell: text} from a dump notes file ("[A1] (author None)" then the text)."""
    notes = {}
    current = None
    lines = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\[([A-Z]{1,3}\d+)\] \(author [^)]*\)\s*$", line)
            if m:
                if current:
                    notes[current] = "".join(lines).strip()
                current, lines = m.group(1), []
            else:
                lines.append(line)
    if current:
        notes[current] = "".join(lines).strip()
    return notes


def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        for r in rows:
            w.writerow([r[h] for h in header])


def main(table_path, notes_path, sources_path, out_dir):
    table = json.load(open(table_path, encoding="utf-8"))
    sheet_notes = parse_notes(notes_path)
    sources = (json.load(open(sources_path, encoding="utf-8"))["sources"]
               if sources_path != "-" else {})
    rows = {r["row"]: r for r in table["rows"]}
    s01_by_s02 = {s["s02_row"]: s for s in table["s01_rows"] if s["s02_row"]}

    row_ids = {}
    for row_no, base in BASE_IDS:
        row_ids[row_no] = base
        nxt = rows.get(row_no + 1)
        if nxt and nxt["key"] and nxt["key"].endswith(" MBW"):
            row_ids[row_no + 1] = base + "-mbw"
    nutrient_rows = sorted(row_ids)
    assert [r for r in range(5, 120)] == nutrient_rows, "nutrient rows not 5-119"

    sels = []
    for s in table["selections"]:
        rid, std, edition, species, stage, mer = REQUIREMENTS[s["name"]]
        sels.append(dict(s, id=rid, standard=std, edition=edition, species=species,
                         life_stage=stage, mer=mer))
    min_cols = {s["min_col"]: s for s in sels}
    max_cols = {s["max_col"]: s for s in sels}
    code_cols = {s["code_col"]: s for s in sels}

    # Notes: number them in sheet order (row, then column) and attach each to its scope.
    note_ids = {}
    note_rows = []
    cell_re = re.compile(r"([A-Z]+)(\d+)")
    for cell in sorted(sheet_notes, key=lambda c: (int(cell_re.fullmatch(c).group(2)),
                                                   col_index(cell_re.fullmatch(c).group(1)))):
        nid = "n%03d" % (len(note_rows) + 1)
        note_ids[cell] = nid
        note_rows.append({"id": nid, "text": sheet_notes[cell],
                          "origin": "DDS template Version 21OCT26b"})
    attach = {}  # (scope key) -> [note ids]
    general = []
    energy_ids = set()
    for cell, nid in note_ids.items():
        col, r = cell_re.fullmatch(cell).groups()
        r = int(r)
        if 5 <= r <= 119 and col in ("B", "C", "D"):
            attach.setdefault(("nutrient", row_ids[r]), []).append(nid)
        elif 5 <= r <= 119 and col in min_cols:
            attach.setdefault(("min", min_cols[col]["id"], row_ids[r]), []).append(nid)
        elif 5 <= r <= 119 and col in max_cols:
            attach.setdefault(("max", max_cols[col]["id"], row_ids[r]), []).append(nid)
        elif 5 <= r <= 119 and col in code_cols:
            attach.setdefault(("max", code_cols[col]["id"], row_ids[r]), []).append(nid)
        elif r <= 3 and col in min_cols:
            attach.setdefault(("requirement", min_cols[col]["id"]), []).append(nid)
        elif r <= 3 and col in max_cols:
            attach.setdefault(("requirement", max_cols[col]["id"]), []).append(nid)
        elif r == 4 and (col in min_cols or col in max_cols):
            sel = min_cols.get(col) or max_cols[col]
            attach.setdefault(("energy", sel["id"]), []).append(nid)
            energy_ids.add(nid)
        else:
            general.append((cell, nid))
    for row in note_rows:
        row["scope"] = ""
    general_ids = {nid for _, nid in general}
    for row in note_rows:
        if row["id"] in general_ids:
            row["scope"] = "table"
        elif row["id"] in energy_ids:
            row["scope"] = "energy"

    # nutrients.csv
    nutrient_out = []
    for r in nutrient_rows:
        nid = row_ids[r]
        s01 = s01_by_s02.get(r)
        k = s01["K"] if s01 else None
        unit = rows[r]["unit"]
        if "BW^0.75" in unit:
            basis = "per-mbw"
        elif "/Mcal" in unit:
            basis = "per-mcal"
        elif unit == "g/100 g DM":
            basis = "per-100g-dm"
        elif unit == "no units":
            basis = "ratio"
        elif unit == "kcal/g DM":
            basis = "energy-density"
        else:
            raise ValueError("unit %r" % unit)
        amount_text = unit.split("Cats:")[0].replace("Dogs:", "").strip()
        amount = ""
        for a in ("mcg", "mg", "g", "IU"):
            if amount_text.startswith(a):
                amount = a
                break
        if basis in ("ratio", "energy-density"):
            amount = ""
        if s01 is None:
            k_text = ""
        elif k is None:
            k_text = "blank"
        elif isinstance(k, str):
            k_text = k
        else:
            k_text = plain(repr(float(k)))
        nutrient_out.append({
            "id": nid, "name": rows[r]["key"], "unit": unit, "amount": amount, "basis": basis,
            "k": k_text,
            "mbw_of": nid[:-4] if nid.endswith("-mbw") else "",
            "enterable": "yes" if s01 else "no", "ig_code": IG_CODES.get(nid, ""),
            "notes": " ".join(attach.get(("nutrient", nid), [])),
        })
    write_csv(os.path.join(out_dir, "nutrients.csv"),
              ["id", "name", "unit", "amount", "basis", "k", "mbw_of", "enterable", "ig_code",
               "notes"],
              nutrient_out)

    # requirements.csv
    write_csv(os.path.join(out_dir, "requirements.csv"),
              ["id", "name", "standard", "edition", "species", "life_stage",
               "mer_kcal_per_mbw", "notes", "energy_notes"],
              [{"id": s["id"], "name": s["name"], "standard": s["standard"],
                "edition": s["edition"], "species": s["species"], "life_stage": s["life_stage"],
                "mer_kcal_per_mbw": s["mer"],
                "notes": " ".join(attach.get(("requirement", s["id"]), [])),
                "energy_notes": " ".join(attach.get(("energy", s["id"]), []))} for s in sels])

    # standards/<edition>/<requirement>.csv
    header = ["nutrient", "min", "min_unit", "min_rule", "min_source", "max", "max_unit",
              "max_rule", "max_type", "max_source", "min_notes", "max_notes"]
    nutrients_by_id = {n["id"]: n for n in nutrient_out}
    for s in sels:
        out = []
        for r in nutrient_rows:
            nid = row_ids[r]
            cells = rows[r]["cells"]
            line = {"nutrient": nid}
            for bound, col in (("min", s["min_col"]), ("max", s["max_col"])):
                figure, unit, rule = convert_cell(cells.get(col), r, col, nutrients_by_id[nid],
                                                  s, row_ids)
                src = sources.get("%s/%s/%s" % (s["id"], nid, bound), {})
                if "figure" in src:
                    figure, unit = src["figure"], src["unit"]
                if figure not in ("none", "") and not src.get("source"):
                    raise ValueError("no source for %s %s %s" % (s["id"], nid, bound))
                if src.get("rule"):
                    rule = src["rule"]
                line[bound] = figure
                line[bound + "_unit"] = unit
                line[bound + "_rule"] = rule
                line[bound + "_source"] = src.get("source", "")
                line[bound + "_notes"] = " ".join(attach.get((bound, s["id"], nid), []))
            code = cells.get(s["code_col"])
            line["max_type"] = code if code is not None else ""
            out.append(line)
        write_csv(os.path.join(out_dir, "standards", s["edition"], s["id"] + ".csv"), header, out)

    write_csv(os.path.join(out_dir, "notes.csv"), ["id", "scope", "text", "origin"], note_rows)
    print("nutrients %d, requirements %d, notes %d (table-wide %d)" % (
        len(nutrient_out), len(sels), len(note_rows), len(general)))
    for cell, nid in general:
        print("  table-wide note", nid, "from", cell)


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    main(*sys.argv[1:])
