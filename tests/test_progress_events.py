"""Progress events, heartbeats, and stream enrichment."""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime

from api.services.graph_runner import _enrich_event
from mindbrew_v2.progress import (
    clear_current_node,
    get_current_node,
    heartbeat,
    log_timing,
    node_start,
    reset_progress_emitter,
    set_progress_emitter,
)
from mindbrew_v2.tools.literature_retrieval import RetrievedDocument, format_context_block


def test_enrich_event_adds_seq_and_ts():
    created = datetime(2026, 6, 5, 12, 30, 0, tzinfo=UTC)
    enriched = _enrich_event({"type": "log", "content": "hello"}, seq=42, created_at=created)
    assert enriched["seq"] == 42
    assert enriched["ts"] == "2026-06-05T12:30:00+00:00"
    assert enriched["content"] == "hello"


def test_log_timing_emits_message():
    received: list[dict] = []
    token = set_progress_emitter(received.append)
    try:
        log_timing("LLM [parser]", 38.234)
    finally:
        reset_progress_emitter(token)
    assert received == [{"type": "log", "content": "LLM [parser] finished in 38.2s", "level": "info"}]


def test_heartbeat_uses_current_node():
    received: list[dict] = []
    token = set_progress_emitter(received.append)
    try:
        node_start("biomni_search", "Literature pathway search (LLM)")
        heartbeat()
    finally:
        reset_progress_emitter(token)
        clear_current_node()

    assert received[0]["type"] == "node_start"
    assert received[1]["type"] == "heartbeat"
    assert received[1]["node_id"] == "biomni_search"
    assert received[1]["content"] == "Literature pathway search (LLM)"


def test_heartbeat_thread_emits_while_worker_blocks():
    received: list[dict] = []
    token = set_progress_emitter(received.append)
    stop = threading.Event()
    node_start("slow_node", "Slow step")

    def heartbeat_loop() -> None:
        while not stop.wait(0.05):
            _, label = get_current_node()
            heartbeat(label=f"Still running: {label}" if label else "Still working…")

    hb = threading.Thread(target=heartbeat_loop, daemon=True)
    hb.start()
    try:
        time.sleep(0.12)
    finally:
        stop.set()
        hb.join(timeout=1.0)
        reset_progress_emitter(token)
        clear_current_node()

    heartbeats = [e for e in received if e.get("type") == "heartbeat"]
    assert len(heartbeats) >= 1


def test_format_context_block_unchanged():
    docs = [
        RetrievedDocument(
            source="pubmed",
            title="Oleate wax ester pathway",
            snippet="Wax ester synthesis in Yarrowia lipolytica.",
            url="https://pubmed.ncbi.nlm.nih.gov/123",
            metadata={"pmid": "123"},
        )
    ]
    text = format_context_block(docs, max_chars=8000)
    assert "Oleate wax ester pathway" in text
    assert "Retrieved evidence" in text
