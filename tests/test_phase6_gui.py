"""Phase 6: the GUI rebuilt from the page mockups (docs/mockups/oan-checker), without a server.

- the markup rules of the mockups' handoff, on every page: native elements only, no script,
  style or event attribute, data-label on every td, unique ids, every reference resolves,
  only the server's field names, no button name or value, no number boxes, no required;
- the caveats, word for word and first, on every page;
- the steward's decisions of 26 Oct 2026: the fact labels and their order, the life stage
  lists, the life-stage fields shown only where used (and a value in a hidden field cannot
  change a result), the value groups, the texts of Screen A, the input report and About;
- the forms read back by the server's own form reader give the request they show.

Run: python3 -I -B tests/test_phase6_gui.py
"""

import os
import re
import sys
import unittest
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
from oan import caveats, energy, inputs, result  # noqa: E402
import gui  # noqa: E402

D = result.Data(os.path.join(ROOT, "data"))
DOG = energy.dog_type_labels(D.tables)
CAT = energy.cat_type_labels(D.tables)
ALLOWED = {"html", "head", "meta", "title", "link", "body", "a", "form", "fieldset", "legend",
           "label", "select", "option", "optgroup", "input", "textarea", "button", "table",
           "caption", "thead", "tbody", "tr", "th", "td", "details", "summary", "ol", "ul",
           "li", "dl", "dt", "dd", "h1", "h2", "h3", "p", "small", "strong", "section",
           "header", "main", "footer"}
VOID = {"meta", "link", "input"}
EXAMPLE = {"requirement": "aafco-cat-adult", "subject": "diet",
           "animal": {"body_weight_kg": 6.5, "adult_cat_type": CAT[1],
                      "caloric_restriction_percent": 25},
           "entries": {"protein": {"low": 120}, "taurine": {"low": 0.6},
                       "phosphorus": {"low": 5.5}, "energy-density": {"low": 3.6},
                       "linoleic-acid": {"low": 2}, "calcium": {"low": 1.2, "high": 3}}}
NRC_DOG = {"requirement": "nrc-dog-adult",
           "animal": {"body_weight_kg": 10, "caloric_restriction_percent": 99},
           "entries": {"linoleic-acid": {"low": 1}, "alpha-linolenic-acid": {"low": 0.01},
                       "epa-dha": {"low": 0.5}, "fat": {"low": "abc"},
                       "protein-mbw": {"low": 60}}}
STYLE = open(os.path.join(ROOT, "server", "static", "style.css"), encoding="utf-8").read()
ABOUT = open(os.path.join(ROOT, "server", "pages", "about.html"), encoding="utf-8").read()
HOW_TO_USE = open(os.path.join(ROOT, "server", "pages", "how-to-use.html"),
                  encoding="utf-8").read()


class Page(HTMLParser):
    """The elements of a page: [(tag, attrs dict, text inside it up to its first child)]."""

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.elements, self.stack, self.text = [], [], []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        el = (tag, dict(attrs), [])
        self.elements.append(el)
        for open_el in self.stack:
            open_el[2].append(el)
        if tag not in VOID:
            self.stack.append(el)

    def handle_endtag(self, tag):
        while self.stack:
            if self.stack.pop()[0] == tag:
                break

    def handle_data(self, data):
        self.text.append(data)
        for open_el in self.stack:
            open_el[2].append(data)

    def all(self, tag):
        return [el for el in self.elements if el[0] == tag]

    @staticmethod
    def inner_text(el):
        out = []
        for part in el[2]:
            if isinstance(part, str):
                out.append(part)
        return re.sub(r"\s+", " ", "".join(out)).strip()


def form_fields(page, form_index=0):
    """The (name, value) pairs a browser submits from a form (no submit button's)."""
    form = page.all("form")[form_index]
    out = []
    for el in form[2]:
        if isinstance(el, str):
            continue
        tag, attrs, inner = el
        if tag == "input" and attrs.get("name") and attrs.get("type") != "submit":
            out.append((attrs["name"], attrs.get("value", "")))
        elif tag == "textarea":
            out.append((attrs["name"], "".join(p for p in inner if isinstance(p, str))))
        elif tag == "select":
            options = [o for o in inner if not isinstance(o, str) and o[0] == "option"]
            chosen = next((o for o in options if "selected" in o[1]), options[0])
            out.append((attrs["name"], chosen[1].get("value", "")))
    return out


