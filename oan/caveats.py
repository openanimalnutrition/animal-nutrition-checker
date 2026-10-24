"""The Result's fixed texts: the caveats on every result, the status line of each entry, the
kinds of maximum, the text checks and the reasons in plain words.

The steward approved this wording on 22 Oct 2026, with four fixes the same day after an AI-read
test (other AI models read sample results as an AI user would). The steward approved the 23 Oct
drafts, the notice's pointer to the changes document and "this checker" for "this template" on
24 Oct 2026. Change it only with the steward's approval: a contract test fails if a caveat is
missing from any result. The conditions' texts are data (data/conditions.csv,
data/limitations.csv).
"""

TEMPLATE_VERSION = "21OCT26b"
GOVERNANCE_URL = ("https://github.com/openanimalnutrition/animal-nutrition-ig/blob/main/"
                  "GOVERNANCE.md")
VERDICT_STATUS = "proposed, pending ratification"

# On top of every result, in this order. {data_version} is filled in.
CAVEATS = (
    ("non_normative_reference",
     "Reference implementation, not a ratified standard. This is a non-normative reference "
     "implementation of the computation proposed by Open Animal Nutrition (the Dynamic Decile "
     "System, based on template Version " + TEMPLATE_VERSION + " with the changes in "
     "docs/changes-from-" + TEMPLATE_VERSION + ".md; data version {data_version}). The "
     "verdicts deficient and excess are the provisional steward's proposal, pending "
     "ratification by a governance body that has not yet been formed."),
    ("steward_disclosed_interest",
     "Disclosed interest. The provisional steward sells nutritional supplements and offers "
     "diet formulation software that implements this standard (Disclosure of interest: " +
     GOVERNANCE_URL + "). The computation references no product, ingredient, supplement or "
     "vendor."),
    ("not_a_safety_or_compliance_assessment",
     "Not a safety or compliance assessment, and not veterinary advice. Each value entered is "
     "compared with the selected requirement's ranges only. This does not show that a diet is "
     "adequate, safe, complete and balanced, or compliant with any regulation. Nutrients that "
     "are not entered are not checked."),
    ("conditions_and_open_points",
     "Some results depend on facts this checker does not take as inputs, for example age, "
     "breed, or whether a nutrient is added as an additive. Each nutrient lists these as "
     "conditions. Where the Implementation Guide leaves a point open, the verdict is empty and "
     "the open point is named."),
)


def caveats(data_version):
    return [{"id": cid, "text": text.replace("{data_version}", data_version)}
            for cid, text in CAVEATS]


def fill(text, values):
    """A text with each {key} replaced by its value."""
    for key, value in values.items():
        text = text.replace("{%s}" % key, value)
    return text


