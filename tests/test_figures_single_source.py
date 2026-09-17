"""Figures must have exactly one source directory, and must not quote retracted statistics.

Why this exists
---------------
`scripts/make_figures.py` writes to `paper/figures/`. A second, byte-different copy of both
figures also lived at `paper/tex/figures/`, and `\\graphicspath` in the root build listed that
directory FIRST -- so every regeneration since 19 August was silently ignored and the built
PDF kept a months-old image. The stale figure carried, rasterised into the PNG, the sign test
that Appendix B.3 withdraws: the prose retracted the statistic and the figure went on showing
it. That is the Appendix B.2 defect ("the file the numbers are read from must itself be
derived") a fourth time, in a file format where nobody thinks to look.
"""
from __future__ import annotations

import hashlib
import os

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
CANONICAL = os.path.join(ROOT, "paper", "figures")
SHADOW = os.path.join(ROOT, "paper", "tex", "figures")
FIGURES = ("figure1_dose_response.png", "figure2_control.png")


def _digest(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


@pytest.mark.parametrize("name", FIGURES)
def test_no_shadow_copy_of_the_figure(name: str):
    """A second copy is allowed only if it is byte-identical; a diverged one shadows the build."""
    shadow = os.path.join(SHADOW, name)
    if not os.path.exists(shadow):
        return
    canonical = os.path.join(CANONICAL, name)
    assert os.path.exists(canonical), f"{name} exists only in the shadow directory"
    assert _digest(shadow) == _digest(canonical), (
        f"{name} differs between paper/figures/ and paper/tex/figures/. The build resolves "
        f"one of them and it is not necessarily the one make_figures.py just wrote. Delete "
        f"the shadow copy rather than syncing it."
    )


def test_graphicspath_prefers_the_generated_directory():
    """The directory make_figures.py writes to must be searched before any other."""
    with open(os.path.join(ROOT, "main.tex"), encoding="utf-8") as f:
        line = next(l for l in f if "\\graphicspath" in l and not l.lstrip().startswith("%"))
    first = line.split("{{", 1)[1].split("}", 1)[0]
    # \includegraphics args are "figures/<name>", so the first search prefix must resolve
    # <prefix>/figures/<name> onto the directory make_figures.py writes.
    resolved = os.path.normpath(os.path.join(ROOT, first, "figures", FIGURES[0]))
    assert resolved == os.path.normpath(os.path.join(CANONICAL, FIGURES[0])), (
        f"graphicspath searches {first!r} first, which resolves to {resolved!r}; "
        f"make_figures.py writes to paper/figures/."
    )


def test_figure_does_not_quote_the_withdrawn_sign_test():
    """B.3 withdrew the p-value; it must not survive rasterised inside the figure."""
    with open(os.path.join(ROOT, "scripts", "make_figures.py"), encoding="utf-8") as f:
        src = f.read()
    body = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    assert "sign_test_p" not in body, (
        "make_figures.py draws the withdrawn sign test into the figure (Appendix B.3)."
    )
