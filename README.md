# csv-duplicate-row-checker-cli

Check CSV files for exact duplicate rows, fail CI when any are found.

[![CI](https://github.com/haiderstudio/csv-duplicate-row-checker-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/haiderstudio/csv-duplicate-row-checker-cli/actions/workflows/ci.yml) [![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE)

## What it does

`csv_duplicate_row_checker` reads each CSV file you point it at
and reports every row that appears more than once, with the line
it first appeared on and every line it repeats on:

- A duplicated row double-counts a record — a sale, a user, a
  reading — and downstream totals come out wrong with no error
  anywhere. This tool reports the repeated row, the line it
  first appeared on, and every line it repeats on, so you can
  find the extra copy at once. The `duplicates.csv` example has
  `1,Alice,90` first on line 2 and repeated on lines 4 and 7,
  and `3,Carol,88` first on line 3 and repeated on line 5.
- Rows are compared exactly, on their parsed field values: the
  same fields in the same order, case-sensitive, no trimming. A
  row that differs by one character, one space, or one extra
  column is a different row and is not flagged. Quoting style
  does not matter — `"1","Alice","90"` and `1,Alice,90` are the
  same row, because the values are the same.
- The header row counts as a row — a data row identical to the
  header is a duplicate of it. A blank line carries no record,
  so it is skipped (empty rows are repo #73's
  `csv-empty-checker-cli`'s job, not this one's).
- A quoted field that spans several lines (an address with a
  line break inside quotes, for example) is one row, and its
  line is the line where the row starts. A quoted field with a
  comma inside it is one field, not two — the `quoted.csv`
  example has both and passes clean.
- A file that cannot be parsed at all — an unbalanced quote — is
  reported as a problem for that file, with the line where the
  parse failed, and any duplicates found before that line are
  still reported. A line with a NUL byte in it is reported as a
  problem for that line, and the rest of the file is still
  checked. Fixing the broken quoting is repo #80's
  `csv-quote-checker-cli`'s job.
- It exits 1 when any duplicate row (or an unreadable file) is
  found, so it can fail a CI run. A clean folder exits 0.
- CSV files come from the command line (one or more), or from a
  folder walk: every `.csv` file under a folder, recursively by
  default (`--no-recursive` stops at the top level). `.git` and
  `__pycache__` folders are never walked, and directory links
  are never followed, so a link cycle cannot loop the check.
- `--delimiter` sets the field separator, for example
  `--delimiter ';'` for semicolon files. A file checked with
  the wrong delimiter is not an error — it is just checked with
  the wrong field split — so pick the delimiter your files use.
- `--exclude PATTERN` skips walked files by glob, for example
  `--exclude 'draft-*'`. It can be repeated. A file passed
  directly on the command line is always checked, even if it
  matches an exclude pattern and even if it has no `.csv`
  extension.
- `--stdin` reads one CSV document from standard input.
- `--json` prints the result as machine-readable JSON (the
  summary goes to standard error, so standard output stays
  clean JSON). Each duplicate carries `first_seen`, the list
  of `repeat_lines`, and the `row` itself.
- It is report-only and runs fully offline: it never edits a
  file, sends nothing anywhere, and needs no API key. Python
  standard library only — the `csv` module does the parsing,
  and a seen-set remembers the first line each row appeared on.

## What it does NOT do

- It does not check column counts — that is repo #58's
  `csv-column-count-checker-cli`. A row with the wrong number
  of columns but no duplicate passes here.
- It does not check empty rows or empty cells — that is repo
  #73's `csv-empty-checker-cli`. A blank line passes here.
- It does not check the header row's names or duplicates —
  that is repo #40's `csv-header-checker-cli`. (A data row
  identical to the header is still flagged here, because it
  is a repeated row.)
- It does not check quotes — that is repo #80's
  `csv-quote-checker-cli`. An unbalanced quote is reported
  only as a file that cannot be parsed, not as a quoting
  problem.
- It does not compare rows across files. Each file is checked
  on its own: the same row in two different files is not a
  duplicate here. Cross-file comparison is a different job
  (see "How this differs").
- It does not do fuzzy matching. `Alice` and `alice`, or
  `90` and `90 `, are different rows. Deciding two rows mean
  the same thing is your job.
- It does not fix a duplicate. A repeated row is reported;
  deciding which copy to keep is your job.
- An empty file passes: it has no rows to repeat. A
  header-only file passes for the same reason.

## Who it is for

Anyone who ships CSV data files and wants each record counted
once: a data analyst checking a spreadsheet export before it
goes into a database, a developer adding a CI step that fails
the build when a data file has a doubled row, or anyone
tidying a folder of CSVs before the totals are made. One
duplicated row is invisible in the file itself — this catches
it before the totals do.

## How this differs from similar tools

The exact name `csv-duplicate-row-checker-cli` matches 0
repositories on GitHub (checked Nov 11, 2026), and the wider
field is small: `csv duplicate row checker` matches 11
repositories. The top ones are Laovvi/duplicateRowChecker,
0 stars — it compares rows across TWO folders (a cross-folder
diff, a different job from checking one file); libmld-dev/
CSVRowChecker, 0 stars — "Checks CSV files for duplicate row
across multiple columns" (the exact job, 0 stars, no test or
CI claim); and anvrachnouu/csv-duplicates-checker, 0 stars —
the exact job (Greek description, 0 stars, no test or CI
claim). Two more tools check duplicate rows as one check
among several in a quality report (SamirMatani13/
CSVQualityChecker and hassan-m-saleeh/
python-data-quality-checker, both 0 stars, neither with a CI
claim). Three 0-star tools do the exact job, none with a test
or CI claim. None of them is a tested Python CLI that checks
CSV files for exact duplicate rows as its one job, reports
each repeated row with the line it first appeared on and
every line it repeats on, and exits 1 for CI. This tool does
that one job: a Python standard-library-only CLI that checks
CSV files for exact duplicate rows — no install beyond
Python, no website, no network.

