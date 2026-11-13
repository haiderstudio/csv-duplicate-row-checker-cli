"""Tests for csv_duplicate_row_checker: duplicate rows, CLI, examples, hygiene.

CWD-robust: every CLI run uses absolute paths and every assertion
checks a file-name suffix plus the message text, never an absolute
path — so this suite passes from any working directory.
"""

import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import csv_duplicate_row_checker as checker

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "csv_duplicate_row_checker.py"
EXAMPLES = ROOT / "examples"
README = ROOT / "README.md"


def dupes(text, delimiter=","):
    """Duplicate rows in a document: (first_seen, repeat_lines, row)."""
    return [(p.first_seen, p.repeat_lines, p.row)
            for p in checker.check_text(text, "t.csv", delimiter)]


def problems(text, delimiter=","):
    """All problems in a document: (line, reason)."""
    return [(p.line, p.reason)
            for p in checker.check_text(text, "t.csv", delimiter)]


class TestExactDuplicates(unittest.TestCase):
    def test_one_repeat(self):
        self.assertEqual(dupes("a,b\n1,2\n1,2\n"),
                         [(2, [3], ["1", "2"])])

    def test_row_repeated_twice(self):
        self.assertEqual(
            dupes("id,name,score\n1,Alice,90\n2,Bob,85\n"
                  "1,Alice,90\n3,Carol,88\n1,Alice,90\n"),
            [(2, [4, 6], ["1", "Alice", "90"])])

    def test_two_different_rows_repeated(self):
        self.assertEqual(
            dupes("a,b\n1,2\n3,4\n1,2\n3,4\n"),
            [(2, [4], ["1", "2"]), (3, [5], ["3", "4"])])

    def test_first_seen_line_is_first_occurrence(self):
        found = dupes("a,b\n1,2\n3,4\n5,6\n3,4\n")
        self.assertEqual(found, [(3, [5], ["3", "4"])])

    def test_repeat_lines_in_file_order(self):
        found = dupes("a\nx\ny\nx\nz\nx\n")
        self.assertEqual(found, [(2, [4, 6], ["x"])])

    def test_duplicate_is_last_row_no_trailing_newline(self):
        self.assertEqual(dupes("a,b\n1,2\n1,2"),
                         [(2, [3], ["1", "2"])])

    def test_duplicate_surrounded_by_clean_rows(self):
        found = dupes("a,b\n1,1\n2,2\n1,1\n3,3\n4,4\n")
        self.assertEqual(found, [(2, [4], ["1", "1"])])

    def test_data_row_identical_to_header_is_a_duplicate(self):
        # The header counts as a row, so a data row that repeats
        # it is a duplicate of line 1.
        self.assertEqual(dupes("id,name\n1,Alice\nid,name\n"),
                         [(1, [3], ["id", "name"])])


class TestNotDuplicates(unittest.TestCase):
    def test_case_differs(self):
        self.assertEqual(dupes("a\nAlice\nalice\n"), [])

    def test_extra_space_differs(self):
        self.assertEqual(dupes("a,b\n1,90\n1,90 \n"), [])

    def test_extra_column_differs(self):
        self.assertEqual(dupes("a,b\n1,2\n1,2,3\n"), [])

    def test_missing_column_differs(self):
        self.assertEqual(dupes("a,b\n1,2\n1\n"), [])

    def test_field_order_differs(self):
        self.assertEqual(dupes("a,b\n1,2\n2,1\n"), [])

    def test_similar_but_different_values(self):
        self.assertEqual(dupes("a,b\n1,2\n1,3\n"), [])


class TestCleanFiles(unittest.TestCase):
    def test_clean_file_passes(self):
        self.assertEqual(dupes("id,name,score\n1,Alice,90\n2,Bob,85\n"),
                         [])

    def test_header_only_file_passes(self):
        self.assertEqual(dupes("a,b,c\n"), [])

    def test_empty_file_passes(self):
        self.assertEqual(dupes(""), [])

    def test_blank_lines_are_skipped(self):
        # Two blank lines are not a duplicated row: a blank line
        # carries no record. Empty rows are repo #73's job.
        self.assertEqual(dupes("a,b\n1,2\n\n\n3,4\n"), [])

    def test_blank_line_between_duplicates(self):
        found = dupes("a,b\n1,2\n\n1,2\n")
        self.assertEqual(found, [(2, [4], ["1", "2"])])

    def test_no_trailing_newline_clean(self):
        self.assertEqual(dupes("a,b\n1,2"), [])


