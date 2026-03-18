#!/usr/bin/env python3
"""
Modernize Early Modern English text using a local Ollama instance with a
three-pass self-review pipeline (draft → critique → conditional revision).

Requires: requests (pip install requests)
"""

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any
from datetime import datetime, timedelta

import requests

# ---------------------------------------------------------------------------
# Prompts (hardcoded at module top)
# ---------------------------------------------------------------------------

DRAFT_PROMPT = """You are a scholarly editor modernizing a 1561 English
translation of Heinrich Bullinger's sermons on the Book of Revelation.
Convert the following passage into clear, modern English.

RULES:
- Preserve the original meaning exactly. Do not add interpretation.
- Preserve theological terminology (Antichrist, Apocalypse, dispensation).
- Modernize proper nouns: Hierom→Jerome, Austen→Augustine,
  Ireney→Irenaeus, Dionisius→Dionysius, Zuryk→Zurich.
- [illegible]: If the word is obvious from context (e.g. doc[illegible]rine →
  doctrine, autho[illegible]ity → authority), fix it and remove the marker.
  Only keep [illegible] when the word or meaning truly cannot be recovered.
- Flag uncertain readings with [?].
- Maintain paragraph structure. Do not add formatting.
- Do NOT add any preamble like "Here is the modernized version:"
  Just output the modernized text directly.
  The passage to modernize follows below.
  """

CRITIQUE_PROMPT = """You are a scholarly reviewer checking a modernized
version of a 1561 English text against its original. You will receive the
ORIGINAL text first, then the DRAFT after it. Compare them carefully.
Check for:

1. MEANING DRIFT: Does the draft change the meaning of the original?
2. ADDED INTERPRETATION: Does the draft explain or interpret rather than
   just modernize the language?
3. LOST AMBIGUITY: Where the original is vague or ambiguous, does the
   draft make it inappropriately specific?
4. THEOLOGICAL TERMS: Were terms like Antichrist, Apocalypse, dispensation,
   sacrament, etc. changed or removed?
5. HALLUCINATION: Is there content in the draft not present in the original?
6. PROPER NOUNS: Were historical names modernized correctly?
   (Hierom→Jerome, Austen→Augustine, Ireney→Irenaeus, etc.)

Be thorough. Most drafts have at least one subtle issue. If you are unsure
whether something is a problem, flag it anyway — false positives are better
than missed errors.

If there are NO problems, respond with exactly: NO ISSUES
If there ARE problems, list each one briefly and specifically.
Do NOT add any preamble. Start directly with your findings."""

REVISION_PROMPT = """You are a scholarly editor. A modernized version of a
1561 English text was reviewed and specific problems were found. You will
receive three things: the ORIGINAL text, the DRAFT modernization, and the
CRITIQUE identifying problems. Fix only what the critique flags. Produce a
corrected modernization that:

1. KEEPS all the good modernizations from the draft (updated spelling,
   clearer syntax, modernized punctuation)
2. FIXES ONLY the specific problems identified in the critique
3. Does NOT revert the entire text back to the original — that defeats
   the purpose

The goal is modern, readable English that faithfully preserves the
original meaning. Not a copy of the original.

Do NOT add any preamble. Just output the corrected modernized text."""

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

OLLAMA_URL = "http://localhost:11434/api/generate"
CRITIQUE_TEMPERATURE = 0.3
RETRY_DELAYS = (2, 4, 8)  # seconds
RATE_LIMIT_DELAY = 1  # second
MAX_RETRIES = 3

# ---------------------------------------------------------------------------
# Call timing / progress statistics
# ---------------------------------------------------------------------------


