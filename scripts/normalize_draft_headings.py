#!/usr/bin/env python3
"""
Normalize sermon headings inside a modernized draft file.

Input format: blocks separated by lines containing only '---', where each block
contains sections like:
  [ORIGINAL]
  ...
  [DRAFT]
  ...
  [CRITIQUE]
  ...
  [FINAL]
  ...

For blocks where the ORIGINAL section is a heading (single line starting with '##'),
we rewrite the FINAL section to a standardized form:
  '## Sermon N: <title>'

This fixes output assembly when headings contain period-style numbering like:
  'The.xxxiij. Sermon.'
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Allow importing sibling modules when run as a script.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.modernize_llm import normalize_heading  # noqa: E402


SECTION_RE = re.compile(r"^\[(ORIGINAL|DRAFT|CRITIQUE|FINAL)\]\s*$", re.MULTILINE)


def split_blocks(text: str) -> list[str]:
    parts = re.split(r"(?m)^\s*---\s*$", text)
    return [p.strip("\n") for p in parts if p.strip()]


def parse_sections(block: str) -> dict[str, str]:
    matches = list(SECTION_RE.finditer(block))
    out: dict[str, str] = {}
    for i, m in enumerate(matches):
        name = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(block)
        out[name] = block[start:end].strip("\n")
    return out


def format_block(sections: dict[str, str]) -> str:
    # Preserve the standard section order even if a section is empty.
    ordered = ["ORIGINAL", "DRAFT", "CRITIQUE", "FINAL"]
    parts: list[str] = []
    for k in ordered:
        parts.append(f"[{k}]")
        parts.append(sections.get(k, "").rstrip())
    return "\n".join(parts).rstrip() + "\n"


def is_heading_text(text: str) -> bool:
    s = (text or "").strip()
    return s.startswith("##") and "\n" not in s


def normalize_file(input_path: Path) -> tuple[str, int]:
    raw = input_path.read_text(encoding="utf-8")
    blocks = split_blocks(raw)
    changed = 0
    out_blocks: list[str] = []

    for b in blocks:
        sections = parse_sections(b)
        original = sections.get("ORIGINAL", "")
        if is_heading_text(original):
            normalized = normalize_heading(original.strip())
            if sections.get("FINAL", "").strip() != normalized.strip():
                sections["FINAL"] = normalized
                changed += 1
        out_blocks.append(format_block(sections).rstrip())

    out_text = "\n---\n".join(out_blocks).rstrip() + "\n"
    return out_text, changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize sermon headings inside a draft file.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("04-modernized/draft_gemma3_12b.txt"),
        help="Draft file to normalize",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: overwrite --input in place)",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input not found: {args.input}")

    out_text, changed = normalize_file(args.input)
    out_path = args.output or args.input
    out_path.write_text(out_text, encoding="utf-8")
    print(f"Normalized {changed} heading blocks -> {out_path}")


if __name__ == "__main__":
    main()

