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
| `tools/` | The one-time converter from the template, the source finder, the validator runner |
| `tests/parity/` | The frozen 21OCT26b baseline: a copy of the data, the test vectors, `SHA256SUMS` |

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
- `notes.csv`: the template's notes as records.
- `RELEASE`: the data version and the content hash.

No CSV cell holds an expression. A value computed from another (for example a per-MBW
maximum) has an empty figure, so it cannot go stale when its source changes.

## Checks

```
nice -n 10 python3 -I -B tests/test_phase1a.py          # baseline, round trip, validator
nice -n 10 python3 -I -B tests/roundtrip.py data        # the limits against 21OCT26b
nice -n 10 python3 -I -B tools/validate_data.py data    # the validator
```

The round trip computes all 4,830 limits from the CSV files and compares them with the
released 21OCT26b values: 4,829 are bit for bit the same, and one differs in the last
binary digit (the template's `=0.17*40` gives 6.800000000000001; the code gives 6.8).

## Status

Phase 1a of the plan: the data format, the converter, per-value sources, the validator,
the frozen baseline. Next: number handling and the vector runner (1b), energy (2),
minimums, maximums and bands (3), the parity gate (4).
