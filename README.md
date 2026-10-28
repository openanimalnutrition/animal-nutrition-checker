# Open Animal Nutrition: the checker

The checker compares the nutrient values of a dog or cat diet with one published requirement:
any of 21 requirements from the 2006 NRC Nutrient Requirements of Dogs and Cats, the 2026
AAFCO Official Publication and the FEDIAF Nutritional Guidelines of September 2025. For each
nutrient entered it reports where the value lies among 14 bands, from below the minimum to
above the range high, and a proposed verdict: `deficient`, `excess` or none. It is the code
version of the Dynamic Decile System (DDS) template, frozen at Version 21OCT26b, and it gives
the same result to people, through a small web page, and to AI systems, through an MCP
server.

It compares a diet with one standard's figures. It is not a safety or compliance assessment,
and not veterinary advice; every result says so first.

## Status: proposed, not ratified

- This is the reference implementation of the computation proposed by Open Animal
  Nutrition: the Implementation Guide (IG) declared it the reference, in place of the
  template, on 24 Oct 2026, from release 0.5.0. Run with the template's rules, which it
  keeps for that check, it reproduces the template, Version 21OCT26b (parity approved by the
  steward on 22 Oct 2026); every difference is recorded with its reason. It is
  non-normative: its rules, and the verdicts `deficient` and `excess`, are the provisional
  steward's proposal, pending ratification by a governance body that has not yet been
  formed. The rules that differ from the template date from 23 and 24 Oct 2026; the groups
  that reviewed the template have not reviewed them.
