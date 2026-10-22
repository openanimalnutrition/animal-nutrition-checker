"""The impact report of a data change: evidence for the steward reviewing a pull request.

Compares the old data folder (the merged data) with the new one (the pull request's):

1. the validator on the new data, against the old;
2. the changed figures: every changed, added or removed row and field of every data file;
3. over a fixed grid of inputs (below): every limit that changes (minimum, maximum, range
   high and its type) and every outcome that changes (the band, or other outcome, of entries
   placed at the old limits' band edges and between them);
4. over the inputs of the 21OCT26b test cases (tests/parity/vectors-21OCT26b) and of the
   extra cases (tests/vectors-extra): every cell of the sheet view that changes;
5. the independent models (tests/models) on the new data, against the core.

Evidence, not an oracle: no expected output is regenerated from the code under review. The
old and the new outcomes are both the core's; the models were written separately.

The grid: every requirement with fixed facts (FACTS; a requirement added later takes its
species' adult facts) under five variants: as is; with a 25% caloric restriction; with an
energy density Min entry of 3.5 kcal/g (the AAFCO dry matter factor); with an energy intake
of 80% of the old energy requirement; with protein Min entries of 1.5 times the old protein
minimums (the arginine increase). An outcome depends only on the entry and the nutrient's
limits, so it can change only where the limits change; there, entries at 0, at each lower
band edge of the old limits, halfway between edges, at the range high and at 1.5 times it
are each described as a Min and as a Max entry, with the old and the new limits.

Usage: python3 -I -B tools/impact_report.py OLD_DATA NEW_DATA [--max-rows N]
The report (Markdown) goes to standard output.
Exit status: 1 when the validator finds errors or a model disagrees with the core, else 0.
"""

import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
import model_agreement  # noqa: E402
import run_vectors  # noqa: E402
from oan import bands, energy, limits, numbers, outcomes, release, table, validate  # noqa: E402

DOG = "Average laboratory or active (130 * kg BW^0.75)"
CAT = "Lean domestic (100 * kgBW^0.67)"
ADULT = {"canine": {"body_weight_kg": 15.0, "adult_dog_type": DOG, "life_stage": "None"},
         "feline": {"body_weight_kg": 4.0, "adult_cat_type": CAT, "life_stage": "None"}}
PUPPY = {"body_weight_kg": 10.0, "mature_weight_kg": 30.0, "adult_dog_type": DOG,
         "life_stage": "Growth: 4 months to adult size", "puppy_body_weight_kg": 10.0}
KITTEN = {"body_weight_kg": 2.0, "mature_weight_kg": 4.5, "adult_cat_type": CAT,
          "life_stage": "Growth: weaning to 4 months"}
FACTS = {
    "nrc-dog-adult": ADULT["canine"], "aafco-dog-adult": ADULT["canine"],
    "fediaf-dog-adult-mer95": ADULT["canine"], "fediaf-dog-adult-mer110": ADULT["canine"],
    "nrc-cat-adult": ADULT["feline"], "aafco-cat-adult": ADULT["feline"],
    "fediaf-cat-adult-mer75": ADULT["feline"], "fediaf-cat-adult-mer100": ADULT["feline"],
    "nrc-puppy-4-14-wk": dict(PUPPY, life_stage="Growth: weaning to 4 months"),
    "nrc-puppy-14-wk-plus": PUPPY, "aafco-dog-growth-reproduction": PUPPY,
    "aafco-dog-growth-large-breed": PUPPY,
    "fediaf-dog-early-growth-reproduction": dict(PUPPY,
                                                 life_stage="Growth: weaning to 4 months"),
    "fediaf-dog-late-growth": PUPPY,
    "nrc-kitten": KITTEN, "aafco-cat-growth-reproduction": KITTEN, "fediaf-cat-growth": KITTEN,
    "nrc-dog-gestation-lactation": {"body_weight_kg": 25.0, "adult_dog_type": DOG,
                                    "life_stage": "Lactation: bitch", "lactation_week": 3,
                                    "puppies_nursing": 6},
    "nrc-cat-late-gestation": {"body_weight_kg": 4.0, "adult_cat_type": CAT,
                               "life_stage": "Gestation: week 5 to birth"},
    "nrc-cat-peak-lactation": {"body_weight_kg": 4.0, "adult_cat_type": CAT,
                               "life_stage": "3-4 Kittens", "lactation_week": 3},
    "fediaf-cat-reproduction": {"body_weight_kg": 4.0, "adult_cat_type": CAT,
                                "life_stage": "3-4 Kittens", "lactation_week": 3},
}
RESTRICTION = 25.0
ENERGY_DENSITY = 3.5
INTAKE_SHARE = 0.8
PROTEIN_SHARE = 1.5
SIDES = ("low", "high")
ENERGY_ROW = "energy"