class CallStats:
    """
    Track timing for Ollama calls and print fun progress information.

    - Records duration of each call.
    - Prints per-call time, rolling averages (last 10, last 50, overall),
      and an ETA based on the overall average.
    """

    def __init__(self, total_expected_calls: int | None = None) -> None:
        self.total_expected_calls = total_expected_calls
        self.start_time = datetime.now()
        self.call_durations: list[float] = []
        self.last10: list[float] = []
        self.last50: list[float] = []
        self.total_calls = 0
        # For bouncing progress bar
        self.bar_width = 30
        self.bar_pos = 0
        self.bar_direction = 1  # 1 = right, -1 = left

    def record(self, duration: float, phase: str | None = None) -> None:
        self.total_calls += 1
        self.call_durations.append(duration)
        self.last10.append(duration)
        self.last50.append(duration)
        if len(self.last10) > 10:
            self.last10.pop(0)
        if len(self.last50) > 50:
            self.last50.pop(0)

        avg_total = sum(self.call_durations) / len(self.call_durations)
        avg10 = sum(self.last10) / len(self.last10)
        avg50 = sum(self.last50) / len(self.last50)

        remaining_calls = None
        eta_str = "n/a"
        done_at_str = "n/a"
        if self.total_expected_calls is not None and self.total_expected_calls > 0:
            remaining_calls = max(self.total_expected_calls - self.total_calls, 0)
            remaining_seconds = avg_total * remaining_calls
            eta = timedelta(seconds=int(remaining_seconds))
            done_at = datetime.now() + eta
            eta_str = str(eta)
            done_at_str = done_at.strftime("%Y-%m-%d %H:%M:%S")

        phase_label = phase or "call"
        # Update bouncing bar position
        self.bar_pos += self.bar_direction
        if self.bar_pos <= 0:
            self.bar_pos = 0
            self.bar_direction = 1
        elif self.bar_pos >= self.bar_width - 1:
            self.bar_pos = self.bar_width - 1
            self.bar_direction = -1

        bar_chars = [" "] * self.bar_width
        bar_chars[self.bar_pos] = "#"
        bar = "[" + "".join(bar_chars) + "]"

        total_str = f"{self.total_calls}"
        if self.total_expected_calls:
            total_str += f"/{self.total_expected_calls}"

        line = (
            f"\r{bar} {phase_label.upper():8s} {total_str:>8s} | "
            f"last {duration:5.2f}s | avg10 {avg10:5.2f}s | "
            f"avg50 {avg50:5.2f}s | avg {avg_total:5.2f}s | "
            f"rem {remaining_calls if remaining_calls is not None else 'n/a'} | "
            f"ETA {eta_str} | done ~ {done_at_str}"
        )
        # Print directly to stderr so it plays nicely with logging to stdout
        sys.stderr.write(line)
        sys.stderr.flush()

# ---------------------------------------------------------------------------
# Paragraph parsing
# ---------------------------------------------------------------------------


def parse_paragraphs(text: str) -> list[tuple[str, bool]]:
    """
    Split text into paragraphs (blank-line separated). Skip empty paragraphs.
    Return list of (text, is_heading). Headings are single lines starting with ##.
    """
    items: list[tuple[str, bool]] = []
    for block in text.split("\n\n"):
        stripped = block.strip()
        if not stripped:
            continue
        # Single line starting with ## is a heading
        is_heading = stripped.startswith("##") and "\n" not in stripped
        items.append((stripped, is_heading))
    return items


def _roman_to_int(s: str) -> int | None:
    s = s.strip().lower().replace(" ", "").replace("j", "i")
    if not s:
        return None
    vals = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
    total = 0
    prev = 0
    for ch in reversed(s):
        v = vals.get(ch)
        if v is None:
            return None
        if v < prev:
            total -= v
        else:
            total += v
            prev = v
    return total or None