class TestQuotedFields(unittest.TestCase):
    def test_quoted_comma_field_duplicated(self):
        found = dupes('a,b\n1,"Carol, Jr."\n1,"Carol, Jr."\n')
        self.assertEqual(found, [(2, [3], ["1", "Carol, Jr."])])

    def test_doubled_quote_duplicated(self):
        found = dupes('a,b\n1,"say ""hi"""\n1,"say ""hi"""\n')
        self.assertEqual(found, [(2, [3], ["1", 'say "hi"'])])

    def test_multiline_quoted_field_duplicated(self):
        found = dupes('id,note\n1,"line one\nline two"\n2,x\n'
                      '1,"line one\nline two"\n')
        self.assertEqual(found, [(2, [5], ["1", "line one\nline two"])])

    def test_multiline_quoted_field_clean_passes(self):
        self.assertEqual(
            dupes('a,b\n"line one\nline two",2\n'), [])

    def test_quoting_style_only_is_still_a_duplicate(self):
        # "1","Alice" and 1,Alice are the same row: the values
        # match, so the quoting does not matter.
        found = dupes('a,b\n"1","Alice"\n1,Alice\n')
        self.assertEqual(found, [(2, [3], ["1", "Alice"])])

    def test_quoted_field_duplicated_with_delimiter(self):
        found = dupes('a;b\n1;"x;y"\n1;"x;y"\n', delimiter=";")
        self.assertEqual(found, [(2, [3], ["1", "x;y"])])


class TestCRLF(unittest.TestCase):
    def test_crlf_duplicate(self):
        found = dupes("a,b\r\n1,2\r\n1,2\r\n")
        self.assertEqual(found, [(2, [3], ["1", "2"])])

    def test_crlf_clean(self):
        self.assertEqual(dupes("a,b\r\n1,2\r\n3,4\r\n"), [])


class TestEdgeCases(unittest.TestCase):
    def test_nul_byte_is_a_parse_problem(self):
        found = problems("a,b\n1,\x002\n")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0][0], 2)
        self.assertIn("NUL byte", found[0][1])

    def test_nul_line_reported_alongside_duplicates(self):
        found = problems("a,b\n1,2\n1,2\n3,\x004\n")
        self.assertEqual(len(found), 2)
        self.assertIn("duplicate row", found[0][1])
        self.assertIn("NUL byte", found[1][1])
        self.assertEqual(found[1][0], 4)

    def test_unbalanced_quote_is_a_parse_problem(self):
        found = problems('a,b\n1,"x\n2,3\n')
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0][0], 2)
        self.assertIn("cannot parse CSV", found[0][1])
        self.assertIn("unexpected end of data", found[0][1])

    def test_duplicates_before_parse_error_are_still_reported(self):
        found = problems('a,b\n1,2\n1,2\n3,"x\n')
        self.assertEqual(len(found), 2)
        self.assertIn("duplicate row", found[0][1])
        self.assertIn("cannot parse CSV", found[1][1])
        self.assertEqual(found[1][0], 4)

    def test_custom_delimiter(self):
        found = dupes("a;b\n1;2\n1;2\n", delimiter=";")
        self.assertEqual(found, [(2, [3], ["1", "2"])])

    def test_tab_delimiter(self):
        found = dupes("a\tb\n1\t2\n1\t2\n", delimiter="\t")
        self.assertEqual(found, [(2, [3], ["1", "2"])])

    def test_problem_text_format(self):
        problem = checker.check_text("a,b\n1,2\n1,2\n", "f.csv")[0]
        self.assertEqual(
            problem.text(),
            "f.csv:2: duplicate row, first seen on line 2, "
            "repeats on line 3: 1,2")

    def test_problem_as_dict(self):
        problem = checker.check_text("a,b\n1,2\n1,2\n", "f.csv")[0]
        self.assertEqual(problem.as_dict(), {
            "file": "f.csv",
            "line": 2,
            "reason": "duplicate row, first seen on line 2, "
                      "repeats on line 3: 1,2",
            "first_seen": 2,
            "repeat_lines": [3],
            "row": ["1", "2"],
        })

    def test_format_row_quotes_fields_that_need_it(self):
        self.assertEqual(
            checker.format_row(["1", "Carol, Jr."], ","),
            '1,"Carol, Jr."')
        self.assertEqual(
            checker.format_row(["1", "Alice", "90"], ";"),
            "1;Alice;90")