# The status line of one entry. {standard}, {kind}, {k} and {reason} are filled in.
STATUS = {
    "deficient": "Below the {standard} minimum for this requirement: deficient (proposed, "
                 "pending ratification).",
    "below-template-minimum": "Below a minimum this checker sets itself, not a standard's: "
                              "no verdict (Implementation Guide open point 6).",
    "below-aafco-open-minimum": "Below the AAFCO minimum as raised for this food's energy "
                                "density, which for this nutrient is not AAFCO's printed dry "
                                "matter value: no verdict (Implementation Guide open point 6).",
    "energy-below-estimate": "Below the estimated daily energy need, which is an estimate, not "
                             "a minimum requirement: no verdict (Implementation Guide open point "
                             "6).",
    "energy-restriction": "The caloric restriction raises the nutrient minimums; it does not "
                          "lower this energy estimate.",
    "energy-optimal-weight": "Feeding the energy at the optimal body weight raises the nutrient "
                             "minimums; it does not lower this estimate, which is for the "
                             "current body weight.",
    "within": "Within the range.",
    "excess": "Above {kind}: excess (proposed, pending ratification).",
    "above-conditional": "Above {kind}: conditional, not excess.",
    "above-template-set": "Above a range high this checker sets or computes: not excess.",
    "above-derived-provisional": "Above a range high derived from the minimum (the minimum × "
                                 "{k}), not a safe limit: not excess.",
    "also-above": "Also above {kind}.",
    "no-minimum": "No minimum for this requirement.",
    "no-range": "No range: this requirement sets no limit for this row.",
    "unavailable": "Not computed: {reason}",
    "below-zero-no-minimum": "Below zero on a row with no minimum: no verdict (Implementation "
                             "Guide open point 3).",
    # A standard's minimum that this checker raises (MINIMUM_RAISE_TEXT); {minimum}, {before},
    # {unit}, {factor}, {for_food} and {why} are filled in.
    "deficient-raised": "Below {minimum} {unit}: the {standard} minimum{for_food}, {before} "
                        "{unit}, raised{factor} {why} (the provisional steward's proposed rule, "
                        "which adds to the standard and does not change it). Deficient "
                        "(proposed, pending ratification).",
    "below-aafco-open-minimum-raised": "Below {minimum} {unit}: the AAFCO minimum as raised for "
                                       "this food's energy density, {before} {unit}, which for "
                                       "this nutrient is not AAFCO's printed dry matter value, "
                                       "raised{factor} {why} (the provisional steward's "
                                       "proposed rule, which adds to the standard and does not "
                                       "change it). No verdict (Implementation Guide open point "
                                       "6).",
    "raise-not-below-deficient": "The value is not below the {standard} minimum before the "
                                 "raise ({before} {unit}); only the raise makes it deficient.",
    "raise-not-below": "The value is not below the {standard} minimum before the raise "
                       "({before} {unit}).",
    "raise-also-below": "The value is also below the {standard} minimum before the raise "
                        "({before} {unit}).",
}

# A standard's minimum raised for a caloric restriction or by the energy factor
# (limits.Request.minimum_raise). The raise counts as the standard's part for the verdict
# (steward, 18 and 22 Oct 2026), but the minimum is never credited to the standard alone: the
# AI-read test of release 0.5.0 found "Below the AAFCO minimum" on a value 66% above AAFCO's
# own minimum (steward, 24 Oct 2026: the raise is a layer that adds to the standards).
# {standard}, {for_food}, {before}, {unit}, {factor}, {minimum}, {why} and {supplies} are
# filled in.
MINIMUM_RAISE_TEXT = ("{standard}'s minimum{for_food} is {before} {unit}. This checker raises "
                      "it{factor} to {minimum} {unit} {why}{supplies}. This is the provisional "
                      "steward's proposed rule, pending ratification: it adds to the standard "
                      "and does not change it. The bands and any verdict use the raised "
                      "minimum.")
RAISE_FOR_FOOD = " at this food's energy density"
RAISE_FACTOR = " × {factor}"
# The reason, short (in a status) and long (in MINIMUM_RAISE_TEXT); {restriction}, {fed} and
# {ref} are filled in.
RAISE_WHY = {
    "caloric-restriction": "for the caloric restriction of {restriction}%",
    "energy-fed-below-reference": "because the energy fed is below the reference energy",
}
RAISE_WHY_LONG = {
    "caloric-restriction": "for the caloric restriction of {restriction}%",
    "energy-fed-below-reference": "because the energy fed ({fed} kcal/day) is below the "
                                  "reference energy ({ref} kcal/day)",
}
RAISE_SUPPLIES = {
    "caloric-restriction": ", so that the diet still supplies the daily amount it would with no "
                           "restriction",
    "energy-fed-below-reference": ", so that the diet still supplies the daily amount that "
                                  "{standard}'s figure gives at the reference energy",
}

