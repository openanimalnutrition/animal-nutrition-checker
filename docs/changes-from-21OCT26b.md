# Changes from template Version 21OCT26b

The steward approved this page's wording on 24 Oct 2026; the rules in section 1 are the
provisional steward's decisions, proposed, pending ratification.

The Dynamic Decile System template (the Google Sheet), Version 21OCT26b, is frozen and is to be
retired; this checker is its successor (steward, 21 to 23 Oct 2026) and, from release 0.5.0,
the reference (declared by the IG on 24 Oct 2026). The parity check
([parity-21OCT26b.md](parity-21OCT26b.md)) shows that the code reproduces the template's
computation. This page lists where the checker now differs from the template, and why, so the
template's notes need not be read beside the checker's. The three differences approved at
parity (inputs outside the template's input rules, and two NRC cat items) are listed on the
parity page.

## Releases

A change to the code's rules gets a new release number, and a change to the data a new data
version; every result states both (`code_release`, `data_version`).

- 0.5.0 (24 Oct 2026): the first numbered release, and the one the IG declared the reference.
  Data version 21OCT26b.7; the rules in section 1. Results before it said `0.5.0.dev0`
  whichever rules computed them; their data version tells them apart: 21OCT26b.5, the
  template's rules (22 Oct 2026); 21OCT26b.6, the rules of 23 Oct; 21OCT26b.7, those of 24 Oct.
- 0.5.1 (24 Oct 2026): data version 21OCT26b.7; the verdicts are unchanged. Three fixes from
  an AI-read test of 0.5.0 (steward, 24 Oct 2026):
  - A minimum this checker raises for a caloric restriction or by the energy factor is no
    longer reported as the standard's own. The status line names the standard's minimum before
    the raise, the factor and the reason, and says whether the value is below the standard's
    minimum itself; a new field, `minimum_raise`, gives the same on every raised row. The test
    found "Below the AAFCO minimum" on a protein value 66% above AAFCO's own minimum for the
    food (120 g/Mcal against 72.22, raised to 122.8); the raise is the provisional steward's
    rule, which adds to the standards and does not change them.
  - NRC's fatty acid advice checks no longer count a nutrient that is not entered as 0 (rule 9).
  - The energy rules text in every result says when each computed range high applies (rules 4
    and 7); it named the NRC dog choline maximum as computed where it was NRC's 500 mg/Mcal.
- 0.6.0 (24 Oct 2026): data version 21OCT26b.8. Fixes from two AI-read tests (steward, 24
  Oct 2026). From the test of 0.5.1, where both models could not tell which moisture category
  a value was compared with, and one read "Cats: 1.43X if Vit D2" as an instruction to
  multiply the entry (section 3):
  - The dry rows of taurine, copper and selenium are named for the foods they cover, and each
    moisture row says which foods it is for and whether the wet and dry limits differ under
    the requirement. On a canned cat food entered on the plain taurine row, the checker
    compared the dry-food minimum, about half the wet-food one.
  - Template data-entry instructions left the row names; the two that carry meaning are now
    conditions (the cat vitamin D form, and arginine without protein under NRC and FEDIAF).
  - The Result's `standard_minimum` is now `verdict_minimum`, as it includes this checker's
    raise; the schema is `oan-check-result/2`, and a condition outside the template's ten
    known limitations has `limitation: null`.

  From a second test, of this release before it was merged:
  - Rules 10, 11 and 12: a value entered on one of a nutrient's per-Mcal and MBW rows is also
    checked on the other (dog A's calcium entered once read "Within the range"; on the MBW row
    the same value is deficient); the large-breed puppy calcium row applies only over 25 kg
    expected mature weight, with the current body weight; AAFCO's maximums are its dry matter
    maximums for a food below 4 kcal/g DM, and authoritative (a cat food's phosphorus that met
    AAFCO's 2.0% DM read above 5.0 g/Mcal, "conditional").
  - The result explains its codes where it uses them: each band's display name in the Dynamic
    Decile System (`outcome_text`), each range high's kind (`max_type_text`), the energies
    (`energies_text`), the entries' low and high (`entries_text`), the verdict (`verdict_text`)
    and the note ids (the notes block's `text`); NRC's and AAFCO's adult cats' reference energy
    says why it is a lean cat's. The ten known limitations cite note ids, not template cells
    (section 2).

  From a third test, no model misread a result; what still confused one was fixed:
  - A value entered alone is shown as `entry`, with `placed` (the template's column it is in);
    `low` and `high` only for a range entered as two ends. The advice checks follow.
  - A nutrient's per-Mcal and MBW rows checked together each name the other's verdict
    (`other_row`): the more protective row applies. `requirement_maximum` names the row that
    holds the requirement's maximum when it is the other one; the large-breed puppy calcium
    row records its NRC SUL.
  - `outcomes_text`: range-d10, Highest (90% of Range or Greater), includes values above the
    range high. The moisture condition where wet and dry limits are the same says so on each
    row (`moisture-same-dry`, `moisture-same-wet`).

  From a fourth test (again no misreading): `outcomes_text` adds that on a row with no maximum
  a band places a value within the minimum × K span, not against a limit; and on such a row
  `comparison_to_max` is `above_range_high` or `not_above_range_high`.

## Where the template's own text is kept

- [template-21OCT26b-notes.csv](template-21OCT26b-notes.csv): all 301 template notes word for
  word, as data version 21OCT26b.5 held them. A test (`tests/test_phase5.py`,
  `test_notes_against_the_template`) checks that a note's origin says "Adapted from" exactly
  when its text differs from this record.
- `tests/parity/data-21OCT26b/`: the frozen baseline (the requirement table, notes n001 to n168,
  energy and template figures), hash-checked and never edited.
- `tests/parity/export-21OCT26b/cells.json`: the released template's cell values.

## 1. Rules

From 23 Oct 2026 (rules 2 and 8 completed on 24 Oct 2026, rule 9 from release 0.5.1, rules 10
to 12 from release 0.6.0) the checker's own rules differ from
the template's (`oan/energy.py`,
`oan/limits.py`; tested by `tests/test_phase5_energy.py`). The parity check still compares the
template's computation: the code keeps the template's rules for that check only
(`limits.Request(..., template_rules=True)`, used by the sheet view and the phase 3 and 4
tests).

1. MBW minimums are converted at the energy fed: the intake entered, or else the requirement's
   energy (at the optimal body weight when that is used) less any caloric restriction. The
   template converts at the energy before the cut, so a restricted diet supplied only
   (1 - restriction) of the daily amount where an MBW row sets the minimum.
2. Fat is the exception: neither fat row takes a caloric restriction or an optimal body weight.
   Its MBW minimum is converted at the energy used, as the template does, except that an intake
   entered with a restriction is divided by (1 - the restriction), the need the intake is a cut
   from; the template converted at the intake, so a restriction entered with an intake raised
   fat's minimum. An intake entered alone is the animal's need, so fat's MBW minimum at it is the
   standard's own. Why (steward, 23 and 24 Oct 2026): fat per se is not essential; a lower
   energy density can help satiety during weight loss; and diets with about 15% of ME from fat
   (about 17 g/Mcal) are common for dogs with fat intolerance.
3. Under adult maintenance requirements, on a row with no MBW minimum (fat's and the ratios'
   excepted, rules 2 and 8), the per Mcal minimum is
   multiplied by the energy factor, the reference energy divided by the energy fed (at least 1
   and at least the restriction's factor); the template applies only the restriction's factor,
   and an entered intake never raised a minimum. Growth, gestation and lactation keep the
   template's rule: the animal is fed more energy than it needs to keep its weight stable and
   the extra goes to growth, a pregnancy or milk, so nutrient needs rise and fall with the
   energy fed and the per Mcal minimums hold at any intake; only a restriction raises them
   (steward, 23 Oct 2026).
4. MBW maximums are converted at the reference energy, the energy the standard's per Mcal
   figures assume at the current body weight: NRC's average adult dog (130 kcal x kg BW^0.75)
   for NRC and AAFCO dogs, NRC's lean adult cat (100 kcal x kg BW^0.67) for NRC and AAFCO cats
   (AAFCO states no energy basis), FEDIAF's stated MER, or else the equation this checker uses
   for the life stage (the intake, when no equation can be computed). Maximums therefore do not
   change per Mcal with the adult type, an intake, a restriction or an optimal body weight, with
   three exceptions, range highs this checker computes from a minimum, which follow that
   minimum: the NRC dog choline maximum (rule 7); the range high of the template's extra calcium
   row for NRC puppies 4 to 14 weeks old of a large expected size, 1.1 times that row's minimum
   once the minimum passes NRC's 4.5 g/Mcal SUL (the calcium row itself keeps 4.5 g/Mcal, and no
   requirement's own calcium maximum, such as AAFCO's 4.5 g/Mcal for large-breed growth, ever
   rises); and the carbohydrate maximum, the energy left after the protein and fat minimums. The
   template converted MBW maximums at the energy used.
5. An energy fed below 10% of the reference energy is rejected: the input that causes it is not
   used (the intake, else the optimal body weight, else the caloric restriction), and the
   result says so.
6. The body weight is the current body weight (for lactating queens, the weight at mating); the
   template's label reads "BW (kg; adults: optimal):". The template's note asked for the optimal
   (lean) body weight of adults, citing FEDIAF, AAFCO and NRC. The checker asks for the current
   body weight (steward, 22 and 24 Oct 2026). This is a layer beyond the standards,
   complementary to them: their figures are based on growth or on a stable body weight, never
   on weight loss, which is often taken as a sign of nutrient deficiency rather than a desired
   outcome. When an animal is fed less to lose weight, the minimums rise so that its needs are
   still met. A caloric restriction is a cut from what the animal eats at its current weight,
   not from an equation's estimate, and back-calculating an optimal weight from body condition
   involves too much variability and calculation for clinical practice. An optional optimal
   body weight (adult
   maintenance only; not a template input) is used when it is below the current body weight and
   no intake is entered: the energy fed is then the requirement's energy at that weight (for NRC
   and AAFCO cats, NRC's lean equation).
7. The choline maximum of the four NRC dog requirements (NRC's presumed safe maximum, 500
   mg/Mcal) is at least 1.1 times the higher of the choline minimum and the choline MBW minimum
   (per Mcal); when raised, its type is TPL, so a value above it is never called excess
   (steward, 23 Oct 2026). No standard sets a choline maximum from controlled safety data, so a
   range is kept above the minimum; calcium, whose tight control has data behind it, keeps the
   template's narrow rule (on the template's extra calcium row for NRC puppies 4 to 14 weeks old
   of a large expected size, the range high is 1.1 times that row's minimum only once the
   minimum passes NRC's 4.5 g/Mcal SUL; see rule 4).
8. Ratios do not change with a restriction or a low energy fed, as a ratio's numerator and
   denominator rise together (steward, 24 Oct 2026). Where a standard states no ratio, its
   range is computed from the other rows' minimums and maximums with the minimums before any
   restriction or energy factor: LA + AA : ALA + EPA + DHA and LA + AA : EPA + DHA for the NRC
   requirements and FEDIAF Dog Early Growth & Reproduction, and the Ca:P maximum of the NRC
   puppy requirements. The template computed them from the raised minimums, so a restriction
   narrowed the range: at a 30% restriction, NRC adult dogs' LA + AA : ALA + EPA + DHA range went
   from 0.31-74 to 0.44-52, and NRC puppies' Ca:P maximum from 1.8 to 1.26. Ratios a standard
   states itself never changed.
9. NRC's fatty acid advice checks (LA:ALA, and EPA's share of EPA + DHA) never count a nutrient
   that is not entered as 0: a check that needs one says it is not checked and names the
   nutrient. An entered 0 is still 0. A nutrient entered as one value counts on both sides of
   a check; one entered as a range counts low with low and high with high. The template read
   the low entries together and the high entries together, with nothing entered counting as 0,
   and so did this checker before release 0.5.1: LA entered without ALA read as outside NRC's
   ratio, and since the placement rule (the template's heading "If No Req't Min, Put In
   Range") puts a lone EPA value on the high side and EPA + DHA on the low, a diet entered as
   one value each was never compared, EPA at 20% of EPA + DHA reading as "EPA is not included"
   for adult cats (steward, 24 Oct 2026, after the AI-read test of release 0.5.0;
   `oan/outcomes.py`, tested by `tests/test_phase5.py`).

10. A value entered on one of a nutrient's two rows, per Mcal and MBW, is also checked on the
    other when that one is not entered and has a limit under the requirement: both rows take
    the diet's per-Mcal value, and the input report says so. The template checked only the
    rows entered, so with an optimal body weight or a low intake, a diet entered once per
    nutrient missed the energy-fed check, which only the MBW rows carry (steward, 24 Oct 2026;
    `oan/result.py`, tested by `tests/test_phase5.py`).
11. The large-breed puppy calcium row (NRC RA Puppy 4-14 Wk Growth) applies only to an expected
    mature body weight over 25 kg (NRC 2006 Table 15-3 footnote h); otherwise it is not
    computed, and says so. Its minimum of 0.54 g calcium per kg body weight a day uses the
    current body weight, which is the puppy's; the template applied the row whenever its
    optional puppy body weight was entered, a second weight field that the checker no longer
    reads. Calcium entered on the general row alone does not apply footnote h, so for those
    puppies that row carries a condition naming the large-breed row; the two rows are not
    checked together, as above 4.5 g/Mcal they can disagree (IG conflict 12) (steward, 24 Oct
    2026).
12. Under the AAFCO requirements, for a food below 4 kcal/g DM with its energy density entered,
    AAFCO's maximums are AAFCO's dry matter maximums for the food (the maximum per Mcal times
    4 ÷ energy density), as its minimums are; ratios are not changed. They are authoritative,
    so a value above one is excess. The template kept them per Mcal, conditional (its known
    limitation 8), so a food could read above a maximum it met on dry matter (steward, 24 Oct
    2026; the IG's other rules proposed for the code version).

## 2. Notes (data versions 21OCT26b.6 to 21OCT26b.8)

The checker's notes describe the checker, not the spreadsheet (steward, 23 Oct 2026). In every
adapted note:

- template cells and columns became the checker's names: the input fields (body_weight_kg,
  mature_weight_kg, puppies_nursing, lactation_week, life_stage, adult_dog_type,
  adult_cat_type, energy_intake_kcal_per_day, caloric_restriction_percent,
  puppy_body_weight_kg), the requirement names and the row names;
- "see the G10 note" and the like became "see note n192" (the note's id);
- the template's descriptors became the IG band codes (e.g., "Highest (90% of Range or
  Greater)" is the top band, range-d10), and its cell messages the checker's reasons;
- "this sheet" and "this application" became "this checker": the choices so marked were made
  in the template and are unchanged;
- the template's version history ("Up to version 18OCT26 ...") and spreadsheet formulas were
  removed.

An adapted note's origin reads "Adapted from DDS template Version 21OCT26b, <tab> <cell>
(docs/changes-from-21OCT26b.md)". Of the template's 301 notes, 3 were deleted,
224 adapted and 74 kept as they were.

### Deleted

- n169: how to change the spreadsheet's formatting (a video link).
- n174: the spreadsheet's requirement lookup helper, and how to rename or add a requirement in the sheet.
- n186: what the tan cell colour means in the spreadsheet.

### Meaning changed to match the rules above

- n175: Body weight: the template asked for the optimal (lean) body weight of adults; the checker asks for the current body weight of every animal, with an optional optimal body weight (rule 6).
- n192: Caloric restriction: the template did not adjust MBW minimums ("separately protective") and offered the MBW basis as an alternative; the checker converts MBW minimums at the energy fed and applies the energy factor (rules 1, 3); fat is not raised on either row (rule 2); ratios do not change (rule 8); the maximums that follow a minimum are named (rule 4).
- n183: Intake below the calculated energy: the template said no limit uses the intake; in the checker the intake is the energy fed, and under adult maintenance a low intake raises minimums on rows with no MBW minimum, fat and the ratios excepted (rules 2, 3, 8).
- n194: Energy row: the MBW minimums follow the energy fed, the energy factor applies under adult maintenance, and an optimal body weight does not lower the energy minimum.
- n214, n219: Fat and ALA MBW rows: "separately protective" removed; the ALA MBW minimum follows the energy fed, and the fat MBW minimum is not raised (rules 1, 2).
- n008, n068, n079: NRC cat MBW minimums and the queen taurine rows: converted at the energy fed; a restriction raises the per Mcal and MBW rows by the same factor, so it does not change which row is higher.
- n003, n009, n004, n006, n010, n012, n020, n024, n025, n027, n208, n212, n267: MBW maximums: the template converted them at the energy used, so the adult type and an entered intake moved them; the checker converts them at the reference energy (rule 4).
- n014, n016, n023, n176: Growth and reproduction: their per Mcal minimums hold at any intake; only a restriction raises them (rule 3).
- n029, n033, n181, n182: Adult dog and cat types: the type sets only the energy fed; the reference energy of NRC and AAFCO adults is NRC's average dog or lean cat, so a type below it raises the minimums of rows with no MBW minimum, e.g., every AAFCO row except fat and the ratios (rules 2, 3, 4, 8).
- n164, n165, n166, n167, n282, n168: NRC dog choline: the maximum is at least 1.1 times the higher choline minimum (rule 7), so the MBW minimum, which can now pass 500 mg/Mcal with a restriction or an optimal body weight as well as a low intake, no longer leaves a diet unable to meet both rows.
- n185: MBW rows: minimums are converted at the energy fed, maximums at the reference energy.
- n030, n031, n034, n035, n138: FEDIAF adults: only the MBW minimums follow an entered intake or a restriction; the MBW maximums stay at FEDIAF's MER (rules 1, 4).
- n278, n279, n289: Values calculated from the minimums (the folate note, the carbohydrate maximum) also follow the energy factor (rule 3).
- n223, n224, n226, n227, n238: Ratios calculated from other rows: the template's notes said they reflect any raise of the minimums, and that a calculated Ca:P maximum falls as the restriction rises; the checker computes them from the minimums before any raise, so they do not change (rule 8).

Data version 21OCT26b.8 changed 15 notes to the new row names only (section 3): n010, n012,
n131, n132, n133, n135, n136, n137, n250, n262, n263, n264, n265, n266, n267.

Data version 21OCT26b.8 also adapted n098 (kept as the template wrote it until then) and changed
n233 and n234 to rule 11: the large-breed puppy calcium row applies over 25 kg expected mature
weight, with the current body weight, and the general calcium row names it. The ten known
limitations (limitations.csv) were adapted like the notes: template cells became note ids,
"this sheet" became "this checker", and item 8 follows rule 12; the template's own text stays
in its export (`tests/parity/export-21OCT26b/`).

The steward read n175, n192 and n183 in full and approved them (23 Oct 2026). On 24 Oct 2026 n181, n182, n183, n192, n214, n223, n224, n226, n227 and n238 changed to follow that day's decisions (rules 2, 4 and 8; data version 21OCT26b.7).

### Wording only

The other adapted notes changed in wording only, by the conventions above: n001, n002, n005, n007, n011, n013, n015, n017, n018, n019, n021, n022, n026, n028, n036, n037, n038, n039, n040, n041, n042, n043, n044, n045, n046, n047, n048, n050, n051, n052, n053, n054, n057, n058, n059, n060, n066, n069, n074, n078, n080, n081, n082, n083, n084, n086, n087, n088, n089, n090, n095, n096, n097, n099, n100, n101, n102, n103, n104, n105, n106, n111, n112, n122, n123, n127, n128, n131, n132, n133, n134, n135, n136, n137, n143, n144, n145, n152, n153, n154, n156, n158, n159, n160, n161, n162, n163, n170, n171, n172, n173, n177, n178, n179, n180, n187, n188, n189, n190, n191, n193, n195, n196, n197, n198, n199, n200, n201, n202, n205, n207, n209, n211, n213, n215, n216, n217, n218, n220, n221, n222, n231, n232, n233, n234, n235, n236, n237, n239, n240, n242, n244, n245, n246, n247, n248, n249, n250, n251, n252, n253, n254, n255, n256, n257, n258, n259, n260, n261, n262, n263, n264, n265, n266, n268, n269, n270, n271, n272, n273, n274, n275, n276, n277, n280, n281, n283, n288, n291, n293, n295, n297, n298, n299.

## 3. Row names (data version 21OCT26b.8)

The template's row names carried data-entry instructions for the spreadsheet's user. The
checker's names say what each row is; an instruction that carries meaning is a condition on
the row, which every result shows (steward, 24 Oct 2026, after the AI-read test of release
0.5.1). The template's names are kept in the frozen baseline (`tests/parity/`).

| Row | Template name | Checker name |
|---|---|---|
| taurine, taurine-mbw | Taurine, Tau (MBW) | Taurine, Tau (For 12% or Less Moisture Foods) (MBW) |
| copper | Copper, Cu | Copper, Cu (For 12% or Less Moisture Foods) |
| selenium | Selenium, Se | Selenium, Se (For 12% or Less Moisture Foods) |
| vitamin-d, vitamin-d-mbw | Vitamin D (D2 +D3) \| Cats: 1.43X if Vit D2 (MBW) | Vitamin D (dogs: D2 + D3; cats: D3) (MBW) |
| vitamin-d2, vitamin-d2-mbw | Vitamin D2 (ergocalciferol) \| Cats Only (MBW) | Vitamin D2 (ergocalciferol), cats only (MBW) |
| arginine, arginine-mbw | Arginine, Arg \| Also Enter Protein if NRC/FEDIAF (MBW) | Arginine, Arg (MBW) |
| calcium-large-breed-puppy | Calcium, Ca (NRC 4-14 Wk Dogs w/ Adult BW >25 kg ONLY) | Calcium, Ca (NRC puppies 4 to 14 weeks, expected adult weight over 25 kg) |
| vitamin-e, vitamin-e-mbw | Vitamin E, Alpha-tocopherol \| [PUFA] or fish oil may affect / [PUFA] may affect MBW | Vitamin E, Alpha-tocopherol (MBW) |

The copper and selenium MBW rows keep their names: they apply to foods of any moisture (notes
n250, n257). The conditions that replace the instructions: `vitamin-d-form-cats` and
`vitamin-d-form-cats-mbw` (enter D3 on the vitamin D row and D2 on the D2 row, whose minimum
is 1.43 times; never multiply an entry), `arginine-protein-not-entered` (NRC and FEDIAF, shown
when protein is not entered); vitamin E's was already `not-calculated-vitamin-e`. The single
moisture condition became four: `moisture-dry` and `moisture-wet` where the two rows' limits
differ under the requirement, `moisture-same` where they do not (with the alert that some
standards set different copper, selenium and taurine limits by moisture or format), and
`moisture-any` on the copper and selenium MBW rows.