class TestCheckFile(unittest.TestCase):
    def test_unreadable_path(self):
        found = checker.check_file("/nonexistent-dir-xyz/f.csv")
        self.assertEqual(len(found), 1)
        self.assertIn("cannot read file", found[0].reason)

    def test_file_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.csv"
            path.write_text("a,b\n1,2\n1,2\n")
            found = checker.check_file(str(path))
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0].first_seen, 2)
            self.assertEqual(found[0].repeat_lines, [3])


class TestCollection(unittest.TestCase):
    def test_folder_walk_finds_csv_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.csv").write_text("a,b\n1,2\n")
            (root / "b.txt").write_text("a,b\n1,2\n1,2\n")
            (root / "sub").mkdir()
            (root / "sub" / "c.csv").write_text("a,b\n1,2\n")
            files, missing = checker.collect_files([str(root)])
            self.assertEqual(missing, [])
            self.assertEqual(
                files, [str(root / "a.csv"), str(root / "sub" / "c.csv")])

    def test_git_folder_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            (root / ".git" / "x.csv").write_text("a,b\n1,2\n1,2\n")
            (root / "a.csv").write_text("a,b\n1,2\n")
            files, _ = checker.collect_files([str(root)])
            self.assertEqual(files, [str(root / "a.csv")])

    def test_no_recursive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.csv").write_text("a,b\n1,2\n")
            (root / "sub").mkdir()
            (root / "sub" / "b.csv").write_text("a,b\n1,2\n")
            files, _ = checker.collect_files([str(root)], recursive=False)
            self.assertEqual(files, [str(root / "a.csv")])

    def test_exclude_pattern(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "draft-a.csv").write_text("a,b\n1,2\n")
            (root / "final.csv").write_text("a,b\n1,2\n")
            files, _ = checker.collect_files(
                [str(root)], exclude=["draft-*"])
            self.assertEqual(files, [str(root / "final.csv")])

    def test_direct_file_checked_despite_exclude_and_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "draft-data.txt"
            target.write_text("a,b\n1,2\n1,2\n")
            files, _ = checker.collect_files(
                [str(target)], exclude=["draft-*"])
            self.assertEqual(files, [str(target)])

    def test_missing_path_reported(self):
        files, missing = checker.collect_files(["/no-such-path-xyz"])
        self.assertEqual(files, [])
        self.assertEqual(missing, ["/no-such-path-xyz"])

    def test_uppercase_extension_walked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "UP.CSV").write_text("a,b\n1,2\n")
            files, _ = checker.collect_files([str(root)])
            self.assertEqual(files, [str(root / "UP.CSV")])

    def test_results_sorted_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "b.csv").write_text("a,b\n1,2\n")
            (root / "a.csv").write_text("a,b\n1,2\n")
            files, _ = checker.collect_files(
                [str(root / "b.csv"), str(root), str(root / "a.csv")])
            self.assertEqual(files, [str(root / "a.csv"),
                                     str(root / "b.csv")])


