"""Phase 1a tests: the frozen baseline, the round trip, a negative control and the validator.

Run: nice -n 10 python3 -I -B tests/test_phase1a.py
"""

import hashlib
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from oan import release, table, validate  # noqa: E402
import roundtrip  # noqa: E402

PARITY = os.path.join(HERE, "parity")
BASELINE = roundtrip.BASELINE
LATE_GROWTH = "fediaf-dog-late-growth"


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def edit_cell(data_dir, edition, requirement, nutrient, field, value):
    """Set one field of one row of a limits file (keeps everything else byte for byte)."""
    import csv
    import io
    path = os.path.join(data_dir, "standards", edition, requirement + ".csv")
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    col = rows[0].index(field)
    for r in rows[1:]:
        if r[0] == nutrient:
            r[col] = value
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(rows)
    write(path, out.getvalue())


class Baseline(unittest.TestCase):
    def test_checksums(self):
        for line in open(os.path.join(PARITY, "SHA256SUMS"), encoding="utf-8"):
            digest, path = line.split(None, 1)
            with open(os.path.join(PARITY, path.strip()), "rb") as f:
                data = f.read()
            self.assertEqual(hashlib.sha256(data).hexdigest(), digest, path)

    def test_release_hash(self):
        rel = release.read_release(BASELINE)
        self.assertEqual(rel["data_version"], "21OCT26b.1")
        self.assertEqual(rel["content_sha256"], release.content_hash(BASELINE))

    def test_validator_clean(self):
        report = validate.validate(BASELINE)
        self.assertEqual(report.errors, [])
        self.assertEqual(report.warnings, [])


class RoundTrip(unittest.TestCase):
    def test_released_limits(self):
        exact, close, diffs = roundtrip.compare(BASELINE)
        self.assertEqual(diffs, [])
        # One limit is within 1e-12, not bit-exact: nrc-cat-adult vitamin-d-mbw min, where
        # the sheet's =0.17*40 gives 6.800000000000001 and the exact conversion 6.8.
        self.assertEqual((exact, close), (4829, 1))

    def test_greater_than_is_the_typed_decimal(self):
        data = table.load(BASELINE)
        self.assertEqual(table.compute_limits(data, "nrc-kitten")["taurine"][1], 2.220000001)
        self.assertEqual(table.compute_limits(data, "nrc-cat-adult")["sodium"][1], 3.750000001)

    def test_mature_weight_rule(self):
        data = table.load(BASELINE)
        for weight, ca_min, ratio_max in ((None, 2.5, 1.6), (0, 2.5, 1.6), (10, 2.0, 1.8),
                                          (15, 2.0, 1.8), (15.01, 2.5, 1.6), (40, 2.5, 1.6)):
            limits = table.compute_limits(data, LATE_GROWTH, weight)
            self.assertEqual(limits["calcium"][0], ca_min, weight)
            self.assertEqual(limits["ca-p-ratio"][1], ratio_max, weight)


class NegativeControl(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.data = os.path.join(self.tmp, "data")
        shutil.copytree(BASELINE, self.data)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_one_changed_figure_fails(self):
        # FEDIAF adult dog (MER 95) calcium maximum, printed 6.25 g/1000 kcal.
        edit_cell(self.data, "FEDIAF-2025", "fediaf-dog-adult-mer95", "calcium", "max", "6.3")
        exact, close, diffs = roundtrip.compare(self.data)
        changed = sorted((d[0], d[1], d[2]) for d in diffs)
        # The per-MBW maximum is computed from it, so it moves too and cannot go stale.
        self.assertEqual(changed, [("fediaf-dog-adult-mer95", "calcium", "max"),
                                   ("fediaf-dog-adult-mer95", "calcium-mbw", "max")])
        report = validate.validate(self.data)
        self.assertEqual(report.errors, [])
        self.assertTrue(any("differ only in the MER" in w for w in report.warnings))
        self.assertTrue(any(w.startswith("RELEASE") for w in report.warnings))


class ValidatorRejects(unittest.TestCase):
    """Each seeded bad file gives an error naming the file, the line and the field."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.data = os.path.join(self.tmp, "data")
        shutil.copytree(BASELINE, self.data)
        self.nrc = os.path.join(self.data, "standards", "NRC-2006", "nrc-cat-adult.csv")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def errors(self):
        return validate.validate(self.data).errors

    def assertError(self, text):
        errors = self.errors()
        self.assertTrue(any(text in e for e in errors), "no error with %r in %r" % (
            text, errors[:5]))

    def test_decimal_comma(self):
        edit_cell(self.data, "NRC-2006", "nrc-cat-adult", "calcium", "min", "0,72")
        self.assertError("use a point, not a comma")

    def test_thousands_separator(self):
        edit_cell(self.data, "NRC-2006", "nrc-cat-adult", "retinol", "max", "25,000")
        self.assertError("thousands separator")

    def test_unicode_minus_and_percent(self):
        edit_cell(self.data, "NRC-2006", "nrc-cat-adult", "calcium", "min", "−0.72")
        self.assertError("cannot be negative")
        edit_cell(self.data, "NRC-2006", "nrc-cat-adult", "calcium", "min", "72%")
        self.assertError("without %")

    def test_none_spelling(self):
        edit_cell(self.data, "NRC-2006", "nrc-cat-adult", "iron", "max", "None")
        self.assertError('write "none" exactly')

    def test_duplicate_row(self):
        lines = read(self.nrc).splitlines(True)
        write(self.nrc, "".join(lines + [lines[5]]))
        self.assertError("appears twice")

    def test_missing_row(self):
        lines = read(self.nrc).splitlines(True)
        write(self.nrc, "".join(lines[:5] + lines[6:]))
        self.assertError("no row for nutrient")

    def test_unknown_rule(self):
        edit_cell(self.data, "NRC-2006", "nrc-cat-adult", "calcium", "min_rule", "x0.5")
        self.assertError("unknown rule")

    def test_stale_derived_cell(self):
        # A typed number where the rule computes the value from the per-Mcal maximum.
        edit_cell(self.data, "FEDIAF-2025", "fediaf-dog-adult-mer95", "calcium-mbw", "max",
                  "0.59")
        self.assertError("leave the figure empty")

    def test_unknown_unit(self):
        edit_cell(self.data, "NRC-2006", "nrc-cat-adult", "calcium", "min_unit", "g/lb DM")
        self.assertError("unknown printed unit")

    def test_missing_source(self):
        edit_cell(self.data, "NRC-2006", "nrc-cat-adult", "calcium", "min_source", "")
        self.assertError("needs its source")

    def test_dangling_note(self):
        edit_cell(self.data, "NRC-2006", "nrc-cat-adult", "calcium", "min_notes", "n999")
        self.assertError("does not exist in notes.csv")

    def test_semicolon_file(self):
        write(self.nrc, read(self.nrc).replace(",", ";"))
        self.assertError("the header row must be exactly")

    def test_bom_and_windows_line_ends_accepted(self):
        write(self.nrc, "﻿" + read(self.nrc).replace("\n", "\r\n"))
        self.assertEqual(self.errors(), [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
