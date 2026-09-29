"""Tests for iw_architect.story.search."""

import json
import os

import pytest

from iw_architect.story import search as search_module
from iw_architect.story.extract import extract_story_data
from iw_architect.story.models import SearchResult
from iw_architect.story.search import (
    MAX_MATCH_CHARS,
    MAX_SNIPPETS_PER_TURN,
    SNIPPET_CONTEXT,
    SNIPPET_MAX_WIDEN,
    _snippet,
    search_turns,
)

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "fixtures")


@pytest.fixture()
def extracted(tmp_path):
    """Extraction of the 5-turn Iron Gate fixture."""
    extract_story_data([os.path.join(FIXTURES, "story_export_single_5turn.txt")], str(tmp_path))
    return str(tmp_path)


def _write_turn_index(tmp_path, turns: list[dict]) -> str:
    """Write a synthetic turn_index.json; each dict overrides a blank turn."""
    full = [
        {
            "number": i + 1,
            "action": None,
            "outcome": None,
            "secretInfo": None,
            "trackedItems": None,
            "hiddenTrackedItems": None,
            "source": "/nowhere.txt",
            "lineRange": [1, 1],
            **t,
        }
        for i, t in enumerate(turns)
    ]
    (tmp_path / "turn_index.json").write_text(json.dumps({"turns": full}))
    return str(tmp_path)


def _turns(result: SearchResult) -> list[int]:
    return [h.turn for h in result.results]


class TestMatching:
    def test_returns_search_result(self, extracted):
        assert isinstance(search_turns(extracted, "rival"), SearchResult)

    def test_keyword_finds_turns_with_counts(self, extracted):
        result = search_turns(extracted, "rival")
        assert _turns(result) == [2, 3, 4, 5]
        assert all(h.section_counts == {"secretInfo": 1} for h in result.results)
        assert result.total_matches == 4
        assert result.matching_turn_count == 4
        assert result.turns_searched == 5

    def test_case_insensitive_by_default(self, extracted):
        assert _turns(search_turns(extracted, "RIVAL")) == [2, 3, 4, 5]

    def test_case_sensitive(self, extracted):
        # Only turns 3 and 5 capitalise "The rival".
        assert _turns(search_turns(extracted, "The rival", case_sensitive=True)) == [3, 5]
        assert _turns(search_turns(extracted, "RIVAL", case_sensitive=True)) == []

    def test_counts_across_sections(self, extracted):
        # Turn 3: "east wing" in both the action and the outcome.
        hit = next(h for h in search_turns(extracted, "east wing").results if h.turn == 3)
        assert hit.section_counts == {"action": 1, "outcome": 1}
        assert hit.match_count == 2

    def test_counts_multiple_matches_in_one_section(self, tmp_path):
        d = _write_turn_index(tmp_path, [{"outcome": "cat cat dog cat"}])
        assert search_turns(d, "cat").results[0].match_count == 3

    def test_keyword_is_literal(self, tmp_path):
        d = _write_turn_index(tmp_path, [{"outcome": "a.b"}, {"outcome": "axb"}])
        assert _turns(search_turns(d, "a.b")) == [1]

    def test_substring_match_without_whole_word(self, extracted):
        # "painting" also hits "paintings" (turn 3) unless whole_word is set.
        assert _turns(search_turns(extracted, "painting")) == [1, 3, 4]

    def test_whole_word(self, extracted):
        assert _turns(search_turns(extracted, "painting", whole_word=True)) == [1, 4]

    def test_whole_word_with_punctuation_edge(self, tmp_path):
        # \b would fail after the "." — lookarounds don't.
        d = _write_turn_index(tmp_path, [{"outcome": "Ask Mr. Hale."}, {"outcome": "Mr.X"}])
        assert _turns(search_turns(d, "Mr.", whole_word=True)) == [1]

    def test_regex(self, extracted):
        result = search_turns(extracted, r"\bthird\s+paint\w*", mode="regex")
        assert _turns(result) == [1, 4]

    def test_regex_multiline_anchors(self, tmp_path):
        d = _write_turn_index(tmp_path, [{"outcome": "first line\nsecond line"}])
        assert search_turns(d, r"^second", mode="regex").total_matches == 1

    def test_zero_length_matches_skipped(self, tmp_path):
        d = _write_turn_index(tmp_path, [{"outcome": "abc"}])
        assert search_turns(d, r"x*", mode="regex").results == []

    def test_matches_do_not_span_sections(self, tmp_path):
        d = _write_turn_index(tmp_path, [{"action": "the end", "outcome": "game over"}])
        assert search_turns(d, r"end\s+game", mode="regex").results == []

    def test_tracked_items_not_searched(self, extracted):
        # "Gold Coins" appears in every turn's tracked items but no narrative text.
        result = search_turns(extracted, "Gold Coins")
        assert result.results == []
        assert result.sections_searched == ["action", "outcome", "secretInfo"]

    def test_turn_one_null_action_tolerated(self, extracted):
        assert search_turns(extracted, "gate", sections=["action"]).results == []

    def test_results_sorted_by_turn(self, tmp_path):
        d = _write_turn_index(
            tmp_path, [{"number": 2, "outcome": "x"}, {"number": 1, "outcome": "x"}]
        )
        assert _turns(search_turns(d, "x")) == [1, 2]


