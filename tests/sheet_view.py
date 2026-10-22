"""The sheet view (tests only): template cells rendered from the core's results, to compare
with the test vectors.

Phase 1b covers the requirement table (s02: limits, maximum types, names, units, the
requirement names and the fixed labels) and the Standards tab's multipliers (s01 column K).
Cells of later phases raise NotModelled.
"""

import re

import sheet_map
from oan import table

CELL = re.compile(r"(s0[12])!([A-Z]+)([0-9]+)$")


class NotModelled(Exception):
    pass


class TableView:
    """The requirement table at one expected mature body weight (None: not entered)."""

    def __init__(self, data, mature_weight_kg=None):
        self.data = data
        self.mature_weight_kg = mature_weight_kg
        self.nutrients = {n["id"]: n for n in data["nutrients"]}
        self.names = {r["id"]: r["name"] for r in data["requirements"]}
        self.columns = {}
        for rid, (min_col, max_col, code_col) in sheet_map.REQUIREMENT_COLUMNS.items():
            self.columns[min_col] = (rid, "min")
            self.columns[max_col] = (rid, "max")
            self.columns[code_col] = (rid, "code")
        self.rows = {row: nid for nid, row in sheet_map.NUTRIENT_ROWS.items()}
        self._limits = {}

    def limits(self, rid):
        if rid not in self._limits:
            self._limits[rid] = table.compute_limits(self.data, rid, self.mature_weight_kg)
        return self._limits[rid]

    def cell(self, ref):
        """(value, kind) of one cell; the value is encoded as in the vectors (a number, a
        text, or None for a blank cell)."""
        m = CELL.match(ref)
        if not m:
            raise NotModelled(ref)
        tab, col, row = m.group(1), m.group(2), int(m.group(3))
        if tab == "s01":
            return self._standards_cell(ref, col, row)
        if col + str(row) in sheet_map.TABLE_LABELS:
            return sheet_map.TABLE_LABELS[col + str(row)], "label"
        nid = self.rows.get(row)
        if nid is not None and col == sheet_map.NAME_COLUMN:
            return self.nutrients[nid]["name"], "name"
        if nid is not None and col == sheet_map.UNIT_COLUMN:
            return self.nutrients[nid]["unit"], "unit"
        rid, role = self.columns.get(col, (None, None))
        if rid is None:
            raise NotModelled(ref)
        if row == sheet_map.NAME_ROW and role in ("min", "code"):
            return self.names[rid], "requirement name"
        if row == sheet_map.CODE_LABEL_ROW and role == "code":
            return sheet_map.CODE_LABEL, "label"
        if nid is None:
            raise NotModelled(ref)
        if role == "code":
            return self.data["limits"][rid][nid]["max_type"] or None, "max type"
        low, high = self.limits(rid)[nid]
        value = low if role == "min" else high
        return (table.NONE if value is None else value), "limit"

    def _standards_cell(self, ref, col, row):
        nid = sheet_map.S01_ROWS.get(row)
        if nid is None or col != sheet_map.MULTIPLIER_COLUMN:
            raise NotModelled(ref)
        k = self.nutrients[nid]["k"]
        if k == "blank":
            return None, "multiplier"
        if k == "N/A":
            return k, "multiplier"
        return float(k), "multiplier"