def pages():
    """[(name, html)] of every page kind, for every requirement's Screen B."""
    out = [("choose", gui.page(D, gui.step1(D), "Choose a requirement")),
           ("about", gui.page(D, ABOUT, "About")),
           ("how to use", gui.page(D, HOW_TO_USE, "How to use")),
           ("example", gui.page(D, gui.step2(D, gui.EXAMPLE["requirement"], gui.EXAMPLE,
                                             note=gui.EXAMPLE_NOTE), "Enter values")),
           ("error", gui.page(D, '<p class="error">x</p>', "Error"))]
    for r in D.tables["requirements"]:
        out.append(("enter " + r["id"], gui.page(D, gui.step2(D, r["id"]), "Enter values")))
    _, parsed, bad = gui.parse_paste(D, "Protein, 120,\nCalcium, Ca, 1.2, 3\nno such thing,1,2")
    out.append(("enter parsed", gui.page(D, gui.step2(
        D, "aafco-cat-adult", EXAMPLE, gui.parsed_message(D, parsed, bad)), "Enter values")))
    for name, req in (("result example", EXAMPLE), ("result nrc", NRC_DOG),
                      ("result no cat type", {"requirement": "nrc-cat-adult",
                                              "animal": {"body_weight_kg": 4},
                                              "entries": {"protein": {"low": 60}}}),
                      ("result no requirement", {"entries": {"calcium": {"low": 1}}})):
        out.append((name, gui.result_page(D, req, result.check(D, req))))
    return out


PAGES = pages()


class Markup(unittest.TestCase):
    def test_native_elements_only(self):
        for name, html in PAGES:
            page = Page(html)
            self.assertEqual({el[0] for el in page.elements} - ALLOWED, set(), name)
            for tag, attrs, _ in page.elements:
                self.assertNotIn("style", attrs, name)
                self.assertFalse([a for a in attrs if a.startswith("on")], name)
                self.assertNotIn("required", attrs, name)
                if tag == "td":
                    self.assertIn("data-label", attrs, name)
                if tag == "input":
                    self.assertIn(attrs.get("type"), ("text", "hidden"), name)
                    self.assertFalse({"min", "max", "step"} & set(attrs), name)
                if tag == "button":
                    self.assertFalse({"name", "value"} & set(attrs), name)

    def test_ids_unique_and_references_resolve(self):
        for name, html in PAGES:
            page = Page(html)
            ids = [el[1]["id"] for el in page.elements if "id" in el[1]]
            self.assertEqual(len(ids), len(set(ids)), name)
            for tag, attrs, _ in page.elements:
                for key in ("aria-labelledby", "aria-describedby"):
                    for ref in attrs.get(key, "").split():
                        self.assertIn(ref, ids, "%s: %s %s" % (name, key, ref))
                if tag == "label" and "for" in attrs:
                    self.assertIn(attrs["for"], ids, name)
                if tag == "button" and "form" in attrs:
                    self.assertIn(attrs["form"], ids, name)
                href = attrs.get("href", "") if tag == "a" else ""
                if href.startswith("#"):
                    self.assertIn(href[1:], ids, "%s: %s" % (name, href))

    def test_field_names_are_the_servers(self):
        allowed = re.compile(r"(requirement|subject|paste|animal\.[a-z_]+|(low|high)\.[a-z0-9-]+)$")
        for name, html in PAGES:
            for tag, attrs, _ in Page(html).elements:
                if tag in ("input", "select", "textarea") and "name" in attrs:
                    self.assertRegex(attrs["name"], allowed, name)

    def test_caveats_first_and_word_for_word(self):
        texts = [c["text"] for c in caveats.caveats(D.version)]
        blocks = set()
        for name, html in PAGES:
            start, main = html.index('<section class="caveats"'), html.index("<main>")
            self.assertLess(start, main, name)
            block = html[start:main]
            blocks.add(block)
            plain = "".join(Page(block).text)
            for text in texts:
                self.assertIn(text, re.sub(r"\s+", " ", plain), name)
            self.assertIn('<a href="%s">' % caveats.GOVERNANCE_URL, block)
        self.assertEqual(len(blocks), 1)

    def test_footer(self):
        for name, html in PAGES:
            self.assertIn('<a href="/about#contact">Report an error</a>', html, name)
            self.assertIn('<a href="/about">About</a>', html, name)
            self.assertIn('<a href="/how-to-use">How to use</a>', html, name)
            self.assertIn("Code %s, data %s (%s)" % (
                result.CODE_RELEASE, D.version, D.sha256[:12]), html, name)


