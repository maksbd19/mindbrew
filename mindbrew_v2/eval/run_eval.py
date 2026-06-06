"""Eval CLI — scorecard by phase."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import yaml

from mindbrew_v2.eval.scorers.base import EvalCase, EvalResult
from mindbrew_v2.eval.scorers.e2e import score_e2e
from mindbrew_v2.eval.scorers.fba import score_fba
from mindbrew_v2.eval.scorers.formalize import score_formalize
from mindbrew_v2.eval.scorers.intake import score_intake
from mindbrew_v2.eval.scorers.pathways import score_pathways

GOLD_PATH = Path(__file__).parent / "gold" / "cases.yaml"
REPORTS_DIR = Path(__file__).parent / "reports"

SCORERS = {
    "intake": score_intake,
    "pathways": score_pathways,
    "formalize": score_formalize,
    "fba": score_fba,
    "e2e": score_e2e,
}


def load_cases() -> list[EvalCase]:
    with GOLD_PATH.open() as f:
        data = yaml.safe_load(f)
    return [EvalCase(**c) for c in data.get("cases", [])]


def run_eval(phase: str | None = None, live: bool = False) -> list[EvalResult]:
    cases = load_cases()
    results: list[EvalResult] = []

    for case in cases:
        if phase and case.phase != phase:
            continue
        if case.requires_live_api and not live:
            continue

        scorer = SCORERS.get(case.phase)
        if not scorer:
            continue
        results.append(scorer(case))

    return results


def render_scorecard(results: list[EvalResult]) -> str:
    by_phase: dict[str, list[EvalResult]] = defaultdict(list)
    for r in results:
        by_phase[r.phase].append(r)

    lines = ["# Brewmind Eval Scorecard", "", f"Generated: {datetime.now().isoformat()}", ""]
    lines.append("| Phase | Passed | Total | Accuracy |")
    lines.append("|-------|--------|-------|----------|")

    total_pass = 0
    total_weight = 0.0
    weighted_pass = 0.0

    for phase in sorted(by_phase.keys()):
        rows = by_phase[phase]
        passed = sum(1 for r in rows if r.passed)
        total = len(rows)
        acc = f"{100 * passed / total:.0f}%" if total else "N/A"
        lines.append(f"| {phase} | {passed} | {total} | {acc} |")
        total_pass += passed
        for r in rows:
            total_weight += r.weight
            if r.passed:
                weighted_pass += r.weight

    overall = f"{100 * weighted_pass / total_weight:.0f}%" if total_weight else "N/A"
    lines.extend(["", f"**Overall (weighted):** {overall}", ""])

    failed = [r for r in results if not r.passed]
    if failed:
        lines.append("## Failures")
        for r in failed:
            lines.append(f"- `{r.case_id}`: {'; '.join(r.failures)}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Run Brewmind eval harness")
    parser.add_argument("--phase", type=str, default=None)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()

    import os

    os.environ.setdefault("BREWMIND_OFFLINE", "true")

    results = run_eval(phase=args.phase, live=args.live)
    scorecard = render_scorecard(results)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = REPORTS_DIR / f"scorecard_{stamp}.md"
    json_path = REPORTS_DIR / f"scorecard_{stamp}.json"
    md_path.write_text(scorecard)
    json_path.write_text(
        json.dumps([{"case_id": r.case_id, "passed": r.passed, "failures": r.failures} for r in results], indent=2)
    )
    print(scorecard)


if __name__ == "__main__":
    main()