class TestCLI(unittest.TestCase):
    def run_cli(self, *args, stdin=None, cwd=None):
        return subprocess.run(
            [sys.executable, str(SRC), *args],
            input=stdin, capture_output=True, text=True, cwd=cwd,
        )

    def test_clean_file_exit_0(self):
        result = self.run_cli(str(EXAMPLES / "good.csv"))
        self.assertEqual(result.returncode, 0)
        self.assertIn("good.csv: OK", result.stdout)
        self.assertIn("no duplicate rows", result.stdout)

    def test_bad_file_exit_1(self):
        result = self.run_cli(str(EXAMPLES / "duplicates.csv"))
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "duplicates.csv:2: duplicate row, first seen on line 2, "
            "repeats on lines 4, 7: 1,Alice,90", result.stdout)
        self.assertIn(
            "duplicates.csv:3: duplicate row, first seen on line 3, "
            "repeats on line 5: 3,Carol,88", result.stdout)

    def test_crlf_exit_1(self):
        result = self.run_cli(str(EXAMPLES / "crlf.csv"))
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "crlf.csv:2: duplicate row, first seen on line 2, "
            "repeats on line 3: 1,Alice,90", result.stdout)

    def test_folder_exit_1_and_summary(self):
        result = self.run_cli(str(EXAMPLES))
        self.assertEqual(result.returncode, 1)
        self.assertIn("Checked 4 file(s), 3 problem(s) in 2 file(s).",
                      result.stdout)

    def test_no_args_exit_2(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)

    def test_missing_path_exit_2(self):
        result = self.run_cli("no-such-file.csv")
        self.assertEqual(result.returncode, 2)
        self.assertIn("no such file or folder", result.stderr)

    def test_empty_folder_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli(tmp)
        self.assertEqual(result.returncode, 2)
        self.assertIn("no CSV files found", result.stderr)

    def test_bad_delimiter_exit_2(self):
        result = self.run_cli("--delimiter", ";;",
                              str(EXAMPLES / "good.csv"))
        self.assertEqual(result.returncode, 2)

    def test_bad_flag_exit_2(self):
        result = self.run_cli("--nope", str(EXAMPLES / "good.csv"))
        self.assertEqual(result.returncode, 2)

    def test_delimiter_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "semi.csv"
            path.write_text("id;name;score\n1;Alice;90\n1;Alice;90\n")
            result = self.run_cli("--delimiter", ";", str(path))
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "semi.csv:2: duplicate row, first seen on line 2, "
            "repeats on line 3: 1;Alice;90", result.stdout)

    def test_stdin(self):
        result = self.run_cli("--stdin", stdin="a,b\n1,2\n1,2\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL <stdin>:2: duplicate row, first seen "
                      "on line 2, repeats on line 3: 1,2",
                      result.stdout)

    def test_stdin_clean(self):
        result = self.run_cli("--stdin", stdin="a,b\n1,2\n")
        self.assertEqual(result.returncode, 0)

    def test_stdin_with_path_exit_2(self):
        result = self.run_cli("--stdin", str(EXAMPLES / "good.csv"))
        self.assertEqual(result.returncode, 2)

    def test_json_output(self):
        result = self.run_cli("--json",
                              str(EXAMPLES / "duplicates.csv"))
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["problems"], 2)
        self.assertEqual(payload["summary"]["checked"], 1)
        self.assertTrue(payload["files"][0]["file"]
                        .endswith("duplicates.csv"))
        first = payload["files"][0]["problems"][0]
        self.assertEqual(first["line"], 2)
        self.assertEqual(first["first_seen"], 2)
        self.assertEqual(first["repeat_lines"], [4, 7])
        self.assertEqual(first["row"], ["1", "Alice", "90"])
        second = payload["files"][0]["problems"][1]
        self.assertEqual(second["first_seen"], 3)
        self.assertEqual(second["repeat_lines"], [5])
        self.assertEqual(second["row"], ["3", "Carol", "88"])
        self.assertIn("Checked 1 file(s), 2 problem(s)",
                      result.stderr)

    def test_json_clean(self):
        result = self.run_cli("--json", str(EXAMPLES / "good.csv"))
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["problems"], 0)

    def test_version(self):
        result = self.run_cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertIn("1.0.0", result.stdout)

    def test_exclude_flag(self):
        result = self.run_cli("--exclude", "duplicates.csv",
                              str(EXAMPLES))
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("duplicates", result.stdout)
        self.assertIn("crlf", result.stdout)


class TestCwdRobustness(unittest.TestCase):
    """The CLI works from any working directory."""

    def test_cli_from_tmp(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(SRC),
                 str(EXAMPLES / "duplicates.csv")],
                capture_output=True, text=True, cwd=tmp,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicates.csv:2: duplicate row, first seen "
                      "on line 2, repeats on lines 4, 7: 1,Alice,90",
                      result.stdout)

    def test_cli_from_filesystem_root(self):
        result = subprocess.run(
            [sys.executable, str(SRC), str(EXAMPLES / "good.csv")],
            capture_output=True, text=True, cwd="/",
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("good.csv: OK", result.stdout)

    def test_cli_from_unrelated_dir(self):
        # The CLI must work from any folder, not only the repo root:
        # run it from a fresh temp folder (no local paths involved,
        # so this passes on a CI runner too).
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(SRC), str(EXAMPLES / "crlf.csv")],
                capture_output=True, text=True, cwd=tmp,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("crlf.csv:2: duplicate row, first seen on line 2, "
                      "repeats on line 3: 1,Alice,90", result.stdout)

    def test_cli_from_tmp_folder_walk(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(SRC), str(EXAMPLES)],
                capture_output=True, text=True, cwd=tmp,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Checked 4 file(s), 3 problem(s) in 2 file(s).",
                      result.stdout)


