# Anchored neural Value-at-Risk — a pre-registered audit (Project 01)

> **Does anchoring a quantile-loss neural network to a classical VaR prior improve its
> out-of-sample tail forecasts?**

## Research question

A neural network trained on the pinball (quantile) loss can, in principle, learn a sharper
one-day-ahead VaR than a fixed parametric or historical rule. In practice, with little tail
data and a single noisy loss signal, it can also wander into poorly-calibrated or degenerate
forecasts (e.g. a near-constant VaR that games unconditional coverage).

The **anchor** is a regularisation term that pulls the network's VaR toward a classical prior
(parametric-Normal or Historical VaR). The central question is an ablation:

> **Does the anchored NN beat the *same* network trained without the anchor — and does the
> anchor buy anything over the classical prior it is anchored to?**

If the anchored NN does not beat the unanchored NN, the anchor is doing nothing. If it does
not beat the classical prior, the network is not adding value over the rule it leans on. The
result is informative whichever way it lands.

> **Note.** An earlier version of this README described a "Physics-Informed NN" enforcing
> monotonicity in α and sub-additivity. No such constraints are implemented. The actual method
> is anchored quantile regression, and the model is named accordingly throughout.

## Method

The forecast target is the one-day-ahead return quantile at α ∈ {0.05, 0.01} (95% / 99% VaR).

- **Loss:** pinball loss `max((α−1)e, αe)` with `e = y − VaR`, plus an anchor penalty
  `weight · (VaR − VaR_prior)²`. `weight = 0` recovers plain quantile regression.
- **Architectures:** `SimpleQuantileNeuron` (a single linear unit — i.e. linear quantile
  regression, which is the *linear ablation*), `QuantileMLP` (the nonlinear rung) and
  `QuantileLSTM`. Registered in `models/registry.py`.
  **Note:** the linear neuron alone cannot support any claim about "neural networks" — the
  MLP-vs-neuron comparison on identical features is what licenses that language. Expect the
  linear spec's inter-seed IQR to be ≈ 0: pinball loss is convex, so every seed converges to
  the same optimum. Seed dispersion only becomes informative for the nonlinear rungs.
- **Anchors:** `Anchor NN` (parametric-Normal prior, `μ − z_α σ`) and `Anchor Hist NN`
  (rolling Historical VaR prior).
- **Why these priors are sensible:** the pinball-loss surface over (mean, std) multipliers is
  minimised near the classical `μ − z_α σ` point (see `functional_loss.png`), so anchoring to
  the parametric rule pulls the network toward the region the loss already prefers.

## Benchmark ladder

Reported in full — the ablation row is the most informative one.

1. **Trivial floor** — parametric-Normal VaR and rolling Historical VaR (fixed windows).
2. **Industry standard** — GARCH(1,1) with Student-t innovations (a benchmark, not the target
   of the paper).
3. **The ablation** — the unanchored NN: identical architecture and features, `weight = 0`.
4. **The models under test** — `Anchor NN` and `Anchor Hist NN`.

## Scoring (see `src/value_at_risk/evaluation/`)

- **Ranking:** mean **pinball loss** — the strictly consistent loss for a quantile. Models are
  ranked by loss, never by breach-rate pass/fail or "capital reserved".
- **Coverage gate:** **Kupiec** (unconditional) and **Christoffersen** (independence +
  conditional coverage). A model must pass both — a correct breach *count* with *clustered*
  breaches still fails.
- **Comparison:** **Diebold–Mariano** on loss differentials (HAC, bw = 5) for pairs; Model
  Confidence Set when comparing the whole ladder.

`scoring.py` and `protocol.py` are pure numpy/scipy and covered by golden tests:

```bash
cd 01_four_findings_var_audit
pip install -e .            # required: src/ layout, makes `value_at_risk` importable
pip install -e ".[run]"     # + torch / arch / yfinance, needed to actually run the study
python -m pytest -q         # 123 passed, 5 skipped (paths come from pyproject, no PYTHONPATH needed)
```

## Evaluation protocol (`protocol.py`)

- **Chronological TRAIN / VAL / TEST.** The anchor weight, rolling windows and architecture are
  chosen on VAL only; TEST is scored once. No shuffling.
- **Seeds.** NN results are a distribution over ≥ 10 seeds, reported as **median + IQR**, never
  the best seed. If the inter-seed IQR swamps the model-vs-benchmark gap, the honest conclusion
  is "no detectable difference".

## Status — closed

The study is complete and the paper is closed: **a pre-registered null.** Anchoring does not
improve out-of-sample pinball loss, and the one finding that looked robust — reduced inter-seed
dispersion — is an algebraic consequence of L2 shrinkage toward any fixed target, real or
nonsense. Every market result is validation-grade: the test block was scored four times and the
paper says so.

