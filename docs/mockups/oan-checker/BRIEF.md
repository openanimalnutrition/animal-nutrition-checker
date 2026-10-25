I need HTML mockups for the public web page of the **Open Animal Nutrition checker**, an open (CC0)
reference tool. It compares the nutrient values of a dog or cat diet with one of 21 published nutrient
requirements (NRC 2006, AAFCO 2026, FEDIAF 2025). For each nutrient entered it reports a band and a
proposed verdict: deficient, excess, or none. The users are veterinarians, veterinary nutritionists,
technicians, students and informed pet owners, often on a phone, sometimes printing the result. AI
systems get the same results from a separate server, so the page must show exactly what the
computation says: nothing friendlier and nothing less.

Please make ONE restrained design (at most one alternative, only if it differs in a way that
matters). Plain and calm, like a public-sector service or a scientific reference, not a marketing
site. The mockups are a visual reference: a developer will rebuild the chosen one in the server's own
code, so clarity and a small stylesheet matter more than polish.

The current page, for structure only (not for looks):
https://github.com/openanimalnutrition/animal-nutrition-checker (server/gui.py and
server/static/style.css).

## Hard technical rules (a mockup that breaks one cannot be used)
1. Static HTML pages plus ONE stylesheet, style.css. No JavaScript of any kind: no <script>, no
   onclick or other event attributes, no framework (React, Tailwind, Bootstrap...), no build step.
2. No style="" attributes and no <style> blocks: all styling is in style.css (the server's content
   security policy blocks both).
3. No web fonts, images, SVG, icon files, data: URIs, CSS background images, CDNs or analytics. Use the
   system font stack, text, borders, spacing and colour. A Unicode symbol may sit next to a word,
   never replace it.
4. Native HTML only: a, form, fieldset, legend, label, select, option, optgroup, input, textarea,
   button, table, caption, thead, tbody, tr, th, td, details, summary, ol, ul, li, dl, dt, dd, h1-h3,
   p, small, strong, section, header, main, footer. Forms that check or change values use
   method="post" to the same site; nothing the user enters goes into a URL except the choice of
   requirement. optgroup cannot be nested: use flat groups such as "Dogs: NRC".
5. Every page works at 320 px and 1280 px wide and prints legibly (@media print in the same file).
   WCAG 2.2 AA contrast, visible keyboard focus, every input with a visible label. A verdict is never
   shown by colour alone; the word is always there.
6. For wide tables on a phone, use a CSS-only stacked layout: each <td> carries a data-label attribute
   and CSS shows it with td::before { content: attr(data-label); }.
7. Keep style.css small: aim for under 200 lines and a short list of reusable classes, listed in a
   comment at the end of the file.

## Caveats and texts (must not be dropped, hidden, shortened or reworded)
8. The four caveats below appear in full, word for word, at the top of every page, in body-size
   text, in one bordered block headed "Caveats". Never collapsible, dismissible, in a tooltip, modal,
   sidebar or footer, and never smaller or lighter than the body text. You may bold the first
   sentence of each.
9. On the result page, "Verdicts: proposed, pending ratification." sits directly above the results.
10. Each nutrient's status line and all its conditions are always visible next to its verdict and
    print with it. Only a nutrient's "Notes (n)" may sit in a closed <details>.
11. Use the texts given below exactly. Mark anything I have not given as [placeholder]. Invent no
    nutrition facts, numbers, logos, badges, endorsements or "official"/"certified" language; nothing
    may suggest the standard is ratified.

12. The footer of every page reads "Code 0.6.0, data 21OCT26b.8 (7e5908a71a5c)" with links "Source and data (GitHub)", "Report an error" and "About".