def _parse_sermon_heading(heading_line: str) -> tuple[int | None, str]:
    """
    Parse a TEI-derived sermon heading into (sermon_number, title).

    Expected input is a single line starting with '##', such as:
      - '## ... The.xxxiij. Sermon.'
      - '## ... The first Sermon.'

    Returns (None, title) when sermon number is not detected.
    """
    s = heading_line.strip()
    if not s.startswith("##"):
        return None, s
    rest = s[2:].strip()

    ordinal_to_int: dict[str, int] = {
        "first": 1,
        "second": 2,
        "third": 3,
        "fourth": 4,
        "fifth": 5,
        "sixth": 6,
        "seventh": 7,
        "eighth": 8,
        "eight": 8,
        "ninth": 9,
        "tenth": 10,
        "eleventh": 11,
        "twelfth": 12,
        "thirteenth": 13,
        "fourteenth": 14,
        "fifteenth": 15,
        "sixteenth": 16,
        "seventeenth": 17,
        "eighteenth": 18,
        "nineteenth": 19,
        "twentieth": 20,
        "twenty-first": 21,
        "twenty-second": 22,
        "twenty-third": 23,
        "twenty-fourth": 24,
        "twenty-fifth": 25,
        "twenty-sixth": 26,
        "twenty-seventh": 27,
        "twenty-eighth": 28,
        "twenty-ninth": 29,
        "thirtieth": 30,
        "thirty-first": 31,
        "thirty-second": 32,
        "thirty-third": 33,
        "thirty-fourth": 34,
        "thirty-fifth": 35,
        "thirty-sixth": 36,
        "thirty-seventh": 37,
        "thirty-eighth": 38,
        "thirty-ninth": 39,
        "fortieth": 40,
        "forty-first": 41,
        "forty-second": 42,
        "forty-third": 43,
        "forty-fourth": 44,
        "forty-fifth": 45,
        "forty-sixth": 46,
        "forty-seventh": 47,
        "forty-eighth": 48,
        "forty-ninth": 49,
        "fiftieth": 50,
        "fifty-first": 51,
        "fifty-second": 52,
        "fifty-third": 53,
        "fifty-fourth": 54,
        "fifty-fifth": 55,
        "fifty-sixth": 56,
        "fifty-seventh": 57,
        "fifty-eighth": 58,
        "fifty-ninth": 59,
        "sixtieth": 60,
        "sixty-first": 61,
        "sixty-second": 62,
        "sixty-third": 63,
        "sixty-fourth": 64,
        "sixty-fifth": 65,
        "sixty-sixth": 66,
        "sixty-seventh": 67,
        "sixty-eighth": 68,
        "sixty-ninth": 69,
        "seventieth": 70,
        "seventy-first": 71,
        "seventy-second": 72,
        "seventy-third": 73,
        "seventy-fourth": 74,
        "seventy-fifth": 75,
        "seventy-sixth": 76,
        "seventy-seventh": 77,
        "seventy-eighth": 78,
        "seventy-ninth": 79,
        "eightieth": 80,
        "eighty-first": 81,
        "eighty-second": 82,
        "eighty-third": 83,
        "eighty-fourth": 84,
        "eighty-fifth": 85,
        "eighty-sixth": 86,
        "eighty-seventh": 87,
        "eighty-eighth": 88,
        "eighty-ninth": 89,
        "ninetieth": 90,
        "ninety-first": 91,
        "ninety-second": 92,
        "ninety-third": 93,
        "ninety-fourth": 94,
        "ninety-fifth": 95,
        "ninety-sixth": 96,
        "ninety-seventh": 97,
        "ninety-eighth": 98,
        "ninety-ninth": 99,
        "hundredth": 100,
    }
    for word, num in ordinal_to_int.items():
        pat = re.compile(r"\bThe\s+" + re.escape(word) + r"\s+Sermon\.?\s*$", re.IGNORECASE)
        if pat.search(rest):
            title = pat.sub("", rest).strip()
            title = re.sub(r"\s*¶\s*$", "", title).strip()
            return num, title

    # Common period style uses extra dots: "The.xxxiij. Sermon." or "The xxvj. Sermon."
    roman_pat = re.compile(
        r"\bThe\.?\s*\.?\s*([ivxlcdmj]+)\.?\s*Sermon\.?\s*$",
        re.IGNORECASE,
    )
    m = roman_pat.search(rest)
    if m:
        num = _roman_to_int(m.group(1))
        if num is not None:
            title = rest[: m.start()].strip()
            title = re.sub(r"\s*¶\s*$", "", title).strip()
            return num, title

    return None, rest


def normalize_heading(heading_line: str) -> str:
    """
    Convert headings like:
      '## ¶ ... The.xxxiij. Sermon.'
    into:
      '## Sermon 33: ¶ ...'

    If we can't detect a sermon number, keep it as a plain '## <title>' heading.
    """
    s = heading_line.strip()
    if not (s.startswith("##") and "\n" not in s):
        return heading_line.strip()
    num, title = _parse_sermon_heading(s)
    title = re.sub(r"\s+", " ", title).strip()
    if num is None:
        return f"## {title}" if title else "##"
    return f"## Sermon {num}: {title}" if title else f"## Sermon {num}"


def needs_revision(critique: str) -> bool:
    """Return True if the critique indicates problems (i.e. revision is needed)."""
    return "no issues" not in critique.strip().lower()


