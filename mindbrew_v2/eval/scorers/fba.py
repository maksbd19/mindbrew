"""FBA phase scorer."""

from __future__ import annotations

import json
from pathlib import Path

from mindbrew_v2.eval.scorers.base import EvalCase, EvalResult
from mindbrew_v2.models import ScorePathwayPayload
from mindbrew_v2.tools.fba_client import score_pathway

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def score_fba(case: EvalCase) -> EvalResult:
    failures = []
    ref = case.input.get("score_pathway_payload_ref", "")
    payload = ScorePathwayPayload.model_validate(json.loads((FIXTURES / ref).read_text()))
    result = score_pathway(payload)

    for assertion in case.assertions:
        atype = assertion.get("type")
        if atype == "fba_status":
            if result.status != assertion.get("value"):
                failures.append(f"status: {result.status} != {assertion['value']}")
        elif atype == "fba_verdict_in":
            if result.verdict not in assertion.get("values", []):
                failures.append(f"verdict: {result.verdict} not in {assertion['values']}")

    return EvalResult(case.id, case.phase, len(failures) == 0, failures, case.weight)
