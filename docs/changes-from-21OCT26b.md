# Changes from template Version 21OCT26b

The steward approved this page's wording on 24 Oct 2026; the rules in section 1 are the
provisional steward's decisions, proposed, pending ratification.

The Dynamic Decile System template (the Google Sheet), Version 21OCT26b, is frozen and is to be
retired; this checker is its successor (steward, 21 to 23 Oct 2026). The parity check
([parity-21OCT26b.md](parity-21OCT26b.md)) shows that the code reproduces the template's
computation. This page lists where the checker now differs from the template, and why, so the
template's notes need not be read beside the checker's. The three differences approved at
parity (inputs outside the template's input rules, and two NRC cat items) are listed on the
parity page.

## Where the template's own text is kept

- [template-21OCT26b-notes.csv](template-21OCT26b-notes.csv): all 301 template notes word for
  word, as data version 21OCT26b.5 held them. A test (`tests/test_phase5.py`,
  `test_notes_against_the_template`) checks that a note's origin says "Adapted from" exactly
  when its text differs from this record.
- `tests/parity/data-21OCT26b/`: the frozen baseline (the requirement table, notes n001 to n168,
  energy and template figures), hash-checked and never edited.
- `tests/parity/export-21OCT26b/cells.json`: the released template's cell values.

## 1. Rules

From 23 Oct 2026 (rules 2 and 8 completed on 24 Oct 2026) the checker's own rules differ from
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

## 2. Notes (data versions 21OCT26b.6 and 21OCT26b.7)

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

The steward read n175, n192 and n183 in full and approved them (23 Oct 2026). On 24 Oct 2026 n181, n182, n183, n192, n214, n223, n224, n226, n227 and n238 changed to follow that day's decisions (rules 2, 4 and 8; data version 21OCT26b.7).

### Wording only

The other adapted notes changed in wording only, by the conventions above: n001, n002, n005, n007, n011, n013, n015, n017, n018, n019, n021, n022, n026, n028, n036, n037, n038, n039, n040, n041, n042, n043, n044, n045, n046, n047, n048, n050, n051, n052, n053, n054, n057, n058, n059, n060, n066, n069, n074, n078, n080, n081, n082, n083, n084, n086, n087, n088, n089, n090, n095, n096, n097, n099, n100, n101, n102, n103, n104, n105, n106, n111, n112, n122, n123, n127, n128, n131, n132, n133, n134, n135, n136, n137, n143, n144, n145, n152, n153, n154, n156, n158, n159, n160, n161, n162, n163, n170, n171, n172, n173, n177, n178, n179, n180, n187, n188, n189, n190, n191, n193, n195, n196, n197, n198, n199, n200, n201, n202, n205, n207, n209, n211, n213, n215, n216, n217, n218, n220, n221, n222, n231, n232, n233, n234, n235, n236, n237, n239, n240, n242, n244, n245, n246, n247, n248, n249, n250, n251, n252, n253, n254, n255, n256, n257, n258, n259, n260, n261, n262, n263, n264, n265, n266, n268, n269, n270, n271, n272, n273, n274, n275, n276, n277, n280, n281, n283, n288, n291, n293, n295, n297, n298, n299.