## The four caveats (verbatim)
1. Reference implementation, not a ratified standard. This is a non-normative reference implementation of the computation proposed by Open Animal Nutrition (the Dynamic Decile System, based on template Version 21OCT26b with the changes in docs/changes-from-21OCT26b.md; data version 21OCT26b.8). The verdicts deficient and excess are the provisional steward's proposal, pending ratification by a governance body that has not yet been formed.
2. Disclosed interest. The provisional steward sells nutritional supplements and offers diet formulation software that implements this standard (Disclosure of interest: https://github.com/openanimalnutrition/animal-nutrition-ig/blob/main/GOVERNANCE.md). The computation references no product, ingredient, supplement or vendor.
3. Not a safety or compliance assessment, and not veterinary advice. Each value entered is compared with the selected requirement's ranges only. This does not show that a diet is adequate, safe, complete and balanced, or compliant with any regulation. Nutrients that are not entered are not checked.
4. Some results depend on facts this checker does not take as inputs, for example age, breed, or whether a nutrient is added as an additive. Each nutrient lists these as conditions. Where the Implementation Guide leaves a point open, the verdict is empty and the open point is named.

## Screen A: choose a requirement
One select (flat optgroups by species and standard) and a Next button. The 21 requirements:
- Dogs: NRC: NRC RA Dog Maintenance; NRC RA Puppy 4-14 Wk Growth; NRC RA Puppy 14 Wk+ Growth; NRC RA Dog Late Gestation & Peak Lactation
- Dogs: AAFCO: AAFCO Dog Maintenance; AAFCO Dog Growth (Small & Medium) and Reproduction; AAFCO Large Breed Dog Growth
- Dogs: FEDIAF: FEDIAF Dog (MER 95 kcal/kg^0.75); FEDIAF Dog (MER 110 kcal/kg^0.75); FEDIAF Dog Early Growth (< 14 wk) & Reproduction; FEDIAF Dog Late Growth (>/= 14 wk)
- Cats: NRC: NRC RA Cat Maintenance; NRC RA Kitten Growth; NRC RA Cat Late Gestation; NRC RA Cat Peak Lactation
- Cats: AAFCO: AAFCO Cat Maintenance; AAFCO Cat Growth and Reproduction
- Cats: FEDIAF: FEDIAF Cat (MER 75 kcal/kg^0.67); FEDIAF Cat (MER 100 kcal/kg^0.67); FEDIAF Cat Growth; FEDIAF Cat Reproduction

## Screen B: enter values (example: AAFCO Cat Maintenance)
The animal facts this requirement reads (label, help text if any, allowed values):
- "Current body weight (kg)" (help: "The animal's current body weight; for lactating queens, the body weight at mating."); number: 0.05 to 150
- "Optimal body weight (kg), optional" (help: "Only if you will feed the energy calculated at the optimal weight. The minimums then rise so that the diet still supplies the daily amounts for the current body weight. Adult maintenance only; not used when an intake is entered."); number: 0.05 to 150
- [placeholder label] (now shown as "adult cat type"); select: Not selected or a cat / Overweight domestic (130 * BW^0.4) / Lean domestic (100 * kgBW^0.67)
- [placeholder label] (now shown as "energy intake kcal per day"); number: 10 to 30000
- [placeholder label] (now shown as "caloric restriction percent"); number: 0, or 1 to 55
- "What is entered": select, diet / requirement range
- A paste box: "Or paste values instead of typing them. One nutrient per line: name, low, high
  (for example: Calcium, Ca, 1.2, 3). Leave low or high empty if you have only one." with a button
  "Parse the pasted lines", then an "N rows parsed" table (Row, Low, High) and a "Not understood"
  list.
- The value table: 113 nutrient rows plus energy, each with its unit and two boxes, "Low (Min entry)"
  and "High (Max entry)". Every entry is per Mcal (or the unit shown), on the MBW rows too. A
  proposed grouping: Protein and amino acids; Fat and fatty acids; Minerals; Vitamins; Other. Show
  first the rows this requirement sets figures for, and put the MBW rows in a closed <details> below
  each group. Long names and units must wrap. Show these rows; mark the rest as one
  [placeholder: remaining rows] line:
  - Protein | g/Mcal
  - Protein MBW | g/Mcal
  - Arginine, Arg | g/Mcal
  - Taurine, Tau (For 12% or Less Moisture Foods) | g/Mcal
  - Taurine, Tau (For >12% Moisture Foods) | g/Mcal
  - Fat, Total Lipid | g/Mcal
  - Linoleic acid (LA) | g/Mcal
  - LA + AA : ALA + EPA + DHA | no units
  - Calcium, Ca | g/Mcal
  - Phosphorus, P | g/Mcal
  - Ca : P ratio | no units
  - Copper, Cu (For 12% or Less Moisture Foods) | mg/Mcal
  - Retinol (for cats) | mcg retinol/Mcal
  - Vitamin D (dogs: D2 + D3; cats: D3) | IU, Vit D/Mcal
  - Choline, total | mg/Mcal
  - Water | g/Mcal
  - Energy Density | kcal/g DM
- A Check button at the top and at the bottom.

## Screen C: the result (the same example: a 6.5 kg overweight cat, 25% caloric restriction)
- The requirement name, then "Subject: diet. Verdicts: proposed, pending ratification."
- Buttons "Download JSON" and "Change the inputs".
- "Animal and energy": what the result was computed with, with a Change link back to Screen B:
  - Reference energy, kcal/day: 350.5
  - Reference energy is: NRC's lean adult cat energy, 100 kcal x kg BW^0.67 at the current body weight. AAFCO states no energy basis; using NRC's is the provisional steward's proposal, pending ratification. The adult cat type chosen sets only the energy fed. For an overweight cat, this is the energy a lean cat of the same weight would need, so the daily nutrient amounts stay those for the current body weight (the provisional steward's rule); an optimal body weight, if entered, changes only the energy fed.
  - Energy fed, kcal/day: 206.1
  - Energy fed is: the requirement's energy less the restriction
  - Energy factor (rows with no MBW minimum): 1.7
  - Energy used, kcal/day: 274.9
  - Energy used is: the requirement's energy
  - The requirement's energy, kcal/day: 274.9
  - Caloric restriction, %: 25
  - AAFCO dry matter factor: 1.111