def format_block(original: str, draft: str, critique: str, final: str) -> str:
    """Format one paragraph's output block with [ORIGINAL], [DRAFT], [CRITIQUE], [FINAL]."""
    return (
        f"[ORIGINAL]\n{original}\n"
        f"[DRAFT]\n{draft}\n"
        f"[CRITIQUE]\n{critique}\n"
        f"[FINAL]\n{final}\n---\n"
    )


# ---------------------------------------------------------------------------
# Ollama API with retry and rate limiting
# ---------------------------------------------------------------------------


def call_ollama(
    prompt: str,
    model: str,
    temperature: float,
    url: str = OLLAMA_URL,
    system: str | None = None,
    stats: CallStats | None = None,
    phase: str | None = None,
) -> str:
    """
    Send prompt to Ollama and return the generated text. Raises on failure after retries.
    Uses stream=False. If system is provided, it is sent as the system prompt and
    prompt is the user message. Sleeps RATE_LIMIT_DELAY after a successful response.
    """
    start = time.perf_counter()
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if system is not None:
        payload["system"] = system
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(url, json=payload, timeout=300)
            resp.raise_for_status()
            data = resp.json()
            text = data.get("response")
            if text is None:
                raise ValueError("Ollama response missing 'response' key")
            time.sleep(RATE_LIMIT_DELAY)
            duration = time.perf_counter() - start
            if stats is not None:
                stats.record(duration, phase)
            return text
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])
    raise last_error  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Single-paragraph pipeline
# ---------------------------------------------------------------------------


def process_one_paragraph(
    paragraph: str,
    is_heading: bool,
    *,
    model: str,
    draft_temp: float,
    no_critique: bool,
    current: int = 0,
    total: int = 0,
    progress_cb: Any = None,
    stats: CallStats | None = None,
) -> dict[str, Any]:
    """
    Run draft → critique → (conditional) revision for one paragraph.
    For headings, return passthrough block (no LLM calls).
    progress_cb(current, total, message) is called before each API call if provided.
    """
    def report(msg: str) -> None:
        if progress_cb:
            progress_cb(current, total, msg)

    if is_heading:
        normalized = normalize_heading(paragraph)
        return {
            "original": paragraph,
            "draft": "(heading preserved)",
            "critique": "",
            "final": normalized,
            "flagged": False,
        }
    # Pass 1: Draft — system prompt sets role, user message is the paragraph only
    report("Pass 1: Draft...")
    draft = call_ollama(
        paragraph,
        model,
        draft_temp,
        system=DRAFT_PROMPT,
        stats=stats,
        phase="draft",
    )
    if no_critique:
        return {
            "original": paragraph,
            "draft": draft,
            "critique": "(skipped)",
            "final": draft,
            "flagged": False,
        }
    # Pass 2: Critique — system prompt sets role, user message is ORIGINAL + DRAFT
    report("Pass 2: Critique...")
    critique_user = f"ORIGINAL:\n{paragraph}\n\nDRAFT:\n{draft}"
    critique = call_ollama(
        critique_user,
        model,
        CRITIQUE_TEMPERATURE,
        system=CRITIQUE_PROMPT,
        stats=stats,
        phase="critique",
    )
    if needs_revision(critique):
        # Pass 3: Revision — system prompt sets role, user message is ORIGINAL + DRAFT + CRITIQUE
        report("Pass 3: Revision...")
        revision_user = (
            f"ORIGINAL:\n{paragraph}\n\nDRAFT:\n{draft}\n\nCRITIQUE:\n{critique}"
        )
        final = call_ollama(
            revision_user,
            model,
            draft_temp,
            system=REVISION_PROMPT,
            stats=stats,
            phase="revision",
        )
        flagged = True
    else:
        final = draft
        flagged = False
    return {
        "original": paragraph,
        "draft": draft,
        "critique": critique,
        "final": final,
        "flagged": flagged,
    }


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------

CHECKPOINT_FILENAME = "checkpoint.json"


def load_checkpoint(checkpoint_path: Path) -> dict[str, Any]:
    """Load checkpoint JSON; return empty state if missing or invalid."""
    if not checkpoint_path.exists():
        return {"last_index": -1, "paragraphs": []}
    try:
        with open(checkpoint_path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"last_index": -1, "paragraphs": []}


