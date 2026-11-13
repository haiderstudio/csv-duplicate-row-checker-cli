# Sample output

Output of `sh examples/run-example.sh` — the checker run over the
whole `examples/` folder (4 files, 3 problems in 2 files):

```
FAIL examples/crlf.csv:2: duplicate row, first seen on line 2, repeats on line 3: 1,Alice,90
FAIL examples/duplicates.csv:2: duplicate row, first seen on line 2, repeats on lines 4, 7: 1,Alice,90
FAIL examples/duplicates.csv:3: duplicate row, first seen on line 3, repeats on line 5: 3,Carol,88
examples/good.csv: OK
examples/quoted.csv: OK
Checked 4 file(s), 3 problem(s) in 2 file(s).
```

`examples/crlf.csv` has the same row twice with Windows line
endings, and `examples/duplicates.csv` has two rows repeated —
`1,Alice,90` on lines 4 and 7, and `3,Carol,88` on line 5.
`examples/good.csv` and `examples/quoted.csv` are clean: the
quoted commas, doubled quotes, and multi-line quoted fields in
them are valid CSV, and no row repeats.
