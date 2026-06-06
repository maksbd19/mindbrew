"""Eval CLI — scorecard by phase."""

from __future__ import annotations

import argparse
import json
import os
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

GOLD_DIR = Path(__file__).parent / "gold"
OFFLINE_CASES_PATH = GOLD_DIR / "cases.yaml"
LIVE_CASES_PATH = GOLD_DIR / "live_cases.yaml"
REPORTS_DIR = Path(__file__).parent / "reports"

SCORERS = {
    "intake": score_intake,
    "pathways": score_pathways,
    "formalize": score_formalize,
    "fba": score_fba,
    "e2e": score_e2e,
}


def _load_yaml_cases(path: Path, default_tier: str) -> list[EvalCase]:
    if not path.exists():
        return []
    with path.open() as f:
        data = yaml.safe_load(f) or {}
    cases: list[EvalCase] = []
    for raw in data.get("cases", []):
        case_dict = dict(raw)
        case_dict.setdefault("tier", default_tier)
        cases.append(EvalCase(**case_dict))
    return cases


def load_cases(*, tier: str = "offline") -> list[EvalCase]:
    cases: list[EvalCase] = []
    if tier in ("offline", "all"):
        cases.extend(_load_yaml_cases(OFFLINE_CASES_PATH, "offline"))
    if tier in ("live", "all"):
        cases.extend(_load_yaml_cases(LIVE_CASES_PATH, "live"))
    return cases


def run_eval(
    phase: str | None = None,
    *,
    tier: str = "offline",
    live: bool = False,
) -> list[EvalResult]:
    if tier == "all" and live:
        os.environ["BREWMIND_OFFLINE"] = "true"
        offline_results = _run_eval_pass(phase=phase, tier="offline", live=False)
        os.environ["BREWMIND_OFFLINE"] = "false"
        live_results = _run_eval_pass(phase=phase, tier="live", live=True)
        return offline_results + live_results

    if tier in ("offline", "all"):
        os.environ["BREWMIND_OFFLINE"] = "true"
    elif tier == "live":
        os.environ["BREWMIND_OFFLINE"] = "false"

    return _run_eval_pass(phase=phase, tier=tier, live=live)


def _run_eval_pass(
    phase: str | None,
    *,
    tier: str,
    live: bool,
) -> list[EvalResult]:
    cases = load_cases(tier=tier)
    results: list[EvalResult] = []

    for case in cases:
        if phase and case.phase != phase:
            continue
        if case.requires_live_api and not live:
            continue
        if not case.requires_live_api and tier == "live":
            continue

        scorer = SCORERS.get(case.phase)
        if not scorer:
            continue
        results.append(scorer(case))

    return results


def render_scorecard(results: list[EvalResult], *, tier: str) -> str:
    by_phase: dict[str, list[EvalResult]] = defaultdict(list)
    for r in results:
        by_phase[r.phase].append(r)

    lines = [
        "# Brewmind Eval Scorecard",
        "",
        f"Generated: {datetime.now().isoformat()}",
        f"Tier: {tier}",
        "",
    ]
    lines.append("| Phase | Passed | Total | Accuracy |")
    lines.append("|-------|--------|-------|----------|")

    total_weight = 0.0
    weighted_pass = 0.0

    for phase_name in sorted(by_phase.keys()):
        rows = by_phase[phase_name]
        passed = sum(1 for r in rows if r.passed)
        total = len(rows)
        acc = f"{100 * passed / total:.0f}%" if total else "N/A"
        lines.append(f"| {phase_name} | {passed} | {total} | {acc} |")
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
    parser.add_argument("--tier", choices=["offline", "live", "all"], default="offline")
    parser.add_argument("--live", action="store_true", help="Run cases that require live API")
    args = parser.parse_args()

    if args.tier == "live" and not args.live:
        parser.error("--tier live requires --live")

    results = run_eval(phase=args.phase, tier=args.tier, live=args.live)
    scorecard = render_scorecard(results, tier=args.tier)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = REPORTS_DIR / f"scorecard_{args.tier}_{stamp}.md"
    json_path = REPORTS_DIR / f"scorecard_{args.tier}_{stamp}.json"
    md_path.write_text(scorecard)
    json_path.write_text(
        json.dumps(
            [{"case_id": r.case_id, "passed": r.passed, "failures": r.failures, "weight": r.weight} for r in results],
            indent=2,
        )
    )
    print(scorecard)


if __name__ == "__main__":
    main()
