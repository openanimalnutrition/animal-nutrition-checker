# Open Animal Nutrition checker: page mockups (handoff, round 2)

Visual reference for rebuilding the public pages in `server/gui.py` and `server/static/style.css`.
The two design briefs are the authority for every text and rule; add them beside this file as
`BRIEF.md` (round 1) and `BRIEF-round2.md` (round 2). This file records what the mockups decided.

## Files
- `choose.html`, `enter.html`, `result.html`, `about.html`: static pages. Example request: AAFCO Cat Maintenance
  (`aafco-cat-adult`), 6.5 kg, overweight domestic, 25% caloric restriction; Protein 120, Taurine (12% or less
  moisture) 0.6, Phosphorus 5.5, Energy Density 3.6, Linoleic acid (LA) 2, Calcium 1.2 to 3.
- `result-variants.html`: mockup only, not a route. It places result lines this example does not produce, each
  taken from the request named above it. Text in `[mockup note: …]` is not page content.
- `style.css`: the whole stylesheet (179 lines; class list in the comment at the end).
- Not here on purpose: the canvas `.dc.html` files (they wrap the same markup in the canvas's own runtime script).

## Routes: static mockup and server
| What | Mockup | Server |
|---|---|---|
| Screen A | `choose.html` | `GET /` |
| Screen B | `enter.html?requirement=<id>` | `GET /?requirement=<id>` |
| Parse the pasted lines | `formaction="enter.html"` | `POST /parse` |
| Check (Screen C) | `action="result.html"` | `POST /check` |
| Download JSON | `formaction="check.json"` (no local target) | `POST /check.json` |
| Change, Change the inputs | `action="enter.html"` | `POST /edit` |
| About (Screen D) | `about.html` | `GET /about` (new route) |
| Stylesheet | `style.css` | `/static/style.css` |

The site name links to Screen A. "Report an error" points at `about.html#report`, a placeholder target.

## What changed in round 2
- **Screen A:** option values are the requirement ids; the empty first option reads "Choose a requirement".
  `required` was removed so the server, not the browser, rejects an empty choice.
- **Screen B:** every value and animal box is `type="text" inputmode="decimal"` with no `min`, `max` or `step`.
  Field names are only `requirement`, `subject`, `paste`, `animal.<fact>`, `low.<row id>`, `high.<row id>`.
  Buttons carry no `name` or `value`: Check is a plain submit and the form's first submit button; Parse has only
  `formaction`. The example request is filled in, and the parse report shows its 6 rows.
- **Screen C, Animal and energy:** every animal fact used, then the energy lines, then the paragraph
  "How energy sets the limits (…)" in full, always visible (its first sentence in bold).
- **Screen C, Input report:** new section between Animal and energy and Results.
- **Screen C, each nutrient** (`section.nutrient`):
  - `<header>` holds the name and every text under it, in this order: the raise text, the no-maximum text, the MBW
    text, the "also checked on its per-Mcal row" text.
  - Then one `dl.summary`: Minimum, Minimum for a verdict (only when it differs), Range high, then Value (or Low,
    then High), each followed by its own indented (`dt class="sub"`) Band, Verdict and Status, then Conditions (n).
  - A verdict left open (Linoleic acid): Verdict reads "none" and the Status names the open point. No other marker.
  - Each condition ends with "(limitation n)", linked to `#limitation-n` in Known limitations.
  - Notes: closed `<details>` holding a `<dl>`: `dt` = note id in `<strong>` plus its origin in parentheses, `dd` = the text.
  - When limits cannot be computed, the Minimum shows the reason and the Status reads "Not computed: …" (see variants).
- **Screen C, sections:** NRC fatty acid checks are left out when there are none (their form is on
  `result-variants.html`: text, then "Status: …", then "Caveat: …" when there is one). Known limitations is a
  `ul.plain`; each `li` has `id="limitation-n"` and its text carries its own number.
- **Screen C, buttons:** one form (`id="inputs"`) holds the entered values as hidden inputs, named as on Screen B.
  Download JSON (`formaction`) and Change the inputs submit it; the Animal and energy "Change" button sits outside it
  and uses `form="inputs"`, so the values appear once. Only entered fields are carried; empty ones are omitted.
- **style.css:** input widths no longer depend on `type="number"`; new classes `sub` and `plain`; the nutrient
  grid places its `<header>` in the left column; a `:target` highlight for the limitation links; note list spacing.

## Structure the server must keep
- Caveats block: `<section class="caveats">` right after the site header, before `<main>`, on every page, word for word.
- Screen A: `GET`; the requirement is the only user choice that goes into a URL.
- Screen B: one `POST` form, Check first; Parse is a second submit in the same form, so typed values survive a parse.
- Value tables: one table per group; MBW rows in a closed `<details>` under their group. Every `<td>` has
  `data-label`. Each input is named by `aria-labelledby="r-<row id> <column th id>"` and described by its unit
  cell (`aria-describedby="u-<row id>"`); ids must be unique per page.
- Screen C: "Verdicts: proposed, pending ratification." directly above the first nutrient. Verdict, Status and
  Conditions always visible in each nutrient's `dl.summary`; only Notes are in `<details>`.
- Verdicts: `<strong class="verdict deficient">DEFICIENT</strong>`, same with `excess`; "none" is plain text.
- No `div`, `span`, `style`, `script` or event attributes anywhere.

## Already checked (round 2)
- Element list, no `style=`/`<style>`/`<script>`/`on…`, `data-label` on every `<td>`, caveats identical on all five
  pages, field names only from the allowed set, no button with `name` or `value`, no `type="number"`/`min`/`max`/`step`,
  every `aria-labelledby`, `aria-describedby` and `#` link target exists, ids unique.
- Clicked through from local files in Chromium: Next, Parse, Check, Change, Change the inputs. No sideways
  scrolling at 320 px or 1280 px on any page.
- Not checked: Safari, Firefox, a screen reader, automated contrast testing.

## Still open
1. For the steward: the hint on Screen A; labels of the facts that have none yet; About (what this is, hosting,
   privacy, how to report an error, the "Use with AI" line); where "Report an error" links; the wording for an empty input report.
2. Adult cat type list: the mockup shows an empty first option, then "Not selected or a cat", "Overweight domestic
   (130 * BW^0.4)" and "Lean domestic (100 * kgBW^0.67)", each with its text as its value. If "Not selected or a cat"
   is the text of the empty option, merge the two. The empty option's text is blank in the mockup.
3. Energy Density's own result block (the sixth entry) was not given; `result.html` has a placeholder line for it.
4. Nutrient order on Screen C follows the Screen B groups; use the server's order.
5. `/edit` receives only the fields that were entered; confirm that is what it expects.
6. Later round (round 2, section 5): the grouping of all 113 rows, the missing fact labels and a dog example.

## Steward decisions (25 Oct 2026)
Recorded after the developer checked round 2 against the server: both mockup forms (Screen B, and Screen C's
hidden inputs) were read by the server's own form reader and each rebuilt the example request exactly, and every
checker text for the example appears word for word except the Energy Density block (open item 3).
- Accepted as designed: limits before the value in each nutrient block, with Band, Verdict and Status under each
  value; "(limitation n)" linked to Known limitations; the hidden inputs once, with `form="inputs"`; no `required`
  on Screen A; `result-variants.html` kept as a mockup page (not a route).
- Open item 2, merged: in the adult cat type list the first option has the value "" and the text "Not selected or
  a cat"; the two cat types follow. The adult dog type list does the same with its own first item, "Not selected or
  a dog". Both texts are the template's, verbatim. The server treats a blank choice and that item the same ("Choose
  the type of adult cat." or "... dog."), so no result changes.
- Open item 3: the rebuild renders the Energy Density block from the checker like any other nutrient.
- Open item 4: the server's order.
- Open item 5: confirmed; `/edit` and `/check` read only the fields sent.
- Open items 1 and 6 stay for a later round.
