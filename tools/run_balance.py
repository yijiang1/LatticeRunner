#!/usr/bin/env python3
"""Run deterministic Lattice Runner playtests in a headless browser.

The browser executes the real simulation embedded in index.html.  This file
only launches batches, aggregates their terminal states, and writes reports.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
from pathlib import Path
import signal
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HTML = ROOT / "index.html"
CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "chromium",
    "chromium-browser",
)
UPGRADES = ("volt", "recon", "det", "blank", "fov", "cryo", "sparse", "scan", "piezo", "shift")


def find_browser(explicit: str | None = None) -> str:
    candidates = (explicit,) if explicit else CHROME_CANDIDATES
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if path.is_file():
            return str(path)
        found = shutil.which(candidate)
        if found:
            return found
    raise RuntimeError(
        "No Chromium-based browser found. Pass --browser /path/to/chrome."
    )


def parse_balance_dom(document: str) -> dict[str, Any]:
    marker = '<pre id="balance-json">'
    start = document.find(marker)
    if start < 0:
        raise RuntimeError("The game did not emit a balance result.")
    start += len(marker)
    end = document.find("</pre>", start)
    if end < 0:
        raise RuntimeError("The balance result was truncated.")
    payload = html.unescape(document[start:end])
    result = json.loads(payload)
    if "error" in result:
        raise RuntimeError(f"Game balance runner failed:\n{result['error']}")
    return result


def run_browser(
    browser: str,
    game_html: Path,
    *,
    runs: int,
    seed: int,
    samples: str,
    modes: str,
    profiles: str,
    rigs: str,
    timeout: int,
) -> dict[str, Any]:
    query = urlencode(
        {
            "balance": "1",
            "runs": runs,
            "seed": seed,
            "samples": samples,
            "modes": modes,
            "profiles": profiles,
            "rigs": rigs,
        }
    )
    url = game_html.resolve().as_uri() + "?" + query
    with tempfile.TemporaryDirectory(prefix="lattice-balance-") as profile_dir:
        command = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--disable-extensions",
            "--disable-background-networking",
            "--disable-component-update",
            "--disable-sync",
            "--metrics-recording-only",
            "--no-first-run",
            "--no-default-browser-check",
            "--virtual-time-budget=1000",
            f"--user-data-dir={profile_dir}",
            "--dump-dom",
            url,
        ]
        stdout_path = Path(profile_dir) / "dom.html"
        stderr_path = Path(profile_dir) / "chrome.log"
        with stdout_path.open("wb") as stdout_file, stderr_path.open("wb") as stderr_file:
            process = subprocess.Popen(
                command,
                stdout=stdout_file,
                stderr=stderr_file,
                start_new_session=True,
            )
            deadline = time.monotonic() + timeout
            document = ""
            while time.monotonic() < deadline:
                stdout_file.flush()
                if stdout_path.exists() and stdout_path.stat().st_size:
                    document = stdout_path.read_text(encoding="utf-8", errors="replace")
                    if '<pre id="balance-json">' in document and "</pre>" in document:
                        break
                if process.poll() is not None:
                    break
                time.sleep(0.1)

            if process.poll() is None:
                # Chrome helpers can retain stdout after --dump-dom has
                # completed. They all live in this dedicated process group.
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait(timeout=5)
            if not document and stdout_path.exists():
                document = stdout_path.read_text(encoding="utf-8", errors="replace")
            if '<pre id="balance-json">' not in document:
                details = stderr_path.read_text(encoding="utf-8", errors="replace").strip()
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"Headless browser timed out after {timeout}s:\n{details}")
                raise RuntimeError(f"Headless browser exited {process.returncode}:\n{details}")
    return parse_balance_dom(document)


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lo = math.floor(position)
    hi = math.ceil(position)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo)


def summarize(results: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for row in results:
        key = (row["specimen"], row["mode"], row["profile"], row["rig"])
        groups.setdefault(key, []).append(row)

    summary: list[dict[str, Any]] = []
    for key in sorted(groups):
        rows = groups[key]
        percents = [float(row["percent"]) for row in rows]
        doses = [float(row["dose"]) for row in rows]
        summary.append(
            {
                "specimen": key[0],
                "mode": key[1],
                "profile": key[2],
                "rig": key[3],
                "runs": len(rows),
                "completionRate": sum(bool(row["completed"]) for row in rows) / len(rows),
                "meanPercent": statistics.fmean(percents),
                "medianPercent": statistics.median(percents),
                "p10Percent": percentile(percents, 0.10),
                "p90Percent": percentile(percents, 0.90),
                "meanDose": statistics.fmean(doses),
                "meanDamage": statistics.fmean(float(row["damaged"]) for row in rows),
                "meanFalls": statistics.fmean(float(row["falls"]) for row in rows),
                "meanPicks": statistics.fmean(float(row["picks"]) for row in rows),
            }
        )
    return summary


def recommendations(summary: list[dict[str, Any]]) -> list[str]:
    """Turn paired stock/upgrade panels into conservative tuning prompts."""
    by_cell = {
        (row["specimen"], row["mode"], row["profile"], row["rig"]): row
        for row in summary
    }
    notes: list[str] = []
    marginal: dict[str, list[float]] = {upgrade: [] for upgrade in UPGRADES}
    for row in summary:
        if row["rig"] != "stock":
            continue
        base_key = (row["specimen"], row["mode"], row["profile"])
        for upgrade in UPGRADES:
            upgraded = by_cell.get((*base_key, f"{upgrade}3"))
            if upgraded:
                marginal[upgrade].append(upgraded["meanPercent"] - row["meanPercent"])

    measured = {key: statistics.fmean(values) for key, values in marginal.items() if values}
    for upgrade, delta in sorted(measured.items(), key=lambda item: item[1], reverse=True):
        if delta > 18:
            notes.append(
                f"{upgrade.upper()} level 3 adds {delta:.1f} coverage points on average; "
                "review it for dominance or move part of its value into earlier levels."
            )
        elif delta < 1:
            notes.append(
                f"{upgrade.upper()} level 3 adds only {delta:.1f} coverage points on average; "
                "its benefit may be too situational or invisible to these player models."
            )

    for row in summary:
        if row["rig"] != "stock":
            if row["rig"] == "max" and row["profile"] == "novice" and row["completionRate"] > 0.80:
                notes.append(
                    f"The max rig gives the novice bot {row['completionRate']:.0%} completion on "
                    f"{row['specimen']} / {row['mode']}; the endgame may be flattening the level."
                )
            continue
        if row["profile"] == "expert" and row["completionRate"] < 0.35:
            notes.append(
                f"Stock expert completion is {row['completionRate']:.0%} on "
                f"{row['specimen']} / {row['mode']}; verify the goal or route geometry."
            )
        if row["profile"] == "novice" and row["completionRate"] > 0.80:
            notes.append(
                f"Stock novice completion is {row['completionRate']:.0%} on "
                f"{row['specimen']} / {row['mode']}; the opening may not create enough pressure."
            )
    return notes or ["No automatic threshold was crossed; inspect the paired distributions before changing constants."]


def markdown_report(payload: dict[str, Any], summary: list[dict[str, Any]]) -> str:
    lines = [
        "# Lattice Runner balance report",
        "",
        f"Balance version: **{payload.get('balanceVersion', '?')}**",
        f"Fixed timestep: **{payload.get('fixedDt', 0):.6f}s**",
        f"Runs per cell: **{payload.get('runsPerCell', '?')}**",
        "",
        "| Specimen | Mode | Player | Rig | Clear | Coverage (median, p10–p90) | Dose | Damage | Falls | Picks |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['specimen']} | {row['mode']} | {row['profile']} | {row['rig']} | "
            f"{row['completionRate']:.0%} | {row['medianPercent']:.1f}% "
            f"({row['p10Percent']:.1f}–{row['p90Percent']:.1f}) | "
            f"{row['meanDose']:.1f} | {row['meanDamage']:.1f} | "
            f"{row['meanFalls']:.1f} | {row['meanPicks']:.2f} |"
        )
    lines.extend(["", "## Automatic review", ""])
    lines.extend(f"- {note}" for note in recommendations(summary))
    lines.extend(
        [
            "",
            "> Bot results are regression evidence, not a substitute for human feel tests. "
            "Use their seeds to reproduce changes, then validate candidate tuning with players.",
            "",
        ]
    )
    return "\n".join(lines)


def expand_rigs(value: str) -> str:
    names = [item.strip() for item in value.split(",") if item.strip()]
    expanded: list[str] = []
    for name in names:
        if name == "marginal":
            expanded.extend(f"{upgrade}3" for upgrade in UPGRADES)
        else:
            expanded.append(name)
    return ",".join(dict.fromkeys(expanded))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=10, help="seeded runs per matrix cell")
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--samples", default="graphene,scandate,mepedf")
    parser.add_argument("--modes", default="session,sprint")
    parser.add_argument("--profiles", default="novice,intermediate,expert")
    parser.add_argument(
        "--rigs",
        default="stock,max",
        help="stock,max, individual IDs such as recon3, or marginal for every level-3 line",
    )
    parser.add_argument("--browser", help="path to a Chromium-based browser")
    parser.add_argument("--game", type=Path, default=DEFAULT_HTML)
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "balance")
    parser.add_argument("--timeout", type=int, default=240, help="browser timeout in seconds")
    parser.add_argument("--quiet", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.runs < 1 or args.runs > 500:
        raise SystemExit("--runs must be between 1 and 500")
    browser = find_browser(args.browser)
    payload = run_browser(
        browser,
        args.game,
        runs=args.runs,
        seed=args.seed,
        samples=args.samples,
        modes=args.modes,
        profiles=args.profiles,
        rigs=expand_rigs(args.rigs),
        timeout=args.timeout,
    )
    summary = summarize(payload["results"])
    report = markdown_report(payload, summary)
    args.output.mkdir(parents=True, exist_ok=True)
    raw_path = args.output / "balance-results.json"
    report_path = args.output / "balance-report.md"
    raw_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")
    if not args.quiet:
        print(report)
        print(f"Raw results: {raw_path}", file=sys.stderr)
        print(f"Report: {report_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
