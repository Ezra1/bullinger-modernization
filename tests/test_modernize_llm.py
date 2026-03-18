"""
Pytest tests for scripts/modernize_llm.py.

Covers: paragraph splitting (including heading pass-through), checkpoint save/load,
retry logic (mocked API), output formatting, NO ISSUES detection, --no-critique.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Allow importing from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from modernize_llm import (
    parse_paragraphs,
    needs_revision,
    format_block,
    load_checkpoint,
    save_checkpoint,
    process_one_paragraph,
    call_ollama,
)


# ---- Paragraph splitting ----


def test_parse_paragraphs_simple():
    """Split on blank lines; return list of (text, is_heading)."""
    text = "First para.\n\nSecond para."
    items = parse_paragraphs(text)
    assert len(items) == 2
    assert items[0] == ("First para.", False)
    assert items[1] == ("Second para.", False)


def test_parse_paragraphs_skip_empty():
    """Empty paragraphs (blank lines) are skipped."""
    text = "One\n\n\n\nTwo"
    items = parse_paragraphs(text)
    assert len(items) == 2
    assert items[0][0] == "One"
    assert items[1][0] == "Two"


def test_parse_paragraphs_heading_single_line():
    """Single line starting with ## is a heading (is_heading=True)."""
    text = "## SERMONS OF HENRI BULLINGER"
    items = parse_paragraphs(text)
    assert len(items) == 1
    assert items[0] == ("## SERMONS OF HENRI BULLINGER", True)


def test_parse_paragraphs_heading_and_paragraphs():
    """Headings and paragraphs mixed; headings are single-line ## only."""
    text = "## Title\n\nFirst para.\n\nSecond para."
    items = parse_paragraphs(text)
    assert len(items) == 3
    assert items[0] == ("## Title", True)
    assert items[1] == ("First para.", False)
    assert items[2] == ("Second para.", False)


def test_parse_paragraphs_multiline_not_heading():
    """A block with newline that starts with ## is not a heading (multi-line)."""
    text = "## Line one\nLine two"
    items = parse_paragraphs(text)
    assert len(items) == 1
    assert items[0][1] is False  # multi-line so not treated as heading


def test_parse_paragraphs_leading_trailing_blank():
    """Leading/trailing blank lines don't create empty entries."""
    text = "\n\nA\n\n"
    items = parse_paragraphs(text)
    assert len(items) == 1
    assert items[0][0] == "A"


# ---- NO ISSUES detection ----


def test_needs_revision_no_issues_uppercase():
    """'NO ISSUES' -> no revision (needs_revision False)."""
    assert needs_revision("NO ISSUES") is False


def test_needs_revision_no_issues_lowercase():
    """'no issues' -> no revision."""
    assert needs_revision("no issues") is False


def test_needs_revision_contains_no_issues():
    """Text containing 'no issues' -> no revision."""
    assert needs_revision("There are NO ISSUES here.") is False
    assert needs_revision("  no issues  ") is False


def test_needs_revision_has_issues():
    """Any other critique text -> revision required."""
    assert needs_revision("1. Meaning drift in sentence 2.") is True
    assert needs_revision("NO ISSUE") is True  # typo, not "no issues"
    assert needs_revision("") is True


# ---- Output formatting ----


def test_format_block_has_all_sections():
    """Block contains [ORIGINAL], [DRAFT], [CRITIQUE], [FINAL] and ends with ---."""
    block = format_block("orig", "draft", "critique", "final")
    assert "[ORIGINAL]" in block
    assert "orig" in block
    assert "[DRAFT]" in block
    assert "draft" in block
    assert "[CRITIQUE]" in block
    assert "critique" in block
    assert "[FINAL]" in block
    assert "final" in block
    assert block.strip().endswith("---")


def test_format_block_order_and_separator():
    """Sections appear in order; block ends with newline after ---."""
    block = format_block("a", "b", "c", "d")
    lines = block.split("\n")
    assert lines[0] == "[ORIGINAL]"
    assert lines[1] == "a"
    assert "[DRAFT]" in block
    assert "[CRITIQUE]" in block
    assert "[FINAL]" in block
    assert lines[-2] == "---"
    assert lines[-1] == ""  # trailing newline


