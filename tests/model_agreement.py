"""The independent models (tests/models) against the core, both on the same data folder.

On the frozen data both also agree with the expected values (tests/test_phase2.py,
test_phase3.py). On changed data the expected values no longer hold, so the models are the
check: each function runs a model's cases on the given data and returns
(values checked, [(case id, cell, core, model)], values that differ from the frozen
expected value). Used by tests/test_phase3.py and tools/impact_report.py.
"""

import json
import os

import run_vectors
import sheet_view
from models import energy_model, formulas_model, values_model
from oan import numbers

VALUES = os.path.join(run_vectors.VECTORS, "values.json")
FORMULAS = os.path.join(run_vectors.VECTORS, "formulas-testcases.json")
ENERGY = os.path.join(run_vectors.VECTORS, "energy-testcases.json")


def energy_agreement(data):
    """The energy model and the core's energy cells (G4, C11 and its highlight)."""
    energy_model.use(data)
    with open(ENERGY, encoding="utf-8") as f:
        cases = json.load(f)["cases"]
    checked, bad, changed = 0, [], 0
    for case in cases:
        inp = case["inputs"]
        try:
            cells = sheet_view.EnergyView(data, inp).cells()
        except (sheet_view.OutsideRule, sheet_view.Missing):
            continue
        model = energy_model.energy_row(case["selection"], inp, inp.get("K4"))
        for cell in ("G4", "C11", "C11_highlighted"):
            checked += 1
            core, exp = cells[cell], case["expected"][cell]
            if not _same(core, model[cell]):
                bad.append((case["id"], cell, core, model[cell]))
            changed += not _same(core, exp)
    return checked, bad, changed


def values_agreement(data):
    """The values model and the core's Standards tab cells over the values cases."""
    values_model.use(data)
    m = values_model.Model(values_model.table_from_data(data))
    checked, bad, changed = 0, [], 0
    for case in values_model.load_cases(VALUES):
        if case["group"] == "table":
            continue
        try:
            sv = sheet_view.StandardsView(data, case["inputs"])
        except sheet_view.OutsideRule:
            continue
        want = [r for r in case["outputs"] if values_model.modelled(r)]
        known = {r: sv.cell(r) for r in values_model.NOT_MODELLED}
        got = m.compute(case["inputs"], known, want)
        for ref in want:
            checked += 1
            core = sv.cell(ref)
            if not values_model.same(core, got[ref]):
                bad.append((case["id"], ref, core, got[ref]))
            changed += not values_model.same(core, case["outputs"][ref])
    return checked, bad, changed


def formulas_agreement(data):
    """The formulas model and the core's target cells over the formulas cases (the cases the
    original skips are skipped)."""
    cases, cells = formulas_model.load(FORMULAS)
    formulas_model.use(data)
    checked, bad, changed, models = 0, [], 0, {}
    for case in cases:
        try:
            sv = sheet_view.StandardsView(data, case["inputs"])
        except sheet_view.OutsideRule:
            continue
        e3 = case["inputs"].get("E3")
        if e3 not in models:
            models[e3] = formulas_model.build_model(data, e3)
        m = models[e3]
        if m.position(case["inputs"].get("O1")) is None:
            continue
        known = {ref: sv.cell(ref) for ref in ("G4", "C11", "C53")}
        expected = dict(zip(cells, case["values"]))
        for t in formulas_model.TARGETS:
            checked += 1
            core = sv.cell(t)
            model = formulas_model._jv(formulas_model.expect(m, case["inputs"], known, t))
            if not formulas_model.same(core, model):
                bad.append((case["id"], t, core, model))
            changed += not formulas_model.same(core, expected[t])
    return checked, bad, changed


MODELS = (("energy", energy_agreement), ("values", values_agreement),
          ("formulas", formulas_agreement))


def _same(a, b):
    if numbers.is_number(a) and numbers.is_number(b):
        return numbers.close(a, b)
    return type(a) is type(b) and a == b
