"""Golden path E2E test — Ticket 1 offline pipeline."""

import os

import pytest

os.environ["BREWMIND_OFFLINE"] = "true"

from mindbrew_v2.config.gem import provisional_validation_mode
from mindbrew_v2.models import Ticket, ValidationMode
from mindbrew_v2.phases.literature_search import run_literature_search
from mindbrew_v2.phases.formalize import formalize_pathways
from mindbrew_v2.phases.intake import run_intake
from mindbrew_v2.phases.report import generate_report
from mindbrew_v2.tools.fba_client import rank_fba_results, score_pathway

TICKET_1_BRIEF = """We're looking for a natural replacement for silicones in our premium haircare line. We want something that delivers the same smoothness and frizz control as dimethicone, but is fully natural and sustainably sourced. We'd like to make it from a common plant oil through fermentation. Can you figure out the best way to produce it and what it would take to manufacture?"""


@pytest.fixture
def ticket1_brief():
    ticket = Ticket(id="golden-ticket1", raw_brief=TICKET_1_BRIEF)
    return run_intake(ticket)


def test_ticket1_intake(ticket1_brief):
    assert ticket1_brief.gatekeeper_verdict == "PROCEED"
    assert "silicone" in ticket1_brief.target_function.lower() or "frizz" in ticket1_brief.target_function.lower()


def test_ticket1_gem_selection(ticket1_brief):
    sel = provisional_validation_mode(ticket1_brief)
    assert sel.validation_mode == ValidationMode.FBA
    assert sel.gem is None


def test_ticket1_full_fba_pipeline(ticket1_brief):
    candidates = run_literature_search(ticket1_brief)[0]
    assert len(candidates) >= 1
    result = formalize_pathways(ticket1_brief, candidates)
    gem, payloads, skipped = result.gem, result.payloads, result.skipped
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
        session_title="Natural Silicone Replacement From Plant Oil",
        score_payloads=payloads,
    )
    assert "# Natural Silicone Replacement From Plant Oil" in report.markdown
    assert "## 1. Project Summary" in report.markdown
    assert "## 5. Genetic Engineering Plan" in report.markdown
    assert "## 7. Validation Plan" in report.markdown
    assert "## 10. References" in report.markdown
    assert "## Appendix" in report.markdown
    assert "### Confidence Methodology" in report.markdown
    assert "### Citation Validation" in report.markdown
    assert report.project_summary
    assert report.genetic_engineering_plan
    assert candidates[0].confidence_factors
    assert "### Pathway Analysis" in report.markdown
    assert "### FBA Validation" in report.markdown
    assert "pw_wax_ester_far_ws" in report.markdown or candidates[0].id in report.markdown