class Facts(unittest.TestCase):
    """The animal facts of Screen B (steward, 26 Oct 2026)."""

    def enter(self, rid, request=None):
        return Page(gui.step2(D, rid, request))

    def test_labels(self):
        self.assertEqual({f: caveats.FACT_TEXTS[f][0] for f in caveats.FACT_TEXTS
                          if caveats.FACT_TEXTS[f][1] is None}, {
            "mature_weight_kg": "Expected mature body weight (kg)",
            "puppies_nursing": "Number of puppies nursing",
            "lactation_week": "Week of lactation",
            "life_stage": "Life stage, or a lactating queen's kittens",
            "adult_dog_type": "Type of adult dog",
            "adult_cat_type": "Type of adult cat",
            "energy_intake_kcal_per_day": "Energy intake (kcal/day), if known",
            "caloric_restriction_percent": "Caloric restriction (%), optional"})
        for r in D.tables["requirements"]:
            page = self.enter(r["id"])
            labels = {el[1].get("for"): Page.inner_text(el) for el in page.all("label")}
            for f in result.facts_read(D, r["id"]):
                self.assertEqual(labels["f-" + f], gui.fact_label(D, r["id"], f), r["id"])

    def test_order(self):
        for r in D.tables["requirements"]:
            names = [el[1]["name"][len("animal."):] for el in self.enter(r["id"]).elements
                     if el[0] in ("input", "select") and
                     el[1].get("name", "").startswith("animal.")]
            self.assertEqual(names, [f for f in gui.FACT_ORDER if f in names], r["id"])
            self.assertEqual(set(names), set(result.facts_read(D, r["id"])), r["id"])

    def test_dog_type_where_late_gestation_uses_it(self):
        # It was missed: the probe's dog type was NRC's average, which a blank type also gives.
        for rid in ("nrc-dog-gestation-lactation", "aafco-dog-growth-reproduction"):
            self.assertIn("adult_dog_type", result.facts_read(D, rid))
        facts = {"body_weight_kg": 10.0, "life_stage": energy.GESTATION_WEEK_5_ON}
        blank = energy.requirement_energy(D.tables, "nrc-dog-gestation-lactation", facts)
        inactive = energy.requirement_energy(D.tables, "nrc-dog-gestation-lactation",
                                             dict(facts, adult_dog_type=DOG[1]))
        self.assertNotEqual(blank, inactive)

    def test_kittens_nursing(self):
        self.assertEqual(inputs.LIFE_STAGES[6:], (
            "<3 Kittens Nursing", "3-4 Kittens Nursing", ">4 Kittens Nursing"))
        for old in ("<3 Kittens", "3-4 Kittens", ">4 Kittens"):
            self.assertEqual(inputs.check_fact("life_stage", old, D.tables).status, "reject")

    def test_life_stage_lists(self):
        expected = {
            "aafco-dog-growth-reproduction": (gui.CHOOSE_LIFE_STAGE, [1, 2, 3, 4, 5]),
            "aafco-dog-growth-large-breed": (gui.CHOOSE_LIFE_STAGE, [1, 2]),
            "fediaf-dog-early-growth-reproduction": ("None", [1, 2, 3, 4, 5]),
            "nrc-dog-gestation-lactation": ("None", [4, 5]),
            "aafco-cat-growth-reproduction": ("None", [1, 2, 3, 4, 6, 7, 8]),
            "nrc-cat-peak-lactation": (gui.CHOOSE_LIFE_STAGE, [6, 7, 8]),
            "fediaf-cat-reproduction": (gui.CHOOSE_LIFE_STAGE, [3, 4, 6, 7, 8]),
        }
        seen = set()
        for r in D.tables["requirements"]:
            page = self.enter(r["id"])
            select = [el for el in page.all("select")
                      if el[1].get("name") == "animal.life_stage"]
            if not select:
                self.assertNotIn(r["id"], expected)
                continue
            seen.add(r["id"])
            first, rest = expected[r["id"]]
            options = [o for o in select[0][2] if not isinstance(o, str) and o[0] == "option"]
            self.assertEqual((options[0][1]["value"], Page.inner_text(options[0])), ("", first))
            self.assertEqual([o[1]["value"] for o in options[1:]],
                             [inputs.LIFE_STAGES[i] for i in rest], r["id"])
            label = gui.fact_label(D, r["id"], "life_stage")
            kittens = any(i >= 6 for i in rest)
            self.assertEqual(label, caveats.FACT_TEXTS["life_stage"][0] if kittens
                             else caveats.LIFE_STAGE_LABEL_NO_KITTENS, r["id"])
        self.assertEqual(seen, set(expected))

    def test_none_given_selects_the_blank_option(self):
        for value in ("None", None):
            animal = {"life_stage": value} if value else {}
            page = self.enter("nrc-dog-gestation-lactation", {"animal": animal})
            self.assertIn(("animal.life_stage", ""), form_fields(page))
        page = self.enter("nrc-dog-adult", {"animal": {"adult_dog_type": DOG[0]}})
        self.assertIn(("animal.adult_dog_type", ""), form_fields(page))

    def test_fields_hidden_by_life_stage(self):
        expected = {
            "aafco-dog-growth-reproduction": {"lactation_week": [5], "puppies_nursing": [5],
                                              "adult_dog_type": [3, 4]},
            "fediaf-dog-early-growth-reproduction": {
                "lactation_week": [5], "puppies_nursing": [5], "mature_weight_kg": [0, 1, 2]},
            "nrc-dog-gestation-lactation": {"lactation_week": [5], "puppies_nursing": [5],
                                            "adult_dog_type": [0, 4]},
            "aafco-cat-growth-reproduction": {"lactation_week": [6, 7, 8]},
            "fediaf-cat-reproduction": {"lactation_week": [6, 7, 8]},
        }
        for r in D.tables["requirements"]:
            got = {}
            for tag, attrs, inner in self.enter(r["id"]).all("p"):
                classes = attrs.get("class", "").split()
                if "dep" in classes:
                    field = next(el[1]["name"] for el in inner if not isinstance(el, str) and
                                 el[0] in ("input", "select"))[len("animal."):]
                    got[field] = sorted(int(c[2:]) for c in classes if c.startswith("s-"))
            self.assertEqual(got, expected.get(r["id"], {}), r["id"])

    def test_stylesheet_hides_under_every_life_stage(self):
        self.assertIn("@supports selector(:has(*))", STYLE)
        self.assertIn("form:has(option.ls-x:checked) .dep", STYLE)
        for i in range(len(inputs.LIFE_STAGES)):
            self.assertIn("form:has(option.ls-%d:checked) .dep:not(.s-%d)" % (i, i), STYLE)

    def test_a_hidden_field_cannot_change_a_result(self):
        sample = {"lactation_week": 3, "puppies_nursing": 4, "adult_dog_type": DOG[1],
                  "adult_cat_type": CAT[2]}
        entries = {"protein": {"low": 70}, "calcium": {"low": 2}, "energy": {"low": 900}}
        compared = 0
        for r in D.tables["requirements"]:
            use = result.life_stage_use(D, r["id"])
            if not use:
                continue
            canine = r["species"] == "canine"
            base_facts = {"body_weight_kg": 10.0 if canine else 4.0,
                          "mature_weight_kg": 30.0 if canine else 5.0}
            stages = [s for s, _ in use] + ([None] if energy.NONE not in dict(use) else [])
            for stage in stages:
                used = dict(use).get(stage, [])
                for fact in set(f for _, fs in use for f in fs) - set(used):
                    animal = dict(base_facts, **{f: sample[f] for f in used if f in sample})
                    if stage:
                        animal["life_stage"] = stage
                    if fact == "mature_weight_kg":
                        animal.pop("mature_weight_kg", None)
                    without = result.check(D, {"requirement": r["id"], "animal": animal,
                                               "entries": entries})
                    value = base_facts["mature_weight_kg"] if fact == "mature_weight_kg" \
                        else sample[fact]
                    with_it = result.check(D, {"requirement": r["id"],
                                               "animal": dict(animal, **{fact: value}),
                                               "entries": entries})
                    for key in ("nutrients", "factors", "checks"):
                        self.assertEqual(with_it[key], without[key],
                                         "%s %s %s" % (r["id"], stage, fact))
                    compared += 1
        self.assertGreaterEqual(compared, 20)


