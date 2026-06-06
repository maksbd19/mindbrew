import asyncio

import pytest

from api.services.graph_runner import SessionInterrupted
from api.services.run_registry import RunRegistry


def test_registry_interrupt_sets_cancel():
    reg = RunRegistry()
    cancel = reg.register("s1")
    assert reg.interrupt("s1") is True
    assert cancel.is_set()
    reg.unregister("s1")
    assert reg.interrupt("s1") is False


@pytest.mark.asyncio
async def test_session_interrupted_is_exception():
    with pytest.raises(SessionInterrupted):
        raise SessionInterrupted()