# A maximum's kind, by its type (the template's codes); AAFCO while the AAFCO dry matter factor
# is above 1 has its own text.
KINDS = {
    "SUL": "an NRC safe upper limit",
    "SUL>": "an NRC safe upper limit printed as a lower bound",
    "SULm": "an NRC safe upper limit per kg BW^0.75 or BW^0.67",
    "SULm>": "an NRC safe upper limit per kg BW^0.75 or BW^0.67",
    "PSM": "NRC's presumed safe maximum for choline",
    "AAFCO": "an AAFCO maximum",
    "N": "a FEDIAF nutritional maximum",
    "L": "a FEDIAF EU legal maximum, which applies only to amounts added as additives",
    "FSL": "a level a FEDIAF footnote states to be safe, not a maximum",
    "N*": "a FEDIAF maximum stated for growth, used beyond it",
    "SULm*": "an NRC safe upper limit stated only for NRC's reference kitten or queen",
}
AAFCO_CONDITIONAL_KIND = ("an AAFCO maximum, which stays per Mcal while AAFCO compares this "
                          "food on dry matter")

# NRC's fatty acid text checks: reported apart from the verdicts (IG open point 16).
CHECK_STATUS = "advice check, not a verdict (Implementation Guide open point 16)"
CHECKS = {
    ("la-ala-ratio", "outside"): "LA:ALA is outside NRC's advised ratio of {low}:1 to {high}:1.",
    ("epa-share-max", "above-maximum"): "EPA is above {x}% of EPA + DHA, NRC's advised maximum "
                                        "share.",
    ("epa-share-range", "outside"): "EPA is outside {low}% to {high}% of EPA + DHA, NRC's advised "
                                    "share.",
    ("epa-share-max-dha-only", "outside"): "EPA is not included, or is above {x}% of EPA + DHA.",
    ("epa-share-max-dha-only", "dha-below-minimum"): "DHA (EPA + DHA minus EPA) is below NRC's "
                                                     "EPA + DHA minimum for adult cats, which "
                                                     "NRC states as DHA.",
}
DHA_NOT_COMPARED = "DHA not compared: this requirement's data has no EPA + DHA minimum."
# A check that needs a nutrient not entered (outcomes.check_entry; steward, 24 Oct 2026: not
# counted as 0, as the template did). {missing} is filled in from CHECK_NAMES.
CHECK_NOT_ENTERED = {
    "la-ala-ratio": "Not checked: {missing} is not entered. Enter it to compare LA:ALA with "
                    "NRC's advised ratio.",
    "epa": "Not checked: {missing} is not entered. Enter it to compare EPA's share of EPA + "
           "DHA with NRC's advice.",
}
CHECK_NAMES = {"linoleic-acid": "LA", "alpha-linolenic-acid": "ALA", "epa": "EPA",
               "epa-dha": "EPA + DHA"}

# How the entries are read (check_diet's description, describe_inputs).
ENTRIES_TEXT = ("low and high are the Min and Max entries: for a diet, one value (placed by "
                "this checker's rule) or both ends of a range such as an analysed "
                "minimum and maximum; for a requirement range, its two ends. Each is described "
                "separately.")
ENERGY_ENTRY_TEXT = ("the energy the diet supplies, kcal per day; to replace the requirement's "
                     "energy with the animal's known intake, use "
                     "animal.energy_intake_kcal_per_day.")

# MBW rows: their limits are a requirement per kg of metabolic body weight a day, converted to
# per Mcal with the animal's energy and body weight; entries are per Mcal (steward, 22 Oct
# 2026: the template's column D label "g/kg BW^0.75" misread as the entry's unit).
MBW_TEXT = ("This row's requirement is per {mbw_unit} a day: {figures}, converted to {unit} at "
            "{energy} and a current body weight of {bw} kg. Enter the diet's {unit}.")