class Values(unittest.TestCase):
    def test_every_row_in_one_group(self):
        groups = gui.group_rows(D)
        self.assertEqual([g[1] for g in groups], [
            "Energy", "Protein and amino acids", "Fat and fatty acids", "Minerals", "Vitamins",
            "Other"])
        placed = [nid for g in groups for part in g[2:] for nid, _, _ in part]
        self.assertEqual(sorted(placed), sorted(nid for nid, _, _ in gui.rows(D)))
        self.assertEqual([nid for nid, _, _ in groups[0][2]], ["energy", "energy-density"])
        self.assertIn("glutamic-acid", [nid for nid, _, _ in groups[1][2]])
        self.assertIn("choline", [nid for nid, _, _ in groups[4][2]])
        for g in groups:
            self.assertTrue(all(nid.endswith("-mbw") for nid, _, _ in g[3]))
            self.assertFalse(any(nid.endswith("-mbw") for nid, _, _ in g[2]))

    def test_mbw_rows_in_a_closed_details(self):
        html = gui.step2(D, "nrc-dog-adult")
        for match in re.finditer(r'name="low\.([a-z0-9-]+)-mbw"', html):
            self.assertGreater(html.rfind("<details>", 0, match.start()),
                               html.rfind("</details>", 0, match.start()))


