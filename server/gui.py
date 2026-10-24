"""The GUI: one server-rendered page in steps, no JavaScript.

1. Choose a requirement.
2. Enter the animal facts that requirement reads, and a low and/or a high value per nutrient
   (or paste "name, low, high" lines, which are shown parsed, with a row count, before
   checking).
3. The result: the caveats on top, then the table; "download JSON" gives the same bytes as the
   MCP check_diet's JSON.

Every text from the data, the request or the result is HTML-escaped here.
"""

import re
from html import escape

from oan import caveats, inputs, limits, result

NUMBER = re.compile(r"-?\d+(\.\d+)?")
MAX_FIELD = 64
MAX_PASTE = 16000


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
        parts = [p.strip() for p in (line.split("\t") if "\t" in line else line.rsplit(",", 2))]
        nid = by_name.get(parts[0].lower()) if parts else None
        if nid is None or len(parts) < 2 or len(parts) > 3:
            bad.append(line)
            continue
        low = parts[1] if len(parts) > 1 else ""
        high = parts[2] if len(parts) > 2 else ""
        if nid in entries or not (low or high):
            bad.append(line)
            continue
        entries[nid] = {k: v for k, v in (("low", low), ("high", high)) if v}
        parsed.append((nid, low, high))
    return entries, parsed, bad


STYLE_LINK = '<link rel="stylesheet" href="/static/style.css">'


def page(data, body, title="Open Animal Nutrition Checker"):
    caveat_items = "".join("<li>%s</li>" % e(c["text"])
                           for c in result.caveats.caveats(data.version))
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<title>%s</title>%s</head><body><h1>%s</h1>"
            "<section class=\"caveats\"><h2>Caveats</h2><ol>%s</ol></section>%s"
            "<footer>Code %s, data %s (%s)</footer></body></html>") % (
        e(title), STYLE_LINK, e(title), caveat_items, body, e(result.CODE_RELEASE),
        e(data.version), e(data.sha256[:12]))


def step1(data, chosen=None):
    options = "".join('<option value="%s"%s>%s</option>' % (
        e(r["id"]), " selected" if r["id"] == chosen else "", e(r["name"]))
        for r in data.tables["requirements"])
    return ('<form method="get" action="/"><label>Requirement <select name="requirement">'
            '<option value="">Choose a requirement</option>%s</select></label> '
            '<button type="submit">Next</button></form>') % options


def _fact_box(data, fact, value):
    kind, rule = inputs.FACTS[fact]
    name = "animal." + fact
    label, description = caveats.FACT_TEXTS.get(fact, (fact.replace("_", " "), None))
    if description:
        label = "%s <small>(%s)</small>" % (e(label), e(description))
    else:
        label = e(label)
    if kind in ("list", "life-stage"):
        items = rule(data.tables) if kind == "list" else rule
        opts = '<option value=""></option>' + "".join(
            '<option value="%s"%s>%s</option>' % (e(i), " selected" if i == value else "", e(i))
            for i in items)
        return '<label>%s <select name="%s">%s</select></label>' % (label, e(name), opts)
    hint = "%s to %s" % rule if kind != "restriction" else "0, or %s to %s" % rule
    return '<label>%s <input name="%s" value="%s" size="8" inputmode="decimal"> ' \
           '<small>%s</small></label>' % (label, e(name), e(value), e(hint))