class TestSections:
    def test_sections_filter(self, extracted):
        result = search_turns(extracted, "east wing", sections=["outcome"])
        assert _turns(result) == [3]
        assert result.sections_searched == ["outcome"]

    def test_sections_reported_in_canonical_order_deduped(self, extracted):
        result = search_turns(extracted, "x", sections=["secretInfo", "action", "action"])
        assert result.sections_searched == ["action", "secretInfo"]

    def test_unknown_section_errors(self, extracted):
        with pytest.raises(ValueError, match="Unknown section"):
            search_turns(extracted, "x", sections=["trackedItems"])

    def test_empty_sections_errors(self, extracted):
        with pytest.raises(ValueError, match="at least one section"):
            search_turns(extracted, "x", sections=[])


class TestSnippets:
    def test_absent_unless_requested(self, extracted):
        assert search_turns(extracted, "rival").results[0].snippets is None

    def test_snippet_fields(self, extracted):
        hit = search_turns(extracted, "RIVAL", include_snippets=True).results[0]
        assert hit.snippets is not None
        (snip,) = hit.snippets
        assert snip.section == "secretInfo"
        assert snip.match == "rival"  # the text as it appears, not the query
        assert snip.text == "The paper was planted by a rival."

    def test_short_section_not_marked_as_cut(self):
        assert _snippet("a short line", 2, 7) == "a short line"

    def test_whitespace_collapsed(self):
        assert _snippet("one\n\n  two   three", 5, 8) == "one two three"

    def test_widens_to_whole_words(self):
        text = "alpha " * 20 + "TARGET" + " omega" * 20
        start = text.index("TARGET")
        snip = _snippet(text, start, start + len("TARGET"))
        assert snip.startswith("…alpha ") and snip.endswith(" omega…")
        core = snip.strip("…")
        # Whole words only, and at least the requested context on each side.
        assert set(core.split()) == {"alpha", "TARGET", "omega"}
        assert core.index("TARGET") >= SNIPPET_CONTEXT - 1
        assert len(core) - core.index("TARGET") - len("TARGET") >= SNIPPET_CONTEXT - 1

    def test_widening_is_capped_for_long_tokens(self):
        text = "x" * 200 + " TARGET " + "y" * 200
        start = text.index("TARGET")
        snip = _snippet(text, start, start + len("TARGET"))
        core = snip.strip("…")
        assert core.startswith("x") and core.endswith("y")
        assert len(core) <= len("TARGET") + 2 * (SNIPPET_CONTEXT + SNIPPET_MAX_WIDEN)

    def test_capped_per_turn_but_count_exact(self, tmp_path):
        d = _write_turn_index(tmp_path, [{"outcome": "cat " * 12}])
        hit = search_turns(d, "cat", include_snippets=True).results[0]
        assert hit.match_count == 12
        assert hit.snippets is not None
        assert len(hit.snippets) == MAX_SNIPPETS_PER_TURN


