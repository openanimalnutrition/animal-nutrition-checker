"""Check a data folder before it is merged. Errors block the merge; warnings ask a reviewer
to look. Every message names the file, the row and the field, in plain words.

Usage: python3 -I -B tools/validate_data.py DATA_DIR [--against OLD_DATA_DIR]
Exit status: 0 no errors, 1 errors.
"""

import csv
import io
import math
import os
import re
import sys

from oan import energy, release, table

NUTRIENTS_HEADER = ["id", "name", "unit", "amount", "basis", "k", "mbw_of", "enterable",
                    "ig_code", "notes"]
REQUIREMENTS_HEADER = ["id", "name", "standard", "edition", "species", "life_stage",
                       "mer_kcal_per_mbw", "notes", "energy_notes"]
LIMITS_HEADER = ["nutrient", "min", "min_unit", "min_rule", "min_source", "max", "max_unit",
                 "max_rule", "max_type", "max_source", "min_notes", "max_notes"]
AMOUNTS = ["g", "mg", "mcg", "IU", ""]
NOTES_HEADER = ["id", "scope", "text", "origin"]
ENERGY_HEADER = ["id", "figure", "unit", "label", "source", "notes"]
# A type's label ends with the figure and exponent it prints: "(95 * kg BW^0.75)".
TYPE_LABEL = re.compile(r".*\((\S+) \* [^()]*\^(\S+)\)")

STANDARDS = {"NRC": ["NRC-2006"], "AAFCO": ["AAFCO-2026"], "FEDIAF": ["FEDIAF-2025"]}
SPECIES = ["canine", "feline"]
LIFE_STAGES = ["growth", "gestation-lactation", "adult-maintenance", "all-life-stages"]
BASES = ["per-mcal", "per-mbw", "per-100g-dm", "ratio", "energy-density"]
IG_NUTRIENT_CODES = ["protein", "calcium", "phosphorus", "potassium", "ca-p-ratio",
                     "vitamin-d"]
# The template's max-type codes (s02 AU3 note); the core maps them to the IG's codes.
MAX_TYPES = ["SUL", "SUL>", "SULm", "SULm*", "AAFCO", "N", "N*", "L", "FSL", "PSM", "EST",
             "CALC"]
NOTE_SCOPES = ["", "table", "energy"]
# Requirements that differ only in the MER; their maximums must stay the same.
MER_PAIRS = [("fediaf-dog-adult-mer95", "fediaf-dog-adult-mer110"),
             ("fediaf-cat-adult-mer75", "fediaf-cat-adult-mer100")]

DECIMAL = re.compile(r"\d+(\.\d+)?")
ID = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
NOTE_ID = re.compile(r"n\d{3,}")
CHANGE_FACTOR = 10


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, where, msg):
        self.errors.append("%s: %s" % (where, msg))

    def warn(self, where, msg):
        self.warnings.append("%s: %s" % (where, msg))


def number_problem(text):
    """None if text is a plain decimal, else a plain-words reason."""
    if DECIMAL.fullmatch(text):
        value = float(text)
        if not math.isfinite(value) or value >= 1e15:
            return "the number is too large"
        return None
    if text.startswith("'"):
        return "remove the leading apostrophe"
    if "−" in text or text.startswith("-"):
        return "numbers cannot be negative (and use the plain - sign, not the Unicode minus)"
    if " " in text or " " in text:
        return "remove the space inside the number"
    if "%" in text:
        return "write the number without %"
    if re.fullmatch(r"\d+,\d+", text) and len(text.split(",")[1]) != 3:
        return "use a point, not a comma, for decimals (0.5, not 0,5)"
    if "," in text:
        return "remove the thousands separator (23500, not 23,500)"
    if text.lower() in ("none", "n/a", "na", "-", "nil"):
        return 'write "none" exactly, in lower case'
    return "not a plain decimal number"


