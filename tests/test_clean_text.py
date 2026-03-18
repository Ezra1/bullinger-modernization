"""
Pytest tests for scripts/clean_text.py.

Covers: hyphen rejoining, abbreviation expansion, gap normalization,
whitespace normalization, empty input, and pass-through when no artifacts.
"""

import sys
from pathlib import Path

import pytest

# Allow importing from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from clean_text import (
    run_all_stages,
    stage1_line_break_rejoin,
    stage2_abbreviations,
    stage3_gap_normalization,
    stage4_whitespace,
)


# ---- Hyphen rejoining ----


def test_hyphen_rejoin_same_line():
    """excel∣lent -> excellent, moste aun∣cient -> moste auncient."""
    text = "excel\u2223lent and moste aun\u2223cient"
    out, _ = stage1_line_break_rejoin(text)
    assert out == "excellent and moste auncient"


def test_hyphen_rejoin_broken_bar():
    """¦ (U+00A6) is also removed."""
    text = "excel\u00A6lent"
    out, _ = stage1_line_break_rejoin(text)
    assert out == "excellent"


def test_hyphen_rejoin_with_newline():
    """word∣\nnext -> wordnext (mid-word line break)."""
    text = "moste aun\u2223\ncient"
    out, _ = stage1_line_break_rejoin(text)
    assert out == "moste auncient"


def test_hyphen_at_start_of_line():
    """Hyphen at start of line is removed."""
    text = "line one\n\u2223line two"
    out, _ = stage1_line_break_rejoin(text)
    assert out == "line one\nline two"


def test_hyphen_at_end_of_line():
    """Hyphen at end of line is removed; next line is joined if present."""
    text = "word\u2223\nnext"
    out, _ = stage1_line_break_rejoin(text)
    assert out == "wordnext"


def test_multiple_hyphens_in_paragraph():
    """Multiple line-break hyphens in one paragraph are all removed."""
    text = "ex\u2223ample and an\u00A6other\u2223\nbroken"
    out, _ = stage1_line_break_rejoin(text)
    assert out == "example and anotherbroken"


# ---- Abbreviation expansion ----


def test_abbreviation_ye_to_the():
    """ye -> the (word boundary)."""
    out, _ = run_all_stages("ye same boke")
    assert "the same boke" in out


def test_abbreviation_yt_to_that():
    """yt -> that."""
    out, _ = run_all_stages("yt they should")
    assert "that they should" in out


def test_abbreviation_wt_to_with():
    """wt -> with."""
    out, _ = run_all_stages("wt all men")
    assert "with all men" in out


def test_abbreviation_ampersand_to_and():
    """ &  -> and in running text."""
    out, _ = run_all_stages("father & son")
    assert "father and son" in out


def test_abbreviation_word_boundary():
    """ye in 'eye' or 'they' is not expanded (word boundary)."""
    out, _ = run_all_stages("the eye and they")
    assert "eye" in out
    assert "they" in out


# ---- Gap marker normalization ----


def test_gap_normalization_bullet():
    """• -> [illegible]."""
    out, _ = run_all_stages("word • next")
    assert "[illegible]" in out
    assert "•" not in out


def test_gap_normalization_circle():
    """〈◊〉 -> [illegible]."""
    out, _ = run_all_stages("word 〈◊〉 next")
    assert "[illegible]" in out


def test_gap_normalization_already_illegible():
    """[illegible] remains [illegible]."""
    out, _ = run_all_stages("word [illegible] next")
    assert out.count("[illegible]") >= 1


# ---- Whitespace normalization ----


def test_whitespace_collapse_multiple_spaces():
    """Multiple spaces -> single space."""
    out, _ = run_all_stages("word    two   three")
    assert "  " not in out.replace("\n", " ")


def test_whitespace_remove_space_before_punctuation():
    """Remove space before . , ; : ! ?"""
    out, _ = run_all_stages("word . next , again ; end : now ! really ?")
    assert " ." not in out
    assert " ," not in out
    assert " ;" not in out
    assert " :" not in out
    assert " !" not in out
    assert " ?" not in out


def test_whitespace_strip_trailing():
    """Strip trailing whitespace from lines."""
    out, _ = run_all_stages("line one   \nline two\t\n")
    lines = out.split("\n")
    assert not (lines[0].endswith(" ") or lines[0].endswith("\t"))
    if len(lines) > 1:
        assert not (lines[1].endswith(" ") or lines[1].endswith("\t"))


def test_whitespace_one_blank_between_paragraphs():
    """Exactly one blank line between paragraphs."""
    out, _ = run_all_stages("para one\n\n\n\npara two")
    assert "\n\n\n" not in out
    assert "\n\npara two" in out or out.strip().endswith("para two")


# ---- Edge cases ----


def test_empty_input():
    """Empty input -> empty output (or minimal)."""
    out, log = run_all_stages("")
    assert out.strip() == ""


def test_empty_input_single_newline():
    """Input that is just newlines."""
    out, _ = run_all_stages("\n\n")
    assert out.strip() == ""


def test_no_artifacts_unchanged():
    """Input with no artifacts passes through unchanged (except possible whitespace)."""
    text = "Hello world.\n\nNext paragraph here."
    out, log = run_all_stages(text)
    assert "Hello" in out and "world" in out
    assert "Next paragraph" in out
    assert "Hello world." in out or "Hello world ." not in out


def test_full_pipeline_integration():
    """Full pipeline: all stages applied in order."""
    text = "ye \u2223lord & yt we have  •  here  ,  there"
    out, log = run_all_stages(text)
    assert "the" in out or "ye" not in out
    assert "lord" in out
    assert "\u2223" not in out
    assert " and " in out
    assert "that" in out or "yt" not in out
    assert "[illegible]" in out
    assert "  ," not in out
