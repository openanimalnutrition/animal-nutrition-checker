# Open Animal Nutrition: reference implementation (work in progress)

The code version of the Dynamic Decile System template (DDS, frozen at Version 21OCT26b).
It becomes the reference once it reproduces the template's published test cases, and only
after the steward approves every difference. Until then it is a non-normative reference
implementation of the proposed computation.

Python 3.9 or later, standard library only. Not yet published; the repository will move to
the Open Animal Nutrition organisation.

## Layout

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
| `tools/` | The one-time converter from the template, the source finder, the validator runner |
| `tests/parity/` | The frozen 21OCT26b baseline: a copy of the data, the test vectors, `SHA256SUMS` |
| `tests/run_vectors.py` | Runs every test vector against the baseline (both orders) and counts them per file |
| `tests/sheet_map.py`, `tests/sheet_view.py` | Test side only: the template's cells, and those cells computed from the code's results |
| `tests/models/energy_model.py` | An energy model written separately from the sources, reading the same figures, to check the core on changed data |
| `tests/models/values_model.py`, `tests/models/formulas_model.py` | The same for the limits and bands: models written separately from the specifications, reading the same data |
| `tests/vectors-extra/` | Cases written after the freeze for what the frozen vectors do not test (the text checks), not frozen |

## The data

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
- `notes.csv`: the template's notes as records.
- `RELEASE`: the data version and the content hash.

No CSV cell holds an expression. A value computed from another (for example a per-MBW
maximum) has an empty figure, so it cannot go stale when its source changes.

## Data versions

The data version (in `data/RELEASE`) is the code's own; the template sheet stays at
Version 21OCT26b. The frozen baseline in `tests/parity/` is never edited.

| Data version | Change |
|---|---|
| 21OCT26b.1 | The 21OCT26b requirement table as CSV, with a source for every figure |
| 21OCT26b.2 | Source text only: the five NRC dog choline minimums (340 mg/Mcal, 45 mg/kg BW^0.75) now say "AI column; see NRC p. 233" (steward, 21 Oct 2026). No value changed |
| 21OCT26b.3 | `energy.csv`: the energy figures of 21OCT26b, moved from the template's formulas into data with a source for each (steward, 21 Oct 2026). No value changed |
| 21OCT26b.4 | `template.csv`: the template's own figures and its four extra rows, moved from the Standards tab's formulas into data with a source for each (steward, 21 Oct 2026). No value changed |

The frozen baseline gained the same `energy.csv` once, in phase 2, and the same
`template.csv` once, in phase 3 (steward, 21 Oct 2026 both times), so the 21OCT26b cases
keep running on 21OCT26b's figures after a standard or a template figure changes. Its
`RELEASE` keeps the label 21OCT26b.1 with the content hash recomputed; each time
`SHA256SUMS` changed in the RELEASE line and gained the new file's line, nothing else.

## Checks

```
nice -n 10 python3 -I -B tests/test_phase1a.py          # baseline, round trip, validator
nice -n 10 python3 -I -B tests/test_phase1b.py          # number handling, input rules, runner
nice -n 10 python3 -I -B tests/test_phase2.py           # energy figures, energy, bands, row 11
nice -n 10 python3 -I -B tests/test_phase3.py           # template figures, limits, outcomes, models
nice -n 10 python3 -I -B tests/run_vectors.py           # the test vectors, counted per file
nice -n 10 python3 -I -B tests/roundtrip.py data        # the limits against 21OCT26b
nice -n 10 python3 -I -B tools/validate_data.py data    # the validator
```

The round trip computes all 4,830 limits from the CSV files and compares them with the
released 21OCT26b values: 4,829 are bit for bit the same, and one differs in the last
binary digit (the template's `=0.17*40` gives 6.800000000000001; the code gives 6.8). The
steward approved the two as the same value (21 Oct 2026).

## Status

Phase 1a of the plan: the data format, the converter, per-value sources, the validator,
the frozen baseline. Phase 1b: number handling, the input rules and the vector runner.
Phase 2: energy (the figures as data, the energy core, the bands, row 11). Phase 3: the
minimums, maximums, range highs and bands of rows 12-130, the type of each range high per
request (the IG's Maximum types), the outcomes other than a band, and NRC's five text
checks (the template's figures as data). Verdicts (deficient, excess) come with the Result
in phase 5.

| Vector file | Cases | Pass | Differ | Outside the rules |
|---|---|---|---|---|
| `inputs.json` (input rules) | 132 | 132 | 0 | 0 |
| `values.json` | 945 | 927 | 0 | 18 |
| `formulas-testcases.json` | 983 | 645 | 0 | 338 |
| `energy-testcases.json` | 2,360 | 2,360 | 0 | 0 |
| `energy-testcases-row11.json` | 1,092 | 1,088 | 0 | 4 |
| `vectors-extra/text-checks-21OCT26b.json` (not frozen) | 198 | 198 | 0 | 0 |

Every value is bit for bit the template's except two, within 1e-12: the vitamin D MBW
minimum of NRC RA Cat Maintenance at an entered intake, and the vitamin D2 MBW minimum
computed from it (formulas case k4-0766). Both come from the 6.8 against
6.800000000000001 difference the steward approved as the same value.

Cases with an input outside its rule, which the code rejects instead of computing with
(one approved category of difference): formulas 338, values 18, row 11 4, and the energy
file's own 30 outside-rule cases (29 rejected by the rules; the 30th has a blank body
weight, which the code reports as missing where the template shows 0 kcal).

The independent models, reading the same data folder, agree with every case they model:
values 8,595 values, formulas 51,229 (53 cases skipped, as in the original: a wildcard or
unmatched requirement name), energy every case. With a template figure changed, the core
and the models still agree (tests/test_phase3.py).

Next: the parity gate (4).
