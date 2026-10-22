"""The sheet view (tests only): template cells rendered from the core's results, to compare
with the test vectors.

Phase 1b covers the requirement table (s02: limits, maximum types, names, units, the
requirement names and the fixed labels) and the Standards tab's multipliers (s01 column K).
Phase 2 adds the energy cells (EnergyView): s01 G4, C11 and its highlight, and row 11.
Cells of later phases raise NotModelled.
"""

import re

import sheet_map
from oan import bands, energy, inputs, numbers, table

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


class OutsideRule(Exception):
    """A case input the input rules reject; the core does not compute with it."""


class Missing(Exception):
    """A required input is not entered (the template computes with a blank as 0)."""


class EnergyView:
    """The energy cells of the Standards tab for one case's inputs ({cell: value}). Inputs a
    case does not list keep the export's (sheet_map.EXPORT_INPUTS) when defaults is True."""

    def __init__(self, data, cells, defaults=False):
        self.data = data
        given = dict(sheet_map.EXPORT_INPUTS) if defaults else {}
        given.update(cells)
        self.facts, self.entries = {}, {}
        for cell, value in sorted(given.items()):
            if cell in sheet_map.RETIRED_CELLS:
                continue
            col, row = cell[:1], cell[1:]
            if cell in sheet_map.INPUT_CELLS:
                field = sheet_map.INPUT_CELLS[cell]
                verdict = inputs.check_fact(field, value, data)
                target, key = self.facts, field
            elif row == str(sheet_map.ENERGY_ROW) and col in sheet_map.ENTRY_COLUMNS:
                verdict = inputs.check_entry(inputs.ENERGY_ENTRY, value, data)
                target, key = self.entries, col
            else:
                raise NotModelled(cell)
            if verdict.status == "reject":
                raise OutsideRule("%s: %s" % (cell, verdict.reason))
            target[key] = verdict.value
        name = self.facts.get("requirement")
        self.requirement_id = next(
            (r["id"] for r in data["requirements"] if r["name"] == name), None)
        if self.requirement_id is None:
            self.requirement = self.used = None
        else:
            self.requirement = energy.requirement_energy(data, self.requirement_id, self.facts)
            self.used = energy.energy_used(self.requirement,
                                           self.facts.get("energy_intake_kcal_per_day"))

    def _shown(self, result):
        if result.kcal is not None:
            return result.kcal
        if result.reason == "body-weight-needed":
            raise Missing(result.reason)
        if result.reason not in sheet_map.ENERGY_MESSAGES:
            raise NotModelled("no template message for %s" % result.reason)
        return sheet_map.ENERGY_MESSAGES[result.reason]

    def cells(self):
        """{cell: value} of G4, C11, E11 and row 11's descriptions and edges, plus
        'C11_highlighted' (the C11 rule: highlighted when C11 is not a number)."""
        out = {}
        if self.requirement is None:
            out["G4"] = {"error": "#N/A"}
            out["C11"] = sheet_map.SELECT_REQUIREMENT
            out["E11"] = {"error": "#N/A"}
        else:
            out["G4"] = self._shown(self.requirement)
            out["C11"] = self._shown(self.used)
            out["E11"] = table.NONE
        c11 = out["C11"]
        out["C11_highlighted"] = not numbers.is_number(c11)
        row = str(sheet_map.ENERGY_ROW)
        edge_cells = [col for col, _ in sheet_map.ROW11_BELOW_MIN] + [sheet_map.ROW11_MIN] + \
            [col for col, _ in sheet_map.ROW11_DECILES] + [sheet_map.ROW11_RANGE_HIGH]
        described = list(sheet_map.ROW11_DESCRIPTIONS.values()) + [sheet_map.ROW11_JOIN[0]]
        if out["C11_highlighted"]:
            for col in edge_cells + described:
                out[col + row] = ""
            return out
        high = energy.range_high(self.data, c11)
        for col, f in sheet_map.ROW11_BELOW_MIN:
            out[col + row] = c11 * f
        out[sheet_map.ROW11_MIN + row] = c11
        for col, f in sheet_map.ROW11_DECILES:
            out[col + row] = ((high - c11) * f) + c11
        out[sheet_map.ROW11_RANGE_HIGH + row] = high
        for entry_col, label_col in sheet_map.ROW11_DESCRIPTIONS.items():
            value = self.entries.get(entry_col)
            if value is None:
                out[label_col + row] = ""
                continue
            code = bands.band(value, c11, high, has_max=False)
            out[label_col + row] = (sheet_map.NO_RANGE_LABEL if code == bands.NO_RANGE
                                    else sheet_map.BAND_LABELS[code])
        both = all(out[c + row] != "" for c in sheet_map.ROW11_DESCRIPTIONS.values())
        out[sheet_map.ROW11_JOIN[0] + row] = sheet_map.ROW11_JOIN[1] if both else ""
        return out