def step2(data, rid, request=None, message=""):
    request = request or {}
    animal = request.get("animal", {})
    entries = request.get("entries", {})
    req = next(r for r in data.tables["requirements"] if r["id"] == rid)
    facts = "".join("<p>%s</p>" % _fact_box(data, f, animal.get(f))
                    for f in result.facts_read(data, rid))
    subject = request.get("subject", "diet")
    subjects = "".join('<option value="%s"%s>%s</option>' % (
        e(s), " selected" if s == subject else "", e(s)) for s in result.SUBJECTS)
    table = "".join(
        '<tr><td>%s</td><td>%s</td><td><input name="low.%s" value="%s" size="9" '
        'inputmode="decimal"></td><td><input name="high.%s" value="%s" size="9" '
        'inputmode="decimal"></td></tr>' % (
            e(name), e(unit), e(nid), e(entries.get(nid, {}).get("low")), e(nid),
            e(entries.get(nid, {}).get("high")))
        for nid, name, unit in rows(data))
    return ('%s<form method="post" action="/check"><input type="hidden" name="requirement" '
            'value="%s"><h2>%s</h2>%s<fieldset><legend>Animal</legend>%s</fieldset>'
            '<p><label>What is entered <select name="subject">%s</select></label></p>'
            '<fieldset><legend>Or paste values instead of typing them</legend><p><small>One '
            'nutrient per line: name, low, high (for example: Calcium, Ca, 1.2, 3). Leave low '
            'or high empty if you have only one. Click Parse to see how each line was read; '
            'the values then fill the table below, and nothing is checked until you click '
            'Check.</small></p><textarea name="paste" rows="5" cols="60"></textarea><p><button '
            'type="submit" formaction="/parse">Parse the pasted lines</button></p></fieldset>'
            '<p><button type="submit">Check</button></p>'
            '<table><thead><tr><th>Nutrient</th><th>Unit</th><th>Low (Min entry)</th>'
            '<th>High (Max entry)</th></tr></thead><tbody>%s</tbody></table>'
            '<p><button type="submit">Check</button></p></form>') % (
        step1(data, rid), e(rid), e(req["name"]), message, facts, subjects, table)


def parsed_message(parsed, bad):
    rows_html = "".join("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (e(n), e(lo), e(hi))
                        for n, lo, hi in parsed)
    out = '<div class="parsed"><p>%d rows parsed. Check them below before checking.</p>' \
          '<table><tr><th>Row</th><th>Low</th><th>High</th></tr>%s</table>' % (
              len(parsed), rows_html)
    if bad:
        out += "<p>Not understood (%d):</p><ul>%s</ul>" % (
            len(bad), "".join("<li>%s</li>" % e(b) for b in bad))
    return out + "</div>"


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
    return "".join(out)


def _num(x):
    return "" if x is None else e(result.numbers.to_text(x) if isinstance(x, float) else x)


def _side(n, side):
    """A nutrient's low or high cells: a range's end, or a value entered alone in its column."""
    if n["entry"] is not None:
        return n["entry"] if n["entry"]["placed"] == side else None
    return n[side]


def _check_text(c):
    if c["entry"] is not None:
        return c["entry"]["text"] or c["entry"]["result"]
    return "low %s, high %s" % (c["low"]["text"] or c["low"]["result"],
                                c["high"]["text"] or c["high"]["result"])


def _entry_cells(entry):
    if entry is None:
        return "<td></td><td></td><td></td>"
    verdict = entry["verdict"] or ""
    band = e(entry["outcome"]) + (
        "<br><small>%s</small>" % e(entry["outcome_text"]) if entry["outcome_text"] else "")
    return '<td>%s</td><td>%s</td><td class="%s">%s<br><small>%s</small></td>' % (
        _num(entry["value"]), band, e(verdict), e(verdict.upper()), e(entry["status"]))


def notes_fold(data, ids):
    """A nutrient's notes, closed until opened (no JavaScript)."""
    if not ids:
        return ""
    items = "".join("<li><b>%s</b> (%s): %s</li>" % (
        e(i), e(data.notes[i]["origin"]), e(data.notes[i]["text"])) for i in ids)
    return "<details><summary>Notes (%d)</summary><ul>%s</ul></details>" % (len(ids), items)


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


