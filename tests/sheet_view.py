"""The sheet view (tests only): template cells rendered from the core's results, to compare
with the test vectors.

Phase 1b covers the requirement table (s02: limits, maximum types, names, units, the
requirement names and the fixed labels) and the Standards tab's multipliers (s01 column K).
Phase 2 adds the energy cells (EnergyView): s01 G4, C11 and its highlight, and row 11.
Phase 3 adds the Standards tab's rows 12-130 (StandardsView): the minimums and maximums
(columns C and E), the band edges and range highs, the descriptions (L, N) and summary
sentences (AR), the text checks (rows 49-58) and the helper cells. Phase 4 adds the rest of
the computed cells the real-Sheets check compares: the edges shown below each band edge, the
row names and multipliers, row 10 (the caloric restriction), the header cells (M2, N2, C3),
the cells that never change (rows 55 and 65, AP6-AP9), and the requirement table's energy
row (s02 row 4) and name-and-unit column (D). Other cells raise NotModelled.
"""

import re

import sheet_map
from oan import bands, energy, inputs, limits, numbers, outcomes, table

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
        if nid is not None and col == sheet_map.NAME_UNIT_COLUMN:
            n = self.nutrients[nid]
            return n["name"] + " " + n["unit"], "name and unit"
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
                verdict = inputs.check_fact(
                    field, sheet_map.checker_value(field, value), data)
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


def _is_error(v):
    return isinstance(v, dict)


def _error(x):
    """The template's error code for the core's Unavailable."""
    code = sheet_map.REQUIREMENT_ERROR if x.reason == limits.REQUIREMENT_NEEDED \
        else sheet_map.OTHER_ERROR
    return {"error": code}


def _cell_value(x):
    """A limit as the template shows it: a number, "none" or an error code."""
    if x is None:
        return table.NONE
    if limits.unavailable(x):
        return _error(x)
    return x