class Texts(unittest.TestCase):
    def test_screen_a_hint(self):
        self.assertIn("One of 21 nutrient requirements from the 2006 NRC, the 2026 AAFCO and "
                      "FEDIAF Sept. 2025.", gui.step1(D))

    def test_empty_input_report(self):
        html = gui.result_page(D, EXAMPLE, result.check(D, EXAMPLE))
        self.assertIn("<p>Every value entered was used; nothing is missing.</p>", html)
        html = gui.result_page(D, NRC_DOG, result.check(D, NRC_DOG))
        self.assertNotIn("Every value entered was used", html)
        self.assertIn("<dt>Caloric restriction (%), optional</dt><dd>Not used: outside 1 to 55 "
                      "(or 0 for none).</dd>", html)
        self.assertIn("<dt>Fat, Total Lipid (Low)</dt>", html)

    def test_about(self):
        self.assertIn('<h2 id="contact">Contact</h2>', ABOUT)
        self.assertIn("To use the checker with an AI assistant, add "
                      "https://checker.openanimalnutrition.org/mcp as an MCP connector or "
                      "plug-in (no sign-in). Privacy, above, says what is kept when an "
                      "assistant calls it.", re.sub(r"\s+", " ", ABOUT))

    def test_result_keeps_every_output(self):
        res = result.check(D, EXAMPLE)
        html = gui.result_page(D, EXAMPLE, res)
        plain = re.sub(r"\s+", " ", "".join(Page(html).text))
        for n in res["nutrients"]:
            for part in ("minimum_raise", "mbw", "other_row"):
                if n[part]:
                    self.assertIn(n[part]["text"], plain)
            for side in ("entry", "low", "high"):
                if n[side]:
                    self.assertIn(n[side]["status"], plain)
                    self.assertIn(n[side]["outcome"], plain)
            for c in n["conditions"]:
                self.assertIn(c["depends_on"], plain)
            if n["range_high"] is not None:
                self.assertIn(n["max_type"] + ", " + n["max_provenance"], plain)
            for i in n["notes"]:
                self.assertIn(D.notes[i]["text"], plain)
        for l in res["limitations"]:
            self.assertIn(l["text"], plain)
        self.assertIn(res["factors"]["energy_rules"], plain)
        self.assertIn("Verdicts: proposed, pending ratification.", plain)
        self.assertIn('<strong class="verdict deficient">DEFICIENT</strong>', html)
        res = result.check(D, NRC_DOG)
        html = gui.result_page(D, NRC_DOG, res)
        for c in res["checks"]:
            self.assertIn("<p>Status: %s</p>" % gui.e(c["status"]), html)