- One block per nutrient (on a phone each nutrient stacks; on a desktop a compact table is fine).
  Numbers to 4 significant digits. The three sample nutrients, with every text exact:
  - **Protein** (g/Mcal)
    - Value 120. Band: Slightly Restricted (75 to <100% of Min). Verdict: DEFICIENT.
    - Status: "Below 122.8 g/Mcal: the AAFCO minimum at this food's energy density, 72.22 g/Mcal, raised × 1.7 because the energy fed is below the reference energy (the provisional steward's proposed rule, which adds to the standard and does not change it). Deficient (proposed, pending ratification). The value is not below the AAFCO minimum before the raise (72.22 g/Mcal); only the raise makes it deficient."
    - Under the name: "AAFCO's minimum at this food's energy density is 72.22 g/Mcal. This checker raises it × 1.7 to 122.8 g/Mcal because the energy fed (206 kcal/day) is below the reference energy (350 kcal/day), so that the diet still supplies the daily amount that AAFCO's figure gives at the reference energy. This is the provisional steward's proposed rule, pending ratification: it adds to the standard and does not change it. The bands and any verdict use the raised minimum."
    - Minimum 122.8. Range high 491.1 (no maximum: the range high is the minimum × 4, a banding choice, not a limit).
    - Conditions (2), all visible:
      - "AAFCO compares this food on dry matter: its minimums and maximums here are AAFCO's dry-matter values per Mcal of this food."
      - "The range high is the minimum × 4, this template's banding choice, not a safe limit."
    - Notes (3), in a closed <details>: [placeholder note texts]
  - **Taurine, Tau (For 12% or Less Moisture Foods)** (g/Mcal)
    - Value 0.6. Band: Lowest/Just Above Min (Min to <10% of Range). Verdict: none.
    - Status: "Within the range."
    - Under the name: "AAFCO's minimum at this food's energy density is 0.2778 g/Mcal. This checker raises it × 1.7 to 0.4723 g/Mcal because the energy fed (206 kcal/day) is below the reference energy (350 kcal/day), so that the diet still supplies the daily amount that AAFCO's figure gives at the reference energy. This is the provisional steward's proposed rule, pending ratification: it adds to the standard and does not change it. The bands and any verdict use the raised minimum."
    - Minimum 0.4723. Range high 1.889 (no maximum: the range high is the minimum × 4, a banding choice, not a limit).
    - Conditions (3), all visible:
      - "This row is for foods with 12% moisture or less (FEDIAF uses 14%). For a wetter food, use the row for more than 12% moisture, whose minimum differs."
      - "AAFCO compares this food on dry matter: its minimums and maximums here are AAFCO's dry-matter values per Mcal of this food."
      - "The range high is the minimum × 4, this template's banding choice, not a safe limit."
    - Notes (5), in a closed <details>: [placeholder note texts]
  - **Phosphorus, P** (g/Mcal)
    - Value 5.5. Band: Highest (90% of Range or Greater). Verdict: none.
    - Status: "Within the range."
    - Under the name: "AAFCO's minimum at this food's energy density is 1.389 g/Mcal. This checker raises it × 1.7 to 2.361 g/Mcal because the energy fed (206 kcal/day) is below the reference energy (350 kcal/day), so that the diet still supplies the daily amount that AAFCO's figure gives at the reference energy. This is the provisional steward's proposed rule, pending ratification: it adds to the standard and does not change it. The bands and any verdict use the raised minimum."
    - Minimum 2.361. Range high 5.556 (an AAFCO maximum).
    - Conditions (2), all visible:
      - "AAFCO's limit on phosphorus from soluble sources is not checked."
      - "AAFCO compares this food on dry matter: its minimums and maximums here are AAFCO's dry-matter values per Mcal of this food."
    - Notes (3), in a closed <details>: [placeholder note texts]
