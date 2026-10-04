"""Build the anonymised supplementary archive for double-blind review.

The repository is NOT edited to anonymise it. HEAD is exported to a temporary directory and
only that copy is transformed: identifying files are dropped, a `SUPPLEMENT.md` is added,
identifying strings are replaced in text files, and the result is scanned. If anything
identifying survives, or the paper's figures no longer reconcile with the result files inside
the copy, the build fails and lists every hit. Binary files are never rewritten, only scanned.

    python scripts/build_supplement.py paper/tex/four-findings-supplement.zip
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

REMOVE = ["CITATION.cff", ".zenodo.json", "LICENSE", "README.md", "docs",
          os.path.join("paper", "_ssrn_v1_prior_anchored")]
REMOVE_SUFFIX = (".pdf",)

# Most specific first.
REPLACEMENTS = [
    ("C:\\Users\\fe_ma", "<HOME>"), ("C:/Users/fe_ma", "<HOME>"),
    ("fe_ma", "<user>"),
    ("amacias@afmaing.cl", "<email>"),
    ("Álvaro F. Macías Araya", "Anonymous"), ("Alvaro Macias", "Anonymous"),
    ("Macías", "Anonymous"), ("Macias", "Anonymous"),
    ("AFMA Ingeniería SpA", "<org>"), ("AFMA Ingenieria SpA", "<org>"),
    ("AFMA Ingenier{\\'\\i}a SpA", "<org>"), ("AFMA", "<org>"),
    ("amacias-afma", "<org>"),
]

LEAKS = ["Macías", "Macias", "Álvaro", "Alvaro", "amacias", "afmaing", "AFMA",
         "0000-0003-0669-1503", "zenodo.22020013", "6669538", "7317079", "fe_ma"]
LEAK_RE = re.compile("|".join(re.escape(x) for x in LEAKS), re.IGNORECASE)
BIN_RE = re.compile(rb"fe_ma|macias|mac\xc3\xadas|afma", re.IGNORECASE)


def files(root):
    for d, dirs, names in os.walk(root):
        dirs[:] = [x for x in dirs if not x.startswith(".git")]
        for n in names:
            yield os.path.join(d, n)


def read_text(path):
    raw = open(path, "rb").read()
    if b"\0" in raw:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def main(out_zip: str) -> int:
    repo = os.getcwd()
    out_zip = os.path.abspath(out_zip)
    tmp = tempfile.mkdtemp(prefix="supplement-")
    root = os.path.join(tmp, "copy")
    os.makedirs(root)
    try:
        tar = os.path.join(tmp, "head.tar")
        subprocess.run(["git", "archive", "--format=tar", "-o", tar, "HEAD"], check=True)
        subprocess.run(["tar", "-xf", tar, "-C", root], check=True)

        for rel in REMOVE:
            p = os.path.join(root, rel)
            if os.path.isdir(p):
                shutil.rmtree(p)
            elif os.path.exists(p):
                os.remove(p)
        for p in list(files(root)):
            base = os.path.basename(p)
            if p.endswith(REMOVE_SUFFIX) or base.startswith(".git"):
                os.remove(p)
        shutil.copy(os.path.join("paper", "tex", "SUPPLEMENT.md"),
                    os.path.join(root, "SUPPLEMENT.md"))

        applied: dict[str, dict[str, int]] = {}
        binaries = []
        for p in files(root):
            text = read_text(p)
            rel = os.path.relpath(p, root)
            if text is None:
                binaries.append(p)
                continue
            new = text
            for old, rep in REPLACEMENTS:
                n = new.count(old)
                if n:
                    applied.setdefault(rel, {})[old] = n
                    new = new.replace(old, rep)
            if new != text:
                with open(p, "w", encoding="utf-8", newline="") as f:
                    f.write(new)

        print("Replacements applied (file: string x count):")
        for rel in sorted(applied):
            for old, n in applied[rel].items():
                print(f"  {rel}: {old!r} x {n}")

        hits = []
        for p in files(root):
            rel = os.path.relpath(p, root)
            if LEAK_RE.search(rel):
                hits.append(f"{rel}: (file name)")
            text = read_text(p)
            if text is None:
                if BIN_RE.search(open(p, "rb").read()):
                    hits.append(f"{rel}: (binary file, not rewritten)")
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if LEAK_RE.search(line):
                    hits.append(f"{rel}:{i}: {line.strip()[:110]}")
        if hits:
            print("\nFAIL: identifying strings remain in the supplementary archive:")
            for h in hits:
                print("  " + h)
            return 1

        r = subprocess.run([sys.executable, "scripts/refresh_paper_figures.py", "--check"],
                           cwd=root, capture_output=True, text=True)
        if r.returncode != 0:
            print("\nFAIL: refresh_paper_figures.py --check fails inside the copy "
                  "(the replacement touched something it should not have):")
            print(r.stdout + r.stderr)
            return 1

        if os.path.exists(out_zip):
            os.remove(out_zip)
        with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
            for p in files(root):
                z.write(p, os.path.relpath(p, root))
        print(f"\nOK  no identifying strings; figures check passes inside the copy\n-> {out_zip}")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "four-findings-supplement.zip"))
