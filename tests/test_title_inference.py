"""Tests for session title inference."""

from api.services.title_inference import brief_title_snippet, infer_session_title, is_auto_title


def test_brief_title_snippet_truncates():
    brief = "a" * 100
    assert len(brief_title_snippet(brief)) == 80
    assert brief_title_snippet(brief).endswith("…")


def test_is_auto_title_detects_snippet():
    brief = "Engineer Yarrowia lipolytica for wax ester production from plant oil"
    assert is_auto_title(brief_title_snippet(brief), brief)
    assert is_auto_title("New session", brief)
    assert not is_auto_title("Wax Ester Pathway in Y. lipolytica", brief)


def test_infer_session_title_offline(monkeypatch):
    monkeypatch.setenv("BREWMIND_OFFLINE", "true")
    from mindbrew_v2.settings import get_settings

    get_settings.cache_clear()

    title = infer_session_title("Engineer Yarrowia lipolytica for wax ester production")
    assert "Engineer" in title
    assert len(title) <= 255

    get_settings.cache_clear()