def save_checkpoint(checkpoint_path: Path, last_index: int, paragraphs: list[dict[str, Any]]) -> None:
    """Write checkpoint JSON."""
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump({"last_index": last_index, "paragraphs": paragraphs}, f, indent=2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(
        description="Modernize Early Modern English text via Ollama (draft → critique → revision)."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("03-normalized/cleaned_text-noxml.txt"),
        help="Input text file (paragraphs separated by blank lines)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("04-modernized/llm_draft.txt"),
        help="Output file for all blocks",
    )
    parser.add_argument(
        "--model",
        default="qwen2.5:7b",
        help="Ollama model name",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.1,
        help="Temperature for draft and revision passes",
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=None,
        metavar="N",
        help="Start from paragraph index N (overrides checkpoint)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process only the first 3 paragraphs",
    )
    parser.add_argument(
        "--no-critique",
        action="store_true",
        help="Single-pass only (draft); skip critique and revision",
    )
    args = parser.parse_args()

    input_path = args.input
    output_path = args.output
    flagged_path = output_path.parent / "flagged_for_review.txt"
    checkpoint_path = output_path.parent / CHECKPOINT_FILENAME

    if not input_path.exists():
        logger.error("Input file not found: %s", input_path)
        sys.exit(1)

    text = input_path.read_text(encoding="utf-8")
    items = parse_paragraphs(text)
    total = len(items)
    if total == 0:
        logger.info("No paragraphs found.")
        return

    # Resolve start index and replay from checkpoint if not --start-from
    start_index = 0
    results: list[dict[str, Any]] = []
    if args.start_from is not None:
        start_index = max(0, args.start_from)
        # Open output for append when starting from middle (user must manage file)
        mode = "a" if start_index > 0 else "w"
    else:
        cp = load_checkpoint(checkpoint_path)
        results = cp.get("paragraphs", [])
        last = cp.get("last_index", -1)
        if last >= 0 and results:
            start_index = last + 1
            # Replay previous blocks to output file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as out:
                for r in results:
                    out.write(
                        format_block(
                            r["original"],
                            r["draft"],
                            r["critique"],
                            r["final"],
                        )
                    )
        mode = "a" if start_index > 0 else "w"

    end_index = total
    if args.dry_run:
        end_index = min(start_index + 3, total)

    # Estimate total expected calls for timing/ETA (approximate: headings=0, body=3 calls each
    # unless --no-critique, then 1 call each).
    remaining_items = items[start_index:end_index]
    per_para_calls = 1 if args.no_critique else 3
    total_expected_calls = sum(0 if is_heading else per_para_calls for _, is_heading in remaining_items)
    stats = CallStats(total_expected_calls=total_expected_calls or None)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, mode, encoding="utf-8") as out_f, open(
        flagged_path, "a", encoding="utf-8"
    ) as flag_f:
        def progress_cb(cur: int, tot: int, msg: str) -> None:
            logger.info("[%d/%d] %s", cur, tot, msg)

        for i in range(start_index, end_index):
            para, is_heading = items[i]
            current = i + 1
            if is_heading:
                logger.info("[%d/%d] Heading (pass-through)", current, total)
                block = {
                    "original": para,
                    "draft": "(heading preserved)",
                    "critique": "",
                    "final": para,
                    "flagged": False,
                }
            else:
                try:
                    block = process_one_paragraph(
                        para,
                        is_heading,
                        model=args.model,
                        draft_temp=args.temperature,
                        no_critique=args.no_critique,
                        current=current,
                        total=total,
                        progress_cb=progress_cb,
                        stats=stats,
                    )
                except Exception as e:
                    logger.exception("Paragraph %d failed after retries: %s", i, e)
                    block = {
                        "original": para,
                        "draft": f"[ERROR: {e!s}]",
                        "critique": "[ERROR]",
                        "final": f"[ERROR: {e!s}]",
                        "flagged": False,
                    }
            results.append(block)
            out_f.write(
                format_block(
                    block["original"],
                    block["draft"],
                    block["critique"],
                    block["final"],
                )
            )
            if block.get("flagged"):
                flag_f.write(
                    format_block(
                        block["original"],
                        block["draft"],
                        block["critique"],
                        block["final"],
                    )
                )
            save_checkpoint(checkpoint_path, i, results)

    logger.info("Done. Processed up to paragraph index %d.", end_index - 1)


if __name__ == "__main__":
    main()
