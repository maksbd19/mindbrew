"""Run sample eval cases from gold/sample_cases.yaml and print a results table."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from mindbrew_v2.eval.scorers.base import EvalCase, EvalResult

SAMPLE_CASES_PATH = Path(__file__).parent / "gold" / "sample_cases.yaml"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run sample eval cases and print a table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Offline stubs (fast, no API key)
  uv run python -m mindbrew_v2.eval.run_sample_cases

  # Live Nebius LLM for every case (requires NEBIUS_API_KEY in .env)
  uv run python -m mindbrew_v2.eval.run_sample_cases --live

  # Live LLM — single phase or case
  uv run python -m mindbrew_v2.eval.run_sample_cases --live --phase intake
  uv run python -m mindbrew_v2.eval.run_sample_cases --live --case sample_silicone_e2e_fba_v1
        """.strip(),
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call Nebius LLM (sets BREWMIND_OFFLINE=false; skips offline stubs)",
    )
    parser.add_argument("--phase", type=str, default=None, help="Filter by phase (intake, pathways, …)")
    parser.add_argument("--case", dest="case_ids", action="append", default=[], help="Run only this case id (repeatable)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print progress while each case runs")
    return parser.parse_args()


def configure_runtime(*, live_llm: bool) -> None:
    """Set offline flag before any settings-backed imports run scorers."""
    os.environ["BREWMIND_OFFLINE"] = "false" if live_llm else "true"
    from mindbrew_v2.settings import get_settings

    get_settings.cache_clear()


def validate_live_config() -> list[str]:
    from mindbrew_v2.settings import get_settings

    settings = get_settings()
    errors: list[str] = []
    if settings.brewmind_offline:
        errors.append("BREWMIND_OFFLINE is still true after configure_runtime()")
    key = settings.nebius_api_key or ""
    if not key or key.startswith("your_"):
        errors.append("NEBIUS_API_KEY is missing or still a placeholder — set it in .env")
    if not settings.nebius_base_url:
        errors.append("NEBIUS_BASE_URL is missing")
    return errors


def load_sample_cases() -> list[EvalCase]:
    from mindbrew_v2.eval.scorers.base import EvalCase

    with SAMPLE_CASES_PATH.open() as f:
        data = yaml.safe_load(f) or {}
    cases: list[EvalCase] = []
    for raw in data.get("cases", []):
        case_dict = dict(raw)
        case_dict.setdefault("tier", "offline")
        cases.append(EvalCase(**case_dict))
    return cases


def _run_case(case: EvalCase) -> EvalResult:
    from mindbrew_v2.eval.run_eval import SCORERS
    from mindbrew_v2.eval.scorers.base import EvalResult

    scorer = SCORERS.get(case.phase)
    if not scorer:
        return EvalResult(case.id, case.phase, False, [f"no scorer for phase {case.phase}"], case.weight)
    return scorer(case)


def run_sample_cases(
    *,
    live_llm: bool = False,
    phase: str | None = None,
    case_ids: list[str] | None = None,
    verbose: bool = False,
) -> list[tuple[EvalCase, EvalResult | None, str]]:
    """Return (case, result, status) where status is pass|fail|skipped."""
    configure_runtime(live_llm=live_llm)
    cases = load_sample_cases()
    rows: list[tuple[EvalCase, EvalResult | None, str]] = []
    wanted = set(case_ids or [])

    for case in cases:
        if phase and case.phase != phase:
            continue
        if wanted and case.id not in wanted:
            continue
        if case.requires_live_api and not live_llm:
            rows.append((case, None, "skipped"))
            continue

        if verbose:
            mode = "live LLM" if live_llm else "offline"
            print(f"→ {case.id} ({case.phase}, {mode})…", flush=True)

        result = _run_case(case)
        status = "pass" if result.passed else "fail"
        rows.append((case, result, status))

        if verbose:
            mark = "PASS" if result.passed else "FAIL"
            detail = f" — {'; '.join(result.failures)}" if result.failures else ""
            print(f"  {mark}{detail}", flush=True)

    return rows


def _truncate(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."


def print_table(rows: list[tuple[EvalCase, EvalResult | None, str]]) -> None:
    headers = ("Case ID", "Phase", "Tier", "Status", "Wt", "Failures")
    col_widths = [34, 10, 8, 8, 5, 40]

    def fmt_row(cells: tuple[str, ...]) -> str:
        return " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(cells))

    sep = "-+-".join("-" * w for w in col_widths)
    print(fmt_row(headers))
    print(sep)

    passed = failed = skipped = 0
    weighted_pass = 0.0
    total_weight = 0.0

    for case, result, status in rows:
        total_weight += case.weight
        if status == "skipped":
            skipped += 1
            status_display = "SKIP"
            failures = "pass --live for live-tier cases"
        elif status == "pass":
            passed += 1
            weighted_pass += case.weight
            status_display = "PASS"
            failures = ""
        else:
            failed += 1
            status_display = "FAIL"
            failures = "; ".join(result.failures) if result else ""

        print(
            fmt_row(
                (
                    _truncate(case.id, col_widths[0]),
                    case.phase,
                    case.tier,
                    status_display,
                    f"{case.weight:.1f}",
                    _truncate(failures, col_widths[5]),
                )
            )
        )

    print(sep)
    ran = passed + failed
    acc = f"{100 * passed / ran:.0f}%" if ran else "N/A"
    weighted = f"{100 * weighted_pass / total_weight:.0f}%" if total_weight else "N/A"
    print(f"Ran: {ran}  Passed: {passed}  Failed: {failed}  Skipped: {skipped}  Accuracy: {acc}  Weighted: {weighted}")


def main() -> int:
    args = _parse_args()

    if not SAMPLE_CASES_PATH.is_file():
        print(f"Sample cases not found: {SAMPLE_CASES_PATH}", file=sys.stderr)
        return 1

    if args.live:
        configure_runtime(live_llm=True)
        config_errors = validate_live_config()
        if config_errors:
            for err in config_errors:
                print(f"Error: {err}", file=sys.stderr)
            return 2

    rows = run_sample_cases(
        live_llm=args.live,
        phase=args.phase,
        case_ids=args.case_ids,
        verbose=args.verbose,
    )

    if not rows:
        print("No cases matched filters.", file=sys.stderr)
        return 1

    try:
        rel = SAMPLE_CASES_PATH.relative_to(Path.cwd())
    except ValueError:
        rel = SAMPLE_CASES_PATH

    from mindbrew_v2.settings import get_settings

    settings = get_settings()
    print(f"Source: {rel}")
    print(f"Mode: BREWMIND_OFFLINE={str(settings.brewmind_offline).lower()}  model={settings.nebius_model}")
    print()

    print_table(rows)

    failed = sum(1 for _, _, status in rows if status == "fail")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
