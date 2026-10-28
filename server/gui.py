"""The GUI: server-rendered pages, no JavaScript (docs/mockups/oan-checker).

1. Choose a requirement (Screen A).
2. Enter the animal facts that requirement reads, and a low and/or a high value per nutrient
   (or paste "name, low, high" lines, which are shown parsed, with a row count, before
   checking) (Screen B).
3. The result: the caveats on top, then the animal and energy, the input report and one block
   per nutrient (Screen C); "Download JSON" gives the same bytes as the MCP check_diet's JSON.
4. About (Screen D): server/pages/about.html in the same frame.
5. How to use: server/pages/how-to-use.html in the same frame; its worked example (EXAMPLE)
   opens pre-filled on Screen B at /example.

Every text from the data, the request or the result is HTML-escaped here.
"""

import os
import re
from html import escape
from string import Template

from oan import caveats, energy, inputs, limits, result

NUMBER = re.compile(r"-?\d+(\.\d+)?")
MAX_FIELD = 64
MAX_PASTE = 16000
PAGES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages")
with open(os.path.join(PAGES, "frame.html"), encoding="utf-8") as _f:
    FRAME = Template(_f.read())

SITE = "Open Animal Nutrition checker"
# Texts approved by the steward on 26 Oct 2026.
REQUIREMENT_HINT = ("One of %d nutrient requirements from the 2006 NRC, the 2026 AAFCO and "
                    "FEDIAF Sept. 2025.")
EMPTY_INPUT_REPORT = "Every value entered was used; nothing is missing."
CHOOSE_LIFE_STAGE = "Choose a life stage"
# Texts approved by the steward on 28 Oct 2026, after the advisory board's first use.
FIRST_TIME = ('First time here? Read <a href="/how-to-use">How to use</a>, or try '
              '<a href="/example">the worked example</a>.')
PASTE_HINT = ("One nutrient per line: its name as in the table, then the value, separated by "
              "commas (for example: Calcium, Ca, 3.16). For a range, give low then high "
              "(Calcium, Ca, 1.2, 3); for only a high, leave low empty (Calcium, Ca, , 6). "
              "Numbers only, with no units. Click Parse to see how each line was read; the "
              "values then fill the table below, and nothing is checked until you click Check.")
UNITS_OTHER = " Rows with another unit take the unit shown; the MBW rows are per Mcal too."
EXAMPLE_NOTE = ("The worked example from How to use: a 20 kg adult dog, and a dry food whose "
                "label gives crude protein 26%, crude fat 16%, calcium 1.2%, phosphorus 1.0%, "
                "moisture 10% and 3,800 kcal ME/kg, converted to per Mcal. Click Check to see "
                "the result.")
# The worked example of How to use (pages/how-to-use.html; a test checks the page against its
# result).
EXAMPLE = {"requirement": "aafco-dog-adult", "subject": "diet",
           "animal": {"body_weight_kg": 20,
                      "adult_dog_type": "Average laboratory or active (130 * kg BW^0.75)"},
           "entries": {"protein": {"low": 68.4}, "fat": {"low": 42.1},
                       "calcium": {"low": 3.16}, "phosphorus": {"low": 2.63},
                       "energy-density": {"low": 4.22}}}
# The order of the animal facts (steward, 26 Oct 2026: weight first, as a veterinarian
# describes a patient). A requirement shows only the facts it reads.
FACT_ORDER = ("body_weight_kg", "optimal_body_weight_kg", "life_stage", "lactation_week",
              "puppies_nursing", "mature_weight_kg", "adult_dog_type", "adult_cat_type",
              "energy_intake_kcal_per_day", "caloric_restriction_percent")
