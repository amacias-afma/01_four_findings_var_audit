# Supplementary archive

To reproduce the paper's checks, from the root of this archive:

```bash
pip install -e ".[run]"
python -m pytest -q                                  # all tests pass, 0 skipped
python -m value_at_risk.data.snapshot --verify       # frozen inputs, sha256
python -m value_at_risk.evaluation.ledger --summary  # the disclosure integers
python scripts/refresh_paper_figures.py --check      # figures file vs result files
python scripts/make_figures.py                       # Figures 1 and 2, from the CSVs
python scripts/measure_contraction.py                # accuracy of the derivation in §3.5
```

The price snapshots are not redistributed (vendor terms). The sha256 manifest in
`data/snapshots/` allows a reader to verify a re-download against the frozen inputs.
