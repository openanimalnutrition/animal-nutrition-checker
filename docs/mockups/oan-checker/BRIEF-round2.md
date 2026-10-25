# Round 2: revise the checker mockups

Thank you for the mockups and HANDOFF.md. The developer compared them with the server code and ran
your example through the checker. The design is the direction: keep its look, its structure, the
stylesheet approach and everything HANDOFF.md says the server must keep. Nothing in the markup
conflicts with the server's content security policy, the four caveats match the code word for
word, and your Screen C numbers are exactly what the checker computes once energy density
3.6 kcal/g DM is entered.

This round adds what the result page must also show, aligns the form with what the server
accepts, and settles your five open decisions. Every hard rule and text rule of the original
brief still applies. Every quoted text and number below is the checker's own output for the
request stated: use it exactly, and mark anything not given here as [placeholder].

## 1. The request behind the example (two nutrients added)
- Requirement: AAFCO Cat Maintenance (id aafco-cat-adult).
- Animal: Current body weight (kg) 6.5; [placeholder label: adult cat type] Overweight domestic (130 * BW^0.4); [placeholder label: caloric restriction percent] 25.
- Entries: Protein 120; Taurine, Tau (For 12% or Less Moisture Foods) 0.6; Phosphorus, P 5.5; Energy Density 3.6; Linoleic acid (LA) 2; Calcium, Ca low 1.2, high 3.
- Show these values filled in on Screen B (this settles your open decision 4) and the two new nutrients on Screen C. Each single value is in its row's Low box.

## 2. Screen B: what the server accepts
- Value and animal boxes: type="text" inputmode="decimal", with no min, max or step. A browser
  empties a number box whose value is not a valid number, so a value the server shows again after
  Parse or Change would drop out unchecked without a word; the checker must be the one that
  rejects a value, with its reason. Keep the "Allowed values" lines as text.
- Field names, exactly: requirement; subject; paste; animal.<fact>; low.<row id>; high.<row id>.
  The server rejects any other name, so the buttons carry no name or value: Check is a plain
  submit, and Parse keeps only its formaction. Keep Check as the form's first submit button.