def read(path, header, report):
    """The rows of a CSV file as (line number, dict), after checking the format."""
    name = os.path.relpath(path, report.root)
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError:
        report.error(name, "the file is missing")
        return []
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        report.error(name, "not UTF-8 text (byte %d)" % e.start)
        return []
    rows = list(csv.reader(io.StringIO(text, newline="")))
    if not rows or rows[0] != header:
        report.error(name + " line 1", "the header row must be exactly: " + ",".join(header))
        return []
    out = []
    for i, r in enumerate(rows[1:], start=2):
        if not r or r == [""]:
            report.error("%s line %d" % (name, i), "empty line")
            continue
        if len(r) != len(header):
            report.error("%s line %d" % (name, i), "%d fields, expected %d (commas separate "
                         "fields; put a field that contains a comma in double quotes)" % (
                             len(r), len(header)))
            continue
        out.append((i, dict(zip(header, r))))
    return out


def check_ids(rows, name, report):
    seen = set()
    for line, r in rows:
        where = "%s line %d id" % (name, line)
        if not ID.fullmatch(r["id"]):
            report.error(where, "ids use lower-case letters, digits and single hyphens")
        if r["id"] in seen:
            report.error(where, "duplicate id %r" % r["id"])
        seen.add(r["id"])
    return seen


def check_note_refs(text, where, note_ids, report):
    for nid in text.split():
        if nid not in note_ids:
            report.error(where, "note %r does not exist in notes.csv" % nid)