# MBW_TEXT's {energy}: named on a row with one limit (steward, 24 Oct 2026); kcal/day in these
# texts are whole numbers (steward, 24 Oct 2026).
MBW_ENERGY = "{kcal} kcal/day"
MBW_ENERGY_NAMED = "{name} ({kcal} kcal/day)"
MBW_MAXIMUM_ENERGY = "the reference energy"
# The minimum at the energy fed, the maximum at the reference energy (ENERGY_RULES_TEXT); the
# steward approved this wording on 24 Oct 2026.
MBW_TEXT_TWO_ENERGIES = ("This row's requirement is per {mbw_unit} a day: {figures}, converted "
                         "to {unit} at a current body weight of {bw} kg, the minimum at "
                         "{minimum_energy} ({minimum_kcal} kcal/day) and the maximum at the "
                         "reference energy ({ref} kcal/day). Enter the diet's {unit}.")
# The energy an MBW minimum is converted at (limits.MBW_NOT_RAISED: steward, 23 Oct 2026).
MBW_MINIMUM_ENERGY = {
    "fed": "the energy fed",
    "used": "the energy with no caloric restriction or optimal body weight applied, as fat per "
            "se is not essential",
}
MBW_ENTRY_TEXT = ("the diet's amount per Mcal, as on the per-Mcal row; the limits are the "
                  "requirement's per kg BW^0.75 (dogs) or BW^0.67 (cats) a day at the current "
                  "body weight, the minimum converted at the energy fed (fat's with no caloric "
                  "restriction or optimal body weight applied) and the maximum at the "
                  "reference energy.")

# The steward's energy rules (23 Oct 2026); the steward approved this wording on 23 Oct 2026,
# and the fat exception ("except fat's ... optimal body weight", decision D1) the same day.
# The adult-maintenance-only sentence ("Under adult maintenance ... raises them", decision D3)
# was approved the same day, with the steward's wording for growth, gestation and lactation
# ("fed more energy than it needs to keep its weight stable ..."). On 24 Oct 2026 the steward
# approved "(fat's and the ratios' excepted)" and the named exceptions to "Maximums do not
# change per Mcal" (choline, the large-breed puppy calcium row, carbohydrate), and, the same day
# after the AI-read test of release 0.5.0, when each of them applies.
ENERGY_RULES_TEXT = (
    "How energy sets the limits (the provisional steward's rules, proposed, pending "
    "ratification). The reference energy is the energy the standard's per-Mcal figures assume, "
    "at the current body weight. The energy fed is the intake entered, or else the "
    "requirement's energy (at the optimal body weight when that is used) less any caloric "
    "restriction. MBW minimums are converted to per Mcal at the energy fed, so the diet still "
    "supplies the daily amount per kg BW^0.75 (dogs) or BW^0.67 (cats), except fat's: fat per "
    "se is not essential, so neither fat row takes a restriction or an optimal body weight. "
    "Under adult maintenance requirements, on a row with no MBW minimum (fat's and the ratios' "
    "excepted), the per-Mcal minimum is multiplied by the energy factor, the reference energy "
    "divided by the energy fed (at least 1, and at least the restriction's factor); in growth, "
    "gestation and lactation, where "
    "the animal is fed more energy than it needs to keep its weight stable and the extra goes "
    "to growth, a pregnancy or milk, nutrient needs rise and fall with the energy fed: per-Mcal "
    "minimums hold at any intake and only a restriction raises them. Maximums do not change "
    "per Mcal, except three range highs this checker computes from a minimum, which follow it: "
    "the NRC dog choline maximum, only when 1.1 times the higher choline minimum (per Mcal or "
    "MBW) is above NRC's 500 mg/Mcal; the range high of NRC's large-breed puppy calcium row, "
    "only when that row's minimum is above NRC's 4.5 g/Mcal; and the carbohydrate maximum, "
    "where the standard sets none. MBW maximums are converted at the reference energy, and a "
    "ratio's computed range uses the minimums before any restriction or energy factor.")