**Paper:** *Stability Is Not Evidence: Shrinkage Artefacts in a Pre-Registered Neural
Value-at-Risk Study* — `main.pdf`, built from `paper/draft-v1.md` (see `ESTADO.md` for the
build rule). It supersedes the July 2026 SSRN preprint *Prior-Anchored Deep Learning VaR*, whose
positive result did not survive this audit; a frozen copy of that preprint is kept in
`paper/_ssrn_v1_prior_anchored/` as the record of the starting state.

**Disclosure integers** (read from the ledger and the run manifests, never counted by hand):
3,555 specifications evaluated; 1,959 test-set evaluations across 16 asset-level cells, four
scoring passes, zero cells scored once.

**Checks that must pass before anything is published:**

```bash
python -m pytest -q                                   # 123 passed, 5 skipped
python scripts/refresh_paper_figures.py --check       # summaries vs result CSVs
python scripts/import_tex.py --check                  # LaTeX current with the markdown
python scripts/check_bib.py                           # refs.bib vs references.md
python -m value_at_risk.evaluation.ledger --summary   # the disclosure integers
```

## Layout

```
src/value_at_risk/
  models/
    registry.py              ← the only place that knows what architectures exist
    deep_var/
      architectures.py       SimpleQuantileNeuron (linear ablation), QuantileMLP, QuantileLSTM
      losses.py              AnchoredQuantileLoss  (pinball + w·(pred − prior)²)
      train.py               walk-forward training loop, registry-driven
      parametric_model.py    parametric & historical priors (the anchors)
      features.py            feature construction
    garch_model.py           GARCH(1,1)-t benchmark (fixed standardized-t quantile)
  evaluation/
    scoring.py               pinball · Kupiec · Christoffersen · Diebold–Mariano
    protocol.py              chronological split · multi-seed median+IQR
    harness.py               VAL-only weight selection · seed loop · CSV
    benchmarks.py            classical rungs as TEST-aligned forecasts
    mcs.py                   Hansen Model Confidence Set
    report.py                ranked ladder table (pinball · DM · MCS · gate)
run_experiment.py            one ticker × one α  → results CSV + meta.json
run_batch_anchored.py        panel × α levels    → anchored_batch_summary.{csv,md}
tests/                       120 tests; torch needed only for the training layer
_archive/                    superseded pipeline + stale results (see _archive/README.md)
```

### Data is frozen, not fetched

The first run downloads each ticker once and writes `data/snapshots/<TICKER>@<END>.csv` plus a
`manifest.json` recording its sha256, row count and date range. Every later run loads that file
and **verifies the hash**, so a rerun cannot silently train on different data. Commit the
snapshots and the manifest.

```bash
python -m value_at_risk.data.snapshot                    # freeze the panel
python -m value_at_risk.data.snapshot --verify           # check nothing drifted
python -m value_at_risk.data.snapshot --force            # deliberate re-freeze (visible in git)
```

Feature construction is frozen too — see `docs/features.md`, pinned by
`tests/test_features_contract.py`.

### Adding a model to test

1. Define the `nn.Module` in `deep_var/architectures.py`.
2. Add one `ModelInfo` entry in `models/registry.py` (declare `expects_sequence` and its
   ladder `rung`).
3. Run it — no other file changes:

```bash
python run_experiment.py --models QuantileMLP --ticker ^GSPC --alpha 0.05 --seeds 10
# nonlinearity ablation: same features, linear vs MLP
python run_batch_anchored.py --models SimpleQuantileNeuron,QuantileMLP --alphas 0.05,0.01
```

## References

- Engle (1982) — ARCH. Bollerslev (1986) — GARCH(1,1).
- Koenker & Bassett (1978) — quantile regression / pinball loss.
- Taylor (2019) - forecasting VaR/ES by a semiparametric asymmetric-Laplace (ES-CAViaR)
  approach. NOTE: an earlier version of this file described this paper as a quantile-loss
  neural network. That was wrong; corrected 2026-08-19. See paper/references.md.
- Kupiec (1995); Christoffersen (1998) — VaR backtesting.
- Diebold & Mariano (1995) — predictive-accuracy comparison.

## Dependencias del sistema (no vienen con pip)

| herramienta | para qué | instalar |
|---|---|---|
| **pandoc** | `scripts/import_tex.py` convierte el markdown a LaTeX | `conda install -c conda-forge pandoc` |
| **LaTeX** (TeX Live / MiKTeX) | compilar `main.tex` | `winget install MiKTeX.MiKTeX` |

`pip install -e .` **no** instala ninguna de las dos. Sin pandoc, `import_tex.py` falla
con una instrucción; sin LaTeX, `latexmk` no existe. Se documentan aquí porque la primera
vez el fallo fue un `FileNotFoundError: [WinError 2]` que no explicaba nada.