- The provisional steward is DVM Consulting, Inc., a California Certified B Corporation. It
  sells nutritional supplements and offers diet formulation software that implements this
  standard ([disclosure of interest](https://github.com/openanimalnutrition/animal-nutrition-ig/blob/main/GOVERNANCE.md)).
  The computation references no product, ingredient, supplement or vendor. Hosting is paid
  for by DVM Consulting, Inc., the provisional steward (disclosure of interest).
- The steward keeps working on the checker. Every change goes through a pull request, is
  recorded with its reason in `docs/changes-from-21OCT26b.md`, and gets a new data version
  when the data change (`data/RELEASE`; now 21OCT26b.11) and a new release number when the
  code's rules change (`oan/result.py`; now 0.10.1). Every result states both
  (`code_release`, `data_version`).

## Where the reasoning is

| What | Where |
|---|---|
| The computation: the basis, the bands, the adequacy interpretation, the open points and the conflicts left for the governance body | The IG's [band computation page](https://github.com/openanimalnutrition/animal-nutrition-ig/blob/main/input/pagecontent/band-computation.md) |
| Where the checker's rules and notes differ from the template, and why | [`docs/changes-from-21OCT26b.md`](docs/changes-from-21OCT26b.md) |
| What was compared with the template, and the three differences the steward approved | [`docs/parity-21OCT26b.md`](docs/parity-21OCT26b.md) |
| Every value, with its source (table and page) | `data/standards/<edition>/<requirement>.csv`, `data/energy.csv`, `data/template.csv` |
| The notes on values and rows | `data/notes.csv` (the template's own wording: `docs/template-21OCT26b-notes.csv`) |
| The template's known limitations, and where each puts a condition on a result | `data/limitations.csv`, `data/conditions.csv` |

## Challenge a rule or report an error

[Open an issue](https://github.com/openanimalnutrition/animal-nutrition-checker/issues/new/choose)
with one of the two forms:

- **Challenge a rule**: the rule, what you propose instead, why (with sources by table and
  page), and which animals or requirements it affects;
- **Report a data error**: the value in the checker and the value in the source, with its
  table and page.

Everything in an issue is public and stays in the record. The steward answers in the issue;
once a governance body is formed, it decides. An accepted change is made by a pull request,
with its entry in the changes document and a new data version.

No GitHub account? Email admin+oan@dvmconsulting.com, and the steward will file it for you
as a public issue.

## Run it

The web page and the MCP server, in Docker (port 8790 on this computer only):

```
docker build --target runtime -t oan-checker:dev .
docker run --rm --read-only --tmpfs /tmp --cpus 1 --memory 512m -p 127.0.0.1:8790:8790 oan-checker:dev
```

Then open http://127.0.0.1:8790/ for the web page; the MCP server is at
http://127.0.0.1:8790/mcp.

Or run the published image instead of building it. Every push to main publishes it, once
the contract tests pass, as `ghcr.io/openanimalnutrition/animal-nutrition-checker`, with
the tags `main` (the newest) and `sha-<commit>`, and labels giving the code release and the
data version (`.github/workflows/image.yml`). The hosted checker runs this image, pinned by
its digest ([`docs/OPERATIONS.md`](docs/OPERATIONS.md)).

```
docker run --rm --read-only --tmpfs /tmp --cpus 1 --memory 512m -p 127.0.0.1:8790:8790 ghcr.io/openanimalnutrition/animal-nutrition-checker:main
```

From Python (3.9 or later, standard library only), in this folder:

```python
from oan import result

data = result.Data("data")
res = result.check(data, {
    "requirement": "nrc-dog-adult",
    "animal": {"body_weight_kg": 20,
               "adult_dog_type": "Average laboratory or active (130 * kg BW^0.75)"},
    "entries": {"protein": 60, "calcium": 1.2},   # in each row's unit, here g/Mcal
})
print(result.to_json(res))
```

`result.list_requirements(data)` lists the requirements, and `result.describe_inputs(data)`
the inputs, their units and their rules.

## License

CC0 1.0 Universal ([`LICENSE`](LICENSE)): the code, the data, the notes and the documents.
The standards and the other works the notes cite remain their publishers'; see
[`NOTICE`](NOTICE).

## Reference

The rest of this page is for those who maintain or check the code.

### Layout

| Path | What it is |
|---|---|
| `data/` | The standards, as CSV files that volunteers edit (see below) |
| `oan/table.py` | Loads `data/` and computes every limit from the printed figures and the rules |
| `oan/validate.py` | Checks a data folder; run `tools/validate_data.py` |
| `oan/release.py` | The data version and content hash in `data/RELEASE` |
| `oan/numbers.py` | Number handling in one place: the template's ROUND, number-to-text, input numbers |
| `oan/inputs.py` | The input rules: what the checker accepts, with a reason for each rejection |
| `oan/energy.py` | Each requirement's daily energy minimum, and the energy the checker uses |
| `oan/bands.py` | The 14 bands: which band of a row a value is in |
| `oan/limits.py` | Each nutrient's minimum, maximum, range high and the type of the range high, for one request |
| `oan/outcomes.py` | What the checker says about each entry (a band or another outcome), and NRC's text checks |
| `oan/interpret.py` | The adequacy interpretation of each entry: the proposed verdict, the comparisons with the minimum and the range high, the open point that leaves it without a verdict |
| `oan/conditions.py` | The conditions on each nutrient: the template's known limitations, by requirement and row |
| `oan/caveats.py` | The Result's fixed texts, as the steward approved them: the caveats, the status lines, the reasons |
| `oan/result.py` | The Result: `check()` (check_diet), `get_limits`, `list_requirements`, `describe_inputs`, `get_notes`, and its one byte form |
| `docs/result.schema.json` | The Result's published schema, `oan-check-result/2` |
| `server/` | The GUI and the MCP server, one small app (runs in Docker: `Dockerfile`, `server/requirements.lock`) |
| `tools/check.py` | Every automatic check in one command (what a pull request must pass) |
| `tools/impact_report.py` | The impact report of a data change, old data against new: evidence for the steward |
| `tools/` (other) | The one-time converters from the template (the table, the export's cell values), the source finder, the validator runner |
| `.github/workflows/checks.yml` | Runs `tools/check.py` on every pull request and on main |
| `.github/workflows/image.yml` | On main: runs the contract tests, then publishes the server's image to GitHub's container registry |
| `.github/ISSUE_TEMPLATE/` | The two issue forms: challenge a rule, report a data error |
| `LICENSE`, `NOTICE` | CC0 1.0; the standards and other cited works remain their publishers' |
| `docs/parity-21OCT26b.md` | The parity gate: what was compared with the template, and every difference with its reason |
| `docs/changes-from-21OCT26b.md` | Where the checker's rules and notes now differ from the template, and why |
| `docs/template-21OCT26b-notes.csv` | The template's 301 notes word for word (the record the adapted notes are checked against) |
| `tests/parity/` | The frozen 21OCT26b baseline: a copy of the data, the test vectors, the export's cell values, `SHA256SUMS` (the vector files' metadata names the build workspace they were made in, which is not published) |
| `tests/run_vectors.py` | Runs every test vector against the baseline (both orders) and counts them per file |
| `tests/real_sheets_check.py` | The one check against Google Sheets' own values: the released template's export |
| `tests/sheet_map.py`, `tests/sheet_view.py` | Test side only: the template's cells, and those cells computed from the code's results |
| `tests/models/energy_model.py` | An energy model written separately from the sources, reading the same figures, to check the core on changed data |
| `tests/models/values_model.py`, `tests/models/formulas_model.py` | The same for the limits and bands: models written separately from the specifications, reading the same data |
| `tests/model_agreement.py` | Runs each model and the core on the same data and lists where they disagree |
| `tests/test_phase5.py`, `tests/schema_check.py` | The Result, verdicts and conditions; a small schema checker (standard library) |
| `tests/contract/` | The server's contract tests, run in the test image |
| `tests/vectors-extra/` | Cases written after the freeze for what the frozen vectors do not test (the text checks; row 10, the header cells, the energy row of the table, the edges shown below band edges), not frozen |

### The data

- `nutrients.csv`: id, the template's name and unit, the amount unit and basis, the K
  multiplier, the per-Mcal nutrient of an MBW row, and whether it can be entered.
- `requirements.csv`: the 21 requirements, with standard, edition, species, life stage and
  (FEDIAF adult only) the MER the per-MBW maximums are computed with.
- `standards/<edition>/<requirement>.csv`: one row per nutrient. For the minimum and the
  maximum:
  - the **figure as the standard prints it**: `12.5`, `>15` (printed as greater than),
    `2|2.5` (two figures for a rule that chooses), `none` (no figure), or empty (computed);
  - the **printed unit** when it is not the nutrient's own, such as `mg/100 g DM` or
    `mcg/1000 kcal`; the code converts exactly;
  - the **rule**, from a closed list in `oan/table.py` (for example `mbw-from-per-mcal`,
    `folic-acid-to-dfe`, `template`);
  - the **source**: the table and printed page, or the note that explains a value the
    template sets itself;
  - the maximum's type (the template's codes) and the note ids.
- `energy.csv`: every figure of the energy equations as the standards print it (the NRC
  dog and cat type factors, the lactation week factors, the kitten coefficients, the
  constants of the growth, gestation and lactation equations, the AVCN growth multiples),
  each with its source (table and page). The adult dog and cat type names are here too,
  next to the figure each one prints; the validator rejects a name whose figure or exponent
  differs from the row's. The shape of each equation, and which requirement uses which,
  is in `oan/energy.py`.
- `template.csv`: what the template sets itself, each with its source and the requirements
  it applies to:
  - its four extra rows: EPA alone (entered only for NRC's EPA checks), vitamin D2 for
    cats (per Mcal and MBW) and the calcium of NRC puppies 4-14 weeks old of a large
    expected size;
  - its own figures: the defaults when a standard sets no minimum (vitamin C,
    carbohydrate, fibres), its fixed limits (water, energy density, oxalate, purine, MCTs,
    the taurine maximum when there is no taurine minimum), and the figures inside its rules
    (vitamin D2 / 0.7, the arginine increase for protein, NRC's LA:ALA ratios and EPA
    shares, the large-breed puppy calcium figures, AAFCO's 4 kcal/g DM, the energy factors
    of the calculated carbohydrate maximum, the n-6:n-3 ratio maximums' defaults). A figure
    that is a maximum carries its type (TPL when the template sets it; the puppy calcium
    maximum of 4.5 is NRC's calcium SUL). The shape of each rule is in `oan/limits.py`.
- `notes.csv`: the notes, adapted from the template's to describe the checker
  (`docs/changes-from-21OCT26b.md`), each with the tab and cell it comes from.
- `limitations.csv`: the template's ten known limitations, word for word (Standards tab A140 to
  A149).
- `conditions.csv`: where each limitation puts a condition on a result: the requirements
  (`*`, a species, a standard or ids), the rows, the case (a closed list in
  `oan/conditions.py`), the "depends on" line the steward approved, and the notes.
- `open-minimums.csv`: minimums whose verdict stays open, and when (the 15 AAFCO cells that
  AAFCO prints differently in its two tables, while the AAFCO dry matter factor is above 1).
- `RELEASE`: the data version and the content hash.

A minimum's rule says whose it is: `printed` (and the rules that convert a printed figure)
and `standard-derived` (the standard's own figure by the standard's own rule) count as the
standard's, so a value below it can be `deficient`; `template` is the template's own, and a
value below it gets no verdict (IG open point 6, as the steward settled it on 22 Oct 2026).

No CSV cell holds an expression. A value computed from another (for example a per-MBW
maximum) has an empty figure, so it cannot go stale when its source changes.

### Data versions

The data version (in `data/RELEASE`) is the code's own; the template sheet stays at
Version 21OCT26b. The frozen baseline in `tests/parity/` is never edited.

| Data version | Change |
|---|---|
| 21OCT26b.1 | The 21OCT26b requirement table as CSV, with a source for every figure |
| 21OCT26b.2 | Source text only: the five NRC dog choline minimums (340 mg/Mcal, 45 mg/kg BW^0.75) now say "AI column; see NRC p. 233" (steward, 21 Oct 2026). No value changed |
| 21OCT26b.3 | `energy.csv`: the energy figures of 21OCT26b, moved from the template's formulas into data with a source for each (steward, 21 Oct 2026). No value changed |
| 21OCT26b.4 | `template.csv`: the template's own figures and its four extra rows, moved from the Standards tab's formulas into data with a source for each (steward, 21 Oct 2026). No value changed |
| 21OCT26b.5 | The Standards tab's 133 notes (n169-n301), and every note's tab and cell; the 31 minimums the template takes from NRC's own figure by NRC's own rule get the rule `standard-derived` (the 29 NRC RA Cat Late Gestation MBW minimums by Table 15-14 footnote d, and pantothenic acid 1.44 mg/Mcal under both NRC queen selections); `limitations.csv`, `conditions.csv`, `open-minimums.csv` (steward, 22 Oct 2026). No value changed |
| 21OCT26b.6 | `notes.csv`: the notes describe the checker, not the spreadsheet: 224 adapted (cells to field names, cross-references to note ids, the rules of 23 Oct 2026), 3 deleted (n169, n174, n186); each change and its reason in `docs/changes-from-21OCT26b.md` (steward, 23 Oct 2026). No value changed |
| 21OCT26b.7 | `notes.csv`: ten notes (n181, n182, n183, n192, n214, n223, n224, n226, n227, n238) follow the rules of 24 Oct 2026: a restriction never raises fat, ratios do not change with a restriction or a low energy fed, and the range highs computed from a minimum are named (steward, 24 Oct 2026). No value changed |
| 21OCT26b.8 | Row names and conditions for AI readers (steward, 24 Oct 2026, after the AI-read test of release 0.5.1): the dry rows of taurine (per Mcal and MBW), copper and selenium are named "(For 12% or Less Moisture Foods)", and the moisture condition says on each row which foods it is for and whether the wet and dry limits differ under the requirement; template instructions left the vitamin D, vitamin D2, arginine and vitamin E names ("Cats: 1.43X if Vit D2" read as "multiply a D2 entry by 1.43"), with two new conditions (cat vitamin D form; arginine without protein); 15 notes follow the new names. Then, after a second AI-read test: the large-breed puppy calcium row's name and notes (n098, n233, n234) and a condition on the general calcium row (rule 11); AAFCO's dry matter maximums in conditions and limitation 8 (rule 12); the ten known limitations cite note ids, not template cells. No requirement figure changed |
| 21OCT26b.9 | `conditions.csv`: the condition on added selenium (`source-form-selenium`) names the separate limits it means, AAFCO's additive approval limit and FEDIAF's limit on organic selenium (steward, 25 Oct 2026, after the AI-read test of release 0.6.0 with new cases: beside FEDIAF's EU legal maximum, which applies to added selenium, "Limits on added selenium are not checked" read as a contradiction). No requirement figure changed |
| 21OCT26b.10 | `limitations.csv`: known limitation 3 says that FEDIAF's EU legal maximums apply only when the nutrient is added as an additive, and then to its total in the food (note n005) (steward, 25 Oct 2026, after the live-call test of release 0.7.0: "apply only to amounts added as additives" read as "only the added portion is limited"). No requirement figure changed |
| 21OCT26b.11 | `notes.csv`: the lactating queen's life stages are named "<3 Kittens Nursing", "3-4 Kittens Nursing" and ">4 Kittens Nursing" in notes n045, n051, n178 and n179, as the checker now names them (steward, 26 Oct 2026, with the GUI rebuild of release 0.10.0). No value changed |

The frozen baseline gained the same `energy.csv` once, in phase 2, and the same
`template.csv` once, in phase 3 (steward, 21 Oct 2026 both times), so the 21OCT26b cases
keep running on 21OCT26b's figures after a standard or a template figure changes. Its
`RELEASE` keeps the label 21OCT26b.1 with the content hash recomputed; each time
`SHA256SUMS` changed in the RELEASE line and gained the new file's line, nothing else.
In phase 4 the baseline gained, beside the data, the cell values of the released
template's export (`tests/parity/export-21OCT26b`, steward, 22 Oct 2026); `SHA256SUMS`
gained that one line.

### Checks

Every check, in one command (what a pull request must pass; GitHub runs the same):

```
nice -n 10 python3 -I -B tools/check.py
nice -n 10 python3 -I -B tools/check.py --against OLD_DATA     # also the impact report
```

It runs the validator on `data/` and on the frozen baseline, the tests of each phase, every
test vector, and the real-Sheets check. Each can also be run alone:

```
nice -n 10 python3 -I -B tests/test_phase1a.py          # baseline, round trip, validator
nice -n 10 python3 -I -B tests/test_phase1b.py          # number handling, input rules, runner
nice -n 10 python3 -I -B tests/test_phase2.py           # energy figures, energy, bands, row 11
nice -n 10 python3 -I -B tests/test_phase3.py           # template figures, limits, outcomes, models
nice -n 10 python3 -I -B tests/test_phase4.py           # real-Sheets check, impact report, parity page
nice -n 10 python3 -I -B tests/test_phase5.py           # the Result, verdicts, conditions, schema
nice -n 10 python3 -I -B tests/run_vectors.py           # the test vectors, counted per file
nice -n 10 python3 -I -B tests/real_sheets_check.py     # against the export's own values
nice -n 10 python3 -I -B tests/roundtrip.py data        # the limits against 21OCT26b
nice -n 10 python3 -I -B tools/validate_data.py data    # the validator
nice -n 10 python3 -I -B tools/impact_report.py OLD_DATA NEW_DATA   # a data change's impact
```

The server's contract tests run in Docker (the GUI's JSON and the MCP's check_diet are the
same bytes; the caveats are in every result; no excess above a non-authoritative maximum;
oversize, malformed and unknown requests are rejected; an MCP client lists and calls every
tool):

```
docker build --target test -t oan-checker:test .
docker run --rm --network none --read-only --tmpfs /tmp oan-checker:test
```

The impact report (evidence for the steward, not an oracle) lists the validator's findings
on the new data, every changed field of every data file, every limit and outcome that
changes over a fixed grid of inputs (every requirement under five sets of inputs, entries at
the old band edges and between them) and over the test cases' inputs, and the independent
models run on the new data against the core. No expected value is regenerated from the code
under review. Changing one figure names exactly the outcomes that use it
(`tests/test_phase4.py`).

The round trip computes all 4,830 limits from the CSV files and compares them with the
released 21OCT26b values: 4,829 are bit for bit the same, and one differs in the last
binary digit (the template's `=0.17*40` gives 6.800000000000001; the code gives 6.8). The
steward approved the two as the same value (21 Oct 2026).

### How it was built, and parity with the template

Phase 1a of the plan: the data format, the converter, per-value sources, the validator,
the frozen baseline. Phase 1b: number handling, the input rules and the vector runner.
Phase 2: energy (the figures as data, the energy core, the bands, row 11). Phase 3: the
minimums, maximums, range highs and bands of rows 12-130, the type of each range high per
request (the IG's Maximum types), the outcomes other than a band, and NRC's five text
checks (the template's figures as data). Phase 4: the parity gate (the real-Sheets check,
the difference list, the impact report, the automatic checks). Phase 5: the Result
(`oan-check-result`, version 2 from release 0.6.0), the proposed verdicts, the conditions, the GUI
and the MCP server.

**Parity with Version 21OCT26b, run with the template's own rules
(`limits.Request(..., template_rules=True)`): no case differs; the three differences in
`docs/parity-21OCT26b.md` were approved by the steward** (21 and 22 Oct 2026).

| Vector file | Cases | Pass | Differ | Outside the rules |
|---|---|---|---|---|
| `inputs.json` (input rules) | 132 | 132 | 0 | 0 |
| `values.json` | 945 | 927 | 0 | 18 |
| `formulas-testcases.json` | 983 | 645 | 0 | 338 |
| `energy-testcases.json` | 2,360 | 2,360 | 0 | 0 |
| `energy-testcases-row11.json` | 1,092 | 1,088 | 0 | 4 |
| `vectors-extra/text-checks-21OCT26b.json` (not frozen) | 198 | 198 | 0 | 0 |
| `vectors-extra/display-21OCT26b.json` (not frozen) | 181 | 181 | 0 | 0 |

The real-Sheets check: at the export's own inputs, every formula cell of the Standards tab
(3,796) and of the requirement table (396), and 5,578 typed cells, equal the values Google
Sheets stored, as Sheets writes them (10 significant digits for a formula's number);
872 typed cells of the layout are not compared, each with its reason.

Every value is bit for bit the template's except ten, within 1e-12, all from the 6.8
against 6.800000000000001 vitamin D difference the steward approved as the same value:
two in formulas case k4-0766 (C97, C99) and eight band edges of row 97 in the display cases.

Cases with an input outside its rule, which the code rejects instead of computing with
(one approved category of difference): formulas 338, values 18, row 11 4, and the energy
file's own 30 outside-rule cases (29 rejected by the rules; the 30th has a blank body
weight, which the code reports as missing where the template shows 0 kcal).

The independent models, reading the same data folder, agree with every case they model:
values 8,595 values, formulas 51,229 (53 cases skipped, as in the original: a wildcard or
unmatched requirement name), energy every case. With a figure changed, the core and the
models still agree (tests/test_phase3.py, tests/test_phase4.py).

### The Result, the GUI and the MCP server

Every result starts with four caveats: a non-normative reference implementation of the
proposed computation; the steward's disclosed interest; not a safety or compliance
assessment, nor veterinary advice; and conditions and open points. Per entry it gives the
band, how the value compares with the minimum and the range high, the proposed verdict
(`deficient`, `excess` or none, always "proposed, pending ratification"), the open IG point
that leaves it without one, and a one-line status. The rules (steward, 22 Oct 2026):
- `deficient` below the standard's part of the minimum, including a minimum raised for a
  caloric restriction or by the AAFCO dry matter factor, arginine, large-breed puppy calcium
  and the `standard-derived` minimums; below a minimum the template sets itself, no verdict
  (IG open point 6);
- `excess` only above an authoritative maximum; above a conditional, template-set or
  derived-provisional one the value is "not excess";
- both compared at 7 decimal places, as the bands are, so a verdict agrees with its band (IG
  open point 7).

The steward's energy rules (23 Oct 2026; proposed, pending ratification) keep the daily
amount of each nutrient at what the standard expected for the current body weight when the
animal is fed less energy than that: MBW minimums are converted at the energy fed, MBW
maximums at the reference energy (the energy the standard's per-Mcal figures assume), and,
under adult maintenance requirements, on a row with no MBW minimum the per-Mcal minimum is
multiplied by the reference energy divided by the energy fed (fat takes no restriction on
either row). The body weight is the current one; an optional optimal body weight sets
the energy fed for adults. Every result states the reference, the energy fed and the factor
(`factors`). The parity check runs the template's own rules (docs/parity-21OCT26b.md); where the checker differs from the template, and why: docs/changes-from-21OCT26b.md.

The MCP tools (stateless Streamable HTTP at `/mcp`): `list_requirements`, `describe_inputs`,
`get_limits`, `check_diet` and `get_notes`. Each returns the whole Result as structured
content and as a text block whose first lines are the caveats. Each tool's description, and
the server's instructions, give what it does and the call order before the caveats; the tools
are annotated read-only, and `get_limits` takes an optional list of nutrient ids. The GUI (`/`)
takes the same inputs and its "download JSON" gives the same bytes. Its pages follow the
mockups in `docs/mockups/oan-checker` (release 0.10.0): plain HTML and one stylesheet, no
script. A requirement's form shows only the animal facts it reads, and, once a life stage is
chosen, only those that life stage uses (in browsers without the CSS `:has()` selector,
every one). How to use (`/how-to-use`, from `server/pages/how-to-use.html`) is the user guide:
typing values, pasting them, and connecting an AI assistant, with a worked example that opens
pre-filled at `/example` (`gui.EXAMPLE`; a test checks the guide's table against its result,
and its "for checker release" against the code release).

To run it, see [Run it](#run-it) above.

Hosted at https://checker.openanimalnutrition.org/, with the MCP server at
https://checker.openanimalnutrition.org/mcp (no sign-in). What the hosted checker keeps is
stated on its About page (`/about`, from `server/pages/about.html`). How it runs, what it costs, how
to release, roll back or take it offline: [`docs/OPERATIONS.md`](docs/OPERATIONS.md).
