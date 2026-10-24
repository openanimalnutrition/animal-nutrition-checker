"""Phase 1b tests: number handling, the input rules and the vector runner.

Run: nice -n 10 python3 -I -B tests/test_phase1b.py

class Semantics has one test per rule of how the template's spreadsheet evaluates its formulas
(numbers, text, blanks, lookups), named after it. A rule the code meets by rejecting the input
(the core rejects inputs outside the rules, decision 1 A) is tested by that rejection. Not
tested, because the code has no such construct: INDEX of a one-row array, IFERROR, and the
branches IF and AND evaluate; the sheet view renders their results in phase 3.
"""

import collections
import contextlib
import copy
import io
import json
import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import run_vectors  # noqa: E402
from oan import inputs, numbers, table  # noqa: E402

BASELINE = run_vectors.BASELINE
DATA = table.load(BASELINE)


def fact(field, value):
    return inputs.check_fact(field, value, DATA)


class Semantics(unittest.TestCase):
    # Numbers
    def test_arithmetic_is_double_precision_in_spec_order(self):
        # No decimal arithmetic outside ROUND and TEXT: the order of operations shows.
        self.assertEqual(0.17 * 40, 6.800000000000001)
        self.assertNotEqual((0.1 + 0.2) + 0.3, 0.1 + (0.2 + 0.3))
        self.assertEqual(15 ** 0.75, math.pow(15, 0.75))

    def test_nothing_is_rounded_except_round_and_text(self):
        # A computed limit keeps every binary digit: the per-MBW maximum is x * MER / 1000.
        limits = table.compute_limits(DATA, "fediaf-dog-adult-mer95")
        self.assertEqual(limits["calcium-mbw"][1], limits["calcium"][1] * 95.0 / 1000)

    def test_numbers_compare_within_relative_1e_12(self):
        self.assertTrue(numbers.close(6.8, 6.800000000000001))
        self.assertTrue(numbers.close(1e6, 1e6 * (1 + 0.9e-12)))
        self.assertFalse(numbers.close(1e6, 1e6 * (1 + 1.1e-12)))
        self.assertFalse(numbers.close(0.0, 1e-300))

    # ROUND
    def test_round_15_digit_value_half_away_from_zero(self):
        self.assertEqual(numbers.sheet_round(1.005, 2), 1.01)
        self.assertEqual(numbers.sheet_round(0.145 * 3, 2), 0.44)
        self.assertEqual(numbers.sheet_round(-1.005, 2), -1.01)
        self.assertEqual(numbers.sheet_round(2.5), 3.0)
        self.assertEqual(numbers.sheet_round(-2.5), -3.0)
        self.assertEqual(numbers.sheet_round(1234.5, -2), 1200.0)

    def test_round_is_not_on_the_binary_or_shortest_value(self):
        # Python's round() works on the binary value, repr on the shortest decimal.
        self.assertEqual(round(1.005, 2), 1.0)
        self.assertEqual(repr(0.145 * 3), "0.43499999999999994")
        self.assertEqual(round(0.145 * 3, 2), 0.43)
        self.assertEqual(numbers.sheet_round(0.145 * 3, 2), 0.44)

    def test_band_edges_compare_rounded_to_7(self):
        # A value computed with binary error still lands on its band edge.
        self.assertNotEqual(0.1 + 0.2, 0.3)
        self.assertEqual(numbers.sheet_round(0.1 + 0.2, 7), numbers.sheet_round(0.3, 7))
        self.assertEqual(numbers.sheet_round(0.29999995, 7), 0.3)
        self.assertEqual(numbers.sheet_round(0.29999994, 7), 0.2999999)

    def test_tie_at_15th_digit_goes_to_even_assumed(self):
        # Exact value 123456789012344.5 (16 digits): %.15g keeps the even 4.
        self.assertEqual(numbers.decimal15(123456789012344.5), 123456789012344)
        self.assertEqual(numbers.to_text(123456789012344.5), "123456789012344")

    # TEXT and number-to-text
    def test_number_to_text_15_digits_integers_plain(self):
        self.assertEqual(numbers.to_text(1 / 3), "0.333333333333333")
        self.assertEqual(numbers.to_text(25.0), "25")
        self.assertEqual(numbers.to_text(-0.0), "0")
        self.assertEqual(numbers.to_text(6.800000000000001), "6.8")
        self.assertEqual(numbers.to_text(1.5e-7), "1.5E-07")  # exponent form: assumed

    def test_text_formats_round_like_round_assumed(self):
        self.assertEqual(numbers.format_fixed(1.0005, 3), "1.001")
        self.assertEqual(numbers.format_fixed(0.145 * 3, 2), "0.44")
        self.assertEqual(numbers.format_fixed(0.12345, 2, percent=True), "12.35%")
        self.assertEqual(numbers.format_fixed(0.25, 2, percent=True), "25.00%")
        self.assertEqual(numbers.format_fixed(-0.0001, 2), "-0.00")

    # Comparisons
    def test_text_equality_ignores_case_where_the_template_compares_text(self):
        # The life stage is compared without case; the list items of the requirement and the
        # dog and cat types match exactly (case variants of O1 are outside-rule cases).
        self.assertEqual(fact("life_stage", "LACTATION: BITCH").value, "Lactation: bitch")
        self.assertEqual(fact("life_stage", "<3 \u212aittens").status, "reject")  # Kelvin sign
        self.assertEqual(fact("requirement", "NRC RA DOG MAINTENANCE").status, "reject")
        self.assertEqual(fact("adult_cat_type", "lean domestic (100 * kgBW^0.67)").status,
                         "reject")

    def test_blank_empty_text_and_zero_are_kept_apart(self):
        self.assertEqual(fact("caloric_restriction_percent", None), ("empty", None, None))
        self.assertEqual(fact("caloric_restriction_percent", 0), ("accept", 0.0, None))
        self.assertEqual(fact("caloric_restriction_percent", "").status, "reject")
        self.assertIsNone(run_vectors.compare(None, ""))
        self.assertIsNone(run_vectors.compare("", None))
        self.assertIsNone(run_vectors.compare(0, None))
        self.assertIsNone(run_vectors.compare("none", None))

    def test_numbers_never_equal_text_and_true_never_equals_1(self):
        self.assertEqual(numbers.as_input_number(True), (None, "true/false is not a number"))
        self.assertIsNone(numbers.as_input_number("15")[0])
        self.assertIsNone(run_vectors.compare(1, True))
        self.assertIsNone(run_vectors.compare(True, 1))
        self.assertIsNone(run_vectors.compare(15, "15"))

    def test_mixed_type_order_never_reaches_the_code(self):
        # Text or true/false against a number happens only with an input outside its rule.
        for value in ("abc", "25", True):
            self.assertEqual(fact("caloric_restriction_percent", value).status, "reject")

    # Lookups
    def test_lookups_by_id_not_by_the_duplicate_name(self):
        names = [n["name"] for n in DATA["nutrients"]]
        ids = [n["id"] for n in DATA["nutrients"]]
        self.assertEqual(names.count("Protein"), 2)
        self.assertEqual(len(ids), len(set(ids)))

    def test_wildcard_requirement_names_are_rejected(self):
        for value in ("*", "NRC RA Dog*", "AAFCO ?at Maintenance"):
            self.assertEqual(fact("requirement", value).status, "reject")

    def test_blank_requirement_is_not_entered(self):
        self.assertEqual(fact("requirement", None).status, "empty")

    # Functions and errors
    def test_n_of_blank_is_0_for_the_mature_weight_rule(self):
        late = "fediaf-dog-late-growth"
        self.assertEqual(table.compute_limits(DATA, late, None)["calcium"][0], 2.5)
        self.assertEqual(table.compute_limits(DATA, late, 10.0)["calcium"][0], 2.0)
        self.assertEqual(fact("mature_weight_kg", "abc").status, "reject")

    def test_trim_removes_spaces_only_assumed(self):
        self.assertEqual(inputs.trim("  >4   Kittens "), ">4 Kittens")
        self.assertEqual(inputs.trim("Lactation:\u00a0bitch"), "Lactation:\u00a0bitch")
        self.assertEqual(fact("life_stage", "Lactation:\u00a0bitch").status, "reject")
        self.assertEqual(fact("life_stage", "\tNone").status, "reject")

    def test_numeric_text_is_rejected_not_converted(self):
        self.assertEqual(fact("body_weight_kg", "15").status, "reject")
        self.assertEqual(fact("energy_intake_kcal_per_day", "1500").status, "reject")

    def test_unknown_requirement_is_rejected(self):
        for value in ("AAFCO", "Requirement Name:", "", " ", 42.0, True):
            self.assertEqual(fact("requirement", value).status, "reject", value)

    # Blank inputs
    def test_blank_inputs_are_not_entered(self):
        for field in ("body_weight_kg", "mature_weight_kg", "puppies_nursing", "lactation_week",
                      "energy_intake_kcal_per_day"):
            self.assertEqual(fact(field, None).status, "empty", field)
        for value in (0, -100.0, 5.0):
            self.assertEqual(fact("energy_intake_kcal_per_day", value).status, "reject")