## Install

Python standard library only — no packages to download. You need
Python 3.8 or newer. Clone the repo and run it in place:

```
git clone https://github.com/haiderstudio/csv-duplicate-row-checker-cli.git
cd csv-duplicate-row-checker-cli
python3 src/csv_duplicate_row_checker.py examples/good.csv
```

```
examples/good.csv: OK
OK — 1 file(s) checked, no duplicate rows.
```

## Usage

Check one clean file (quoted commas, doubled quotes, and a
multi-line quoted field all pass, and no row repeats):

```
python3 src/csv_duplicate_row_checker.py examples/good.csv
```

```
examples/good.csv: OK
OK — 1 file(s) checked, no duplicate rows.
```

Check a file with duplicate rows (`1,Alice,90` first on line 2,
repeated on lines 4 and 7; `3,Carol,88` first on line 3,
repeated on line 5):

```
python3 src/csv_duplicate_row_checker.py examples/duplicates.csv
```

```
FAIL examples/duplicates.csv:2: duplicate row, first seen on line 2, repeats on lines 4, 7: 1,Alice,90
FAIL examples/duplicates.csv:3: duplicate row, first seen on line 3, repeats on line 5: 3,Carol,88
Checked 1 file(s), 2 problem(s) in 1 file(s).
```

Check a file of quoted fields with commas and line breaks
inside the quotes — no row repeats, so it passes:

```
python3 src/csv_duplicate_row_checker.py examples/quoted.csv
```

```
examples/quoted.csv: OK
OK — 1 file(s) checked, no duplicate rows.
```

Check a file with Windows line endings — the duplicate is
still caught, on the right lines:

```
python3 src/csv_duplicate_row_checker.py examples/crlf.csv
```

```
FAIL examples/crlf.csv:2: duplicate row, first seen on line 2, repeats on line 3: 1,Alice,90
Checked 1 file(s), 1 problem(s) in 1 file(s).
```

Check a whole folder:

```
python3 src/csv_duplicate_row_checker.py examples/
```

```
FAIL examples/crlf.csv:2: duplicate row, first seen on line 2, repeats on line 3: 1,Alice,90
FAIL examples/duplicates.csv:2: duplicate row, first seen on line 2, repeats on lines 4, 7: 1,Alice,90
FAIL examples/duplicates.csv:3: duplicate row, first seen on line 3, repeats on line 5: 3,Carol,88
examples/good.csv: OK
examples/quoted.csv: OK
Checked 4 file(s), 3 problem(s) in 2 file(s).
```

Check a semicolon file — first make one, then check it with
the flag (delete it after; it is only a scratch file):

```
printf 'id;name;score\n1;Alice;90\n1;Alice;90\n' > semi.csv
python3 src/csv_duplicate_row_checker.py --delimiter ';' semi.csv
rm semi.csv
```

```
FAIL semi.csv:2: duplicate row, first seen on line 2, repeats on line 3: 1;Alice;90
Checked 1 file(s), 1 problem(s) in 1 file(s).
```

Check one document from standard input:

```
python3 src/csv_duplicate_row_checker.py --stdin < examples/duplicates.csv
```

```
FAIL <stdin>:2: duplicate row, first seen on line 2, repeats on lines 4, 7: 1,Alice,90
FAIL <stdin>:3: duplicate row, first seen on line 3, repeats on line 5: 3,Carol,88
Checked 1 file(s), 2 problem(s) in 1 file(s).
```

Machine-readable output with `--json` (the summary goes to
standard error, so standard output stays clean JSON):

```
python3 src/csv_duplicate_row_checker.py --json examples/duplicates.csv
```

