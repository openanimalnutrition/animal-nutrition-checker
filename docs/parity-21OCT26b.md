# Parity with the template, Version 21OCT26b

**Status: for the steward's approval** (the parity gate, phase 4 of the plan). Until it is
approved, the code is a non-normative reference implementation.

The code becomes the reference for the Dynamic Decile System once it reproduces the
released template, Version 21OCT26b, and the steward approves every difference. This page
lists what was compared, the result, and every difference with its reason. The counts are
checked by `tests/test_phase4.py`, so this page cannot fall out of date without a test
failing.

## What was compared

**The test vectors** (frozen in `tests/parity/vectors-21OCT26b`): cases with inputs and the
values the template gives, computed by the project's evaluator from the template's formulas.
Every case runs through the core and the test-side sheet view (the template's cells drawn
from the core's results), in file order and in reverse.

| File | Cases | Pass | Differ | Outside the input rules |
|---|---|---|---|---|
| `inputs.json` | 132 | 132 | 0 | 0 |
| `values.json` | 945 | 927 | 0 | 18 |
| `formulas-testcases.json` | 983 | 645 | 0 | 338 |
| `energy-testcases.json` | 2,360 | 2,360 | 0 | 0 |
| `energy-testcases-row11.json` | 1,092 | 1,088 | 0 | 4 |

**The extra cases** (`tests/vectors-extra`, not frozen), from the same evaluator, for cells
the frozen vectors do not test: NRC's five text checks (phase 3), and row 10, the header
cells, the requirement table's energy row and the edges shown below each band edge
(phase 4).

| File | Cases | Pass | Differ | Outside the input rules |
|---|---|---|---|---|
| `text-checks-21OCT26b.json` | 198 | 198 | 0 | 0 |
| `display-21OCT26b.json` | 181 | 181 | 0 | 0 |

**The real-Sheets check** (`tests/real_sheets_check.py`): every other expected value came
from the project's evaluator; these came from Google Sheets itself. The template was
exported from Sheets on 21 Oct 2026, and the value Sheets stored in each cell of the
Standards tab and the requirement table is frozen in `tests/parity/export-21OCT26b`. The
code, at the export's own inputs (NRC RA Dog Maintenance, 15 kg, average laboratory or
active), gives every cell the export holds, except layout:

| Tab | Cells in the export | Formula cells compared | Typed cells compared | Blank cells compared | Differ | Not compared (layout) |
|---|---|---|---|---|---|---|
| Standards tab (s01) | 4,839 | 3,796 of 3,796 | 357 | 40 | 0 | 686 |
| Requirement table (s02) | 5,803 | 396 of 396 | 5,221 | 2,082 | 0 | 186 |

Of the formula cells, those whose number Sheets wrote in full are identical (Standards tab
1,746, requirement table 338); the others are equal as Sheets writes them (2,050 and 58),
explained under "How numbers were compared". A blank cell compared is one the code draws as
blank where the export holds nothing.

Not compared, with their reasons (typed cells only; a formula cell is never left out):

- Standards tab: column A (row IDs, headings and instructions) 144; headings and labels of
  rows 1-9: 78; the unit labels of columns D, F, H and J: 455 (the units themselves are
  compared on the requirement table); the inputs: 7 (checked separately to be the export's
  inputs); the instruction in C55: 1; the multiplier in K55, which the template never uses
  (row 55 has no bands): 1.
- Requirement table: column A (row IDs and the title) 118; the headings, labels and
  reference IDs of rows 1-3: 68.

## The result

**No case differs.** Every difference from the template is in one of the three items below.
Items 1 and 2 were approved on 21 Oct 2026; item 3 is new.

## The differences

### 1. Inputs outside the template's input rules (approved 21 Oct 2026, decision 1 A)

The code rejects an input that the template's input rules reject, with a reason, instead of
computing with it as Sheets does. These cases count as one category of difference, by count:

- `formulas-testcases.json`: 338 (G10 231, G10 and G130 8, G130 41, O1 58);
- `values.json`: 18 (E3 10, I67 8);
- `energy-testcases-row11.json`: 4 (O1);
- the energy file's own 30 outside-rule cases: 29 rejected by the input rules, and one
  (EN-OUT-020) has a blank body weight, which the code reports as a missing input where the
  template shows 0 kcal.

### 2. NRC RA Cat Maintenance, vitamin D per kg BW^0.67 (approved 21 Oct 2026)

The template's `=0.17*40` gives 6.800000000000001; the code's exact conversion gives 6.8. The
steward approved the two as the same value. The difference is in the 16th digit and shows as
values within a relative 1e-12 instead of bit for bit: one in the round trip of the limits;
two in `formulas-testcases.json` (case k4-0766, C97 and C99); eight in
`display-21OCT26b.json` (the edges shown below row 97's band edges). It does not show in the
real-Sheets check: the export writes the number with 10 significant digits.

### 3. NRC RA Cat Maintenance, the DHA check of row 58, on changed data only (new)

Row 58 checks that EPA is included but at most 20% of EPA + DHA, and then that DHA (EPA +
DHA minus EPA) is at least the EPA + DHA minimum. If the EPA + DHA minimum of NRC RA Cat
Maintenance were "none", the code would skip the DHA comparison and report the EPA share
result alone (OK when the share is within 20%); the template would show an error (#VALUE!).

No case reaches this: the 21OCT26b data has that minimum (0.025 g/Mcal). Only a data change
could: the validator rejects removing the minimum alone, because the LA + AA : EPA + DHA
maximum of NRC RA Cat Maintenance is computed from it, so the change would also have to give
that maximum a figure of its own. `tests/test_phase4.py` tests both. The alternative is to
report the check as unavailable.

## Corrections to the test side (not differences)

The real-Sheets check found 19 cells that the sheet view drew wrongly, none of them in a
frozen vector. The core's results were right in each; the sheet view now draws the cells as
the template does:

- row 55 (EPA alone), 17 cells: the view drew limits and band edges; the template leaves
  them blank and shows an instruction in C55;
- M123 and AR123 (water): L123 has no formula in the template, so the summary sentence
  reads "Water Based on 1416 g/Mcal As a Highest Range"; the view added the text for a
  row with no minimum, and drew M123 as empty text instead of a blank cell.

## How numbers were compared

- The test vectors and extra cases: bit for bit, except the values of item 2, which are
  within a relative 1e-12.
- The real-Sheets check: Sheets writes a formula's number in the export with at most 10
  significant digits. The code's number is written the same way (its 15-significant-digit
  value, rounded half away from zero to 10 significant digits) and must then be equal; a
  typed number must be equal; texts must be identical. One cell shows why the rule matters:
  the code's value in AG72 is 1.9750000004999999 as stored, 1.9750000005 at 15 digits, and
  Sheets wrote 1.975000001; rounding the stored value directly would give 1.975.

## What approval means

Approving this page approves the three differences above and declares parity with
Version 21OCT26b. An approved difference is a versioned change of the specification with its
own tests (items 1 and 2 have theirs; item 3 is described in the formulas specification,
section 7, and the code's text checks).

To check again: `python3 -I -B tools/check.py`.
