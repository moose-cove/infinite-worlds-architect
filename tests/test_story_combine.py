"""Tests for iw_architect.story.combine."""

import os

import pytest

from iw_architect.story.combine import combine

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture(name: str) -> str:
    return os.path.join(FIXTURES, name)


class TestCombineSingleFile:
    def test_five_turn_returns_five_turns(self):
        result = combine([fixture("story_export_single_5turn.txt")])
        assert len(result["turns"]) == 5

    def test_first_turn_number_is_1(self):
        result = combine([fixture("story_export_single_5turn.txt")])
        assert result["turns"][0]["number"] == 1

    def test_header_contains_title(self):
        result = combine([fixture("story_export_single_5turn.txt")])
        assert "The Iron Gate" in result["header"]

    def test_no_warnings_for_contiguous_turns(self):
        result = combine([fixture("story_export_single_5turn.txt")])
        assert result["warnings"] == []

    def test_combined_text_is_str(self):
        result = combine([fixture("story_export_single_5turn.txt")])
        assert isinstance(result["combined_text"], str)

    def test_source_is_absolute(self):
        result = combine([fixture("story_export_single_5turn.txt")])
        for t in result["turns"]:
            assert os.path.isabs(t["source"])

    def test_mtime_is_float(self):
        result = combine([fixture("story_export_single_5turn.txt")])
        for t in result["turns"]:
            assert isinstance(t["mtime"], float)

    def test_no_hidden_file_loads(self):
        result = combine([fixture("story_export_no_hidden.txt")])
        assert len(result["turns"]) == 2

    def test_crlf_normalised(self, tmp_path):
        src = tmp_path / "crlf.txt"
        content = "== CRLF Test ==\r\n\r\n-- Turn 1 --\r\n\r\nOutcome\r\n-------\r\nIt worked.\r\n"
        src.write_bytes(content.encode("utf-8"))
        result = combine([str(src)])
        assert len(result["turns"]) == 1
        assert "\r" not in result["combined_text"]


class TestCombineNoTurn1:
    def test_raises_without_turn1(self):
        with pytest.raises(ValueError, match="No Turn 1 found"):
            combine([fixture("story_export_no_turn1.txt")])

    def test_succeeds_when_merged_with_turn1_file(self, tmp_path):
        # Create a minimal Turn 1 file.
        t1 = tmp_path / "turn1.txt"
        t1.write_text(
            "== Merged ==\n\n-- Turn 1 --\n\nOutcome\n-------\nStarted.\n\n",
            encoding="utf-8",
        )
        # no_turn1.txt has turns 3-4; merge with the Turn 1 file.
        os.utime(str(t1), (1_000_000, 1_000_000))  # older
        no_t1 = fixture("story_export_no_turn1.txt")
        os.utime(no_t1, (2_000_000, 2_000_000))  # newer
        result = combine([str(t1), no_t1])
        numbers = [t["number"] for t in result["turns"]]
        assert 1 in numbers
        assert 3 in numbers
        assert 4 in numbers


class TestCombineMultiFile:
    def test_mtime_precedence_picks_newer_turn2(self, tmp_path):
        import shutil

        merge_a = tmp_path / "merge_a.txt"
        merge_b = tmp_path / "merge_b.txt"
        shutil.copy(fixture("story_export_merge_a.txt"), str(merge_a))
        shutil.copy(fixture("story_export_merge_b.txt"), str(merge_b))

        # merge_a is older, merge_b is newer → merge_b's Turn 2 body wins.
        os.utime(str(merge_a), (1_000_000, 1_000_000))
        os.utime(str(merge_b), (2_000_000, 2_000_000))

        result = combine([str(merge_a), str(merge_b)])
        turn2 = next(t for t in result["turns"] if t["number"] == 2)
        assert "Version B" in turn2["content"]
        assert "Version A" not in turn2["content"]

    def test_gap_produces_warning(self, tmp_path):
        import shutil

        merge_a = tmp_path / "merge_a.txt"
        merge_b = tmp_path / "merge_b.txt"
        shutil.copy(fixture("story_export_merge_a.txt"), str(merge_a))
        shutil.copy(fixture("story_export_merge_b.txt"), str(merge_b))
        os.utime(str(merge_a), (1_000_000, 1_000_000))
        os.utime(str(merge_b), (2_000_000, 2_000_000))

        # Merge a (turns 1-2) + b (turns 2-3) = contiguous, no gap.
        result = combine([str(merge_a), str(merge_b)])
        assert result["warnings"] == []

    def test_gap_warning_non_contiguous(self, tmp_path):
        # Craft a file with turns 1 and 5 to force a gap.
        gapped = tmp_path / "gapped.txt"
        gapped.write_text(
            "== Gap Test ==\n\n"
            "-- Turn 1 --\n\nOutcome\n-------\nStart.\n\n"
            "-- Turn 5 --\n\nAction\n------\nJump.\n\nOutcome\n-------\nLanded.\n\n",
            encoding="utf-8",
        )
        result = combine([str(gapped)])
        assert len(result["warnings"]) == 1
        assert "gap" in result["warnings"][0].lower()

    def test_header_from_newest_file(self, tmp_path):
        import shutil

        merge_a = tmp_path / "merge_a.txt"
        merge_b = tmp_path / "merge_b.txt"
        shutil.copy(fixture("story_export_merge_a.txt"), str(merge_a))
        shutil.copy(fixture("story_export_merge_b.txt"), str(merge_b))
        os.utime(str(merge_a), (1_000_000, 1_000_000))
        os.utime(str(merge_b), (2_000_000, 2_000_000))

        result = combine([str(merge_a), str(merge_b)])
        # merge_b has the same title but is newer — header should come from it.
        assert "The Clockwork Vault" in result["header"]

    def test_newest_file_without_header_keeps_older_header(self, tmp_path):
        older = tmp_path / "older.txt"
        newer = tmp_path / "newer.txt"
        older.write_text(
            "== Original World ==\n\n-- Story Background --\n\nBG.\n\n"
            "-- Turn 1 --\n\nOutcome\n-------\nStart.\n\n",
            encoding="utf-8",
        )
        # Newer re-export begins directly with a turn marker — no header.
        newer.write_text(
            "-- Turn 2 --\n\nAction\n------\nGo.\n\nOutcome\n-------\nGone.\n\n",
            encoding="utf-8",
        )
        os.utime(str(older), (1_000_000, 1_000_000))
        os.utime(str(newer), (2_000_000, 2_000_000))
        result = combine([str(older), str(newer)])
        # The header-less newest file must NOT clobber the older real header.
        assert "Original World" in result["header"]

    def test_empty_paths_raises(self):
        with pytest.raises(ValueError):
            combine([])
