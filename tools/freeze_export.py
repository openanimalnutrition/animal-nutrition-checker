"""One-time copy of the released template's cell values, for the real-Sheets check.

Reads the template exported from Google Sheets as .xlsx (Version 21OCT26b, exported 21 Oct
2026) and writes the value Sheets stored in every non-empty cell of the Standards tab (s01)
and the requirement table (s02): whether the cell holds a formula, the value's type and the
value as written in the file. Formulas, notes and formatting are not copied.

Sheets writes a formula's number with at most 10 significant digits and a typed number in
full; the value is kept as the text in the file, so nothing is rounded twice.

Usage: python3 -I -B tools/freeze_export.py BOOK_XLSX OUT_JSON
"""

import hashlib
import json
import posixpath
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
TABS = {"s01": "Standards | Dyn Decile Sys Tabl", "s02": "Healthy Dog Cat Reqt Data"}
# The value types of the file: n a number, s a shared text, str a formula's text, inlineStr a
# typed text, b true/false, e an error.
TYPES = {"n", "s", "str", "inlineStr", "b", "e"}
REF = re.compile(r"([A-Z]+)([0-9]+)$")


def text_of(el):
    """The text of a shared or inline string (plain or in runs)."""
    return "".join(t.text or "" for t in el.iter("{%s}t" % NS["m"]))


def sheet_parts(z):
    book = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    targets = {r.get("Id"): r.get("Target") for r in rels.findall("rel:Relationship", NS)}
    parts = {}
    for s in book.find("m:sheets", NS):
        target = targets[s.get("{%s}id" % NS["r"])]
        parts[s.get("name")] = posixpath.normpath(
            target.lstrip("/") if target.startswith("/") else posixpath.join("xl", target))
    return parts


def column_number(col):
    n = 0
    for ch in col:
        n = n * 26 + ord(ch) - 64
    return n


def read_cells(z, part, shared):
    cells = []
    sheet = ET.fromstring(z.read(part))
    for c in sheet.iter("{%s}c" % NS["m"]):
        ref = c.get("r")
        typ = c.get("t", "n")
        if typ not in TYPES:
            raise ValueError("%s: unknown value type %r" % (ref, typ))
        formula = c.find("m:f", NS) is not None
        if typ == "inlineStr":
            el = c.find("m:is", NS)
            value = None if el is None else text_of(el)
        else:
            v = c.find("m:v", NS)
            value = None if v is None else v.text or ""
            if typ == "s" and value is not None:
                value = shared[int(value)]
        if value is None:
            continue  # formatted but empty
        typ = "s" if typ == "inlineStr" else typ
        col, row = REF.match(ref).groups()
        cells.append(((int(row), column_number(col)), ref, [1 if formula else 0, typ, value]))
    cells.sort()
    return [(ref, cell) for _, ref, cell in cells]


def main(argv):
    book, out = argv[1], argv[2]
    with open(book, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    with zipfile.ZipFile(book) as z:
        shared = [text_of(si) for si in ET.fromstring(z.read("xl/sharedStrings.xml"))]
        parts = sheet_parts(z)
        tabs = {tab: read_cells(z, parts[name], shared) for tab, name in TABS.items()}
    lines = ["{",
             '  "about": "The cell values of the DDS template Version 21OCT26b as Google Sheets '
             'exported them (.xlsx, 21 Oct 2026), for the real-Sheets check '
             '(tests/real_sheets_check.py). Each cell: [1 if a formula, the value type '
             '(n number, s text, str a formula\'s text, b true/false, e error), the value as '
             'written in the file]. Written once by tools/freeze_export.py; never edited.",',
             '  "xlsx_sha256": %s,' % json.dumps(digest),
             '  "tabs": %s,' % json.dumps(TABS, ensure_ascii=False),
             '  "cells": {']
    for i, (tab, cells) in enumerate(tabs.items()):
        lines.append('    %s: {' % json.dumps(tab))
        for j, (ref, cell) in enumerate(cells):
            comma = "," if j < len(cells) - 1 else ""
            lines.append('      %s: %s%s' % (json.dumps(ref), json.dumps(cell, ensure_ascii=False),
                                             comma))
        lines.append('    }' + ("," if i < len(tabs) - 1 else ""))
    lines += ["  }", "}"]
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("%s: %s" % (out, ", ".join("%s %d cells" % (t, len(c)) for t, c in tabs.items())))


if __name__ == "__main__":
    main(sys.argv)