def animal_section(res):
    """What the result was computed with: the animal facts as accepted, and the energy."""
    facts = "".join("<li>%s: %s</li>" % (
        e(caveats.FACT_TEXTS.get(k, (k.replace("_", " "),))[0]), _num(v))
        for k, v in res["inputs"]["normalized"]["animal"].items())
    f = res["factors"]
    factors = "".join("<li>%s: %s</li>" % (e(label), _num(f[key]))
                      for key, label in FACTOR_LABELS if f[key] is not None)
    if f["energy_reason"]:
        factors += "<li>Energy: %s</li>" % e(f["energy_reason"]["text"])
    if f["optimal_body_weight"]:
        factors += "<li>Optimal body weight: %s</li>" % e(f["optimal_body_weight"]["text"])
    factors += "<li><small>%s</small></li>" % e(f["energy_rules"])
    return ("<section><h3>Animal and energy</h3><ul>%s</ul><ul>%s</ul></section>" % (
        facts or "<li>No animal facts entered</li>", factors))


def result_page(data, request, res):
    report = "".join("<li>%s: %s</li>" % (e(i["input"]), e(i["text"]))
                     for i in res["input_report"] if i["status"] != "defaulted")
    rows_html = []
    for n in res["nutrients"]:
        conds = "".join("<li>%s%s</li>" % (e(c["depends_on"]), "" if c["limitation"] is None
                                           else " (limitation %s)" % e(c["limitation"]))
                        for c in n["conditions"])
        unavailable = n["limits_unavailable"]
        rows_html.append(
            "<tr><td>%s<br><small>%s</small>%s</td><td>%s</td><td>%s</td><td>%s</td>%s%s"
            "<td><ul>%s</ul>%s</td></tr>" % (
                e(n["name"]), e(n["unit"]),
                ("<br><small>%s</small>" % e(n["minimum_raise"]["text"])
                 if n["minimum_raise"] else "") +
                ("<br><small>%s</small>" % e(n["other_row"]["text"])
                 if n["other_row"] else "") +
                ("<br><small>%s</small>" % e(n["mbw"]["text"]) if n["mbw"] else "") + (
                    "<br><small>%s</small>" % e(n["requirement_maximum"]["text"])
                    if n["requirement_maximum"] and not n["requirement_maximum"]["set"]
                    else ""),
                _num(n["minimum"]) or ("none" if not unavailable else e(unavailable["text"])),
                _num(n["verdict_minimum"]),
                "none" if n["range_high"] is None else "%s<br><small>%s, %s: %s</small>" % (
                    _num(n["range_high"]), e(n["max_type"]), e(n["max_provenance"]),
                    e(n["max_type_text"] or "")),
                _entry_cells(_side(n, "low")), _entry_cells(_side(n, "high")),
                conds, notes_fold(data, n["notes"])))
    checks = "".join("<li>%s: %s%s</li>" % (
        e(c["id"]), e(_check_text(c)), (" " + e(c["caveat"])) if c["caveat"] else "")
        for c in res["checks"])
    lims = "".join("<li>%s</li>" % e(l["text"]) for l in res["limitations"])
    req = res["requirement"]
    body = (
        '<h2>%s</h2><p>Subject: %s. Verdicts: %s.</p>'
        '<form method="post" action="/check.json">%s<button type="submit">Download JSON'
        '</button> <button type="submit" formaction="/edit">Change the inputs</button></form>'
        '%s<section><h3>Input report</h3><ul>%s</ul></section>'
        '<table class="result"><thead><tr><th>Nutrient</th><th>Minimum</th>'
        '<th>Minimum for a verdict</th><th>Range high (type, kind)</th><th>Low</th>'
        '<th>Band</th><th>Verdict</th><th>High</th><th>Band</th><th>Verdict</th>'
        '<th>Conditions, notes</th></tr></thead><tbody>%s</tbody></table>'
        '<section><h3>NRC fatty acid checks</h3><ul>%s</ul></section>'
        '<section><h3>Known limitations</h3><ul>%s</ul></section>') % (
        e(req["name"] or "No requirement"), e(res["subject"]), e(res["verdict_status"]),
        _hidden(request), animal_section(res), report, "".join(rows_html), checks, lims)
    return page(data, body)
