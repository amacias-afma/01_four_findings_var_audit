"""The figures file the paper is generated from must agree with the result files.

This is the control for the near-miss recorded in draft §3.5: after the E7 correction the
demonstration outputs were rewritten and `paper_figures.json` was not, so it kept the exact
pair of numbers whose quotient was the retracted "2.5x" headline. Prose was correct; the
machine-readable summary was stale. These tests make the derivation testable and the drift
detectable.
"""
from __future__ import annotations

import json
import os

import pytest

pytest.importorskip("pandas")

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from refresh_paper_figures import (  # noqa: E402
    DEMO_CSV, DEMO_PAIRED, FIGURES, LEDGER, demo_fields, disclosure_fields,
)

_HAVE_OUTPUTS = all(os.path.exists(p) for p in (DEMO_CSV, DEMO_PAIRED, FIGURES))
needs_outputs = pytest.mark.skipif(not _HAVE_OUTPUTS, reason="demo outputs not present")


@needs_outputs
def test_figures_file_matches_demo_outputs():
    """The regression that actually happened: figures file drifting from its sources."""
    derived = demo_fields()
    with open(FIGURES, encoding="utf-8") as f:
        figures = json.load(f)
    stale = [k for k, v in derived.items()
             if k not in figures or abs(float(figures[k]) - v) > 1e-12 * max(1.0, abs(v))]
    assert not stale, (
        f"paper_figures.json is stale in {stale}. "
        f"Run `python scripts/refresh_paper_figures.py`."
    )


@needs_outputs
def test_retracted_cherry_picked_pair_is_absent():
    """Guard the specific values E7 removed, so they cannot reappear unnoticed.

    5.570818 / 13.851437 = 2.49, the 'nonsense stabilises 2.5x more' figure the Editor
    rejected as the largest of four cells. Named explicitly because a generic staleness
    check would pass on any self-consistent-but-wrong file.
    """
    with open(FIGURES, encoding="utf-8") as f:
        figures = json.load(f)
    for key, retracted in (("truth_ratio", 5.570817881915514),
                           ("nonsense_ratio", 13.851437014782304)):
        assert abs(figures[key] - retracted) > 1e-9, (
            f"{key} holds the retracted four-weight value {retracted}; "
            f"the E7 correction has been reverted."
        )


@needs_outputs
def test_paired_claim_is_the_one_the_paper_makes():
    """The draft claims 9 of 10 weights and a median paired ratio near parity.

    The sign test that once accompanied the count (p = 0.021) was WITHDRAWN in Appendix B.3:
    the ten grid cells lie along one smooth monotone curve, so they are not the ten
    independent draws the test assumes. This test no longer asserts that p-value -- asserting
    it would pin the suite to a statistic the paper has retracted. The count and the ratio are
    what Section 3.5 now claims, and they are what is checked.
    """
    d = demo_fields()
    assert d["demo_paired_n"] == 10
    assert d["demo_paired_k"] == 9
    # The claim is 'at least as much', not 'more' - the median must be near parity, not large.
    assert 1.0 <= d["demo_paired_median"] < 1.2


@needs_outputs
def test_withdrawn_sign_test_is_not_quoted_in_the_draft():
    """B.3 withdrew the p-value. Guard it the way B.1's cherry-picked pair is guarded."""
    draft = os.path.join(os.path.dirname(__file__), "..", "paper", "draft-v1.md")
    if not os.path.exists(draft):
        pytest.skip("draft not present")
    with open(draft, encoding="utf-8") as f:
        text = f.read()
    body = text.split("## Appendix B")[0]
    # The value may appear ONCE, in the sentence that records the withdrawal -- this paper
    # retracts in public rather than deleting. What must not reappear is the value quoted as
    # a live claim, so every occurrence has to sit next to the word "withdrawn".
    hits = [i for i in range(len(body)) if body.startswith("0.021", i)]
    for i in hits:
        window = body[max(0, i - 250):i + 250]
        assert "withdrawn" in window, (
            "the withdrawn sign test p-value is quoted in the body of the draft outside its "
            "retraction; Appendix B.3 retracted it."
        )
    assert len(hits) <= 1, f"expected at most one retraction mention, found {len(hits)}"


@needs_outputs
def test_dose_response_spans_every_anchor():
    """The demonstration's point is that the dose-response holds for ANY target.

    30 = 10 non-zero weights x 3 anchors. If this collapses to 10 or 20, the correlation is
    being computed within a single anchor and no longer supports the claim made.
    """
    d = demo_fields()
    assert d["demo_n"] == 30
    assert d["demo_weights"] == 10
    assert d["demo_rho"] > 0.9


# --- The disclosure integers -------------------------------------------------------------
# standards/figures-and-disclosure.md requires TWO integers. The draft carried one, and the
# four ledger fields in paper_figures.json were literals that --check did not cover.

_HAVE_LEDGER = os.path.exists(LEDGER)
needs_ledger = pytest.mark.skipif(not _HAVE_LEDGER, reason="ledger not present")


@needs_ledger
def test_both_disclosure_integers_are_present_and_derived():
    """Non-negotiable #6: specifications evaluated AND test-set evaluations."""
    derived = disclosure_fields()
    with open(FIGURES, encoding="utf-8") as f:
        figures = json.load(f)
    for k in ("specs", "evals"):
        assert k in figures, f"{k} missing from paper_figures.json"
        assert figures[k] == derived[k], f"{k} stale: {figures[k]} != {derived[k]}"


@needs_ledger
def test_evaluation_count_comes_from_the_ledger_not_the_manifests():
    """The 60-evaluation gap is the reason the ledger exists. Guard it explicitly."""
    d = disclosure_fields()
    assert d["evals"] == 1959
    assert d["specs_manifest_evals"] == 1899
    assert d["evals_no_manifest"] == 60, (
        "the ledger/manifest gap changed; Section 4 and Appendix A both quote 60."
    )


@needs_ledger
def test_specification_count_is_declared_a_lower_bound():
    """specs omits the two unmanifested debugging runs; the draft must not imply otherwise."""
    d = disclosure_fields()
    assert d["specs_is_lower_bound"] == 1
    assert d["specs"] > d["evals"], "fewer specifications than evaluations is implausible"