class Paste(unittest.TestCase):
    """The pasted lines: a row's name may hold commas (28 Oct 2026: "Calcium, Ca, 3.16", the
    hint's own form with one value, was read as low "Ca" and high 3.16)."""

    def parse(self, line):
        _, parsed, bad = gui.parse_paste(D, line)
        return parsed[0] if parsed else None

    def test_lines_read_as_before(self):
        for line, want in (
                ("Protein, 60, 70", ("protein", "60", "70")),
                ("Protein, , 70", ("protein", "", "70")),
                ("Protein, 68.4,", ("protein", "68.4", "")),
                ("Calcium, Ca, 1.2, 3", ("calcium", "1.2", "3")),
                ("Calcium, Ca, , 6", ("calcium", "", "6")),
                ("Protein\t68.4", ("protein", "68.4", "")),
                ("Calcium, Ca\t3.16", ("calcium", "3.16", "")),
                ("CALCIUM, 3.16", ("calcium", "3.16", "")),
                ("energy-density, 4.22", ("energy-density", "4.22", "")),
                # still passed on, for the input report to reject with a reason
                ("Protein, 68.4 g/Mcal", ("protein", "68.4 g/Mcal", ""))):
            self.assertEqual(self.parse(line), want, line)

    def test_names_with_commas(self):
        for line, want in (
                ("Calcium, Ca, 3.16", ("calcium", "3.16", "")),
                ("Folate, DFE, Vitamin B9, 500", ("folate", "500", "")),
                ("Calcium, Ca (NRC puppies 4 to 14 weeks, expected adult weight over 25 kg), "
                 "2.5", ("calcium-large-breed-puppy", "2.5", ""))):
            self.assertEqual(self.parse(line), want, line)

    def test_lines_not_understood(self):
        for line in ("Ca, 3.16", "Protein: 68.4", "Protein 68.4", "Protein", "Protein, 1, 2, 3",
                     "Protein, ,", "no such thing, 1, 2"):
            self.assertIsNone(self.parse(line), line)
        _, parsed, bad = gui.parse_paste(D, "Protein, 60\nprotein, 70")
        self.assertEqual((len(parsed), bad), (1, ["protein, 70"]))

    def test_every_row_name_and_id(self):
        for nid, name, _ in gui.rows(D):
            for label in (name, nid):
                self.assertEqual(self.parse("%s, 1" % label), (nid, "1", ""), label)
                self.assertEqual(self.parse("%s, 1, 2" % label), (nid, "1", "2"), label)

    def test_hint_examples(self):
        for line, want in (("Calcium, Ca, 3.16", ("calcium", "3.16", "")),
                           ("Calcium, Ca, 1.2, 3", ("calcium", "1.2", "3")),
                           ("Calcium, Ca, , 6", ("calcium", "", "6"))):
            self.assertIn(line, gui.PASTE_HINT)
            self.assertEqual(self.parse(line), want, line)


