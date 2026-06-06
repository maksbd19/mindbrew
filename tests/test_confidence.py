"""Tests for confidence factor computation."""

import os

os.environ.setdefault("BREWMIND_OFFLINE", "true")

from mindbrew_v2.models import Citation, PathwayCandidate, ReactionStep
from mindbrew_v2.tools.confidence import (
    compute_confidence_factors,
    enrich_pathway_candidate,
    format_references_markdown,
)


def test_compute_confidence_factors():
    candidate = PathwayCandidate(
        id="pw1",
        name="Test pathway",
        reaction_steps=[
            ReactionStep(step_number=1, description="step", heterologous=True),
            ReactionStep(step_number=2, description="step", heterologous=False, enzyme_ec="1.2.1.84"),
        ],
        citations=[
            Citation(doi="10.1002/bit.26067", validation_status="verified", url="https://doi.org/10.1002/bit.26067"),
        ],
        reported_titer="1 g/L",
        biomni_provenance=["literature_search"],
        confidence="strong",
    )
    factors = compute_confidence_factors(candidate)
    assert any("verified citation" in f for f in factors)
    assert any("reported titer" in f for f in factors)
    assert any("heterologous" in f for f in factors)


def test_enrich_pathway_candidate():
    candidate = PathwayCandidate(
        id="pw1",
        name="Test",
        citations=[Citation(doi="10.1002/bit.26067")],
    )
    enriched = enrich_pathway_candidate(candidate)
    assert len(enriched.confidence_factors) > 0


def test_format_references_markdown():
    md = format_references_markdown([
        Citation(
            title="Wax ester paper",
            url="https://doi.org/10.1002/bit.26067",
            validation_status="verified",
        )
    ])
    assert "Wax ester paper" in md
    assert "doi.org" in md
