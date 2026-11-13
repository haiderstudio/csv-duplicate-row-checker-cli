"""csv-duplicate-row-checker-cli: check CSV files for exact duplicate rows.

Reads one or more CSV files (or folders of them), and reports every
row that appears more than once, with the line it first appeared on
and every line it repeats on. A duplicated row in a data file
double-counts a record — a sale, a user, a reading — and downstream
totals come out wrong with no error anywhere. This tool catches the
duplication before the totals are made. Report-only: it never
rewrites a file. Exit 0 when every file is clean, 1 when any
duplicate row (or an unreadable file) is found, 2 for a usage error.

Rows are compared exactly, on their parsed field values: the same
fields in the same order, case-sensitive, no trimming. A row that
differs by one character, one space, or one extra column is a
different row and is not flagged. The header row counts as a row —
a data row identical to the header is a duplicate of it. A blank
line carries no record, so it is skipped (empty rows are repo #73's
csv-empty-checker-cli's job, not this one's). A quoted field that
spans several lines (an address with a line break inside quotes,
for example) is one row, and its line is the line where the row
starts. A file that cannot be parsed at all — an unbalanced quote
— is reported as a problem for that file and the check of that
file stops there; a line with a NUL byte in it is reported as a
problem for that line, and the rest of the file is still checked.

The check is done with Python's csv module: each row is read as a
tuple of fields, and a seen-set remembers the first line each row
appeared on. No row is ever written back anywhere.
"""

import argparse
import csv
import fnmatch
import io
import json
import os
import sys
from pathlib import Path

__version__ = "1.0.0"

CSV_SUFFIX = ".csv"


def format_row(fields, delimiter=","):
    """Render one parsed row back as a single line of CSV text."""
    buffer = io.StringIO()
    csv.writer(buffer, delimiter=delimiter,
               lineterminator="").writerow(fields)
    return buffer.getvalue()


class Problem:
    """One problem in one file: path, anchor line, plain reason.

    For a duplicate row the anchor line is the line the row first
    appeared on, and the problem also carries every line it repeats
    on plus the row itself. For a file that cannot be parsed, the
    anchor line is the line where the parse failed.
    """

    def __init__(self, path, line, reason, first_seen=None,
                 repeat_lines=None, row=None):
        self.path = path
        self.line = line
        self.reason = reason
        self.first_seen = first_seen
        self.repeat_lines = repeat_lines
        self.row = row

    def text(self):
        return f"{self.path}:{self.line}: {self.reason}"

    def as_dict(self):
        data = {"file": self.path, "line": self.line,
                "reason": self.reason}
        if self.first_seen is not None:
            data["first_seen"] = self.first_seen
            data["repeat_lines"] = self.repeat_lines
            data["row"] = self.row
        return data


def check_text(text, path, delimiter=","):
    """Check one CSV document given as text. Returns a list of Problems."""
    nul_lines = [lineno for lineno, line in
                 enumerate(text.splitlines(), start=1)
                 if "\x00" in line]
    seen = {}
    order = []
    parse_problem = None
    reader = csv.reader(io.StringIO(text, newline=""),
                        delimiter=delimiter, strict=True)
    while True:
        start_line = reader.line_num + 1
        try:
            row = next(reader)
        except StopIteration:
            break
        except csv.Error as exc:
            parse_problem = Problem(
                path, start_line, f"cannot parse CSV: {exc}")
            break
        if row == []:
            continue
        key = tuple(row)
        if key in seen:
            seen[key][1].append(start_line)
        else:
            seen[key] = (start_line, [])
            order.append(key)
    problems = []
    for key in order:
        first_seen, repeats = seen[key]
        if not repeats:
            continue
        if len(repeats) == 1:
            repeats_text = f"repeats on line {repeats[0]}"
        else:
            repeats_text = ("repeats on lines "
                            + ", ".join(str(line) for line in repeats))
        problems.append(Problem(
            path,
            first_seen,
            "duplicate row, first seen on line "
            f"{first_seen}, {repeats_text}: "
            f"{format_row(list(key), delimiter)}",
            first_seen=first_seen,
            repeat_lines=repeats,
            row=list(key),
        ))
    if parse_problem is not None:
        problems.append(parse_problem)
    for lineno in nul_lines:
        problems.append(Problem(
            path, lineno,
            "line contains NUL byte (not valid CSV text)"))
    return problems


