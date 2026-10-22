"""The Result's fixed texts: the caveats on every result, the status line of each entry, the
kinds of maximum, the text checks and the reasons in plain words.

The steward approved this wording on 22 Oct 2026 (ig-build caveat-wording-draft-20261022.md;
sean-answers, "Code phase 5"), with four fixes after the AI-read test the same day
(sean-answers, "Code phase 5: wording fixes after the AI-read test"). Change it only with the steward's approval: a contract test
fails if a caveat is missing from any result. The conditions' texts are data
(data/conditions.csv, data/limitations.csv).
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
     "System, template Version " + TEMPLATE_VERSION + "; data version {data_version}). The "
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


# The status line of one entry. {standard}, {kind}, {k} and {reason} are filled in.
STATUS = {
    "deficient": "Below the {standard} minimum for this requirement: deficient (proposed, "
                 "pending ratification).",
    "below-template-minimum": "Below a minimum this template sets itself, not a standard's: "
                              "no verdict (Implementation Guide open point 6).",
    "below-aafco-open-minimum": "Below the AAFCO minimum as raised for this food's energy "
                                "density, which for this nutrient is not AAFCO's printed dry "
                                "matter value: no verdict (Implementation Guide open point 6).",
    "energy-below-estimate": "Below the estimated daily energy need, which is an estimate, not "
                             "a minimum requirement: no verdict (Implementation Guide open point "
                             "6).",
    "energy-restriction": "The caloric restriction raises the nutrient minimums; it does not "
                          "lower this energy estimate.",
    "within": "Within the range.",
    "excess": "Above {kind}: excess (proposed, pending ratification).",
    "above-conditional": "Above {kind}: conditional, not excess.",
    "above-template-set": "Above a range high this template sets or computes: not excess.",
    "above-derived-provisional": "Above a range high derived from the minimum (the minimum × "
                                 "{k}), not a safe limit: not excess.",
    "also-above": "Also above {kind}.",
    "no-minimum": "No minimum for this requirement.",
    "no-range": "No range: this requirement sets no limit for this row.",
    "unavailable": "Not computed: {reason}",
    "below-zero-no-minimum": "Below zero on a row with no minimum: no verdict (Implementation "
                             "Guide open point 3).",
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

# How the entries are read (check_diet's description, describe_inputs).
ENTRIES_TEXT = ("low and high are the template's Min and Max entries: for a diet, one value "
                "(placed by the template's rule) or both ends of a range such as an analysed "
                "minimum and maximum; for a requirement range, its two ends. Each is described "
                "separately.")
ENERGY_ENTRY_TEXT = ("the energy the diet supplies, kcal per day; to replace the requirement's "
                     "energy with the animal's known intake, use "
                     "animal.energy_intake_kcal_per_day.")

# MBW rows: their limits are a requirement per kg of metabolic body weight a day, converted to
# per Mcal with the animal's energy and body weight; entries are per Mcal (steward, 22 Oct
# 2026: the template's column D label "g/kg BW^0.75" misread as the entry's unit).
MBW_TEXT = ("This row's requirement is per {mbw_unit} a day: {figures}, converted to {unit} at "
            "{kcal} kcal/day and a body weight of {bw} kg. Enter the diet's {unit}.")
MBW_ENTRY_TEXT = ("the diet's amount per Mcal, as on the per-Mcal row; the limits are the "
                  "requirement's per kg BW^0.75 (dogs) or BW^0.67 (cats) a day, converted with "
                  "the animal's energy and body weight.")

# A requirement that sets no maximum for a nutrient, on either basis (steward, 22 Oct 2026: AI
# readers brought in other standards' or life stages' limits from memory).
NO_MAXIMUM_TEXT = ("{requirement} sets no {nutrient} maximum{basis}; limits from other "
                   "standards or life stages do not apply to this check.")

# Reasons in plain words.
REASONS = {
    "requirement-needed": "Choose a requirement.",
    "body-weight-needed": "Enter the body weight (for adults, the optimal body weight).",
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
