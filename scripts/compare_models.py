#!/usr/bin/env python3
"""
Compare model draft outputs: read the four draft files in 04-modernized/,
extract [ORIGINAL] and [FINAL] per paragraph, align by index, and write
04-modernized/model_comparison.txt.
"""

import sys
from pathlib import Path

# Draft files and their display names
DRAFT_FILES = [
    ("draft_qwen2_5_7b.txt", "QWEN 2.5 7B"),
    ("draft_mistral_7b.txt", "MISTRAL 7B"),
    ("draft_gemma3_12b.txt", "GEMMA3 12B"),
    ("draft_llama3_1_8b.txt", "LLAMA3.1 8B"),
]
OUTPUT_FILE = "model_comparison.txt"
DELIMITER = "---"
SECTION_ORIGINAL = "[ORIGINAL]"
SECTION_FINAL = "[FINAL]"


def parse_draft_file(path: Path) -> list[tuple[str, str]]:
    """
    Split content on ---, then for each block extract (original_text, final_text).
    Returns list of (original, final) per paragraph.
    """
    text = path.read_text(encoding="utf-8")
    blocks = [b.strip() for b in text.split(f"\n{DELIMITER}\n") if b.strip()]
    result = []
    for block in blocks:
        if SECTION_ORIGINAL not in block or SECTION_FINAL not in block:
            result.append(("", ""))
            continue
        # Original: from after [ORIGINAL] until [DRAFT]
        after_orig = block.split(SECTION_ORIGINAL, 1)[1]
        original = after_orig.split("[DRAFT]")[0].strip()
        # Final: from after [FINAL] to end of block
        after_final = block.split(SECTION_FINAL, 1)[1]
        final = after_final.strip()
        result.append((original, final))
    return result


def main() -> None:
    base = Path(__file__).resolve().parent.parent
    modernized = base / "04-modernized"
    if not modernized.is_dir():
        print(f"Directory not found: {modernized}", file=sys.stderr)
        sys.exit(1)

    # Load all drafts and parse into list of (original, final) per paragraph
    all_paragraphs: list[list[tuple[str, str]]] = []  # [file_idx][paragraph_idx] = (orig, final)
    for filename, _ in DRAFT_FILES:
        path = modernized / filename
        if not path.is_file():
            print(f"Missing file: {path}", file=sys.stderr)
            sys.exit(1)
        all_paragraphs.append(parse_draft_file(path))

    num_paragraphs = len(all_paragraphs[0])
    for i, (filename, name) in enumerate(DRAFT_FILES):
        if len(all_paragraphs[i]) != num_paragraphs:
            print(
                f"Warning: {filename} has {len(all_paragraphs[i])} paragraphs, "
                f"expected {num_paragraphs}",
                file=sys.stderr,
            )

    # Sanity check: same paragraph index should have same [ORIGINAL] in all files
    for p in range(num_paragraphs):
        ref_original = all_paragraphs[0][p][0]
        for f in range(1, len(DRAFT_FILES)):
            orig = all_paragraphs[f][p][0]
            if orig != ref_original:
                print(
                    f"Warning: paragraph {p + 1} [ORIGINAL] differs between "
                    f"{DRAFT_FILES[0][0]} and {DRAFT_FILES[f][0]}",
                    file=sys.stderr,
                )

    # Build comparison output
    lines = []
    sep = "=" * 40
    for p in range(num_paragraphs):
        lines.append(f"=== Paragraph {p + 1} ===")
        lines.append("")
        # Use original from first file (they should match)
        lines.append("ORIGINAL:")
        lines.append(all_paragraphs[0][p][0])
        lines.append("")
        for f, (_, display_name) in enumerate(DRAFT_FILES):
            lines.append(f"{display_name}:")
            lines.append(all_paragraphs[f][p][1])
            lines.append("")
        lines.append(sep)
        lines.append("")

    out_path = modernized / OUTPUT_FILE
    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