def validate(data_dir, against=None):
    report = Report()
    report.root = data_dir

    notes = read(os.path.join(data_dir, "notes.csv"), NOTES_HEADER, report)
    note_ids = set()
    for line, r in notes:
        where = "notes.csv line %d" % line
        if not NOTE_ID.fullmatch(r["id"]):
            report.error(where + " id", "note ids look like n001")
        if r["id"] in note_ids:
            report.error(where + " id", "duplicate id %r" % r["id"])
        note_ids.add(r["id"])
        if r["scope"] not in NOTE_SCOPES:
            report.error(where + " scope", "scope must be empty, table or energy")
        if not r["text"].strip():
            report.error(where + " text", "the note has no text")

    nutrients = read(os.path.join(data_dir, "nutrients.csv"), NUTRIENTS_HEADER, report)
    nutrient_ids = check_ids(nutrients, "nutrients.csv", report)
    for line, r in nutrients:
        where = "nutrients.csv line %d" % line
        if r["basis"] not in BASES:
            report.error(where + " basis", "basis must be one of " + ", ".join(BASES))
        if r["amount"] not in AMOUNTS:
            report.error(where + " amount", "amount must be g, mg, mcg, IU or empty")
        if r["k"] not in ("", "blank", "N/A"):
            problem = number_problem(r["k"])
            if problem:
                report.error(where + " k", problem)
        if r["mbw_of"] and r["mbw_of"] not in nutrient_ids:
            report.error(where + " mbw_of", "unknown nutrient %r" % r["mbw_of"])
        if r["enterable"] not in ("yes", "no"):
            report.error(where + " enterable", "yes or no")
        if r["ig_code"] and r["ig_code"] not in IG_NUTRIENT_CODES:
            report.error(where + " ig_code", "not a code of the IG's nutrient code system")
        check_note_refs(r["notes"], where + " notes", note_ids, report)
    nutrient_order = [r["id"] for _, r in nutrients]
    nutrients_by_id = {r["id"]: r for _, r in nutrients}

    requirements = read(os.path.join(data_dir, "requirements.csv"), REQUIREMENTS_HEADER,
                        report)
    check_ids(requirements, "requirements.csv", report)
    for line, r in requirements:
        where = "requirements.csv line %d" % line
        if r["standard"] not in STANDARDS:
            report.error(where + " standard", "standard must be one of " + ", ".join(STANDARDS))
        elif r["edition"] not in STANDARDS[r["standard"]]:
            report.error(where + " edition", "edition %r is not an edition of %s" % (
                r["edition"], r["standard"]))
        if r["species"] not in SPECIES:
            report.error(where + " species", "canine or feline")
        for stage in r["life_stage"].split() or [""]:
            if stage not in LIFE_STAGES:
                report.error(where + " life_stage", "life stages are " + ", ".join(LIFE_STAGES))
        if r["mer_kcal_per_mbw"]:
            problem = number_problem(r["mer_kcal_per_mbw"])
            if problem:
                report.error(where + " mer_kcal_per_mbw", problem)
        check_note_refs(r["notes"], where + " notes", note_ids, report)
        check_note_refs(r["energy_notes"], where + " energy_notes", note_ids, report)

    check_energy(data_dir, note_ids, requirements, report)

    # Every requirement has exactly one limits file, and there are no others.
    expected_files = {os.path.join(r["edition"], r["id"] + ".csv") for _, r in requirements}
    standards_dir = os.path.join(data_dir, "standards")
    for dirpath, _, files in os.walk(standards_dir):
        for f in files:
            rel = os.path.relpath(os.path.join(dirpath, f), standards_dir)
            if rel not in expected_files:
                report.error("standards/" + rel, "no requirement in requirements.csv uses "
                             "this file (check the edition folder and the file name)")

    by_requirement = {}
    for _, req in requirements:
        name = "standards/%s/%s.csv" % (req["edition"], req["id"])
        rows = read(os.path.join(data_dir, name), LIMITS_HEADER, report)
        seen = {}
        for line, r in rows:
            where = "%s line %d" % (name, line)
            nid = r["nutrient"]
            if nid not in nutrient_ids:
                report.error(where + " nutrient", "unknown nutrient %r" % nid)
                continue
            if nid in seen:
                report.error(where + " nutrient", "%r appears twice (also line %d)" % (
                    nid, seen[nid]))
                continue
            seen[nid] = line
            check_limit(r, "min", where, req, nutrients_by_id.get(nid), report)
            check_limit(r, "max", where, req, nutrients_by_id.get(nid), report)
            numeric_max = r["max"] not in ("none",)
            if numeric_max and r["max_type"] not in MAX_TYPES:
                report.error(where + " max_type", "a maximum needs its type, one of " +
                             ", ".join(MAX_TYPES))
            if not numeric_max and r["max_type"]:
                report.error(where + " max_type", 'only a maximum that is not "none" has a type')
            check_note_refs(r["min_notes"], where + " min_notes", note_ids, report)
            check_note_refs(r["max_notes"], where + " max_notes", note_ids, report)
        if req["mer_kcal_per_mbw"]:
            # The standard prints no per-MBW maximum for these: it is computed from the
            # per-Mcal maximum, so the two can never disagree.
            mbw_of = {r["id"]: r["mbw_of"] for _, r in nutrients}
            by_id = {r["nutrient"]: (line, r) for line, r in rows}
            for nid, (line, r) in by_id.items():
                parent = by_id.get(mbw_of.get(nid, ""), (None, None))[1]
                if (parent and parent["max"] != "none" and r["max"] not in ("none", "")
                        and r["max_rule"] != "mbw-from-per-mcal"):
                    report.error("%s line %d max" % (name, line), "the per-MBW maximum of a "
                                 "requirement with a MER is computed from the per-Mcal "
                                 "maximum: use the rule mbw-from-per-mcal and leave the "
                                 "figure empty, so the two can never disagree")
        for nid in nutrient_order:
            if nid in nutrient_ids and nid not in seen and rows:
                report.error(name, "no row for nutrient %r (every nutrient needs a row; "
                             'write "none" where the standard sets nothing)' % nid)
        by_requirement[req["id"]] = {r["nutrient"]: (line, r) for line, r in rows}

    try:
        rel = release.read_release(data_dir)
        if rel.get("content_sha256") != release.content_hash(data_dir):
            report.warn("RELEASE", "the content hash is not that of these files; the release "
                        "step writes a new one")
    except OSError:
        report.warn("RELEASE", "missing; the release step writes it")

    if report.errors:
        return report

    # Computed checks: every rule resolves, min not above max, MER pairs, big changes.
    data = table.load(data_dir)
    computed = {}
    for _, req in requirements:
        name = "standards/%s/%s.csv" % (req["edition"], req["id"])
        try:
            computed[req["id"]] = table.compute_limits(data, req["id"])
        except (table.DataError, KeyError, TypeError, ValueError) as e:
            report.error(name, "a rule cannot be computed: %s" % e)
            continue
        for nid, (lo, hi) in computed[req["id"]].items():
            if lo is not None and hi is not None and lo > hi:
                line = by_requirement[req["id"]][nid][0]
                report.warn("%s line %d" % (name, line), "the minimum %g is above the "
                            "maximum %g" % (lo, hi))
    for a, b in MER_PAIRS:
        if a in by_requirement and b in by_requirement:
            for nid, (line, ra) in by_requirement[a].items():
                rb = by_requirement[b].get(nid, (None, None))[1]
                if rb is None:
                    continue
                for field in ("max", "max_rule", "max_type"):
                    if ra[field] != rb[field]:
                        report.warn("%s and %s, nutrient %s" % (a, b, nid), "the %s differs "
                                    "(%r and %r); these two requirements differ only in "
                                    "the MER" % (field, ra[field], rb[field]))
    if against:
        try:
            old = table.load(against)
            for fid, row in data["energy"].items():
                prev = old["energy"].get(fid)
                if prev is None:
                    continue
                new, before = float(row["figure"]), float(prev["figure"])
                if new and before and max(new / before, before / new) > CHANGE_FACTOR:
                    report.warn("energy.csv %s" % fid, "changed more than %dx (%g to %g)" % (
                        CHANGE_FACTOR, before, new))
            for rid, now in computed.items():
                if rid not in old["limits"]:
                    continue
                before = table.compute_limits(old, rid)
                for nid, pair in now.items():
                    if nid not in before:
                        continue
                    for bound, new, prev in zip(("min", "max"), pair, before[nid]):
                        if new and prev and max(new / prev, prev / new) > CHANGE_FACTOR:
                            report.warn("%s %s %s" % (rid, nid, bound), "changed more "
                                        "than %dx (%g to %g): check the unit (mg or mcg?)"
                                        % (CHANGE_FACTOR, prev, new))
        except (OSError, KeyError, table.DataError) as e:
            report.warn(against, "could not compare with the old data: %s" % e)
    return report


