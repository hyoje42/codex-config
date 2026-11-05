"""Exercise the spec-brief data audit through its public CLI."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "home/skills/spec-brief/scripts/data_audit.py"
)


class DataAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        self.data.mkdir()

    def run_audit(self, path=None):
        return subprocess.run(
            [sys.executable, "-I", str(SCRIPT), str(path or self.data)],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def successful_output(self):
        before = {p.name: p.read_bytes() for p in self.data.iterdir()}
        result = self.run_audit()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(
            {p.name: p.read_bytes() for p in self.data.iterdir()}, before
        )
        return result.stdout

    def test_csv_and_tsv_columns_and_unit_mismatch(self):
        for suffix, delimiter in (("csv", ","), ("tsv", "\t"), ("TSV", "\t")):
            with self.subTest(suffix=suffix):
                text = "\ufeffid,value\r\na,1\r\nb,2\r\nc,3kg\r\n"
                (self.data / f"values.{suffix}").write_bytes(
                    text.replace(",", delimiter).encode("utf-8")
                )
        output = self.successful_output()
        self.assertEqual(output.count("rows: 3 (+header)  columns: 2"), 3)
        self.assertEqual(output.count("1 row(s) are num+unit"), 3)
        self.assertEqual(output.count("UTF-8 BOM at start of file"), 3)
        self.assertEqual(output.count("CRLF line endings"), 3)

    def test_multiline_records_report_physical_start_lines(self):
        text = (
            'id,note,value\n'
            'a,"hello\nworld",1\n'
            'b,ok,-3\n'
            'a,"hello\nworld",1\n'
            'a,other,2\n'
            'c,ok,0\n'
            'd,ok,3kg\n'
            '\n'
            'e,ok\n'
            'f, padded ,4\n'
            'b,changed,5\n'
        )
        for newline in ("\n", "\r\n", "\r"):
            with self.subTest(newline=repr(newline)):
                (self.data / "rows.csv").write_bytes(
                    text.replace("\n", newline).encode("utf-8")
                )
                output = self.successful_output()
                for expected in (
                    "rows: 10 (+header)  columns: 3",
                    "negative values at lines [4]",
                    "rows.csv:5 exact duplicate of line 2",
                    "rows.csv:7 duplicate id 'a' (first at line 2)",
                    "has zero at lines [8]",
                    "lines [9]; e.g. 9:'3kg'",
                    "rows.csv:10 blank row",
                    "rows.csv:11 has 2 fields, header has 3",
                    "rows.csv:12 column 'note' has surrounding spaces",
                    "rows.csv:13 duplicate id 'b' (first at line 4)",
                ):
                    self.assertIn(expected, output)

    def test_multiline_header_counts_toward_physical_lines(self):
        (self.data / "header.csv").write_text(
            'id,"note\ntext",value\na,ok,1\nb,ok,-2\n', encoding="utf-8"
        )
        output = self.successful_output()
        self.assertIn("rows: 2 (+header)  columns: 3", output)
        self.assertIn("negative values at lines [4]", output)

    def test_missing_directory_is_an_error(self):
        path = self.root / "missing"
        result = self.run_audit(path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(path), result.stderr)
        self.assertFalse(path.exists())

    def test_file_instead_of_directory_is_an_error(self):
        path = self.data / "input.csv"
        path.write_text("id,value\na,1\n", encoding="utf-8")
        result = self.run_audit(path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(path), result.stderr)

    def test_empty_directory_is_valid(self):
        self.successful_output()

    def test_json_and_grid_checks_still_run(self):
        for name, text in {
            "broken.json": "{",
            "null.json": "null",
            "grid.txt": "####\n#..#\n###\n",
        }.items():
            (self.data / name).write_text(text, encoding="utf-8")
        output = self.successful_output()
        self.assertIn("invalid JSON", output)
        self.assertIn("top-level value is null", output)
        self.assertIn("grid.txt:3 (y=2) width 3 != 4", output)


if __name__ == "__main__":
    unittest.main()