SPECIES = (("canine", "Dogs"), ("feline", "Cats"))
STANDARDS = ("NRC", "AAFCO", "FEDIAF")
# The value table's groups (steward, 26 Oct 2026); each row keeps the checker's order, and
# an MBW row goes under its per-Mcal row's group.
GROUPS = (
    ("en", "Energy", (inputs.ENERGY_ENTRY, "energy-density")),
    ("pa", "Protein and amino acids", (
        "protein", "arginine", "histidine", "isoleucine", "leucine", "lysine", "methionine",
        "methionine-cystine", "phenylalanine", "phenylalanine-tyrosine", "threonine",
        "tryptophan", "valine", "taurine", "taurine-wet", "glutamic-acid")),
    ("fa", "Fat and fatty acids", (
        "fat", "linoleic-acid", "alpha-linolenic-acid", "arachidonic-acid", "epa-dha", "epa",
        "la-aa-to-ala-epa-dha-ratio", "la-aa-to-epa-dha-ratio", "mct")),
    ("mi", "Minerals", (
        "calcium", "calcium-large-breed-puppy", "phosphorus", "ca-p-ratio", "potassium",
        "sodium", "chloride", "magnesium",
        "iron", "copper", "copper-wet", "manganese", "zinc", "iodine", "selenium",
        "selenium-wet")),
    ("vi", "Vitamins", (
        "retinol", "vitamin-a", "vitamin-d", "vitamin-d2", "vitamin-e", "vitamin-k1", "thiamine",
        "riboflavin", "pantothenic-acid", "niacin", "pyridoxine", "folate", "biotin",
        "cobalamin", "choline", "vitamin-c")),
    ("ot", "Other", (
        "water", "carbohydrate", "fiber-total", "fiber-insoluble", "fiber-soluble", "oxalate",
        "purine")),
)
MBW_SUFFIX = "-mbw"
FACTOR_LABELS = (
    ("reference_energy_kcal_per_day", "Reference energy, kcal/day"),
    ("reference_energy_basis", "Reference energy is"),
    ("energy_fed_kcal_per_day", "Energy fed, kcal/day"),
    ("energy_fed_is", "Energy fed is"),
    ("energy_factor", "Energy factor (rows with no MBW minimum)"),
    ("energy_used_kcal_per_day", "Energy used, kcal/day"),
    ("energy_used_is", "Energy used is"),
    ("energy_requirement_kcal_per_day", "The requirement's energy, kcal/day"),
    ("caloric_restriction_percent", "Caloric restriction, %"),
    ("aafco_dry_matter_factor", "AAFCO dry matter factor"),
    ("intake_shortfall", "Intake below the requirement's energy, share"),
)


class FormError(ValueError):
    pass


def e(x):
    return escape("" if x is None else str(x), quote=True)


def number(text):
    """A number from a form box: plain decimals with "." only; other text is passed on as
    text, for the input rules to reject with a reason."""
    text = text.strip()
    if not NUMBER.fullmatch(text):
        return text
    return int(text) if "." not in text else float(text)


def rows(data):
    """(id, name, unit) of every row a value can be entered for."""
    out = [(inputs.ENERGY_ENTRY, result.ENERGY_NAME, result.ENERGY_UNIT)]
    for nid in limits.nutrient_ids(data.tables):
        name, unit, _, _, _ = result._row_info(data, nid)
        out.append((nid, name, unit))
    return out


def request_from_form(data, form):
    """The request dict (as the MCP's check_diet takes it) from the form's fields. Unknown
    fields are rejected."""
    ids = {r[0] for r in rows(data)}
    req = {"requirement": None, "animal": {}, "entries": {}}
    for key, value in form:
        if len(value) > (MAX_PASTE if key == "paste" else MAX_FIELD):
            raise FormError("the field %s is too long" % key)
        value = value.strip()
        if key == "requirement":
            req["requirement"] = value or None
        elif key == "subject":
            req["subject"] = value
        elif key == "paste":
            continue
        elif key.startswith("animal."):
            fact = key[len("animal."):]
            if fact not in inputs.FACTS or fact == "requirement":
                raise FormError("unknown field %s" % key)
            if value:
                kind = inputs.FACTS[fact][0]
                req["animal"][fact] = value if kind in ("list", "life-stage") else number(value)
        elif key.startswith(("low.", "high.")):
            side, nid = key.split(".", 1)
            if nid not in ids:
                raise FormError("unknown field %s" % key)
            if value:
                req["entries"].setdefault(nid, {})[side] = number(value)
        else:
            raise FormError("unknown field %s" % key)
    if req["requirement"] is None:
        req.pop("requirement")
    return req


def _split_line(by_name, line):
    """(id, [low] or [low, high]) of a pasted line, or None. A row's name may hold commas
    ("Calcium, Ca"), so the longest leading run of fields that names a row is the name, and
    one or two fields must follow it."""
    parts = [p.strip() for p in (line.split("\t") if "\t" in line else line.split(","))]
    for k in range(len(parts) - 1, 0, -1):
        nid = by_name.get(", ".join(parts[:k]).lower())
        if nid is not None and 1 <= len(parts) - k <= 2:
            return nid, parts[k:]
    return None


