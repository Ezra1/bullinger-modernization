#!/usr/bin/env python3
"""
Utilities for resuming the modernization pipeline by sermon number.

Why this exists:
- `modernize_llm.py` resumes by *paragraph index* (its internal unit of work).
- In practice, we want to resume by *sermon number* (e.g. start at sermon 36).

This script computes the paragraph index where a given sermon heading occurs in a
normalized input file (default: 03-normalized/cleaned_text-noxml.txt).
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def parse_paragraphs(text: str) -> list[tuple[str, bool]]:
    items: list[tuple[str, bool]] = []
    for block in text.split("\n\n"):
        stripped = block.strip()
        if not stripped:
            continue
        is_heading = stripped.startswith("##") and "\n" not in stripped
        items.append((stripped, is_heading))
    return items


def roman_to_int(s: str) -> int | None:
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


def sermon_num_from_heading(line: str) -> int | None:
    """
    Extract sermon number from a TEI-derived heading line.
    Examples:
    - "## ... The xxxv. Sermon." -> 35
    - "## ... The C. Sermon." -> 100
    - "## ... The first Sermon." -> 1
    """
    s = line.strip()
    if not s.startswith("##"):
        return None
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
    for w, i in ordinal_to_int.items():
        if re.search(rf"\bThe\s+{re.escape(w)}\s+Sermon\.?\s*$", rest, re.IGNORECASE):
            return i

    m = re.search(r"\bThe\.?\s*([ivxlcdm]+)\.?\s*Sermon\.?\s*$", rest, re.IGNORECASE)
    if not m:
        return None
    return roman_to_int(m.group(1))


def sermon_start_index(items: list[tuple[str, bool]], sermon_num: int) -> int | None:
    for i, (para, is_heading) in enumerate(items):
        if not is_heading:
            continue
        n = sermon_num_from_heading(para)
        if n == sermon_num:
            return i
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute modernization paragraph index for a sermon number.")
    parser.add_argument("--sermon", type=int, required=True, help="Sermon number to start at (e.g. 36).")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("03-normalized/cleaned_text-noxml.txt"),
        help="Normalized input file used by modernize_llm.py",
    )
    args = parser.parse_args()

    text = args.input.read_text(encoding="utf-8")
    items = parse_paragraphs(text)
    idx = sermon_start_index(items, args.sermon)
    if idx is None:
        raise SystemExit(f"Could not find sermon {args.sermon} heading in {args.input}")
    print(idx)


if __name__ == "__main__":
    main()

