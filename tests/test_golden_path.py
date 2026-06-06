"""Golden path E2E test — Ticket 1 offline pipeline."""

import os

import pytest

os.environ["BREWMIND_OFFLINE"] = "true"

from mindbrew_v2.config.gem import select_gem
from mindbrew_v2.models import Ticket, ValidationMode
from mindbrew_v2.phases.biomni import run_biomni_search
from mindbrew_v2.phases.formalize import formalize_pathways
from mindbrew_v2.phases.intake import run_intake
from mindbrew_v2.phases.report import generate_report
from mindbrew_v2.demo_tickets import TICKET_1
from mindbrew_v2.tools.fba_client import rank_fba_results, score_pathway


@pytest.fixture
def ticket1_brief():
    ticket = Ticket(id="golden-ticket1", raw_brief=TICKET_1)
    return run_intake(ticket)


def test_ticket1_intake(ticket1_brief):
    assert ticket1_brief.gatekeeper_verdict == "PROCEED"
    assert "silicone" in ticket1_brief.target_function.lower() or "frizz" in ticket1_brief.target_function.lower()


def test_ticket1_gem_selection(ticket1_brief):
    sel = select_gem(ticket1_brief)
    assert sel.validation_mode == ValidationMode.FBA
    assert sel.gem is not None
    assert sel.gem.gem_id == "iyli647"


def test_ticket1_full_fba_pipeline(ticket1_brief):
    candidates = run_biomni_search(ticket1_brief)
    assert len(candidates) >= 1
    gem, payloads, skipped = formalize_pathways(ticket1_brief, candidates)
    assert gem is not None
    assert len(payloads) >= 1
    results = [score_pathway(p) for p in payloads]
    ranked = rank_fba_results(results)
    assert ranked[0].status == "optimal"
    report = generate_report(
        ticket1_brief,
        ValidationMode.FBA,
        candidates,
        candidates[0].id,
        ranked,
    )
    assert "What Worked" in report.markdown
    assert "Recommendations" in report.markdown
    assert "## References" in report.markdown
    assert "## Confidence Methodology" in report.markdown
    assert candidates[0].confidence_factors