def parse_paste(data, text):
    """(entries {id: {low, high}}, parsed rows, lines not understood) from pasted lines
    "name, low, high" (commas or tabs; a name or an id, any case)."""
    by_name = {}
    for nid, name, _ in rows(data):
        by_name[nid.lower()] = nid
        by_name.setdefault(name.lower(), nid)
    entries, parsed, bad = {}, [], []
    for line in text.splitlines():
        if not line.strip():
            continue
        found = _split_line(by_name, line)
        if found is None:
            bad.append(line)
            continue
        nid, values = found
        low = values[0]
        high = values[1] if len(values) > 1 else ""
        if nid in entries or not (low or high):
            bad.append(line)
            continue
        entries[nid] = {k: v for k, v in (("low", low), ("high", high)) if v}
        parsed.append((nid, low, high))
    return entries, parsed, bad


# The frame of every page.

def _caveat_html(text):
    """A caveat with its first sentence bold and the disclosure URL as a link."""
    first, sep, rest = text.partition(". ")
    html = "<strong>%s.</strong> %s" % (e(first), e(rest)) if sep else e(text)
    url = e(caveats.GOVERNANCE_URL)
    return html.replace(url, '<a href="%s">%s</a>' % (url, url))


def page(data, body, title=None):
    return FRAME.substitute(
        title=e("%s | %s" % (title, SITE) if title else SITE),
        caveats="\n".join("<li>%s</li>" % _caveat_html(c["text"])
                          for c in caveats.caveats(data.version)),
        body=body, code=e(result.CODE_RELEASE), data=e(data.version),
        sha=e(data.sha256[:12]))


# Screen A: choose a requirement.

def step1(data, chosen=None):
    reqs = data.tables["requirements"]
    groups = []
    for species, plural in SPECIES:
        for standard in STANDARDS:
            options = "".join('<option value="%s"%s>%s</option>' % (
                e(r["id"]), " selected" if r["id"] == chosen else "", e(r["name"]))
                for r in reqs if r["species"] == species and r["standard"] == standard)
            if options:
                groups.append('<optgroup label="%s: %s">%s</optgroup>' % (
                    e(plural), e(standard), options))
    return ('<form method="get" action="/">\n'
            '<h1><label for="requirement">Choose a requirement</label></h1>\n'
            '<p>%s</p>\n'
            '<p class="field">\n<small class="hint" id="requirement-hint">%s</small>\n'
            '<select id="requirement" name="requirement" aria-describedby="requirement-hint">'
            '\n<option value="">Choose a requirement</option>\n%s\n</select>\n</p>\n'
            '<p class="actions"><button type="submit">Next</button></p>\n</form>') % (
        FIRST_TIME, e(REQUIREMENT_HINT % len(reqs)), "\n".join(groups))


# Screen B: enter values.

def _kittens(use):
    return any(stage in energy.KITTENS for stage, _ in use or ())


def fact_label(data, rid, fact):
    if fact == "life_stage" and rid and not _kittens(result.life_stage_use(data, rid)):
        return caveats.LIFE_STAGE_LABEL_NO_KITTENS
    return caveats.FACT_TEXTS.get(fact, (fact.replace("_", " "),))[0]


def ordered_facts(facts):
    return sorted(facts, key=lambda f: FACT_ORDER.index(f) if f in FACT_ORDER
                  else len(FACT_ORDER))


def _stage_class(stage):
    """The class of a life stage's option: ls-<its index in inputs.LIFE_STAGES>."""
    return "ls-%d" % inputs.LIFE_STAGES.index(stage)


def _life_stage_select(name, label, use, value):
    """The covered life stages only; the blank first option is None where None is covered,
    else "Choose a life stage"."""
    stages = [s for s, _ in use]
    none_covered = energy.NONE in stages
    current = energy.NONE if value in (None, "", energy.NONE) else value
    first = '<option value="" class="%s"%s>%s</option>' % (
        _stage_class(energy.NONE) if none_covered else "ls-x",
        " selected" if current == energy.NONE else "",
        e(energy.NONE if none_covered else CHOOSE_LIFE_STAGE))
    options = "".join('<option value="%s" class="%s"%s>%s</option>' % (
        e(s), _stage_class(s), " selected" if s == current else "", e(s))
        for s in stages if s != energy.NONE)
    return ('<label for="f-life_stage">%s</label>\n<select id="f-life_stage" name="%s">%s%s'
            '</select>') % (label, name, first, options)


