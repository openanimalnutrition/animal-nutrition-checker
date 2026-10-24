"""One-time converter (data version 21OCT26b.5): the Standards tab's cell notes into data/.

Phase 1a took the requirement table tab's notes (n001-n168). This adds the 133 notes of the
Standards tab of the 21OCT26b export, word for word, as n169 onwards in sheet order (row,
then column), and attaches each:
- rows 1-10 (the header, the inputs, the caloric restriction row): table-wide (scope table);
- row 11 (energy): scope energy;
- a nutrient row (columns B, C, E, K): that nutrient's notes in nutrients.csv;
- a template row (EPA alone, vitamin D2, large-breed puppy calcium and its body weight row
  65): that row's notes in template.csv;
- a template figure whose source cites a Standards tab note ("note C122"): that figure's
  notes in template.csv.
Every note's origin now names its tab and cell, the old ones too, so a reader can find it.

Usage: python3 -I -B tools/add_standards_notes.py S01_NOTES S02_NOTES DATA_DIR
"""

import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

from convert_sheet_table import col_index, parse_notes  # noqa: E402
import sheet_map  # noqa: E402

ORIGIN = "DDS template Version 21OCT26b"
S01_TAB = "Standards tab"
S02_TAB = "Healthy Dog Cat Reqt Data tab"
CELL = re.compile(r"([A-Z]+)(\d+)")
NOTE_COLUMNS = ("B", "C", "E", "K")
# Row 65 holds the puppy body weight of the large-breed puppy calcium row.
EXTRA_TEMPLATE_ROWS = {65: "calcium-large-breed-puppy"}


def sheet_order(cell):
    col, row = CELL.fullmatch(cell).groups()
    return int(row), col_index(col)


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    return rows[0], [dict(zip(rows[0], r)) for r in rows[1:]]


def write(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        for r in rows:
            w.writerow([r[h] for h in header])


def write_last_field(path, header, rows):
    """Rewrite only the last field (the notes ids) of each changed line, keeping every other
    byte of the file as it is (some files quote fields the csv module would not)."""
    assert header[-1] == "notes", path
    with open(path, encoding="utf-8", newline="") as f:
        lines = f.read().split("\n")
    assert lines[-1] == "" and len(lines) == len(rows) + 2, path
    for i, row in enumerate(rows, start=1):
        old = next(csv.reader([lines[i]]))[-1]
        assert lines[i].endswith("," + old), (path, i)
        lines[i] = lines[i][:len(lines[i]) - len(old)] + row["notes"]
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines))


def add(ids_text, nid):
    ids = ids_text.split()
    if nid not in ids:
        ids.append(nid)
    return " ".join(ids)


def main(s01_path, s02_path, data_dir):
    s01 = parse_notes(s01_path)
    s02 = parse_notes(s02_path)
    notes_header, notes = read(os.path.join(data_dir, "notes.csv"))
    nut_header, nutrients = read(os.path.join(data_dir, "nutrients.csv"))
    tpl_header, template = read(os.path.join(data_dir, "template.csv"))

    # The existing notes are the requirement table tab's, numbered in sheet order.
    s02_cells = sorted(s02, key=sheet_order)
    assert len(s02_cells) == len(notes), (len(s02_cells), len(notes))
    for cell, row in zip(s02_cells, notes):
        assert row["origin"] == ORIGIN, row["id"]
        assert row["text"] == s02[cell], (row["id"], cell)
        row["origin"] = "%s, %s %s" % (ORIGIN, S02_TAB, cell)

    by_nutrient = {r["id"]: r for r in nutrients}
    by_template = {r["id"]: r for r in template}
    template_rows = dict(sheet_map.TEMPLATE_ROWS)
    template_rows.update(EXTRA_TEMPLATE_ROWS)
    first = len(notes) + 1
    cell_ids = {}
    unplaced = []
    for i, cell in enumerate(sorted(s01, key=sheet_order)):
        nid = "n%03d" % (first + i)
        cell_ids[cell] = nid
        col, r = CELL.fullmatch(cell).groups()
        r = int(r)
        scope = ""
        if r <= 10:
            scope = "table"
        elif r == sheet_map.ENERGY_ROW:
            scope = "energy"
        elif r in sheet_map.S01_ROWS and col in NOTE_COLUMNS:
            row = by_nutrient[sheet_map.S01_ROWS[r]]
            row["notes"] = add(row["notes"], nid)
        elif r in template_rows and col in NOTE_COLUMNS:
            row = by_template[template_rows[r]]
            row["notes"] = add(row["notes"], nid)
        else:
            scope = "table"
            unplaced.append(cell)
        notes.append({"id": nid, "scope": scope, "text": s01[cell],
                      "origin": "%s, %s %s" % (ORIGIN, S01_TAB, cell)})

    cited = 0
    for row in template:
        for cell in re.findall(r"\bnote ([A-Z]+\d+)\b", row["source"]):
            row["notes"] = add(row["notes"], cell_ids[cell])
            cited += 1

    write(os.path.join(data_dir, "notes.csv"), notes_header, notes)
    write_last_field(os.path.join(data_dir, "nutrients.csv"), nut_header, nutrients)
    write_last_field(os.path.join(data_dir, "template.csv"), tpl_header, template)
    print("notes: %d table tab + %d Standards tab (n%03d-n%03d); template sources citing a "
          "note: %d; table-wide by position: %s" % (
              len(s02_cells), len(s01), first, first + len(s01) - 1, cited,
              " ".join(unplaced) or "none"))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