def check_file(path, delimiter=","):
    """Check one CSV file on disk. Returns a list of Problems."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [Problem(str(path), 0,
                        f"cannot read file: {exc.strerror or exc}")]
    return check_text(text, str(path), delimiter)


def is_excluded(name, patterns):
    """True when a file name matches any --exclude glob pattern."""
    return any(fnmatch.fnmatchcase(name, pattern)
               for pattern in patterns)


def collect_files(paths, recursive=True, exclude=()):
    """Gather CSV files from the given paths.

    A file passed directly is always checked, even without a .csv
    extension and even if it matches an --exclude pattern. A folder
    contributes its .csv files (recursively unless --no-recursive),
    skipping .git and __pycache__ folders, never following directory
    links. Returns (files, missing) with files sorted and deduplicated.
    """
    files = []
    missing = []
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            missing.append(raw)
            continue
        if path.is_file():
            files.append(str(path))
            continue
        for root, dirs, names in os.walk(path):
            dirs[:] = sorted(
                name for name in dirs
                if name not in (".git", "__pycache__")
                and not os.path.islink(os.path.join(root, name))
            )
            if not recursive:
                dirs[:] = []
            for name in sorted(names):
                if not name.lower().endswith(CSV_SUFFIX):
                    continue
                if is_excluded(name, exclude):
                    continue
                files.append(str(Path(root) / name))
    return sorted(set(files)), missing


def build_parser():
    parser = argparse.ArgumentParser(
        prog="csv_duplicate_row_checker",
        description="Check CSV files for exact duplicate rows.",
    )
    parser.add_argument(
        "paths", nargs="*", metavar="PATH",
        help="CSV file(s) or folder(s) to check",
    )
    parser.add_argument(
        "--delimiter", default=",",
        help="field delimiter (default: ',')",
    )
    parser.add_argument(
        "--exclude", action="append", default=[], metavar="PATTERN",
        help="skip walked files whose name matches this glob "
             "(repeatable; direct files are always checked)",
    )
    parser.add_argument(
        "--no-recursive", action="store_true",
        help="do not walk into subfolders",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="print the result as machine-readable JSON "
             "(the summary goes to standard error)",
    )
    parser.add_argument(
        "--stdin", action="store_true",
        help="read one CSV document from standard input",
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__,
    )
    return parser


def report_text(results, checked, total):
    """Print the plain-text report. Returns the exit code."""
    files_with_problems = sum(1 for _, probs in results if probs)
    for path, problems in results:
        if problems:
            for problem in problems:
                print(f"FAIL {problem.text()}")
        else:
            print(f"{path}: OK")
    if total == 0:
        print(f"OK — {checked} file(s) checked, "
              "no duplicate rows.")
        return 0
    print(f"Checked {checked} file(s), {total} problem(s) "
          f"in {files_with_problems} file(s).")
    return 1


def report_json(results, checked, total):
    """Print the JSON report. Returns the exit code."""
    files_with_problems = sum(1 for _, probs in results if probs)
    payload = {
        "files": [
            {
                "file": path,
                "problems": [problem.as_dict() for problem in problems],
            }
            for path, problems in results
        ],
        "summary": {
            "checked": checked,
            "files_with_problems": files_with_problems,
            "problems": total,
        },
    }
    print(json.dumps(payload, indent=2))
    print(f"Checked {checked} file(s), {total} problem(s) "
          f"in {files_with_problems} file(s).", file=sys.stderr)
    return 1 if total else 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if len(args.delimiter) != 1:
        parser.error("--delimiter must be a single character")
    if args.stdin:
        if args.paths:
            parser.error("--stdin takes no PATH arguments")
        results = [("<stdin>", check_text(
            sys.stdin.read(), "<stdin>", args.delimiter))]
        checked = 1
    else:
        if not args.paths:
            parser.error("give at least one PATH, or use --stdin")
        files, missing = collect_files(
            args.paths,
            recursive=not args.no_recursive,
            exclude=args.exclude,
        )
        if missing:
            for raw in missing:
                print(f"error: no such file or folder: {raw}",
                      file=sys.stderr)
            return 2
        if not files:
            print("error: no CSV files found", file=sys.stderr)
            return 2
        results = [(path, check_file(path, args.delimiter))
                   for path in files]
        checked = len(files)
    total = sum(len(problems) for _, problems in results)
    if args.json:
        return report_json(results, checked, total)
    return report_text(results, checked, total)


if __name__ == "__main__":
    sys.exit(main())
