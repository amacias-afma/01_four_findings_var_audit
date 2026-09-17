"""Split `paper/draft-v1.md` into LaTeX fragments under `paper/tex/sections/`.

Why a script and not hand transcription
---------------------------------------
Appendix C of the paper reports five citation errors, four of them introduced by copying a
source's *description* rather than the source. Retyping 7,000 words of prose into LaTeX is
the same operation at larger scale. So the conversion is mechanical and repeatable: edit the
markdown, re-run this, and the LaTeX follows.

Consequence, stated so nobody is surprised: **`paper/draft-v1.md` is the source of truth.**
Hand edits to `paper/tex/sections/*.tex` are overwritten on the next import. Anything that
must live only in the LaTeX (float placement, `\\ref`, layout) belongs in `main.tex` or in
the manual-override list below.

    python scripts/import_tex.py            # convert
    python scripts/import_tex.py --check    # verify the .tex is current, exit 1 if stale
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys

SRC = os.path.join("paper", "draft-v1.md")
OUT = os.path.join("paper", "tex", "sections")

# markdown heading -> fragment filename. Order matters only for readability.
MAP = [
    ("## Abstract",                              "abstract"),
    ("## 1. Introduction",                       "01-introduction"),
    ("### 1.1 Where this paper came from",       "01a-provenance"),
    ("### 1.2 Setting and scope",                "01b-scope"),
    ("## 2. Setup",                              "02-setup"),
    ("## 3. Four findings and their withdrawals", "03-findings"),
    ('### 3.1 "Anchoring improves',              "03a-multiplicity"),
    ('### 3.2 "Weight selection',                "03b-power"),
    ('### 3.3 "Higher capacity',                 "03c-capacity"),
    ('### 3.4 "Anchoring stabilises',            "03d-tautology"),
    ("### 3.5 The artefact isolated",            "03e-synthetic"),
    ("## 4. Disclosure",                         "04-disclosure"),
    ("## 5. Three defects",                      "05-defects"),
    ("## 6. Checks on this study",               "06-checks"),
    ("## 7. Controls, what they caught",                       "07-taxonomy"),
    ("## 8. Limitations",                        "08-limitations"),
    ("## 9. Conclusion",                         "09-conclusion"),
    ("## Reproducibility statement",             "10-reproducibility"),
    ("## Appendix A",                            "A-ledger"),
    ("## Appendix B",                            "B-corrections"),
    ("## Appendix C",                            "C-citations"),
    ("## Appendix D",                            "D-survey"),
    ("## Appendix E",                            "E-selection"),
]

# Cross-reference rewriting: the markdown says "§3.4", LaTeX should say \Cref{sec:tautology}.
XREF = {
    r"§1\.1": r"\\Cref{sec:provenance}", r"§1\.2": r"\\Cref{sec:scope}",
    r"§3\.1": r"\\Cref{sec:multiplicity}", r"§3\.2": r"\\Cref{sec:power}",
    r"§3\.3": r"\\Cref{sec:capacity}", r"§3\.4": r"\\Cref{sec:tautology}",
    r"§3\.5": r"\\Cref{sec:synthetic}", r"§1\b": r"\\Cref{sec:intro}",
    r"§2\b": r"\\Cref{sec:setup}", r"§3\b": r"\\Cref{sec:findings}",
    r"§4\b": r"\\Cref{sec:disclosure}", r"§5\b": r"\\Cref{sec:defects}",
    r"§6\b": r"\\Cref{sec:checks}", r"§7\b": r"\\Cref{sec:taxonomy}",
    r"§8\b": r"\\Cref{sec:limitations}", r"§9\b": r"\\Cref{sec:conclusion}",
    r"Appendix A": r"\\Cref{app:ledger}", r"Appendix B\.2": r"\\Cref{app:corrections}",
    r"Appendix B": r"\\Cref{app:corrections}", r"Appendix C": r"\\Cref{app:citations}",
    r"Appendix D": r"\\Cref{app:survey}",
    r"Appendix E": r"\\Cref{app:selection}",
}

# Figure label -> (LaTeX label, caption). Captions live here because the markdown carries
# only pandoc alt-text, and alt-text became the caption: the typeset paper read
# "Figure 1: Figure 1". The caption WAS defined in this dict and the emitter unpacked it into
# a throwaway `_cap` and never wrote it out -- a value defined, carried, and dropped one line
# from where it was needed. standards/figures-and-disclosure.md requires a caption stating
# what is plotted, the sample, n, and the takeaway; alt-text satisfies none of that.
FIGURES = {
    "figures/figure1_dose_response.png": ("fig:dose",
        r"\textbf{The dose--response that convinced us, and it is an artefact.} "
        r"Inter-seed IQR reduction (unanchored $\div$ anchored, log scale) against the anchor "
        r"weight selected on validation, pooled across the four scoring passes; eight "
        r"instruments, two quantile levels, ten-year frozen snapshots; $n = 85$ comparisons. "
        r"Spearman $\rho = +0.585$, $p = 4.1 \times 10^{-9}$. The same relationship appears "
        r"when the anchor is replaced by one carrying no information (\Cref{fig:control}), "
        r"which is why the curve is not evidence that the prior is good."),
    "figures/figure2_control.png": ("fig:control",
        r"\textbf{The same effect, with a matched control.} "
        r"(a) Empirical, three assets at $\alpha = 0.05$: replacing the anchor with a "
        r"scale-matched permutation of itself leaves the stabilisation intact --- the permuted "
        r"anchor stabilises at least as much as the real one in 3 of 6 comparisons "
        r"(Wilcoxon $p = 0.84$). (b) Synthetic, ground truth known: inter-seed IQR reduction "
        r"against penalty weight $w$ over a ten-point log-spaced grid and 40 seeds, for the "
        r"true optimum and a scale-matched nonsense anchor; $n = 30$ non-zero-weight cells. "
        r"The contraction tracks the penalty, not the target."),
}

# Author-year mentions -> natbib commands.
#
# Why this exists
# ---------------
# The prose is written in markdown, which has no citation markup, so the first LaTeX build
# produced a bibliography with **zero entries**: bibtex reported "I found no \citation
# commands". `scripts/check_bib.py` had said so plainly — "42 entries not yet cited in the
# LaTeX" — and that warning was dismissed as an artefact of an in-progress import. It was
# not. A check fired, was explained away, and the paper compiled without references.
#
# Mapping here rather than editing the markdown keeps `paper/draft-v1.md` readable as prose
# and keeps the conversion mechanical. Order matters: longest patterns first, so that
# "Ojala & Garriga (2010)" is consumed before any shorter overlapping pattern.
#
# `\citet` = textual ("Cawley and Talbot (2010) established"); `\citep` = parenthetical.
CITATIONS = [
    # multi-work parentheticals first — these must not be split
    (r"\(Fisher 1935;\s*\n?Pitman 1937; Ojala & Garriga 2010\)",
     r"\\citep{fisher1935design,pitman1937significance,ojala2010permutation}"),
    (r"\(Fisher 1935; Pitman 1937\)",
     r"\\citep{fisher1935design,pitman1937significance}"),
    # textual mentions
    (r"Bertrand, Duflo and Mullainathan \(2004\)", r"\\citet{bertrand2004how}"),
    (r"Cawley and Talbot \(2010\)", r"\\citet{cawley2010over}"),
    (r"Cawley & Talbot \(2010\)", r"\\citet{cawley2010over}"),
    (r"Ojala and Garriga \(2010\)", r"\\citet{ojala2010permutation}"),
    (r"Ojala & Garriga \(2010\)", r"\\citet{ojala2010permutation}"),
    (r"Zhang et al\. \(2017\)", r"\\citet{zhang2017understanding}"),
    (r"Adebayo et al\. \(2018\)", r"\\citet{adebayo2018sanity}"),
    (r"Madani et al\. \(2004\)", r"\\citet{madani2004covalidation}"),
    (r"Taylor \(2019\)", r"\\citet{taylor2019forecasting}"),
    (r"Fisher \(1935\)", r"\\citet{fisher1935design}"),
    (r"Bhojanapalli et\s*\n?al\. \(2021\)", r"\\citet{bhojanapalli2021reproducibility}"),
    # parenthetical mentions
    (r"\(Lin et al\. 2024\)", r"\\citep{lin2024registered}"),
    (r"\(Bhojanapalli et al\. 2021\)", r"\\citep{bhojanapalli2021reproducibility}"),
    (r"\(Petneházi 2019\)", r"\\citep{petnehazi2021quantile}"),
]


# Unicode the T1 fonts cannot set. Each is mapped rather than dropped, because a silently
# dropped minus sign in the contraction formula would corrupt the paper's central equation.
_SUBS = {
    "\u2014": "---", "\u2013": "--", "\u2212": "$-$", "\u221e": r"$\infty$",
    "\u2264": r"$\leq$", "\u2265": r"$\geq$", "\u2248": r"$\approx$", "\u2260": r"$\neq$",
    "\u00d7": r"$\times$", "\u00f7": r"$\div$", "\u00b1": r"$\pm$",
    "\u2192": r"$\to$", "\u2190": r"$\leftarrow$", "\u21d2": r"$\Rightarrow$",
    "\u03c1": r"$\rho$", "\u03b1": r"$\alpha$", "\u03b2": r"$\beta$", "\u03bc": r"$\mu$",
    "\u03c3": r"$\sigma$", "\u03b7": r"$\eta$", "\u03bd": r"$\nu$", "\u03c4": r"$\tau$",
    "\u0394": r"$\Delta$", "\u03b8": r"$\theta$", "\u03bb": r"$\lambda$", "\u03a3": r"$\Sigma$",
    "\u00a7": r"\S", "\u2026": r"\ldots", "\u00b7": r"$\cdot$",
}

# Inside verbatim LaTeX sets characters literally, so a math substitution would print
# "$-$" as visible text. Fall back to ASCII lookalikes there.
_VERBATIM_ASCII = {
    "\u2014": "--", "\u2212": "-", "\u00d7": "x", "\u2264": "<=",
    "\u2265": ">=", "\u2248": "~", "\u2192": "->", "\u221e": "inf",
}


def split_sections(text: str) -> dict[str, str]:
    """Cut the markdown at each mapped heading. Unmapped headings stay inside their parent."""
    marks = []
    for needle, name in MAP:
        i = text.find(needle)
        if i < 0:
            print(f"  [warn] heading not found, fragment will be empty: {needle!r}")
            continue
        marks.append((i, needle, name))
    marks.sort()
    out = {}
    for k, (i, needle, name) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(text)
        body = text[i + len(needle):end]
        # drop the remainder of the heading line
        body = body.split("\n", 1)[1] if "\n" in body else ""
        out[name] = body.strip()
    return out


def require_pandoc() -> None:
    """Fail with an instruction instead of a traceback when pandoc is missing.

    This conversion shells out to pandoc, which is a system dependency and not a Python
    one, so `pip install -e .` does not provide it. On a machine without it the original
    failure was a bare `FileNotFoundError: [WinError 2]` from subprocess — accurate and
    useless. A dependency that is only discovered by crashing is not documented.
    """
    if shutil.which("pandoc") is None:
        sys.exit(
            "\nERROR: pandoc not found on PATH.\n\n"
            "This script converts paper/draft-v1.md to LaTeX using pandoc, which is a\n"
            "system dependency (pip does not install it). Install it with ONE of:\n\n"
            "  conda install -c conda-forge pandoc     # inside your conda env\n"
            "  winget install --id JohnMacFarlane.Pandoc   # Windows, system-wide\n"
            "  sudo apt install pandoc                 # Debian/Ubuntu\n"
            "  brew install pandoc                     # macOS\n\n"
            "Then re-run:  python scripts/import_tex.py\n"
        )


def apply_citations(md: str) -> str:
    """Rewrite author-year prose into natbib commands, before pandoc sees it."""
    for pat, rep in CITATIONS:
        md = re.sub(pat, rep, md)
    return md


def to_latex(md: str) -> str:
    md = apply_citations(md)
    p = subprocess.run(
        ["pandoc", "--from=markdown+pipe_tables+raw_tex", "--to=latex",
         "--wrap=preserve", "--no-highlight"],
        input=md, capture_output=True, text=True, check=True)
    tex = p.stdout

    # pandoc ALREADY emits a figure float for a lone image. Do not wrap it again: nesting
    # floats raises "Not in outer par mode". Set the width and attach our label instead, so
    # the prose can \Cref it.
    for path, (label, cap) in FIGURES.items():
        tex = re.sub(
            r"\\includegraphics(\[[^\]]*\])?\{" + re.escape(path) + r"\}",
            r"\\includegraphics[width=\\linewidth]{" + path + r"}",
            tex)

        # Write the real caption over pandoc's alt-text, and put \label AFTER \caption --
        # a label before the caption binds to the enclosing counter, so \Cref would have
        # resolved to the wrong number.
        def _caption(match, path=path, label=label, cap=cap):
            block = match.group(0)
            if path not in block:
                return block
            return re.sub(r"\\caption\{[^}]*\}",
                          lambda _: "\\caption{" + cap + "}\n\\label{" + label + "}",
                          block, count=1)

        tex = re.sub(r"\\begin\{figure\}.*?\\end\{figure\}", _caption, tex, flags=re.S)
    tex = tex.replace(r"\begin{figure}" + "\n", r"\begin{figure}[t]" + "\n")
    tex = tex.replace(r"\pandocbounded{", "{")

    # Cross-references and unicode are rewritten ONLY outside verbatim. An earlier version
    # applied XREF to the whole document, so a "\S3.5" inside a shell comment became the
    # literal string "\Cref{sec:synthetic}" in the typeset code block — visible to the
    # reader as raw LaTeX. Verbatim means verbatim; protect it once and apply both passes
    # to the prose only.
    parts = re.split(r"(\\begin\{verbatim\}.*?\\end\{verbatim\})", tex, flags=re.S)
    for i, part in enumerate(parts):
        if part.startswith(r"\begin{verbatim}"):
            for u, a in _VERBATIM_ASCII.items():
                part = part.replace(u, a)
            parts[i] = part
            continue
        for pat, rep in XREF.items():
            part = re.sub(pat, rep, part)
        for u, r in _SUBS.items():
            part = part.replace(u, r)
        parts[i] = part
    tex = "".join(parts)

    # Any remaining non-Latin-1 character is a transcription hazard: fail loudly rather than
    # let pdflatex drop it. This is the same discipline as the numbers check.
    leftover = sorted({c for c in tex if ord(c) > 0x2000})
    if leftover:
        print(f"  [warn] unmapped unicode still present: {leftover}")
    return tex


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify the fragments match the markdown; do not write")
    args = ap.parse_args()

    if not os.path.exists(SRC):
        print(f"MISSING: {SRC}", file=sys.stderr)
        return 2
    require_pandoc()
    os.makedirs(OUT, exist_ok=True)
    text = open(SRC, encoding="utf-8").read()

    stale = []
    for name, md in split_sections(text).items():
        tex = to_latex(md) if md.strip() else "% (empty section)\n"
        path = os.path.join(OUT, f"{name}.tex")
        new = hashlib.sha256(tex.encode()).hexdigest()
        old = (hashlib.sha256(open(path, "rb").read()).hexdigest()
               if os.path.exists(path) else None)
        if new != old:
            stale.append(name)
            if not args.check:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(tex)
        print(f"  {'stale' if new != old else 'ok   '}  {name}")

    if args.check and stale:
        print(f"\n--check: {len(stale)} fragment(s) out of date. Run without --check.")
        return 1
    print(f"\n{'Verified' if args.check else 'Wrote'} {OUT}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
