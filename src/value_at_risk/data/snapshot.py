"""Frozen data snapshots - download once, then reproduce forever.

The problem this solves: ``read_data`` pulls a rolling 10-year window from yfinance at call
time, so rerunning the study next month silently trains on different data and every published
number quietly changes. Hashing the frame after the fact detects drift but does not prevent it.

The rule here: **the first run downloads and writes a CSV snapshot plus a manifest entry with
its sha256; every later run loads that file and verifies the hash.** A changed or corrupted
snapshot raises instead of silently altering results. Re-downloading is possible but explicit
(``force_download=True`` / ``--force``), and it rewrites the manifest entry so the change is
visible in git.

Layout:

    data/snapshots/manifest.json
    data/snapshots/GSPC@2026-06-30.csv
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

import pandas as pd

DEFAULT_SNAPSHOT_DIR = os.path.join("data", "snapshots")
MANIFEST_NAME = "manifest.json"

__all__ = [
    "SnapshotEntry", "snapshot_key", "snapshot_filename", "sha256_file",
    "load_manifest", "save_manifest", "get_prices", "verify_snapshots",
]


@dataclass(frozen=True)
class SnapshotEntry:
    ticker: str
    end_date: str
    filename: str
    sha256: str
    rows: int
    first_date: str
    last_date: str
    source: str
    retrieved_at_utc: str


def snapshot_key(ticker: str, end_date: str) -> str:
    return f"{ticker}@{end_date}"


def _safe(ticker: str) -> str:
    """Filesystem-safe ticker: ^GSPC -> GSPC, CLP=X -> CLP_X, BRK.B -> BRK_B."""
    return re.sub(r"[^A-Za-z0-9\-]+", "_", ticker).strip("_")


def snapshot_filename(ticker: str, end_date: str) -> str:
    return f"{_safe(ticker)}@{end_date}.csv"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(snapshot_dir: str = DEFAULT_SNAPSHOT_DIR) -> dict:
    path = os.path.join(snapshot_dir, MANIFEST_NAME)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(manifest: dict, snapshot_dir: str = DEFAULT_SNAPSHOT_DIR) -> None:
    os.makedirs(snapshot_dir, exist_ok=True)
    path = os.path.join(snapshot_dir, MANIFEST_NAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)


def _write_csv(df: pd.DataFrame, path: str) -> None:
    """Deterministic write, so the hash is stable across runs on the same data."""
    out = df.copy()
    out.index.name = "date"
    out.to_csv(path, float_format="%.10f", date_format="%Y-%m-%d")


def _read_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, index_col="date", parse_dates=["date"])
    return df


def get_prices(
    ticker: str,
    end_date: str,
    snapshot_dir: str = DEFAULT_SNAPSHOT_DIR,
    source: str = "yfinance",
    force_download: bool = False,
    downloader=None,
) -> pd.DataFrame:
    """Return the frozen price frame for ``(ticker, end_date)``.

    Loads the snapshot if present (verifying its sha256), otherwise downloads once and
    freezes it. ``downloader`` is injectable for tests; by default it calls
    ``data.market.read_data`` lazily so this module imports without yfinance.
    """
    os.makedirs(snapshot_dir, exist_ok=True)
    key = snapshot_key(ticker, end_date)
    fname = snapshot_filename(ticker, end_date)
    fpath = os.path.join(snapshot_dir, fname)
    manifest = load_manifest(snapshot_dir)

    if os.path.exists(fpath) and not force_download:
        entry = manifest.get(key)
        if entry is None:
            raise FileNotFoundError(
                f"snapshot {fname} exists but has no manifest entry; delete it or "
                f"re-run with force_download=True to re-freeze it"
            )
        actual = sha256_file(fpath)
        if actual != entry["sha256"]:
            raise ValueError(
                f"snapshot hash mismatch for {key}:\n"
                f"  manifest: {entry['sha256']}\n  on disk : {actual}\n"
                f"The frozen data changed. Results built on it are not reproducible."
            )
        return _read_csv(fpath)

    if downloader is None:
        def downloader(tk, ed):                      # lazy: keeps yfinance optional
            from value_at_risk.data.market import read_data
            return read_data(ticker=tk, market_data_source=source, end_date=ed)

    df = downloader(ticker, end_date)
    if df is None or len(df) == 0:
        raise ValueError(f"downloader returned no rows for {key}")
    df = df.sort_index()
    _write_csv(df, fpath)

    manifest[key] = asdict(SnapshotEntry(
        ticker=ticker, end_date=end_date, filename=fname, sha256=sha256_file(fpath),
        rows=int(len(df)), first_date=str(pd.Timestamp(df.index[0]).date()),
        last_date=str(pd.Timestamp(df.index[-1]).date()), source=source,
        retrieved_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    ))
    save_manifest(manifest, snapshot_dir)
    return _read_csv(fpath)


def verify_snapshots(snapshot_dir: str = DEFAULT_SNAPSHOT_DIR) -> list[str]:
    """Check every manifest entry against disk. Returns a list of problems (empty == clean)."""
    manifest = load_manifest(snapshot_dir)
    problems = []
    for key, entry in manifest.items():
        path = os.path.join(snapshot_dir, entry["filename"])
        if not os.path.exists(path):
            problems.append(f"{key}: file missing ({entry['filename']})")
            continue
        actual = sha256_file(path)
        if actual != entry["sha256"]:
            problems.append(f"{key}: hash mismatch (expected {entry['sha256'][:12]}..., "
                            f"got {actual[:12]}...)")
    return problems


def main():
    import argparse

    ap = argparse.ArgumentParser(description="Freeze or verify price snapshots.")
    ap.add_argument("--tickers", default="^GSPC,BTC-USD,TSLA,NVDA,SQM,CLP=X,HG=F,CL=F")
    ap.add_argument("--end-date", default="2026-06-30")
    ap.add_argument("--snapshot-dir", default=DEFAULT_SNAPSHOT_DIR)
    ap.add_argument("--force", action="store_true", help="re-download and re-freeze")
    ap.add_argument("--verify", action="store_true", help="only verify existing snapshots")
    args = ap.parse_args()

    if args.verify:
        problems = verify_snapshots(args.snapshot_dir)
        if problems:
            print("PROBLEMS:")
            for p in problems:
                print("  -", p)
            raise SystemExit(1)
        print(f"All snapshots in {args.snapshot_dir} verified clean.")
        return

    for ticker in [t.strip() for t in args.tickers.split(",") if t.strip()]:
        try:
            df = get_prices(ticker, args.end_date, args.snapshot_dir,
                            force_download=args.force)
            print(f"{ticker:10s} rows={len(df):5d}  {df.index[0].date()} -> {df.index[-1].date()}")
        except Exception as exc:
            print(f"{ticker:10s} FAILED: {exc}")
    print(f"\nManifest: {os.path.join(args.snapshot_dir, MANIFEST_NAME)}")


if __name__ == "__main__":
    main()