class InputRules(unittest.TestCase):
    def test_life_stage_variants_of_the_energy_cases(self):
        # The 70 conformance cases tagged "m3-variant: '<typed>' reads as '<item>'".
        with open(os.path.join(run_vectors.VECTORS, "energy-testcases.json"),
                  encoding="utf-8") as f:
            cases = json.load(f)["cases"]
        seen = 0
        for case in cases:
            for tag in case["tags"]:
                if tag.startswith("m3-variant: "):
                    typed, item = tag[len("m3-variant: "):].split(" reads as ")
                    verdict = fact("life_stage", case["inputs"]["M3"])
                    self.assertEqual(repr(case["inputs"]["M3"]), typed)
                    self.assertEqual(repr(verdict.value), item)
                    seen += 1
        self.assertEqual(seen, 70)

    def test_input_numbers(self):
        for value in (float("nan"), float("inf"), -float("inf"), 1e15, -1e15, [1], {"x": 1}):
            self.assertIsNone(numbers.as_input_number(value)[0], value)
        self.assertEqual(numbers.as_input_number(999999999999999), (999999999999999.0, None))
        self.assertEqual(numbers.as_input_number(-2.5), (-2.5, None))

    def test_whole_numbers(self):
        self.assertEqual(fact("puppies_nursing", 8), ("accept", 8.0, None))
        self.assertEqual(fact("puppies_nursing", 8.0), ("accept", 8.0, None))
        self.assertEqual(fact("lactation_week", 2.5).status, "reject")

    def test_unknown_input(self):
        self.assertEqual(fact("body_weight_lb", 30).status, "reject")

    def test_entries(self):
        def entry(nid, value):
            return inputs.check_entry(nid, value, DATA).status
        self.assertEqual(entry("calcium", 1.2), "accept")
        self.assertEqual(entry("calcium", -1.0), "accept")  # the sheet's rule: any number
        self.assertEqual(entry("calcium", "1.2"), "reject")
        self.assertEqual(entry("calcium", None), "empty")
        self.assertEqual(entry("energy-density", 1.99), "reject")
        self.assertEqual(entry("energy-density", 4.0), "accept")
        self.assertEqual(entry("protein-dm", 30.0), "reject")  # computed, not entered
        self.assertEqual(entry("vitamin-z", 1.0), "reject")