def _list_select(name, fid, label, items, value):
    """A list whose first item is "Not selected or a ..." takes it as the blank option."""
    current = items[0] if value in (None, "") else value
    opts = '<option value=""%s>%s</option>' % (
        " selected" if current == items[0] else "", e(items[0]))
    opts += "".join('<option value="%s"%s>%s</option>' % (
        e(i), " selected" if i == current else "", e(i)) for i in items[1:])
    return '<label for="%s">%s</label>\n<select id="%s" name="%s">%s</select>' % (
        fid, label, fid, name, opts)


def _fact_box(data, rid, fact, value, use):
    """One animal fact as a field. Under a requirement that reads the life stage, a fact
    that only some of its life stages use carries the classes dep and s-<stage index> of
    each, and the stylesheet hides it under the others (no script)."""
    kind, rule = inputs.FACTS[fact]
    name = "animal." + fact
    fid = "f-" + fact
    label = e(fact_label(data, rid, fact))
    classes = "field"
    if use and fact != "life_stage":
        stages = [s for s, used in use if fact in used]
        if stages and len(stages) < len(use):
            classes += " dep " + " ".join(
                "s-%d" % inputs.LIFE_STAGES.index(s) for s in stages)
    if kind == "life-stage":
        inner = _life_stage_select(name, label, use or [(s, []) for s in rule], value)
    elif kind == "list":
        inner = _list_select(name, fid, label, rule(data.tables), value)
    else:
        description = caveats.FACT_TEXTS.get(fact, (None, None))[1]
        allowed = "%s to %s" % rule if kind != "restriction" else "0, or %s to %s" % rule
        hints, described = "", []
        if description:
            hints += '<small class="hint" id="%s-hint">%s</small>\n' % (fid, e(description))
            described.append(fid + "-hint")
        hints += '<small class="hint" id="%s-allowed">Allowed values: %s</small>\n' % (
            fid, e(allowed))
        described.append(fid + "-allowed")
        inner = ('<label for="%s">%s</label>\n%s<input id="%s" name="%s" type="text" '
                 'inputmode="decimal" value="%s" aria-describedby="%s">') % (
            fid, label, hints, fid, name, e(value), " ".join(described))
    return '<p class="%s">\n%s\n</p>' % (classes, inner)


def _row_html(nid, name, unit, entries, lo, hi):
    cells = []
    for side, col in (("low", lo), ("high", hi)):
        cells.append('<td data-label="%s"><input type="text" inputmode="decimal" '
                     'name="%s.%s" value="%s" aria-labelledby="r-%s %s" '
                     'aria-describedby="u-%s"></td>' % (
                         "Low (Min entry)" if side == "low" else "High (Max entry)",
                         side, e(nid), e(entries.get(nid, {}).get(side)), e(nid), col, e(nid)))
    return ('<tr><th scope="row" id="r-%s">%s</th><td class="wide" data-label="Unit" '
            'id="u-%s">%s</td>%s</tr>') % (e(nid), e(name), e(nid), e(unit), "".join(cells))


def _value_table(key, rows_, entries, label_attr):
    head = ('<thead><tr><th scope="col">Nutrient</th><th scope="col">Unit</th>'
            '<th scope="col" id="lo-%s">Low (Min entry)</th>'
            '<th scope="col" id="hi-%s">High (Max entry)</th></tr></thead>') % (key, key)
    body = "\n".join(_row_html(nid, name, unit, entries, "lo-" + key, "hi-" + key)
                     for nid, name, unit in rows_)
    return '<table class="stack" %s>\n%s\n<tbody>\n%s\n</tbody>\n</table>' % (
        label_attr, head, body)