def check_energy(data_dir, note_ids, requirements, report):
    """energy.csv: exactly the code's figures, each a plain number in the unit the code reads
    it in, with its source; the adult types' labels print their figures."""
    rows = read(os.path.join(data_dir, "energy.csv"), ENERGY_HEADER, report)
    by_id = {}
    for line, r in rows:
        where = "energy.csv line %d" % line
        fid = r["id"]
        if fid not in energy.FIGURES:
            report.error(where + " id", "unknown figure %r (the code reads only the figures "
                         "listed in oan/energy.py)" % fid)
            continue
        if fid in by_id:
            report.error(where + " id", "%r appears twice (also line %d)" % (fid, by_id[fid][0]))
            continue
        by_id[fid] = (line, r)
        problem = number_problem(r["figure"])
        if problem:
            report.error(where + " figure", "%r: %s" % (r["figure"], problem))
        if r["unit"] != energy.FIGURES[fid]:
            report.error(where + " unit", "the code reads %s in %s; a figure in another unit "
                         "needs a code change, not a new unit here" % (
                             fid, energy.FIGURES[fid] or "no unit (a plain number)"))
        if not r["source"].strip():
            report.error(where + " source", "every figure needs its source (table and page)")
        check_note_refs(r["notes"], where + " notes", note_ids, report)
        if fid not in energy.TYPE_EXPONENTS:
            if r["label"]:
                report.error(where + " label", "only the adult dog and cat types have a label")
    for fid in energy.FIGURES:
        if fid not in by_id:
            report.error("energy.csv", "no row for %r (the code needs every figure)" % fid)
    labels = {}
    for fid, exponent_id in energy.TYPE_EXPONENTS.items():
        if fid not in by_id or exponent_id not in by_id:
            continue
        line, r = by_id[fid]
        where = "energy.csv line %d label" % line
        m = TYPE_LABEL.fullmatch(r["label"])
        if not m:
            report.error(where, "a type's label ends with its equation in brackets, for "
                         'example "(95 * kg BW^0.75)"')
            continue
        exponent = by_id[exponent_id][1]["figure"]
        if number_problem(m.group(1)) or number_problem(r["figure"]) or \
                float(m.group(1)) != float(r["figure"]):
            report.error(where, "the label prints %s but the figure is %s: change both "
                         "together" % (m.group(1), r["figure"]))
        if number_problem(m.group(2)) or number_problem(exponent) or \
                float(m.group(2)) != float(exponent):
            report.error(where, "the label prints the exponent %s but %s is %s: change both "
                         "together" % (m.group(2), exponent_id, exponent))
        if r["label"] in labels:
            report.error(where, "the same label as line %d" % labels[r["label"]])
        labels[r["label"]] = line
    for line, r in requirements:
        if r["id"] not in energy.RULES:
            report.error("requirements.csv line %d id" % line, "no energy rule for %r: a new "
                         "requirement needs one in oan/energy.py" % r["id"])


