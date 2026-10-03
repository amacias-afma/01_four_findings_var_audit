"""The two LaTeX build roots must not drift apart.

Why this exists
---------------
There are two roots: `main.tex` (repository root, for Overleaf and SSRN) and
`paper/tex/main.tex` (for `make named` / `make anon`, the build that goes to TMLR). Titles,
the front page and section headings live in those roots, not in the markdown. After the
17 September revision `paper/tex/main.tex` still carried the old title and the old Section 7
heading, so the PDF that would have been submitted would have shown a retracted title. Two
sources of truth that separated: the Appendix B defect again, in a file nobody regenerates.
"""
from __future__ import annotations

import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
MAIN_ROOT = os.path.join(ROOT, "main.tex")
MAIN_TMLR = os.path.join(ROOT, "paper", "tex", "main.tex")

HEADING = re.compile(r"\\(section|subsection|subsubsection\*?)\s*\{")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    # drop comments (an unescaped % to end of line)
    return re.sub(r"(?<!\\)%.*", "", text)


def _group(text: str, start: int) -> tuple[str, int]:
    """Return the brace-balanced group whose opening brace is at text[start - 1]."""
    depth, i = 1, start
    while depth:
        c = text[i]
        if c == "\\":
            i += 2
            continue
        depth += c == "{"
        depth -= c == "}"
        i += 1
    return text[start:i - 1], i


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\\\\", " ")).strip()


def headings(text: str) -> list[tuple[str, str, str]]:
    out = []
    for m in HEADING.finditer(text):
        title, end = _group(text, m.end())
        lab = re.match(r"\s*\\label\{([^}]*)\}", text[end:])
        out.append((m.group(1), _norm(title), lab.group(1) if lab else ""))
    return out


def inputs(text: str) -> list[str]:
    names = re.findall(r"\\input\{([^}]*)\}", text)
    return [os.path.basename(n) for n in names if "sections/" in n]


def title(text: str) -> str:
    m = re.search(r"\\title\s*\{", text)
    body, _ = _group(text, m.end())
    body = re.sub(r"\\textbf\s*", "", body)
    return _norm(body.replace("{", "").replace("}", ""))


def test_headings_and_labels_match():
    assert headings(_read(MAIN_ROOT)) == headings(_read(MAIN_TMLR))


def test_section_inputs_match():
    assert inputs(_read(MAIN_ROOT)) == inputs(_read(MAIN_TMLR))


def test_titles_match():
    assert title(_read(MAIN_ROOT)) == title(_read(MAIN_TMLR))