def group_rows(data):
    """[(key, title, rows, MBW rows)]: every enterable row in exactly one group."""
    group_of = {nid: key for key, _, ids in GROUPS for nid in ids}
    out = {key: ([], []) for key, _, _ in GROUPS}
    for nid, name, unit in rows(data):
        if nid.endswith(MBW_SUFFIX):
            out[group_of[nid[:-len(MBW_SUFFIX)]]][1].append((nid, name, unit))
        else:
            out[group_of[nid]][0].append((nid, name, unit))
    return [(key, title) + out[key] for key, title, _ in GROUPS]


def value_tables(data, entries):
    parts = []
    for key, title, plain, mbw in group_rows(data):
        parts.append('<h3 id="g-%s">%s</h3>\n%s' % (
            key, e(title), _value_table(key, plain, entries, 'aria-labelledby="g-%s"' % key)))
        if mbw:
            parts.append('<details>\n<summary>MBW rows (%d)</summary>\n%s\n</details>' % (
                len(mbw), _value_table(key + "-mbw", mbw, entries,
                                       'aria-label="%s: MBW rows"' % e(title))))
    return "\n".join(parts)


def step2(data, rid, request=None, message="", note=""):
    """Screen B; note is a paragraph's text shown above the first Check button."""
    request = request or {}
    animal = request.get("animal", {})
    entries = request.get("entries", {})
    req = next(r for r in data.tables["requirements"] if r["id"] == rid)
    use = result.life_stage_use(data, rid)
    facts = "\n".join(_fact_box(data, rid, f, animal.get(f), use)
                      for f in ordered_facts(result.facts_read(data, rid)))
    subject = request.get("subject", "diet")
    subjects = "".join('<option value="%s"%s>%s</option>' % (
        e(s), " selected" if s == subject else "", e(s)) for s in result.SUBJECTS)
    return (
        '<form method="post" action="/check">\n<h1>Enter values</h1>\n<p>%s</p>\n'
        '<dl class="summary">\n<dt>Requirement</dt>\n<dd>%s <a class="noprint" href="/" '
        'aria-label="Change the requirement">Change</a></dd>\n</dl>\n'
        '<input type="hidden" name="requirement" value="%s">\n%s'
        '<p class="actions"><button type="submit">Check</button></p>\n'
        '<fieldset>\n<legend>Animal and energy</legend>\n%s\n</fieldset>\n'
        '<h2>Values</h2>\n<p>%s</p>\n'
        '<p class="field">\n<label for="subject">What is entered</label>\n'
        '<select id="subject" name="subject">%s</select>\n</p>\n'
        '<p class="field">\n<label for="paste">Or paste values instead of typing them.</label>\n'
        '<small class="hint" id="paste-hint">%s</small>\n'
        '<textarea id="paste" name="paste" rows="8" aria-describedby="paste-hint"></textarea>'
        '\n</p>\n<p class="actions"><button type="submit" class="secondary" '
        'formaction="/parse">Parse the pasted lines</button></p>\n%s\n%s\n'
        '<p class="actions"><button type="submit">Check</button></p>\n</form>') % (
        FIRST_TIME, e(req["name"]), e(rid), "<p>%s</p>\n" % e(note) if note else "", facts,
        e(caveats.UNITS_TEXT + UNITS_OTHER), subjects, e(PASTE_HINT), message,
        value_tables(data, entries))


def parsed_message(data, parsed, bad):
    names = {nid: name for nid, name, _ in rows(data)}
    rows_html = "\n".join(
        '<tr><th scope="row">%s</th><td data-label="Low">%s</td><td data-label="High">%s'
        '</td></tr>' % (e(names[n]), e(lo), e(hi)) for n, lo, hi in parsed)
    out = ('<table class="stack">\n<caption>%d rows parsed</caption>\n<thead><tr><th '
           'scope="col">Row</th><th scope="col">Low</th><th scope="col">High</th></tr></thead>'
           '\n<tbody>\n%s\n</tbody>\n</table>\n<p>Check them below before checking.</p>') % (
        len(parsed), rows_html)
    if bad:
        out += "\n<h3>Not understood (%d)</h3>\n<ul>%s</ul>" % (
            len(bad), "".join("<li>%s</li>" % e(b) for b in bad))
    return out


# Screen C: the result.