class StandardsView:
    """The Standards tab's cells for one case's inputs ({cell: value}). Inputs a case does
    not list keep the export's (sheet_map.EXPORT_INPUTS)."""

    ENTRY_ROWS = {**sheet_map.S01_ROWS, **sheet_map.TEMPLATE_ROWS}

    def __init__(self, data, cells):
        self.data = data
        given = dict(sheet_map.EXPORT_INPUTS)
        given.update(cells)
        energy_cells, self.facts, self.entries = {}, {}, {}
        for cell, value in sorted(given.items()):
            if cell in sheet_map.RETIRED_CELLS:
                continue
            col, row = cell[:1], cell[1:]
            if cell in sheet_map.INPUT_CELLS:
                field = sheet_map.INPUT_CELLS[cell]
                verdict = inputs.check_fact(
                    field, sheet_map.checker_value(field, value), data)
                self.facts[field] = verdict.value
                energy_cells[cell] = value
            elif col in sheet_map.ENTRY_COLUMNS and row == str(sheet_map.ENERGY_ROW):
                verdict = inputs.check_entry(inputs.ENERGY_ENTRY, value, data)
                energy_cells[cell] = value
            elif col in sheet_map.ENTRY_COLUMNS and row.isdigit() and \
                    int(row) in self.ENTRY_ROWS:
                nid = self.ENTRY_ROWS[int(row)]
                verdict = inputs.check_entry(nid, value, data)
                self.entries.setdefault(nid, {})[sheet_map.ENTRY_COLUMNS[col]] = verdict.value
            else:
                raise NotModelled(cell)
            if verdict.status == "reject":
                raise OutsideRule("%s: %s" % (cell, verdict.reason))
        self.energy = EnergyView(data, energy_cells)
        self.name = self.facts.get("requirement")
        # The template's own rules: the sheet view reproduces Version 21OCT26b (parity).
        self.request = limits.Request(data, self.energy.requirement_id, self.facts,
                                      self.entries, template_rules=True)
        self.table = TableView(data, self.facts.get("mature_weight_kg"))
        self.nutrients = {n["id"]: n for n in data["nutrients"]}
        self._energy_cells = None
        self._checks = None

    # Cells.

    def cell(self, ref):
        if ref.startswith("s02!"):
            return self._table_cell(ref)
        if ref.startswith("s01!"):
            return self.table.cell(ref)[0]
        m = re.match(r"([A-Z]+)([0-9]+)$", ref)
        if not m:
            raise NotModelled(ref)
        col, row = m.group(1), int(m.group(2))
        if ref in sheet_map.INSTRUCTION_CELLS or ref in sheet_map.UNUSED_CELLS:
            raise NotModelled(ref)
        if ref in sheet_map.FIXED_CELLS:
            return sheet_map.FIXED_CELLS[ref]
        if row >= sheet_map.RESTRICTION_ROW:
            if col == sheet_map.NAME_COLUMN and (row in sheet_map.S01_LABELS or
                                                 row in self.ENTRY_ROWS):
                return self._label(self.ENTRY_ROWS.get(row), row)
            if col == sheet_map.EDGE_BOTTOM and (row in self.ENTRY_ROWS or row in (
                    sheet_map.RESTRICTION_ROW, sheet_map.ENERGY_ROW)):
                return 0.0
            if col == sheet_map.MULTIPLIER_COLUMN and row in sheet_map.TEMPLATE_ROWS:
                return float(self.data["template"][sheet_map.TEMPLATE_ROWS[row]]["k"])
            if col == sheet_map.MULTIPLIER_COLUMN and row == sheet_map.ENERGY_ROW:
                return float(self.data["energy"]["energy-range-high"]["figure"])
        if row <= 4 or row == sheet_map.ENERGY_ROW:
            return self._top(ref)
        if row == sheet_map.RESTRICTION_ROW:
            return self._restriction(col, ref)
        if col == sheet_map.MULTIPLIER_COLUMN:
            return self.table.cell("s01!" + ref)[0]
        for (cid, fid), check_row in sheet_map.TEXT_CHECK_ROWS.items():
            if row == check_row and col in sheet_map.DESCRIPTOR_COLUMNS:
                return self._text_check(row, sheet_map.DESCRIPTOR_COLUMNS[col])
        nid = self.ENTRY_ROWS.get(row)
        if nid is None:
            raise NotModelled(ref)
        if col in sheet_map.LIMIT_COLUMNS:
            if sheet_map.LIMIT_COLUMNS[col] == "min":
                return _cell_value(self.request.minimum(nid))
            return _cell_value(self.request.maximum(nid))
        if col in sheet_map.DESCRIPTOR_COLUMNS:
            return self._describe(nid, row, sheet_map.DESCRIPTOR_COLUMNS[col])
        if col == sheet_map.SUMMARY_COLUMN:
            return self._summary(nid, row)
        if col == sheet_map.JOIN_COLUMN:
            return self._join(nid, row)
        edges = self._edges(nid)
        if col in edges:
            return edges[col]
        raise NotModelled(ref)

    def _top(self, ref):
        if ref == sheet_map.SPECIES_CELL:
            r = self.request.requirement
            return "" if r is None else sheet_map.SPECIES_LABELS[r["species"]]
        if ref == sheet_map.SELECTED_CELL[0]:
            return sheet_map.SELECTED_CELL[1] + (self.name or "")
        if ref == sheet_map.POUNDS_CELL[0]:
            text, per_kg = sheet_map.POUNDS_CELL[1:]
            bw = self.facts.get("body_weight_kg") or 0.0
            return text + numbers.to_text(numbers.sheet_round(bw * per_kg, 1))
        if ref == sheet_map.POSITION_CELL:
            if self.request.requirement is None:
                return {"error": sheet_map.REQUIREMENT_ERROR}
            column = sheet_map.REQUIREMENT_COLUMNS[self.request.requirement["id"]][0]
            return float(_column_number(column) - 1)
        if ref == sheet_map.AAFCO_FACTOR_CELL:
            return _cell_value(self.request.aafco_factor)
        if ref in sheet_map.ARGININE_BASE_CELLS:
            return _cell_value(self.request.arginine_base(sheet_map.ARGININE_BASE_CELLS[ref]))
        if ref == sheet_map.INTAKE_LABEL[0]:
            return sheet_map.INTAKE_LABEL[1]
        if ref == sheet_map.INTAKE_SHORTFALL_CELL:
            shortfall = self.request.intake_shortfall
            return "" if shortfall is None else shortfall
        if ref == sheet_map.SUMMARY_COLUMN + str(sheet_map.ENERGY_ROW):
            return self._summary("energy", sheet_map.ENERGY_ROW)
        if self._energy_cells is None:
            self._energy_cells = self.energy.cells()
        if ref in self._energy_cells:
            return self._energy_cells[ref]
        raise NotModelled(ref)

    def _table_cell(self, ref):
        """A requirement table cell; its energy row (row 4) needs the Standards tab's
        inputs."""
        col, row = sheet_map.col_row(ref[len("s02!"):])
        if row != sheet_map.TABLE_ENERGY_ROW:
            return self.table.cell(ref)[0]
        name, unit = sheet_map.TABLE_ENERGY_NAME
        if col == sheet_map.NAME_COLUMN:
            return name
        if col == sheet_map.UNIT_COLUMN:
            return unit
        if col == sheet_map.NAME_UNIT_COLUMN:
            return name + " " + unit
        rid, role = self.table.columns.get(col, (None, None))
        if role == "min":
            return self.energy._shown(energy.requirement_energy(self.data, rid, self.facts))
        if role == "max":
            return table.NONE
        raise NotModelled(ref)

    def _restriction(self, col, ref):
        """Row 10: the restriction's range is C10 (0: no restriction) to E10, the input
        rule's highest restriction; L10 gives the band of the restriction entered in G10."""
        low = 0.0
        high = float(inputs.FACTS["caloric_restriction_percent"][1][1])
        if col == "C":
            return low
        if col == "E":
            return high
        edges = self._edge_cells(low, high, None)
        if col in edges:
            return edges[col]
        r = self.facts.get("caloric_restriction_percent")
        label = (sheet_map.RESTRICTION_NONE_LABEL if r is None or r == 0
                 else sheet_map.BAND_LABELS[bands.band(r, low, high, has_max=True)])
        if col == "L":
            return label
        if col == sheet_map.SUMMARY_COLUMN:
            return inputs.trim(label + sheet_map.RESTRICTION_SUMMARY)
        raise NotModelled(ref)

    def _edges(self, nid):
        return self._edge_cells(_cell_value(self.request.minimum(nid)),
                                _cell_value(self.request.maximum(nid)),
                                self.request.multiplier(nid))

    def _edge_cells(self, c, e, k):
        """The band edges, the edges shown below them and the range high as the template
        computes them from a row's C, E and K cells (an error in C gives errors; AP is 0
        when C is an error and E none)."""
        if _is_error(e):
            ap = e
        elif e == table.NONE:
            ap = (c if numbers.is_number(c) else 0.0) * (k or 0.0)
        elif e == 0:
            ap = 0.0
        else:
            ap = e
        out = {sheet_map.RANGE_HIGH: ap}
        if _is_error(c):
            for col, _ in (sheet_map.EDGE_BELOW_MIN + sheet_map.EDGE_DECILES +
                           sheet_map.EDGE_SHOWN_BELOW_MIN + sheet_map.EDGE_SHOWN_DECILES):
                out[col] = c
            out[sheet_map.EDGE_MIN] = c
            return out
        minimum = None if c == table.NONE else c
        base = minimum or 0.0
        if _is_error(ap):
            edges = [base * f for _, f in sheet_map.EDGE_BELOW_MIN] + \
                [base] + [ap] * len(sheet_map.EDGE_DECILES)
        else:
            edges = bands.lower_edges(minimum, ap)
        cols = [col for col, _ in sheet_map.EDGE_BELOW_MIN] + [sheet_map.EDGE_MIN] + \
            [col for col, _ in sheet_map.EDGE_DECILES]
        out.update(zip(cols, edges))
        # Shown below each edge: C x fraction (0 when C is none), and ((AP - C) x fraction)
        # + C, with W (0) for C when C is none.
        for col, f in sheet_map.EDGE_SHOWN_BELOW_MIN:
            out[col] = base * f
        for col, f in sheet_map.EDGE_SHOWN_DECILES:
            out[col] = ap if _is_error(ap) else ((ap - base) * f) + base
        return out

    def _describe(self, nid, row, side):
        """L (low) or N (high): the template's text for the core's outcome."""
        if nid == "energy":
            return self._top(("L" if side == "low" else "N") + str(row))
        lim = self.request.limits(nid)
        value = self.entries.get(nid, {}).get(side)
        o = outcomes.describe(value, side, lim)
        if o.code == outcomes.NOT_ENTERED:
            # The template counts nothing entered as 0 under Min.
            if side == "low" and limits.unavailable(lim.minimum):
                return _error(lim.minimum)
            if side == "low" and lim.minimum is None:
                return sheet_map.NO_MIN_LABEL
            return ""
        if o.code == outcomes.NO_MINIMUM:
            return sheet_map.NO_MIN_LABEL
        if o.code == outcomes.UNAVAILABLE:
            return _error(limits.Unavailable(o.reason))
        if o.code == outcomes.NO_RANGE:
            return sheet_map.NO_RANGE_LABEL
        if o.code not in sheet_map.BAND_LABELS:
            raise NotModelled("no template text for the outcome %s" % o.code)
        return sheet_map.BAND_LABELS[o.code]

    def _shown(self, nid, row, side):
        """L or N as the template shows it: a fixed cell, or the description."""
        ref = ("L" if side == "low" else "N") + str(row)
        if ref in sheet_map.FIXED_CELLS:
            return sheet_map.FIXED_CELLS[ref]
        return self._describe(nid, row, side)

    def _join(self, nid, row):
        low, high = self._shown(nid, row, "low"), self._shown(nid, row, "high")
        for x in (low, high):
            if _is_error(x):
                return x
        return "" if not low or not high else "to"

    def _label(self, nid, row):
        if row in sheet_map.S01_LABELS:
            return sheet_map.S01_LABELS[row]
        if nid in self.nutrients:
            return self.nutrients[nid]["name"]
        return self.data["template"][nid]["name"]

    def _summary(self, nid, row):
        """AR: TRIM of the descriptions joined by "to", the row's name, "Based on" the
        requirement, and the row's phrases."""
        ref = sheet_map.SUMMARY_COLUMN + str(row)
        if ref in sheet_map.FIXED_CELLS:
            return sheet_map.FIXED_CELLS[ref]
        low = self._shown(nid, row, "low")
        high = self._shown(nid, row, "high")
        for x in (low, high):
            if _is_error(x):
                return x
        low, high = low or "", high or ""
        join = "" if low == "" or high == "" else "to"
        phrase = self._phrase(nid, row)
        if _is_error(phrase):
            return phrase
        text = low + (" " + join if join else "") + (" " + high if high else "") + \
            " " + self._label(nid, row) + phrase
        return inputs.trim(text)

    def _phrase(self, nid, row):
        t = sheet_map.AR_TEXTS
        shape = sheet_map.AR_SHAPES[row]
        based_on = t["based-on"] + (self.name or "")
        if shape in ("default-min", "water"):
            fid = sheet_map.AR_FIGURES[row]
            figure = float(self.data["template"][fid]["figure"])
            unit = self.nutrients[nid]["unit"]
            if shape == "water":
                return t["based-on"] + "%s %s%s" % (numbers.to_text(figure), unit, t["water"])
            c = _cell_value(self.request.minimum(nid))
            if _is_error(c):
                return c
            if numbers.is_number(c) and (c == figure or
                                         numbers.to_text(c) == numbers.to_text(figure)):
                return t["based-on"] + "%s %s%s" % (numbers.to_text(figure), unit,
                                                    t["default-min"])
            return based_on
        out = based_on
        if shape in ("restriction+aafco", "restriction"):
            r = self.facts.get("caloric_restriction_percent")
            if r is not None and r > 0:
                out += t["restriction"][0] + numbers.format_fixed(r / 100, 2, percent=True) + \
                    t["restriction"][1]
        if shape in ("restriction+aafco", "aafco"):
            a = self.request.aafco_factor
            c = self.request.minimum(nid)
            if limits.number(a) and limits.number(c) and a != 1:
                out += t["aafco"] + numbers.format_fixed(a, 3)
        if shape in ("intake", "intake-mbw"):
            n4 = self.request.intake_shortfall
            if n4 is not None and n4 > 0:
                shown = n4 / 100 if shape == "intake-mbw" and n4 > 1 else n4
                out += t["intake"][0] + numbers.format_fixed(shown, 2, percent=True) + \
                    t["intake"][1]
        return out

    def _text_check(self, row, side):
        if self._checks is None:
            self._checks = outcomes.checks(self.request)
        for cid, sides in self._checks.items():
            check = sides[side]
            high = next((f for f in check.figures if f in limits.LA_ALA_HIGH), None)
            if sheet_map.TEXT_CHECK_ROWS.get((cid, high)) == row:
                return sheet_map.TEXT_CHECK_TEXTS[row][check.result]
        return sheet_map.NOT_APPLICABLE


def _column_number(col):
    n = 0
    for ch in col:
        n = n * 26 + ord(ch) - 64
    return n