# Loading.

def load(data_dir):
    """(data, None) or (None, the reason it does not load)."""
    try:
        return table.load(data_dir), None
    except Exception as e:  # a data folder the validator rejects may not load at all
        return None, "%s: %s" % (type(e).__name__, e)


# 2. Changed figures.

def read_rows(path):
    """(header, {key: row}) of a CSV file, keyed by its id (or nutrient) column."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return [], {}
    header = rows[0]
    key = "id" if "id" in header else ("nutrient" if "nutrient" in header else header[0])
    i = header.index(key)
    out = {}
    for r in rows[1:]:
        if r and len(r) == len(header):
            out[r[i]] = dict(zip(header, r))
    return header, out


def files_of(data_dir):
    out = set()
    for dirpath, _, files in os.walk(data_dir):
        for f in files:
            out.add(os.path.relpath(os.path.join(dirpath, f), data_dir).replace(os.sep, "/"))
    return out


def changed_figures(old_dir, new_dir):
    """[(file, row, field, old, new)]; a whole file or row added or removed has field "-"."""
    out = []
    old_files, new_files = files_of(old_dir), files_of(new_dir)
    for rel in sorted(old_files | new_files):
        if rel == "RELEASE":
            continue
        if rel not in new_files:
            out.append((rel, "-", "-", "the file", "removed"))
            continue
        if rel not in old_files:
            out.append((rel, "-", "-", "added", "the file"))
            continue
        if not rel.endswith(".csv"):
            with open(os.path.join(old_dir, rel), "rb") as a, \
                    open(os.path.join(new_dir, rel), "rb") as b:
                if a.read() != b.read():
                    out.append((rel, "-", "-", "the file", "changed"))
            continue
        old_header, old_rows = read_rows(os.path.join(old_dir, rel))
        new_header, new_rows = read_rows(os.path.join(new_dir, rel))
        if old_header != new_header:
            out.append((rel, "header", "-", ",".join(old_header), ",".join(new_header)))
        for key in list(old_rows) + [k for k in new_rows if k not in old_rows]:
            a, b = old_rows.get(key), new_rows.get(key)
            if a is None:
                out.append((rel, key, "-", "added", "the row"))
            elif b is None:
                out.append((rel, key, "-", "the row", "removed"))
            else:
                for field in new_header:
                    if a.get(field, "") != b.get(field, ""):
                        out.append((rel, key, field, a.get(field, ""), b.get(field, "")))
    return out


# 3. The grid.

def facts_for(data, rid):
    if rid in FACTS:
        return dict(FACTS[rid])
    species = next(r["species"] for r in data["requirements"] if r["id"] == rid)
    return dict(ADULT[species])


def variants(old, rid):
    """[(name, facts, entries)] of one requirement, fixed from the old data."""
    facts = facts_for(old, rid)
    out = [("as is", facts, {}),
           ("restriction %g%%" % RESTRICTION, dict(facts, caloric_restriction_percent=RESTRICTION),
            {}),
           ("energy density Min %g" % ENERGY_DENSITY, facts,
            {"energy-density": {"low": ENERGY_DENSITY}})]
    kcal = energy.requirement_energy(old, rid, facts).kcal
    if kcal is not None:
        intake = float(round(kcal * INTAKE_SHARE))
        out.append(("intake %g kcal/day" % intake,
                    dict(facts, energy_intake_kcal_per_day=intake), {}))
    base = limits.Request(old, rid, facts, {})
    protein = {}
    for nid in ("protein", "protein-mbw"):
        m = base.minimum(nid)
        if limits.number(m) and m > 0:
            protein[nid] = {"low": m * PROTEIN_SHARE}
    if protein:
        out.append(("protein Min x %g" % PROTEIN_SHARE, facts, protein))
    return out


def points(minimum, range_high):
    """The entries probed on a row: 0, the band edges and the points between them, the range
    high and 1.5 times it (or around the minimum on a row with no range high)."""
    pts = {0.0}
    low = minimum if limits.number(minimum) else None
    high = range_high if limits.number(range_high) else None
    if high is not None:
        edges = bands.lower_edges(low, high) + [high]
        pts.update(edges)
        pts.update((a + b) / 2 for a, b in zip(edges, edges[1:]))
        pts.add(high * 1.5)
    elif low is not None:
        pts.update((low, low * 0.5, low * 1.5))
    else:
        pts.add(1.0)
    return sorted(pts)


def _limits(request, nid):
    try:
        return request.limits(nid)
    except (KeyError, StopIteration, table.DataError) as e:
        return "not computed (%s)" % type(e).__name__


def _energy(data, rid, facts):
    """The energy row of a request: (energy used or its reason, range high)."""
    req = energy.requirement_energy(data, rid, facts)
    used = energy.energy_used(req, facts.get("energy_intake_kcal_per_day"))
    if used.kcal is None:
        return limits.Unavailable(used.reason), None
    return used.kcal, energy.range_high(data, used.kcal)


def grid(old, new):
    """(changed limits, changed outcomes, requirements added, requirements removed).
    changed limits: [(rid, variant, nid, old Limits, new Limits)]; changed outcomes:
    [(rid, variant, nid, side, points changed, points probed, (point, old, new))]."""
    old_ids = [r["id"] for r in old["requirements"]]
    new_ids = [r["id"] for r in new["requirements"]]
    nids = limits.nutrient_ids(old)
    nids += [n for n in limits.nutrient_ids(new) if n not in nids]
    changed_limits, changed_outcomes = [], []
    for rid in old_ids:
        if rid not in new_ids:
            continue
        for name, facts, entries in variants(old, rid):
            a = limits.Request(old, rid, facts, entries)
            b = limits.Request(new, rid, facts, entries)
            rows = [(nid, _limits(a, nid), _limits(b, nid)) for nid in nids]
            e_old, e_new = _energy(old, rid, facts), _energy(new, rid, facts)
            rows.append((ENERGY_ROW, e_old, e_new))
            for nid, la, lb in rows:
                if la == lb:
                    continue
                changed_limits.append((rid, name, nid, la, lb))
                if isinstance(la, str) or isinstance(lb, str):
                    continue
                probed = points(*la) if nid == ENERGY_ROW else points(la.minimum,
                                                                      la.range_high)
                for side in SIDES:
                    diffs = []
                    for p in probed:
                        oa, ob = describe(nid, p, side, la), describe(nid, p, side, lb)
                        if oa != ob:
                            diffs.append((p, oa, ob))
                    if diffs:
                        changed_outcomes.append((rid, name, nid, side, len(diffs),
                                                 len(probed), diffs[0]))
    added = [r for r in new_ids if r not in old_ids]
    removed = [r for r in old_ids if r not in new_ids]
    return changed_limits, changed_outcomes, added, removed


def describe(nid, value, side, lim):
    """The outcome code of an entry; the energy row is banded from the energy used to its
    range high, with no maximum."""
    if nid != ENERGY_ROW:
        o = outcomes.describe(value, side, lim)
        return o.code if o.reason is None else "%s (%s)" % (o.code, o.reason)
    used, high = lim
    if limits.unavailable(used):
        return "unavailable (%s)" % used.reason
    return bands.band(value, used, high, has_max=False)


# 4. The test cases' inputs.

def cases(old, new):
    """{file: (cases run, [(case id, cell, kind, old, new)])} over the test cases' inputs."""
    out = {}
    for name in run_vectors.FILES + run_vectors.EXTRA_FILES:
        docs, _ = run_vectors.load_cases(name)
        a = run_vectors.run_file(name, docs, old, "forward")
        b = run_vectors.run_file(name, docs, new, "forward")
        diffs = []
        for case in docs:
            cid = case["id"]
            got_a = {cell: (kind, got) for cell, _, got, kind, _ in a[cid][1]}
            got_b = {cell: (kind, got) for cell, _, got, kind, _ in b[cid][1]}
            if a[cid][0] != b[cid][0] and "outside-rule" in (a[cid][0], b[cid][0]):
                diffs.append((cid, "-", "input rules", a[cid][0], b[cid][0]))
            for cell in list(got_a) + [c for c in got_b if c not in got_a]:
                ka, va = got_a.get(cell, (None, None))
                kb, vb = got_b.get(cell, (None, None))
                if run_vectors.compare(va, vb) != "exact" or cell not in got_a or \
                        cell not in got_b:
                    diffs.append((cid, cell, ka or kb, va, vb))
        out[name] = (len(docs), diffs)
    return out