# ---- Checkpoint save/load ----


def test_save_and_load_checkpoint(tmp_path):
    """Save checkpoint JSON and load it back; last_index and paragraphs preserved."""
    cp_path = tmp_path / "checkpoint.json"
    paragraphs = [
        {
            "original": "x",
            "draft": "y",
            "critique": "z",
            "final": "y",
            "flagged": False,
        }
    ]
    save_checkpoint(cp_path, 0, paragraphs)
    assert cp_path.exists()
    loaded = load_checkpoint(cp_path)
    assert loaded["last_index"] == 0
    assert len(loaded["paragraphs"]) == 1
    assert loaded["paragraphs"][0]["original"] == "x"
    assert loaded["paragraphs"][0]["final"] == "y"


def test_load_checkpoint_missing_returns_empty():
    """Loading missing checkpoint returns empty state."""
    loaded = load_checkpoint(Path("/nonexistent/checkpoint.json"))
    assert loaded["last_index"] == -1
    assert loaded["paragraphs"] == []


# ---- Retry logic (mocked API) ----


def test_call_ollama_retries_then_succeeds():
    """After 2 failures, third request succeeds; response text returned."""
    with patch("modernize_llm.requests.post") as mock_post:
        mock_post.side_effect = [
            Exception("fail 1"),
            Exception("fail 2"),
            MagicMock(status_code=200, json=lambda: {"response": "ok", "done": True}),
        ]
        with patch("modernize_llm.time.sleep"):
            result = call_ollama("prompt", "model", 0.1)
    assert result == "ok"
    assert mock_post.call_count == 3


def test_call_ollama_raises_after_all_retries():
    """If all 3 attempts fail, call_ollama raises."""
    with patch("modernize_llm.requests.post") as mock_post:
        mock_post.side_effect = [Exception("e1"), Exception("e2"), Exception("e3")]
        with patch("modernize_llm.time.sleep"):
            with pytest.raises(Exception):
                call_ollama("prompt", "model", 0.1)
    assert mock_post.call_count == 3


# ---- process_one_paragraph: --no-critique skips passes 2 and 3 ----


def test_process_one_paragraph_no_critique_single_call():
    """With no_critique=True, only one Ollama call (draft); no critique or revision."""
    with patch("modernize_llm.call_ollama") as mock_call:
        mock_call.return_value = "modernized draft"
        result = process_one_paragraph(
            "Old text.",
            False,
            model="test-model",
            draft_temp=0.1,
            no_critique=True,
        )
    assert mock_call.call_count == 1
    assert result["draft"] == "modernized draft"
    assert result["critique"] == "(skipped)"
    assert result["final"] == "modernized draft"
    assert result["flagged"] is False


def test_process_one_paragraph_heading_no_api_call():
    """Heading paragraph triggers no API call."""
    with patch("modernize_llm.call_ollama") as mock_call:
        result = process_one_paragraph(
            "## A heading",
            True,
            model="test-model",
            draft_temp=0.1,
            no_critique=False,
        )
    mock_call.assert_not_called()
    assert result["original"] == "## A heading"
    assert result["final"] == "## A heading"
    assert result["draft"] == "(heading preserved)"


def test_process_one_paragraph_no_issues_keeps_draft():
    """When critique is 'NO ISSUES', final is draft and no revision call."""
    with patch("modernize_llm.call_ollama") as mock_call:
        mock_call.side_effect = ["draft text", "NO ISSUES"]
        result = process_one_paragraph(
            "Original.",
            False,
            model="m",
            draft_temp=0.1,
            no_critique=False,
        )
    assert mock_call.call_count == 2  # draft + critique only
    assert result["final"] == "draft text"
    assert result["flagged"] is False


def test_process_one_paragraph_with_issues_calls_revision():
    """When critique has issues, revision pass runs and final is revised."""
    with patch("modernize_llm.call_ollama") as mock_call:
        mock_call.side_effect = ["draft", "1. Meaning drift.", "revised text"]
        result = process_one_paragraph(
            "Original.",
            False,
            model="m",
            draft_temp=0.1,
            no_critique=False,
        )
    assert mock_call.call_count == 3  # draft, critique, revision
    assert result["final"] == "revised text"
    assert result["flagged"] is True