import os

os.environ["BREWMIND_OFFLINE"] = "true"

from mindbrew_v2.config.gem import provisional_validation_mode
from mindbrew_v2.models import Ticket, ValidationMode
from mindbrew_v2.phases.intake import run_intake


def test_ticket2_literature_branch():
    ticket = Ticket(
        id="t2",
        raw_brief="Scalp microbiome ingredient for dandruff via fermentation.",
    )
    brief = run_intake(ticket)
    sel = provisional_validation_mode(brief)
    assert sel.validation_mode == ValidationMode.LITERATURE_PATHWAY
    assert sel.gem is None