class HowToUse(unittest.TestCase):
    """The user guide (pages/how-to-use.html) and its worked example (gui.EXAMPLE)."""

    def test_revised_for_this_release(self):
        found = re.search(r"Last revised (\d{1,2} \w+ \d{4}), for checker release ([\d.]+)\.",
                          HOW_TO_USE)
        self.assertIsNotNone(found)
        self.assertEqual(found.group(2), result.CODE_RELEASE)

    def test_example_result_as_the_guide_shows_it(self):
        res = result.check(D, gui.EXAMPLE)
        page = Page(HOW_TO_USE)
        rows = {}
        for tr in page.all("tr"):
            cells = [Page.inner_text(c) for c in tr[2]
                     if not isinstance(c, str) and c[0] in ("th", "td")]
            rows[cells[0]] = cells[1:]
        shown = {n["name"]: n for n in res["nutrients"]}
        for name, cells in rows.items():
            key = re.sub(r" \((computed|kcal/g DM)\)$", "", name)
            if key not in shown:
                continue
            n = shown.pop(key)
            entry = n["entry"] or n["low"]
            self.assertEqual(cells[1:5], [
                result.numbers.to_text(n["minimum"]), result.numbers.to_text(n["range_high"]),
                entry["outcome_text"], entry["verdict"] or "none"], name)
        self.assertEqual(shown, {})
        html = gui.result_page(D, gui.EXAMPLE, res)
        self.assertIn("<p>%s</p>" % gui.EMPTY_INPUT_REPORT, html)
        self.assertIn('"%s"' % gui.EMPTY_INPUT_REPORT, re.sub(r"\s+", " ", HOW_TO_USE))

    def test_example_values_from_the_label(self):
        # 26% x 10,000 / 3,800 kcal ME/kg, and so on; energy density on dry matter (10% water)
        for nid, percent in (("protein", 26), ("fat", 16), ("calcium", 1.2),
                             ("phosphorus", 1.0)):
            self.assertEqual(gui.EXAMPLE["entries"][nid]["low"],
                             round(percent * 10000 / 3800, 1 if percent > 2 else 2), nid)
        self.assertEqual(gui.EXAMPLE["entries"]["energy-density"]["low"], round(3.8 / 0.9, 2))
        self.assertIn(gui.EXAMPLE["animal"]["adult_dog_type"], DOG)

    def test_first_time_link_on_steps_1_and_2(self):
        self.assertIn(gui.FIRST_TIME, gui.step1(D))
        self.assertIn(gui.FIRST_TIME, gui.step2(D, "nrc-cat-adult"))

    def test_units_text_on_step_2(self):
        html = gui.step2(D, "nrc-cat-adult")
        self.assertIn("<h2>Values</h2>\n<p>%s</p>" % gui.e(caveats.UNITS_TEXT + gui.UNITS_OTHER),
                      html)
        self.assertNotIn("Every entry is per Mcal (or the unit shown)", html)


class Forms(unittest.TestCase):
    """The pages' forms, read back by the server's form reader."""

    def test_screen_b_gives_its_request(self):
        page = Page(gui.step2(D, "aafco-cat-adult", EXAMPLE))
        self.assertEqual(gui.request_from_form(D, form_fields(page)), EXAMPLE)

    def test_screen_c_gives_its_request(self):
        html = gui.result_page(D, EXAMPLE, result.check(D, EXAMPLE))
        page = Page(html)
        form = [i for i, f in enumerate(page.all("form")) if f[1].get("id") == "inputs"][0]
        self.assertEqual(gui.request_from_form(D, form_fields(page, form)), EXAMPLE)

    def test_example_gives_its_request(self):
        html = gui.step2(D, gui.EXAMPLE["requirement"], gui.EXAMPLE, note=gui.EXAMPLE_NOTE)
        self.assertEqual(gui.request_from_form(D, form_fields(Page(html))), gui.EXAMPLE)
        self.assertLess(html.index(gui.e(gui.EXAMPLE_NOTE)), html.index("<button"))

    def test_check_is_the_first_submit(self):
        page = Page(gui.step2(D, "aafco-cat-adult"))
        buttons = page.all("button")
        self.assertEqual(Page.inner_text(buttons[0]), "Check")
        parse = [b for b in buttons if b[1].get("formaction") == "/parse"]
        self.assertEqual(len(parse), 1)


if __name__ == "__main__":
    unittest.main()