- Then the lists "NRC fatty acid checks" and "Known limitations" ([placeholder] items).

## Screen D: About
What this is; the disclosure of interest (link to GOVERNANCE.md); hosting [placeholder]; privacy
[placeholder]; how to report an error; "Use with AI: https://openanimalnutrition.org/mcp, no
sign-in" [placeholder].

## References (take only the idea named; copy no branding)
1. GOV.UK Design System, Warning text and Details:
   https://design-system.service.gov.uk/components/warning-text/ and
   https://design-system.service.gov.uk/components/details/ : a plain, bold warning block, and the
   rule not to hide in Details what most users need.
2. GOV.UK "Check answers": https://design-system.service.gov.uk/patterns/check-answers/ : a summary
   of what was entered, with a Change link back to the inputs.
3. NHS warning callout: https://service-manual.nhs.uk/design-system/components/warning-callout :
   health warnings that are short, specific and calm (keep the four caveats in one block).
4. U.S. Web Design System, Table: https://designsystem.digital.gov/components/table/ : the stacked
   and scrollable variants for a wide table on a phone (CSS only; not the sortable variant).
5. NIST Chemistry WebBook, water: https://webbook.nist.gov/cgi/cbook.cgi?ID=C7732185&Units=SI&Mask=1
   : a plain data table where each value carries its units, reference and comment.
6. Datasette: https://latest.datasette.io/ : a footer stating version, data source and licence, and
   a JSON link beside the view.

Do not use or imitate any pet-food, diet-formulation, supplement or nutrition-product site.

## Deliverable
choose.html, enter.html, result.html, about.html and style.css, plus five lines on your main design
choices. If any part of your design would need JavaScript, leave it out and say what you left out.