def check_limit(r, bound, where, req, nutrient, report):
    text = r[bound]
    rule = r[bound + "_rule"]
    field = "%s %s" % (where, bound)
    if rule not in table.RULES:
        report.error(field + "_rule", "unknown rule %r; the rules are: %s" % (
            rule, ", ".join(table.RULES)))
        return
    kind = table.RULES[rule][0]
    if rule == "mbw-from-per-mcal" and not req["mer_kcal_per_mbw"]:
        report.error(field + "_rule", "this requirement has no MER in requirements.csv")
    unit = r[bound + "_unit"]
    if text in ("none", "") and unit:
        report.error(field + "_unit", "only a figure has a printed unit")
    if text == "none":
        if rule != "printed":
            report.error(field + "_rule", 'a "none" cell takes the rule "printed"')
        return
    if text == "":
        if kind != "derived":
            report.error(field, 'empty: write the figure, or "none" if the standard sets '
                         "nothing")
        return
    if unit and nutrient:
        try:
            table.unit_factor(unit, nutrient, req["species"])
        except table.DataError as e:
            report.error(field + "_unit", str(e))
    if kind == "derived":
        report.error(field, "the rule %s computes this value; leave the figure empty "
                     "(a typed number here would go stale when its source changes)" % rule)
        return
    body = text
    if body.startswith(">"):
        if bound != "max":
            report.error(field, 'only a maximum can be printed as "greater than" (>)')
        body = body[1:]
    parts = body.split("|")
    if kind == "pair" and len(parts) != 2:
        report.error(field, "the rule %s takes two figures, written 2|2.5" % rule)
        return
    if kind != "pair" and len(parts) != 1:
        report.error(field, "only the rule fediaf-late-growth-by-mature-weight takes two "
                     "figures")
        return
    for part in parts:
        problem = number_problem(part)
        if problem:
            report.error(field, "%r: %s" % (text, problem))
    if not r[bound + "_source"].strip():
        report.error(field + "_source", "every figure needs its source (table and page)")


def main(argv):
    args = argv[1:]
    against = None
    if "--against" in args:
        i = args.index("--against")
        against = args[i + 1]
        del args[i:i + 2]
    if len(args) != 1:
        sys.exit(__doc__)
    report = validate(args[0], against)
    for e in report.errors:
        print("ERROR   " + e)
    for w in report.warnings:
        print("WARNING " + w)
    print("%d errors, %d warnings" % (len(report.errors), len(report.warnings)))
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