def _hidden(request):
    out = ['<input type="hidden" name="requirement" value="%s">' % e(request.get("requirement"))]
    if "subject" in request:
        out.append('<input type="hidden" name="subject" value="%s">' % e(request["subject"]))
    for fact, value in request.get("animal", {}).items():
        out.append('<input type="hidden" name="animal.%s" value="%s">' % (e(fact), e(value)))
    for nid, sides in request.get("entries", {}).items():
        for side, value in sides.items():
            out.append('<input type="hidden" name="%s.%s" value="%s">' % (
                e(side), e(nid), e(value)))
    return "\n".join(out)


def _num(x):
    return "" if x is None else e(result.numbers.to_text(x) if isinstance(x, float) else x)


def _check_text(c):
    if c["entry"] is not None:
        return c["entry"]["text"] or c["entry"]["result"]
    return "low %s, high %s" % (c["low"]["text"] or c["low"]["result"],
                                c["high"]["text"] or c["high"]["result"])


def _bold_first(text):
    first, sep, rest = text.partition(". ")
    return "<strong>%s.</strong> %s" % (e(first), e(rest)) if sep else e(text)


def _summary(pairs):
    """A dl.summary from (dt html, dd html, dt class) triples."""
    return '<dl class="summary">\n%s\n</dl>' % "\n".join(
        '<dt%s>%s</dt><dd>%s</dd>' % (' class="%s"' % cls if cls else "", dt, dd)
        for dt, dd, cls in pairs)


def animal_section(data, res):
    """What the result was computed with: the animal facts as accepted, and the energy."""
    rid = (res.get("requirement") or {}).get("id")
    animal = res["inputs"]["normalized"]["animal"]
    pairs = [(e(fact_label(data, rid, k)), _num(animal[k]), None)
             for k in ordered_facts(animal)]
    f = res["factors"]
    pairs += [(e(label), _num(f[key]), None) for key, label in FACTOR_LABELS
              if f[key] is not None]
    if f["energy_reason"]:
        pairs.append(("Energy", e(f["energy_reason"]["text"]), None))
    if f["optimal_body_weight"]:
        pairs.append(("Optimal body weight", e(f["optimal_body_weight"]["text"]), None))
    body = ("" if animal else "<p>No animal facts entered</p>\n") + _summary(pairs)
    if f["body_weight_text"]:
        body += "\n<p>%s</p>" % e(f["body_weight_text"])
    body += "\n<p>%s</p>" % _bold_first(f["energy_rules"])
    return ('<section aria-labelledby="ae-title">\n<header class="split">\n'
            '<h2 id="ae-title">Animal and energy</h2>\n<button type="submit" form="inputs" '
            'class="link noprint" aria-label="Change the animal and energy inputs">Change'
            '</button>\n</header>\n%s\n</section>') % body


def _report_label(data, rid, key):
    names = {nid: name for nid, name, _ in rows(data)}
    if key == "requirement":
        return "Requirement"
    if key.startswith("animal."):
        return fact_label(data, rid, key[len("animal."):])
    if key.startswith("entries."):
        nid, _, side = key[len("entries."):].partition(".")
        if nid in names:
            return names[nid] + (" (%s)" % side.capitalize() if side else "")
    return key


def input_report(data, res):
    rid = (res.get("requirement") or {}).get("id")
    items = [i for i in res["input_report"] if i["status"] != "defaulted"]
    body = _summary([(e(_report_label(data, rid, i["input"])), e(i["text"]), None)
                     for i in items]) if items else "<p>%s</p>" % e(EMPTY_INPUT_REPORT)
    return ('<section aria-labelledby="ir-title">\n<h2 id="ir-title">Input report</h2>\n%s\n'
            '</section>') % body


def _entry_pairs(label, entry):
    verdict = entry["verdict"]
    band = e(entry["outcome"])
    if entry["outcome_text"]:
        band = "%s <small>(%s)</small>" % (e(entry["outcome_text"]), band)
    return [
        (label, _num(entry["value"]), None),
        ("Band", band, "sub"),
        ("Verdict", '<strong class="verdict %s">%s</strong>' % (e(verdict), e(verdict.upper()))
         if verdict else "none", "sub"),
        ("Status", e(entry["status"]), "sub"),
    ]


def _range_high(n):
    if n["range_high"] is None:
        return "none"
    codes = "%s, %s" % (e(n["max_type"]), e(n["max_provenance"]))
    return "%s (%s)" % (_num(n["range_high"]), "%s; %s" % (e(n["max_type_text"]), codes)
                        if n["max_type_text"] else codes)