class TestErrors:
    def test_empty_query(self, extracted):
        with pytest.raises(ValueError, match="non-empty"):
            search_turns(extracted, "   ")

    def test_unknown_mode(self, extracted):
        with pytest.raises(ValueError, match="Unknown mode"):
            search_turns(extracted, "x", mode="fuzzy")

    def test_invalid_regex(self, extracted):
        with pytest.raises(ValueError, match="Invalid regex"):
            search_turns(extracted, "(unclosed", mode="regex")

    def test_whole_word_with_regex(self, extracted):
        with pytest.raises(ValueError, match="keyword mode only"):
            search_turns(extracted, "x", mode="regex", whole_word=True)

    def test_missing_turn_index(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="turn_index.json"):
            search_turns(str(tmp_path), "x")

    def test_malformed_turn_index_is_value_error(self, tmp_path):
        (tmp_path / "turn_index.json").write_text("{not json")
        with pytest.raises(ValueError):
            search_turns(str(tmp_path), "x")

    def test_search_exceeding_budget_errors(self, tmp_path, monkeypatch):
        monkeypatch.setattr(search_module, "SEARCH_TIMEOUT_SECONDS", 0.0)
        d = _write_turn_index(tmp_path, [{"outcome": "a" * 200_000}])
        with pytest.raises(ValueError, match="timed out"):
            search_turns(d, "a")


class TestSnippetEdges:
    """Exact-string pins for where the window lands and where "…" goes."""

    def test_no_leading_ellipsis_when_widening_reaches_section_start(self):
        text = "a" * 20 + " " + "b" * 40 + "TARGET"
        start = text.index("TARGET")
        assert _snippet(text, start, start + 6) == text

    def test_no_trailing_ellipsis_when_widening_reaches_section_end(self):
        text = "TARGET" + "b" * 40 + " " + "a" * 20
        assert _snippet(text, 0, 6) == text

    def test_left_cut_on_whitespace_does_not_widen(self):
        # start - 50 lands exactly on the space after the w-run: no extra word pulled in.
        text = "w" * 9 + " " + "z" * 48 + " TARGET"
        start = text.index("TARGET")
        assert _snippet(text, start, start + 6) == "…" + "z" * 48 + " TARGET"

    def test_right_cut_after_whitespace_does_not_widen(self):
        # end + 50 lands just after the space before the w-run.
        text = "TARGET " + "z" * 48 + " " + "w" * 9
        assert _snippet(text, 0, 6) == "TARGET " + "z" * 48 + "…"

    def test_snippet_window_end_to_end(self, tmp_path):
        outcome = "lorem " * 25 + "NEEDLE " + "ipsum " * 25
        d = _write_turn_index(tmp_path, [{"outcome": outcome}])
        hit = search_turns(d, "needle", include_snippets=True).results[0]
        assert hit.snippets is not None
        (snip,) = hit.snippets
        assert snip.text.startswith("…lorem ") and snip.text.endswith(" ipsum…")
        assert "NEEDLE" in snip.text
        assert len(snip.text) < len(outcome.strip())

    def test_long_match_truncated(self, tmp_path):
        d = _write_turn_index(tmp_path, [{"outcome": "q" * 500}])
        hit = search_turns(d, "q+", mode="regex", include_snippets=True).results[0]
        assert hit.match_count == 1
        assert hit.snippets is not None
        (snip,) = hit.snippets
        assert snip.match == "q" * MAX_MATCH_CHARS + "…"
        assert len(snip.text) <= MAX_MATCH_CHARS + SNIPPET_CONTEXT + SNIPPET_MAX_WIDEN + 2


class TestCountingEdges:
    def test_snippet_cap_spans_sections(self, tmp_path):
        d = _write_turn_index(tmp_path, [{"action": "cat cat cat", "outcome": "cat cat cat"}])
        hit = search_turns(d, "cat", include_snippets=True).results[0]
        assert hit.match_count == 6
        assert hit.snippets is not None
        assert [s.section for s in hit.snippets] == ["action"] * 3 + ["outcome"] * 2

    def test_zero_length_matches_skipped_not_terminal(self, tmp_path):
        d = _write_turn_index(tmp_path, [{"outcome": "axxb"}])
        result = search_turns(d, r"x*", mode="regex", include_snippets=True)
        assert result.total_matches == 1
        assert result.results[0].snippets is not None
        assert result.results[0].snippets[0].match == "xx"

    def test_whole_word_stays_case_insensitive(self, extracted):
        assert _turns(search_turns(extracted, "PAINTING", whole_word=True)) == [1, 4]