# The reference energy's basis; the steward approved this wording on 24 Oct 2026. {figure},
# {exponent}, {species} and {who} are filled in.
REFERENCE_BASIS = {
    "NRC": "NRC's {who} energy, {figure} kcal x kg BW^{exponent} at the current body weight: "
           "the energy NRC's per-Mcal figures assume. The adult {species} type chosen sets only "
           "the energy fed.",
    "NRC-for-AAFCO": "NRC's {who} energy, {figure} kcal x kg BW^{exponent} at the current body "
                     "weight. AAFCO states no energy basis; using NRC's is the provisional "
                     "steward's proposal, pending ratification. The adult {species} type chosen "
                     "sets only the energy fed.",
    "FEDIAF": "FEDIAF's stated MER for this requirement, {figure} kcal x kg BW^{exponent} at the "
              "current body weight.",
    "life-stage": "The energy equation this checker uses for this requirement's life stage (the "
                  "energy row's; see the requirement's energy notes), at the current body "
                  "weight; an adult dog or cat type, if chosen, is not used.",
}
# The steward approved this wording on 24 Oct 2026 (also ENERGY_FED_FLOOR_TEXT), with
# "no-current-weight" added that day.
OPTIMAL_WEIGHT_STATUS = {
    "used": "Used: the energy fed is the requirement's energy at the optimal body weight (for "
            "NRC and AAFCO cats, NRC's lean equation), less any caloric restriction.",
    "not-adult": "Not used: an optimal body weight applies only to adult maintenance "
                 "requirements.",
    "intake-entered": "Not used: an intake is entered, and the intake is the energy fed.",
    "no-current-weight": "Not used: no current body weight is entered.",
    "not-below-current": "Not used: it is not below the current body weight.",
}
ENERGY_FED_FLOOR_TEXT = ("Not used: the energy fed would be {fed} kcal/day, below {floor}% of the "
                         "reference energy ({ref} kcal/day). Check the entry.")
# Labels and descriptions of animal facts (describe_inputs, the GUI). The steward approved the
# optimal body weight wording on 23 Oct 2026 and the current body weight wording on 24 Oct 2026.
FACT_TEXTS = {
    "body_weight_kg": ("Current body weight (kg)",
                       "The animal's current body weight; for lactating queens, the body "
                       "weight at mating."),
    "optimal_body_weight_kg": ("Optimal body weight (kg), optional",
                               "Only if you will feed the energy calculated at the optimal "
                               "weight. The minimums then rise so that the diet still supplies "
                               "the daily amounts for the current body weight. Adult "
                               "maintenance only; not used when an intake is entered."),
}

# A requirement that sets no maximum for a nutrient, on either basis (steward, 22 Oct 2026: AI
# readers brought in other standards' or life stages' limits from memory).
NO_MAXIMUM_TEXT = ("{requirement} sets no {nutrient} maximum{basis}; limits from other "
                   "standards or life stages do not apply to this check.")

# Reasons in plain words.
REASONS = {
    "requirement-needed": "Choose a requirement.",
    "body-weight-needed": "Enter the current body weight (for lactating queens, the body weight "
                          "at mating).",
    "adult-dog-type-needed": "Choose the type of adult dog.",
    "adult-cat-type-needed": "Choose the type of adult cat.",
    "mature-weight-needed": "Enter the expected mature body weight.",
    "mature-weight-below-body-weight": "The expected mature body weight must be at least the "
                                       "current body weight.",
    "life-stage-not-covered": "Choose a life stage this requirement covers.",
    "lactation-week-and-puppies-needed": "Enter the week of lactation and the number of puppies "
                                         "nursing.",
    "no-estimate-after-lactation-week-4": "NRC and FEDIAF give no energy estimate after week 4 "
                                          "of lactation: enter the intake (kcal per day).",
    "lactation-week-and-kittens-needed": "Enter the week of lactation and the number of kittens.",
    "calculation-needs-a-missing-minimum": "Not computed: the rule needs a limit this "
                                           "requirement does not set.",
    "rule-needs-a-number": "Not computed: the rule needs a limit this requirement does not set.",
}