def nutrient_block(data, n):
    nid = e(n["id"])
    under = [n["minimum_raise"]["text"] if n["minimum_raise"] else None,
             n["requirement_maximum"]["text"] if n["requirement_maximum"] and
             not n["requirement_maximum"]["set"] else None,
             n["mbw"]["text"] if n["mbw"] else None,
             n["other_row"]["text"] if n["other_row"] else None]
    unavailable = n["limits_unavailable"]
    pairs = [("Minimum", _num(n["minimum"]) or (
        "none" if not unavailable else e(unavailable["text"])), None)]
    if n["verdict_minimum"] != n["minimum"] or n["minimum_text"]:
        dd = _num(n["verdict_minimum"]) or "none"
        if n["minimum_text"]:
            dd += ' <small class="hint">%s</small>' % e(n["minimum_text"])
        pairs.append(("Minimum for a verdict", dd, None))
    pairs.append(("Range high", _range_high(n), None))
    if n["entry"] is not None:
        pairs += _entry_pairs("Value", n["entry"])
    else:
        for side in ("low", "high"):
            if n[side] is not None:
                pairs += _entry_pairs(side.capitalize(), n[side])
    conds = "".join("<li>%s%s</li>" % (
        e(c["depends_on"]), "" if c["limitation"] is None else
        ' (<a href="#limitation-%s">limitation %s</a>)' % (e(c["limitation"]),
                                                          e(c["limitation"])))
        for c in n["conditions"])
    pairs.append(("Conditions (%d)" % len(n["conditions"]),
                  "<ul>%s</ul>" % conds if conds else "none", None))
    notes = ""
    if n["notes"]:
        notes = "\n<details>\n<summary>Notes (%d)</summary>\n<dl>\n%s\n</dl>\n</details>" % (
            len(n["notes"]), "\n".join(
                "<dt><strong>%s</strong> (%s)</dt>\n<dd>%s</dd>" % (
                    e(i), e(data.notes[i]["origin"]), e(data.notes[i]["text"]))
                for i in n["notes"]))
    return ('<section class="nutrient" id="n-%s" aria-labelledby="h-%s">\n<header>\n'
            '<h3 id="h-%s">%s <small>(%s)</small></h3>\n%s\n</header>\n%s%s\n</section>') % (
        nid, nid, nid, e(n["name"]), e(n["unit"]),
        "\n".join("<p>%s</p>" % e(t) for t in under if t), _summary(pairs), notes)


def checks_section(res):
    if not res["checks"]:
        return ""
    items = "\n".join("<li><p>%s</p><p>Status: %s</p>%s</li>" % (
        e(_check_text(c)), e(c["status"]),
        "<p>Caveat: %s</p>" % e(c["caveat"]) if c["caveat"] else "") for c in res["checks"])
    return ('<section aria-labelledby="fa-title">\n<h2 id="fa-title">NRC fatty acid checks</h2>'
            '\n<ul>\n%s\n</ul>\n</section>') % items


def result_page(data, request, res):
    req = res["requirement"]
    name = req["name"] or "No requirement"
    lims = "\n".join('<li id="limitation-%s">%s</li>' % (e(l["item"]), e(l["text"]))
                     for l in res["limitations"])
    body = (
        '<h1>%s</h1>\n<p>Subject: %s. Verdicts: %s.</p>\n'
        '<form id="inputs" class="actions" method="post" action="/edit">\n%s\n'
        '<button type="submit" class="secondary" formaction="/check.json">Download JSON'
        '</button>\n<button type="submit" class="secondary">Change the inputs</button>\n'
        '</form>\n%s\n%s\n'
        '<section aria-labelledby="results-title">\n<h2 id="results-title">Results</h2>\n'
        '<p><strong>Verdicts: %s.</strong></p>\n%s\n</section>\n%s\n'
        '<h2>Known limitations</h2>\n<ul class="plain">\n%s\n</ul>') % (
        e(name), e(res["subject"]), e(res["verdict_status"]), _hidden(request),
        animal_section(data, res), input_report(data, res),
        e(res["verdict_status"]), "\n".join(nutrient_block(data, n) for n in res["nutrients"]),
        checks_section(res), lims)
    return page(data, body, "%s result" % name)