- The animal fields of this requirement: animal.body_weight_kg (Current body weight (kg)); animal.optimal_body_weight_kg (Optimal body weight (kg), optional); animal.adult_cat_type ([placeholder label: adult cat type]); animal.energy_intake_kcal_per_day ([placeholder label: energy intake kcal per day]); animal.caloric_restriction_percent ([placeholder label: caloric restriction percent]).
- Row ids of the sample rows: Protein = protein; Protein MBW = protein-mbw; Arginine, Arg = arginine; Taurine, Tau (For 12% or Less Moisture Foods) = taurine; Taurine, Tau (For >12% Moisture Foods) = taurine-wet; Fat, Total Lipid = fat; Linoleic acid (LA) = linoleic-acid; LA + AA : ALA + EPA + DHA = la-aa-to-ala-epa-dha-ratio; Calcium, Ca = calcium; Phosphorus, P = phosphorus; Ca : P ratio = ca-p-ratio; Copper, Cu (For 12% or Less Moisture Foods) = copper; Retinol (for cats) = retinol; Vitamin D (dogs: D2 + D3; cats: D3) = vitamin-d; Choline, total = choline; Water = water; Energy Density = energy-density.
- Requirement option values are the ids: NRC RA Dog Maintenance = nrc-dog-adult; AAFCO Dog Maintenance = aafco-dog-adult; FEDIAF Dog (MER 95 kcal/kg^0.75) = fediaf-dog-adult-mer95; FEDIAF Dog (MER 110 kcal/kg^0.75) = fediaf-dog-adult-mer110; NRC RA Cat Maintenance = nrc-cat-adult; AAFCO Cat Maintenance = aafco-cat-adult; FEDIAF Cat (MER 75 kcal/kg^0.67) = fediaf-cat-adult-mer75; FEDIAF Cat (MER 100 kcal/kg^0.67) = fediaf-cat-adult-mer100; NRC RA Puppy 4-14 Wk Growth = nrc-puppy-4-14-wk; NRC RA Puppy 14 Wk+ Growth = nrc-puppy-14-wk-plus; AAFCO Dog Growth (Small & Medium) and Reproduction = aafco-dog-growth-reproduction; AAFCO Large Breed Dog Growth = aafco-dog-growth-large-breed; FEDIAF Dog Early Growth (< 14 wk) & Reproduction = fediaf-dog-early-growth-reproduction; FEDIAF Dog Late Growth (>/= 14 wk) = fediaf-dog-late-growth; NRC RA Kitten Growth = nrc-kitten; AAFCO Cat Growth and Reproduction = aafco-cat-growth-reproduction; FEDIAF Cat Growth = fediaf-cat-growth; NRC RA Dog Late Gestation & Peak Lactation = nrc-dog-gestation-lactation; NRC RA Cat Late Gestation = nrc-cat-late-gestation; NRC RA Cat Peak Lactation = nrc-cat-peak-lactation; FEDIAF Cat Reproduction = fediaf-cat-reproduction.
- The first, empty requirement option reads "Choose a requirement" (the server's text).
- "What is entered" option values: "diet" / "requirement range" (exactly, with the space).
- A list such as the adult cat type: an empty first option, then each option with its text as its value (for example value="Overweight domestic (130 * BW^0.4)").
- Keep your static click-through (actions pointing at the .html files) and record the real
  routes in HANDOFF.md: GET / (Screen A; Screen B with ?requirement=<id>), POST /parse,
  POST /check (Screen C), POST /check.json (Download JSON), POST /edit (Change and Change the
  inputs), GET /about (Screen D, a new route). The stylesheet is served at /static/style.css.

## 3. Screen C: what the page shows today and the mockup has no place for
The page must show exactly what the computation says, nothing less. Keep each item below; you decide only where it goes and how it looks.

### a. More texts under a nutrient's name
After the raise text, when the requirement sets no maximum for the row, the page shows that. In this example:
- Protein: "AAFCO Cat Maintenance sets no protein maximum, per Mcal; limits from other standards or life stages do not apply to this check."
- Taurine, Tau (For 12% or Less Moisture Foods): "AAFCO Cat Maintenance sets no taurine maximum, per Mcal; limits from other standards or life stages do not apply to this check."
- Linoleic acid (LA): "AAFCO Cat Maintenance sets no linoleic acid (LA) maximum, per Mcal; limits from other standards or life stages do not apply to this check."
- Calcium, Ca: "AAFCO Cat Maintenance sets no calcium maximum, per Mcal; limits from other standards or life stages do not apply to this check."
Other requests put up to three more texts there. From NRC RA Cat Maintenance, a 4 kg lean cat, Protein and Protein MBW both entered as 60:
- On an MBW row: "This row's requirement is per kg BW^0.67 a day: minimum 4.96 g/kg BW^0.67 (49.6 g/Mcal), converted to g/Mcal at the energy fed (253 kcal/day) and a current body weight of 4 kg. Enter the diet's g/Mcal."
- On each of the two rows: "This nutrient is also checked on its per-Mcal row (protein): no verdict. The more protective of the two rows applies."
- When a row's limits cannot be computed (the same request without the adult cat type), the Minimum shows the reason instead of a number, "Choose the type of adult cat.", and the status reads "Not computed: Choose the type of adult cat."
- When the minimum for a verdict differs from the minimum, the block shows it too, labelled "Minimum for a verdict" (the current page's label).

### b. A verdict left open (your open decision 3): Linoleic acid (LA)
- Value 2. Band: Slightly Restricted (75 to <100% of Min). Verdict: none.
- Status: "Below 2.645 g/Mcal: the AAFCO minimum as raised for this food's energy density, 1.556 g/Mcal, which for this nutrient is not AAFCO's printed dry matter value, raised × 1.7 because the energy fed is below the reference energy (the provisional steward's proposed rule, which adds to the standard and does not change it). No verdict (Implementation Guide open point 6). The value is not below the AAFCO minimum before the raise (1.556 g/Mcal)."
- Under the name: "AAFCO's minimum at this food's energy density is 1.556 g/Mcal. This checker raises it × 1.7 to 2.645 g/Mcal because the energy fed (206 kcal/day) is below the reference energy (350 kcal/day), so that the diet still supplies the daily amount that AAFCO's figure gives at the reference energy. This is the provisional steward's proposed rule, pending ratification: it adds to the standard and does not change it. The bands and any verdict use the raised minimum."
- Minimum 2.645. Range high 10.58 (no maximum: the range high is the minimum × 4, a banding choice, not a limit).
- Conditions (2), all visible:
  - "AAFCO compares this food on dry matter: its minimums and maximums here are AAFCO's dry-matter values per Mcal of this food." (limitation 8)
  - "The range high is the minimum × 4, this template's banding choice, not a safe limit." (limitation 10)
- Notes (3), in a closed <details>.
- Markup: the Verdict reads "none", exactly as on every entry without a verdict, and the Status beside it names the open point. Add no other wording or marker.

### c. A range entered (low and high): Calcium, Ca
Two values, each with its own band, verdict and status; show both in the one block ("Low" and "High").
- Low: value 1.2. Band: Severely Restricted (25 to <50% of Min). Verdict: DEFICIENT.
  Status: "Below 2.834 g/Mcal: the AAFCO minimum at this food's energy density, 1.667 g/Mcal, raised × 1.7 because the energy fed is below the reference energy (the provisional steward's proposed rule, which adds to the standard and does not change it). Deficient (proposed, pending ratification). The value is also below the AAFCO minimum before the raise (1.667 g/Mcal)."
- High: value 3. Band: Lowest/Just Above Min (Min to <10% of Range). Verdict: none.
  Status: "Within the range."
- Under the name: "AAFCO's minimum at this food's energy density is 1.667 g/Mcal. This checker raises it × 1.7 to 2.834 g/Mcal because the energy fed (206 kcal/day) is below the reference energy (350 kcal/day), so that the diet still supplies the daily amount that AAFCO's figure gives at the reference energy. This is the provisional steward's proposed rule, pending ratification: it adds to the standard and does not change it. The bands and any verdict use the raised minimum."
- Minimum 2.834. Range high 11.33 (no maximum: the range high is the minimum × 4, a banding choice, not a limit).
- Conditions (2), all visible:
  - "AAFCO compares this food on dry matter: its minimums and maximums here are AAFCO's dry-matter values per Mcal of this food." (limitation 8)
  - "The range high is the minimum × 4, this template's banding choice, not a safe limit." (limitation 10)
- Notes (3), in a closed <details>.

### d. Animal and energy (your open decision 1: keep, for every fact)
List every animal fact the result was computed with, then the energy lines as in your mockup. Here:
- Current body weight (kg): 6.5
- [placeholder label: adult cat type]: Overweight domestic (130 * BW^0.4)
- [placeholder label: caloric restriction percent]: 25
Then, visible and in full, this paragraph:
"How energy sets the limits (the provisional steward's rules, proposed, pending ratification). The reference energy is the energy the standard's per-Mcal figures assume, at the current body weight. The energy fed is the intake entered, or else the requirement's energy (at the optimal body weight when that is used) less any caloric restriction. MBW minimums are converted to per Mcal at the energy fed, so the diet still supplies the daily amount per kg BW^0.75 (dogs) or BW^0.67 (cats), except fat's: fat per se is not essential, so neither fat row takes a restriction or an optimal body weight. Under adult maintenance requirements, on a row with no MBW minimum (fat's and the ratios' excepted), the per-Mcal minimum is multiplied by the energy factor, the reference energy divided by the energy fed (at least 1, and at least the restriction's factor); in growth, gestation and lactation, where the animal is fed more energy than it needs to keep its weight stable and the extra goes to growth, a pregnancy or milk, nutrient needs rise and fall with the energy fed: per-Mcal minimums hold at any intake and only a restriction raises them. Maximums do not change per Mcal, except three range highs this checker computes from a minimum, which follow it: the NRC dog choline maximum, only when 1.1 times the higher choline minimum (per Mcal or MBW) is above NRC's 500 mg/Mcal; the range high of NRC's large-breed puppy calcium row, only when that row's minimum is above NRC's 4.5 g/Mcal; and the carbohydrate maximum, where the standard sets none. MBW maximums are converted at the reference energy, and a ratio's computed range uses the minimums before any restriction or energy factor."
Other requests add a line here:
- When the energy cannot be computed: "Energy: Choose the type of adult cat."
- When an optimal body weight is entered: "Optimal body weight: Not used: an intake is entered, and the intake is the energy fed." (here: an intake is also entered)

### e. Input report
A short visible section after Animal and energy, before the results: each input that was not used or is missing, with its label and the checker's reason. Nothing is listed in this example: [placeholder: wording when every input was used]. From other requests:
- [placeholder label: caloric restriction percent]: "Not used: outside 1 to 55 (or 0 for none)."
- Current body weight (kg): "Not used: outside 0.05 to 150."

### f. Notes
Each note shows its id and origin, then its text. Protein's three notes, exactly; keep the other nutrients' notes as [placeholder note texts]:
- n196 (Adapted from DDS template Version 21OCT26b, Standards tab B12 (docs/changes-from-21OCT26b.md)): "FEDIAF Sept. 2025 values apply to foods made from ingredients with normal digestibility (at least 70% dry matter and 80% protein digestibility) and average bioavailability (page 10), and FEDIAF's protein levels take into account an apparent crude protein digestibility of 80% (pages 22 and 27). If a protein digestibility of at least 80% cannot be guaranteed, FEDIAF recommends increasing the essential amino acid levels by a minimum of 10% (page 13); this checker makes no such increase, so in that case compare the amino acid rows with their FEDIAF mins times 1.1. If formulating below FEDIAF's recommended minimum for total protein (adult dogs), FEDIAF states that it is particularly important to ensure that the amino acid profile meets its guidelines for adult maintenance (page 22). For bitches, FEDIAF's reproduction protein recommendation assumes the diet contains some carbohydrate, to decrease the risk of hypoglycemia in the bitch and neonatal mortality; if carbohydrate is absent or at a very low level, the protein requirement is much higher and may be double (page 22). No adjustment is made here for this (see note n288 on the carbohydrate default)."
- n299 (Adapted from DDS template Version 21OCT26b, Standards tab C130 (docs/changes-from-21OCT26b.md)): "Set at 3.5 kcal/g dry matter (DM) based on the lowest historical threshold in some regulatory guidelines (pre-2016 AAFCO Official Publications (dog profiles)) to switch to using requirements on a dry matter basis instead of an energy basis when a food's energy density is below this value. It is this checker's own minimum, not an energy density requirement of the 2006 NRC, 2026 AAFCO, or FEDIAF Sept. 2025, and neither is this row's fixed 6 kcal/g DM range high (see note n301). The 2026 AAFCO dog and cat profiles presume 4000 kcal ME/kg DM (4 kcal/g DM) and state that "formulations less than 4000 kcal ME/kg should not be corrected for energy" (Footnote a on pages 164 and 175; page 183 states the same rule), so AAFCO compares such foods, whatever their moisture, with its dry matter values without energy correction. This checker compares every food per Mcal, which matches the 2006 NRC (page 355) and FEDIAF Sept. 2025 (page 13), as both correct for any energy density. To apply AAFCO's rule under an AAFCO requirement, when the energy density entered (this row's low entry) is above 0 and below 4 kcal/g DM, each min that a caloric restriction raises, and the fat min, is multiplied by 4 divided by that energy density (the AAFCO dry matter factor; see note n180), together with any caloric restriction factor. This equals AAFCO's dry matter comparison to within the rounding between its dry matter and per 1,000 kcal tables: e.g., at 3.6 kcal/g DM the 65 g/Mcal adult cat protein min becomes 72.2 g/Mcal, which is 26% protein in DM. The exception is 7 values that AAFCO prints differently in its two tables (for cats, valine for growth and reproduction, and linoleic acid; for dogs, EPA + DHA, sodium, chloride and selenium for growth and reproduction, and selenium for adult maintenance): for these the factored min corresponds to a dry matter value other than the one AAFCO prints, so a food can meet it here and not AAFCO's dry matter value, or the reverse (see notes n060, n080, n081, n089, n090, n111, n112, n122, n123, n131, n135, n132, n136, n133 and n137). The maximums stay per Mcal, this checker's cautious choice, as an animal eating a less energy-dense food to its energy needs takes in the per Mcal amount; so such a food at an AAFCO dry matter maximum can read above the per Mcal maximum here. Nothing is adjusted when no energy density is entered or it is 4 or more, or under an NRC or FEDIAF requirement. AAFCO adds that formulations of low energy density should not be considered adequate for reproductive needs (dogs) or for growth or reproductive needs (cats) based on comparison to the profiles alone (Footnote a on pages 164 and 175). For reference, the 2026 AAFCO (page 167) states that before the 2016 revisions to its profiles the presumed caloric density for dog foods was 3500 kcal ME/kg DM for nutrient concentrations per kg DM."
- n171 (Adapted from DDS template Version 21OCT26b, Standards tab K1 (docs/changes-from-21OCT26b.md)): "Each row has a multiplier that derives the range high from the min when there is no SUL or max: 4, unless the row's notes give another factor. A range high derived this way (the min times the multiplier) is this checker's banding device, not a max or a safe upper limit (code K in note n027; the Open Animal Nutrition FHIR IG calls it derived-provisional and never calls a value above it excess). That a standard sets no max does not mean that higher intakes are safe: the 2026 AAFCO (page 163) states that the absence of a maximum concentration should not be interpreted to mean that nutrients without a specific maximum content are safe at any concentration, as it reflects the lack of information in dogs and cats on toxic concentrations of that nutrient, and the 2006 NRC (page 354) states that SUL values are not available for many required nutrients, especially minerals and vitamins. For potassium, the 2026 AAFCO (page 170) did not establish a maximum for dogs because potential toxicosis of potassium was not a practical concern. A value above such a range high falls in the top band (range-d10), as does a value from 90% of the range up to it; neither description shows the value to be safe or excessive."

### g. NRC fatty acid checks
Each check shows its text, its status and, when it has one, its caveat (for example: "DHA not compared: this requirement's data has no EPA + DHA minimum."). This AAFCO example has none, so leave the section out when there are none. From an NRC dog request:
- "LA:ALA is outside NRC's advised ratio of 2.6:1 to 26:1." Status: "advice check, not a verdict (Implementation Guide open point 16)"
- "EPA is outside 50% to 60% of EPA + DHA, NRC's advised share." Status: "advice check, not a verdict (Implementation Guide open point 16)"

### h. Limitation numbers on conditions
The page ends a condition with the number of the known limitation it belongs to. The three nutrients of your first round, exactly:
- Protein: "AAFCO compares this food on dry matter: its minimums and maximums here are AAFCO's dry-matter values per Mcal of this food." (limitation 8); "The range high is the minimum × 4, this template's banding choice, not a safe limit." (limitation 10)
- Taurine, Tau (For 12% or Less Moisture Foods): "This row is for foods with 12% moisture or less (FEDIAF uses 14%). For a wetter food, use the row for more than 12% moisture, whose minimum differs." (limitation 7); "AAFCO compares this food on dry matter: its minimums and maximums here are AAFCO's dry-matter values per Mcal of this food." (limitation 8); "The range high is the minimum × 4, this template's banding choice, not a safe limit." (limitation 10)
- Phosphorus, P: "AAFCO's limit on phosphorus from soluble sources is not checked." (limitation 4); "AAFCO compares this food on dry matter: its minimums and maximums here are AAFCO's dry-matter values per Mcal of this food." (limitation 8)

### i. Known limitations, exactly (this example)
- "4. Sources: iron added as oxide or carbonate and copper added as oxide should not be counted toward the mins (notes n246 and n248); limits on added selenium and on phosphorus from soluble sources (cats) are not checked (notes n255 and n235)."
- "7. Moisture: foods with more than 12% moisture count as wet, a lower cut than FEDIAF's 14% (note n209); FEDIAF's wet-diet selenium values per kg BW^0.75 (dogs) or BW^0.67 (cats) are not used (note n257)."
- "8. Energy density: under an AAFCO requirement, a food below 4 kcal/g DM is compared with AAFCO's dry matter minimums and maximums only when its energy density is entered; without it, AAFCO's per Mcal values are used (note n299)."
- "10. This checker's own choices where the standards give no value: range highs derived from the min (notes n171 and n241), the carbohydrate default min (note n288), the energy density range (note n299), the energy estimates for the AAFCO requirements (note n029) and the folate DFE conversion (note n278)."

## 4. Your open decisions
1. Keep, and list every fact used (3d), not only two.
2. Accepted as you wrote them: "Allowed values: ...", the headings "Values" and "Results", and
   the Requirement row with its Change link.
3. As in 3b.
4. Settled by section 1.
5. Filled by sections 2 and 3 wherever the server has a value. These stay placeholders, for the
   steward later: the hint on Screen A; the labels of the facts that have none yet; About (what
   this is, hosting, privacy, how to report an error, the "Use with AI" line); where "Report an
   error" links; the wording for an empty input report.

## 5. Not in this round
The grouping of all 113 rows, the missing fact labels and a dog example come in a later round.

## Deliverable
Updated choose.html, enter.html, result.html, about.html and style.css (still under 200 lines),
and HANDOFF.md updated: what changed in this round, the structure the server must keep, and what
is still open. One zip. Re-run your checks: the element list, no style or script, a data-label on
every td, the caveats identical on every page.