```
{
  "files": [
    {
      "file": "examples/duplicates.csv",
      "problems": [
        {
          "file": "examples/duplicates.csv",
          "line": 2,
          "reason": "duplicate row, first seen on line 2, repeats on lines 4, 7: 1,Alice,90",
          "first_seen": 2,
          "repeat_lines": [
            4,
            7
          ],
          "row": [
            "1",
            "Alice",
            "90"
          ]
        },
        {
          "file": "examples/duplicates.csv",
          "line": 3,
          "reason": "duplicate row, first seen on line 3, repeats on line 5: 3,Carol,88",
          "first_seen": 3,
          "repeat_lines": [
            5
          ],
          "row": [
            "3",
            "Carol",
            "88"
          ]
        }
      ]
    }
  ],
  "summary": {
    "checked": 1,
    "files_with_problems": 1,
    "problems": 2
  }
}
```

Exit codes: 0 when every checked file is clean, 1 when any
duplicate row (or an unreadable file) is found, 2 for a usage
problem (no files given, a bad flag, a bad `--delimiter`
value, or a missing file or folder).

## Examples

### 1. A folder of data files, default comma delimiter

`examples/` holds four CSV files. Two are clean, two have
duplicate rows:

```
python3 src/csv_duplicate_row_checker.py examples/
```

```
FAIL examples/crlf.csv:2: duplicate row, first seen on line 2, repeats on line 3: 1,Alice,90
FAIL examples/duplicates.csv:2: duplicate row, first seen on line 2, repeats on lines 4, 7: 1,Alice,90
FAIL examples/duplicates.csv:3: duplicate row, first seen on line 3, repeats on line 5: 3,Carol,88
examples/good.csv: OK
examples/quoted.csv: OK
Checked 4 file(s), 3 problem(s) in 2 file(s).
```

### 2. Quoted fields that look alike but are not duplicates

`examples/quoted.csv` has three rows whose quoted fields hold
commas and line breaks. None of the rows repeat, so the file
passes — the commas inside quotes never split a field, and the
line breaks inside quotes never split a row:

```
python3 src/csv_duplicate_row_checker.py examples/quoted.csv
```

```
examples/quoted.csv: OK
OK — 1 file(s) checked, no duplicate rows.
```

### 3. The bundled examples, all at once

```
sh examples/run-example.sh
```

The script checks the whole `examples/` folder (fail, on
purpose — it picks up the duplicate rows). Its full output is in
`examples/sample-output.md`, ending with `Checked 4 file(s),
3 problem(s) in 2 file(s).` The failing run exits 1, which
is the expected result — the script ends with exit 0 so it
can be run as a demo.

## How it is tested

Tests, standard library `unittest` only, no packages to install:

```
python3 tests/test_csv_duplicate_row_checker.py
```

The tests cover: exact duplicate detection (one repeat, a row
repeated twice, two different rows repeated in one file, the
first-seen line and every repeat line, a row repeated three
times), rows that must not be flagged (a different case, an
extra space, an extra column, a missing column, quoting style
only), clean files (a header-only file, an empty file, a file
with no trailing newline, blank lines skipped, a data row
identical to the header flagged), quoted fields (commas inside
quotes, a doubled quote, a multi-line quoted field duplicated
— reported on the line where the row starts — a quoted field
duplicated with different quoting), CRLF line endings, edge
cases (a NUL byte, an unbalanced quote reported as a parse
problem with duplicates found before it still reported, a
custom delimiter, a tab-delimited file, an unreadable path),
file collection (a good file, a missing path, a folder walk,
`.git` skipped, `--no-recursive`, `--exclude`, a direct file
checked even without a `.csv` extension and even if
excluded, an empty folder, uppercase `.CSV` extensions,
sorted and deduplicated results), the CLI (exit 0/1/2, each
flag, `--stdin` good and bad, `--json` output with
`first_seen`, `repeat_lines`, and `row`, `--version`, bad
flags, a bad delimiter, missing paths, a folder summary
count, and every bundled example file read back with its
expected problems), the bundled examples (sample output
compared byte-for-byte against a fresh run, and the
README-quoted outputs checked against it),
working-directory robustness (the tests pass from the repo
root, from a temp folder, and from the filesystem root —
paths are checked by file name and message, never by an
absolute path), and hygiene checks (no placeholder text, no
absolute paths, stdlib imports only, `.env` first in
`.gitignore`, CI file runs the test file).

## Contributing

Small, focused improvements are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE).

## Original work

This tool was written from scratch for this repo. The idea
of checking CSV files for duplicate rows is not new — the
similar tools named above (the cross-folder comparer, the
two 0-star duplicate checkers, and the two quality-report
tools) are listed in "How this differs" — but every line of
code here is original, and the tool builds on nothing but
Python's standard library.