class Runner(unittest.TestCase):
    def test_baseline(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = run_vectors.main(["run_vectors.py"])
        text = out.getvalue()
        self.assertEqual(status, 0, text)
        self.assertIn("inputs.json: 132 cases: 132 pass, 0 differ, 0 outside-rule, 0 pending",
                      text)
        # 781 table cases since phase 1b; the other 164 since phase 3 (18 outside the rules).
        self.assertIn("values.json: 945 cases: 927 pass, 0 differ, 18 outside-rule, "
                      "0 pending", text)

    def run_changed(self, name, change):
        cases, _ = run_vectors.load_cases(name)
        cases = copy.deepcopy(cases)
        changed_id = change(cases)
        results = run_vectors.run_file(name, cases, DATA, "forward")
        return results[changed_id][0]

    def test_negative_controls(self):
        def table_case(cell, new):
            def change(cases):
                case = next(c for c in cases if cell in c.get("outputs", {}))
                case["outputs"][cell] = new
                return case["id"]
            return change
        # A limit off by more than 1e-12, a limit that is "none", a max type, a name, K69.
        self.assertEqual(self.run_changed("values.json", table_case(
            "s02!T87", 750.0 * (1 + 2e-12))), "difference")
        self.assertEqual(self.run_changed("values.json", table_case(
            "s02!T87", 750.0 * (1 + 0.5e-12))), "pass")
        self.assertEqual(self.run_changed("values.json", table_case("s02!U6", 0.0)),
                         "difference")
        self.assertEqual(self.run_changed("values.json", table_case("s02!B90",
                         "Vitamin K1, Pylloquinone")), "difference")
        self.assertEqual(self.run_changed("values.json", table_case("s01!K69", 1.0)),
                         "difference")

        def flip_verdict(cases):
            cases[0]["verdict"] = "accept" if cases[0]["verdict"] == "reject" else "reject"
            return cases[0]["id"]
        self.assertEqual(self.run_changed("inputs.json", flip_verdict), "difference")

    def test_outside_rule_counts(self):
        # Decision 1 A: cases with an input outside its rule are one approved category of
        # difference. Formulas: the 338 of the 19 Oct tally, by input and by group. Values: 18,
        # not that tally's 10: 8 cases of group 5a5b type the text "none" into I67, which the
        # text-entry rule (=ISNUMBER, added 20 Oct, in 21OCT26b) rejects. Row 11: 4 cases with
        # an unmatched requirement name.
        expected = {
            "formulas-testcases.json": (338, {"G10": 231, "O1": 58, "G130": 41, "G10+G130": 8}),
            "values.json": (18, {"E3": 10, "I67": 8}),
            "energy-testcases.json": (0, {}),
            "energy-testcases-row11.json": (4, {"O1": 4}),
        }
        for name, (n, by_inputs) in expected.items():
            cases, _ = run_vectors.load_cases(name)
            self.assertEqual(run_vectors.outside_counts(cases, DATA)[:2], (n, by_inputs), name)
        cases, _ = run_vectors.load_cases("formulas-testcases.json")
        groups = collections.Counter(
            c["group"] for c in cases if run_vectors.outside_rules(c["inputs"], DATA)[0])
        self.assertEqual(groups, {"grid": 84, "selection-edge": 55, "selection-wildcard": 3,
                                  "g10-edge": 105, "g130-edge": 30, "random": 61})
        # Energy: the input rules reject 29 of the file's 30 outside-rule cases; the 30th has
        # a blank body weight, which no rule validates (phase 2 reports it as missing).
        _, outside = run_vectors.load_cases("energy-testcases.json")
        self.assertEqual([c["id"] for c in outside
                          if not run_vectors.outside_rules(c["inputs"], DATA)[0]],
                         ["EN-OUT-020"])

    def test_max_type_negative_control(self):
        cases, _ = run_vectors.load_cases("values.json")
        cases = copy.deepcopy(cases)
        case = next(c for c in cases if c["group"] == "table"
                    and c["cell_info"]["role"] == "code"
                    and list(c["outputs"].values())[0] == "SUL")
        ref = list(case["outputs"])[0]
        case["outputs"][ref] = "SUL>"
        results = run_vectors.run_file("values.json", cases, DATA, "forward")
        self.assertEqual(results[case["id"]][0], "difference")


if __name__ == "__main__":
    unittest.main(verbosity=1)