class TestExamples(unittest.TestCase):
    def test_bundled_files_expected_problems(self):
        expected = {
            "good.csv": [],
            "quoted.csv": [],
            "crlf.csv": [(2, [3], ["1", "Alice", "90"])],
            "duplicates.csv": [
                (2, [4, 7], ["1", "Alice", "90"]),
                (3, [5], ["3", "Carol", "88"]),
            ],
        }
        for name, want in expected.items():
            text = (EXAMPLES / name).read_text()
            got = [(p.first_seen, p.repeat_lines, p.row)
                   for p in checker.check_text(text, name)]
            self.assertEqual(got, want, name)

    def test_sample_output_matches_fresh_run(self):
        result = subprocess.run(
            ["sh", str(EXAMPLES / "run-example.sh")],
            capture_output=True, text=True, cwd="/tmp",
        )
        self.assertEqual(result.returncode, 0)
        sample = (EXAMPLES / "sample-output.md").read_text()
        block = sample.split("```\n")[1]
        self.assertEqual(result.stdout, block)

    def test_readme_quoted_outputs_are_real(self):
        readme = README.read_text()
        for line in [
            "examples/good.csv: OK",
            "OK — 1 file(s) checked, no duplicate rows.",
            "FAIL examples/duplicates.csv:2: duplicate row, first "
            "seen on line 2, repeats on lines 4, 7: 1,Alice,90",
            "FAIL examples/duplicates.csv:3: duplicate row, first "
            "seen on line 3, repeats on line 5: 3,Carol,88",
            "FAIL examples/crlf.csv:2: duplicate row, first seen "
            "on line 2, repeats on line 3: 1,Alice,90",
            "Checked 4 file(s), 3 problem(s) in 2 file(s).",
            "FAIL <stdin>:2: duplicate row, first seen on line 2, "
            "repeats on lines 4, 7: 1,Alice,90",
            "FAIL semi.csv:2: duplicate row, first seen on line 2, "
            "repeats on line 3: 1;Alice;90",
        ]:
            self.assertIn(line, readme, line)


class TestHygiene(unittest.TestCase):
    def test_no_placeholder_text(self):
        banned = ["TODO", "FIXME", "XXX", "coming soon", "lorem"]
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if "tests" in path.parts:
                continue
            text = path.read_text(errors="replace")
            for word in banned:
                self.assertNotIn(word, text,
                                 f"{word} in {path.relative_to(ROOT)}")

    def test_no_absolute_paths(self):
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if "tests" in path.parts:
                continue
            text = path.read_text(errors="replace")
            self.assertNotIn("/home/hatch", text,
                             f"absolute path in {path.relative_to(ROOT)}")
            self.assertNotIn("/Users/", text,
                             f"absolute path in {path.relative_to(ROOT)}")
            self.assertNotIn("/tmp/", text,
                             f"absolute path in {path.relative_to(ROOT)}")

    def test_stdlib_only_imports(self):
        allowed_src = {
            "argparse", "csv", "fnmatch", "io", "json", "os", "sys",
            "pathlib",
        }
        allowed_tests = allowed_src | {
            "ast", "json", "subprocess", "tempfile", "unittest",
            "csv_duplicate_row_checker",
        }
        for path, allowed in [(SRC, allowed_src),
                              (Path(__file__), allowed_tests)]:
            tree = ast.parse(path.read_text())
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(a.name.split(".")[0]
                                    for a in node.names)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported.add(node.module.split(".")[0])
            self.assertTrue(imported <= allowed,
                            f"{path.name} imports non-stdlib: "
                            f"{imported - allowed}")
            self.assertNotIn("yaml", imported)

    def test_no_yaml_anywhere_in_source(self):
        text = SRC.read_text()
        self.assertNotIn("yaml", text)

    def test_no_secrets_in_repo(self):
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if "tests" in path.parts:
                continue
            text = path.read_text(errors="replace").lower()
            for marker in ["api_key", "api-key", "password =", "secret ="]:
                self.assertNotIn(marker, text,
                                 f"possible secret in {path.relative_to(ROOT)}")

    def test_gitignore_env_first(self):
        lines = (ROOT / ".gitignore").read_text().splitlines()
        self.assertEqual(lines[0], ".env")

    def test_ci_runs_this_test_file(self):
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
        self.assertIn("actions/checkout", ci)
        self.assertIn("setup-python", ci)
        self.assertIn("test_csv_duplicate_row_checker.py", ci)
        self.assertIn("push", ci)
        self.assertIn("pull_request", ci)


if __name__ == "__main__":
    unittest.main()