# 5. The models.

def models(new):
    return [(name, fn(new)) for name, fn in model_agreement.MODELS]


# The report.

def fmt(v):
    if v is None:
        return "none"
    if limits.unavailable(v):
        return "unavailable (%s)" % v.reason
    if isinstance(v, limits.Limits):
        return "min %s, max %s, range high %s, type %s" % tuple(fmt(x) for x in v)
    if isinstance(v, tuple):
        return ", ".join(fmt(x) for x in v)
    if isinstance(v, dict) and "error" in v:
        return v["error"]
    if numbers.is_number(v):
        return numbers.to_text(v)
    return str(v)


def cell(v):
    return fmt(v).replace("|", "\\|").replace("\n", " ")


def table_md(header, rows, max_rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in rows[:max_rows]:
        lines.append("| " + " | ".join(cell(x) for x in r) + " |")
    if len(rows) > max_rows:
        lines.append("")
        lines.append("... and %d more." % (len(rows) - max_rows))
    return lines


def report(old_dir, new_dir, max_rows=200):
    """(Markdown text, exit status)."""
    lines = ["# Impact report", ""]
    status = 0
    versions = []
    for label, d in (("Old", old_dir), ("New", new_dir)):
        try:
            rel = release.read_release(d)
        except OSError:
            rel = {}
        versions.append("- %s data: `%s`, data version %s, content hash %s" % (
            label, d, rel.get("data_version", "(no RELEASE)"),
            release.content_hash(d)[:12]))
    lines += versions + ["", "Evidence for the reviewer, not an oracle: both sides are the "
                         "core's outcomes, and the models were written separately. No "
                         "expected value is regenerated from the code under review.", ""]

    v = validate.validate(new_dir, against=old_dir)
    if v.errors:
        status = 1
    figures = changed_figures(old_dir, new_dir)
    old, old_error = load(old_dir)
    new, new_error = load(new_dir)
    sections = []

    sections += ["## 1. Validator (new data, against the old)", ""]
    if not v.errors and not v.warnings:
        sections.append("No errors, no warnings.")
    for e in v.errors:
        sections.append("- ERROR %s" % e)
    for w in v.warnings:
        sections.append("- warning %s" % w)
    sections.append("")

    sections += ["## 2. Changed figures", ""]
    if figures:
        sections += table_md(["File", "Row", "Field", "Old", "New"], figures, max_rows)
    else:
        sections.append("No data file changed.")
    sections.append("")

    summary = [("Data file fields, rows or files changed", len(figures)),
               ("Validator errors", len(v.errors)), ("Validator warnings", len(v.warnings))]
    if old is None or new is None:
        status = 1
        sections += ["The %s data does not load (%s); sections 3 to 5 need both." % (
            "old" if old is None else "new", old_error or new_error), ""]
    elif v.errors:
        sections += ["The validator found errors in the new data; sections 3 to 5 need data "
                     "it accepts.", ""]
    else:
        changed_limits, changed_outcomes, added, removed = grid(old, new)
        sections += ["## 3. Over the grid of inputs", "",
                     "Requirements added: %s. Removed: %s." % (
                         ", ".join(added) or "none", ", ".join(removed) or "none"), "",
                     "### Changed limits", ""]
        if changed_limits:
            sections += table_md(["Requirement", "Inputs", "Nutrient", "Old", "New"],
                                 changed_limits, max_rows)
        else:
            sections.append("No limit changed.")
        sections += ["", "### Changed outcomes", ""]
        if changed_outcomes:
            rows = [(rid, name, nid, "Min entry" if side == "low" else "Max entry",
                     "%d of %d" % (n, m), "%s: %s -> %s" % (fmt(ex[0]), ex[1], ex[2]))
                    for rid, name, nid, side, n, m, ex in changed_outcomes]
            sections += table_md(["Requirement", "Inputs", "Nutrient", "Entry",
                                  "Entries changed", "Example"], rows, max_rows)
        else:
            sections.append("No outcome changed.")
        sections.append("")

        case_diffs = cases(old, new)
        sections += ["## 4. Over the test cases' inputs", ""]
        n_cells = 0
        for name, (n_cases, diffs) in case_diffs.items():
            changed_cases = len({d[0] for d in diffs})
            n_cells += len(diffs)
            sections.append("- %s: %d of %d cases changed, %d cells" % (
                name, changed_cases, n_cases, len(diffs)))
        sections.append("")
        rows = [(name,) + d for name, (_, diffs) in case_diffs.items() for d in diffs]
        if rows:
            sections += table_md(["File", "Case", "Cell", "Kind", "Old", "New"], rows,
                                 max_rows)
            sections.append("")

        sections += ["## 5. The independent models on the new data", "",
                     "| Model | Values checked | Disagree with the core |", "|---|---|---|"]
        disagreements = []
        for name, (checked, bad, _) in models(new):
            sections.append("| %s | %d | %d |" % (name, checked, len(bad)))
            disagreements += [(name,) + b for b in bad]
        sections.append("")
        if disagreements:
            status = 1
            sections += table_md(["Model", "Case", "Cell", "Core", "Model"], disagreements,
                                 max_rows)
            sections.append("")
        summary += [("Limits changed (grid)", len(changed_limits)),
                    ("Outcomes changed (grid: nutrient, inputs and entry side)",
                     len(changed_outcomes)),
                    ("Test case cells changed", n_cells),
                    ("Model disagreements with the core", len(disagreements))]

    lines += ["## Summary", "", "| | |", "|---|---|"]
    lines += ["| %s | %d |" % (k, n) for k, n in summary]
    lines += [""] + sections
    return "\n".join(lines) + "\n", status


def main(argv):
    args = [a for a in argv[1:]]
    max_rows = 200
    if "--max-rows" in args:
        i = args.index("--max-rows")
        max_rows = int(args[i + 1])
        del args[i:i + 2]
    if len(args) != 2:
        print(__doc__)
        return 2
    text, status = report(args[0], args[1], max_rows)
    sys.stdout.write(text)
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv))
