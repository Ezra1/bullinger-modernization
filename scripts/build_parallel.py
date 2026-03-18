#!/usr/bin/env python3
"""
Assemble final output from the modernization pipeline.

Reads 04-modernized/llm_draft.txt (or reviewed_modern.txt / custom path) and
02-cleaned/metadata.json; writes 05-output/parallel_edition.md, modern_only.md,
and glossary.md.

Input format: blocks separated by ---, each block with [ORIGINAL] and one of
[MODERN], [DRAFT], or [FINAL]. Prefer [FINAL] over [DRAFT] over [MODERN] for modern text.
"""

import argparse
import json
import re
from pathlib import Path

# Section markers (order for modern text preference)
MARKER_ORIGINAL = "[ORIGINAL]"
MARKER_MODERN = "[MODERN]"
MARKER_DRAFT = "[DRAFT]"
MARKER_CRITIQUE = "[CRITIQUE]"
MARKER_FINAL = "[FINAL]"
MODERN_MARKERS = [MARKER_FINAL, MARKER_DRAFT, MARKER_MODERN]
BLOCK_SEP = "\n---\n"

# Roman numeral mapping for "The.xiij. Sermon" / "The xv. Sermon" style (j = i in period spelling)
ROMAN = {
    "i": 1, "j": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000,
    "ii": 2, "iii": 3, "iij": 3, "iv": 4, "vi": 6, "vii": 7, "viii": 8, "ix": 9,
    "xi": 11, "xii": 12, "xiii": 13, "xiij": 13, "xiv": 14, "xv": 15, "xvi": 16,
    "xvii": 17, "xviii": 18, "xix": 19, "xx": 20, "xxi": 21, "xxii": 22,
    "xxiii": 23, "xxiv": 24, "xxv": 25, "xxvi": 26, "xxvj": 26, "xxvii": 27,
    "xxviii": 28, "xxix": 29, "xxx": 30, "xl": 40, "lx": 60, "lxx": 70, "lxxx": 80,
    "xc": 90,
}
# Ordinal words for "The first Sermon", "The second Sermon"
# NOTE: Some headings use "The Eight Sermon." (not "eighth"). Treat both as 8.
ORDINAL_TO_INT: dict[str, int] = {
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

# Curated proper noun modernizations (period spelling -> modern)
PROPER_NOUN_MAP = {
    "Austen": "Augustine",
    "Ireney": "Irenaeus",
    "Hierom": "Jerome",
    "Iuſtine": "Justin",
    "Iustine": "Justin",
    "Pathmos": "Patmos",
    "Origin": "Origen",
    "Eraſmus": "Erasmus",
    "Erasmus": "Erasmus",
    "Oecolampadius": "Oecolampadius",
    "Ceſarea": "Caesarea",
    "Epheſus": "Ephesus",
    "Ephesus": "Ephesus",
    "Ioel": "Joel",
    "Zachar": "Zechariah",
    "Zacharie": "Zechariah",
    "Pergamos": "Pergamum",
    "Ioachim": "Jehoiakim",
    "Merline": "Merlin",
    "Iohn": "John",
    "Iohns": "John's",
    "Chriſt": "Christ",
    "Chriſte": "Christ",
    "Paules": "Paul's",
    "Moyſes": "Moses",
    "Daniel": "Daniel",
    "Matthew": "Matthew",
    "Ieſu": "Jesus",
    "Ieſus": "Jesus",
    "Domitian": "Domitian",
    "Eusebius": "Eusebius",
    "Dioniſius": "Dionysius",
    "Papias": "Papias",
    "Iuſtinian": "Justinian",
    "Ezechias": "Hezekiah",
    "Philipp.": "Philippians",
    "Corinth.": "Corinthians",
    "Timoth.": "Timothy",
    "Rom.": "Romans",
    "BVLLINger": "Bullinger",
    "BULLINGER": "Bullinger",
    "Apocalipſe": "Apocalypse",
    "Reuelation": "Revelation",
    "reuelatio": "revelation",
}


def _roman_to_int(s: str) -> int | None:
    s = s.strip().lower().replace(" ", "")
    if not s:
        return None
    n = 0
    i = 0
    while i < len(s):
        # Prefer longest match (e.g. xiij -> 13)
        found = False
        for length in (4, 3, 2, 1):
            if i + length <= len(s):
                tok = s[i : i + length]
                if tok in ROMAN:
                    n += ROMAN[tok]
                    i += length
                    found = True
                    break
        if not found:
            return None
    return n if n else None


def get_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_metadata(repo_root: Path) -> dict:
    path = repo_root / "02-cleaned" / "metadata.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data
    except (json.JSONDecodeError, OSError):
        return {}


def _next_marker_pos(text: str, start: int = 0) -> int:
    """Return position of next section marker in text after start, or len(text)."""
    pattern = re.compile(
        r"\[(?:ORIGINAL|MODERN|DRAFT|CRITIQUE|FINAL)\]",
        re.IGNORECASE,
    )
    m = pattern.search(text, start)
    return m.start() if m else len(text)


def parse_blocks(content: str) -> list[tuple[str, str]]:
    """
    Split on ---; for each block extract (original, modern).
    Modern = text from first of [FINAL], [DRAFT], [MODERN] until next section.
    """
    blocks = [b.strip() for b in content.split(BLOCK_SEP) if b.strip()]
    result = []
    for block in blocks:
        original = ""
        modern = ""
        if MARKER_ORIGINAL not in block:
            result.append((original, modern))
            continue
        idx_orig = block.find(MARKER_ORIGINAL)
        start_orig = idx_orig + len(MARKER_ORIGINAL)
        end_orig = _next_marker_pos(block, start_orig)
        original = block[start_orig:end_orig].strip()

        modern_start = -1
        modern_marker = None
        for marker in MODERN_MARKERS:
            pos = block.find(marker)
            if pos >= 0 and (modern_start < 0 or pos < modern_start):
                modern_start = pos
                modern_marker = marker
        if modern_start >= 0 and modern_marker:
            start_mod = modern_start + len(modern_marker)
            end_mod = _next_marker_pos(block, start_mod)
            modern = block[start_mod:end_mod].strip()

        result.append((original, modern))
    return result


def is_heading(original: str, modern: str) -> bool:
    return (
        original.strip().startswith("##")
        or modern.strip() == "(heading preserved)"
    )


def parse_sermon_heading(line: str) -> tuple[int | None, str]:
    """
    Parse a ## line into (sermon_number, title).
    E.g. "## ☞ Of the author... The first Sermon." -> (1, "Of the author...")
    Returns (None, full_line) for book-level title; (N, title) for sermon N.
    """
    line = line.strip()
    if not line.startswith("##"):
        return None, line
    rest = line[2:].strip()
    # Match ordinal: "The second Sermon." (sometimes followed by extra text on same line)
    for word, num in ORDINAL_TO_INT.items():
        pat = re.compile(r"\bThe\s+" + re.escape(word) + r"\s+Sermon\.?\b", re.IGNORECASE)
        m = pat.search(rest)
        if m:
            title = rest[: m.start()].strip()
            title = re.sub(r"\s*¶\s*$", "", title).strip()
            return num, title
    # Roman: "The.xiij. Sermon" / "The.xxxiij. Sermon" / "The.XCvij. Sermon"
    # (Period style often includes extra dots and uses j ~ i.)
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
    # No sermon number (e.g. main title)
    return None, rest


def parse_sermon_heading_extra(line: str) -> tuple[int | None, str, str]:
    """
    Like parse_sermon_heading(), but also returns any trailing text that occurs
    *after* the 'The ... Sermon.' marker on the same line.
    """
    line = line.strip()
    if not line.startswith("##"):
        return None, line, ""
    rest = line[2:].strip()

    for word, num in ORDINAL_TO_INT.items():
        pat = re.compile(r"\bThe\s+" + re.escape(word) + r"\s+Sermon\.?\b", re.IGNORECASE)
        m = pat.search(rest)
        if m:
            title = rest[: m.start()].strip()
            extra = rest[m.end() :].strip()
            title = re.sub(r"\s*¶\s*$", "", title).strip()
            return num, title, extra

    roman_pat = re.compile(
        r"\bThe\.?\s*\.?\s*([ivxlcdmj]+)\.?\s*Sermon\.?\b",
        re.IGNORECASE,
    )
    m = roman_pat.search(rest)
    if m:
        num = _roman_to_int(m.group(1))
        if num is not None:
            title = rest[: m.start()].strip()
            extra = rest[m.end() :].strip()
            title = re.sub(r"\s*¶\s*$", "", title).strip()
            return num, title, extra

    return None, rest, ""


def collect_proper_nouns(blocks: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Collect (original, modern) proper noun pairs that appear in the text (exclude identity pairs)."""
    seen: set[tuple[str, str]] = set()
    for orig, mod in blocks:
        if is_heading(orig, mod):
            continue
        for period_form, modern_form in PROPER_NOUN_MAP.items():
            if period_form != modern_form and period_form in orig and modern_form in mod:
                seen.add((period_form, modern_form))
        # Heuristic: capitalized words that differ (simple word-boundary)
        orig_words = set(re.findall(r"\b([A-Z][a-z]+)\b", orig))
        mod_words = set(re.findall(r"\b([A-Z][a-z]+)\b", mod))
        for w in orig_words:
            if w not in mod_words and w in PROPER_NOUN_MAP:
                m = PROPER_NOUN_MAP[w]
                if m != w and (m in mod_words or m in mod):
                    seen.add((w, m))
    return sorted(seen, key=lambda x: (x[0].lower(), x[1].lower()))


def collect_flagged_passages(
    blocks: list[tuple[str, str]],
    heading_info: list[tuple[int | None, str, int]],
) -> list[tuple[str, str]]:
    """
    Find [?] in modern text; return list of (location, snippet).
    heading_info: list of (sermon_num, title, block_index) for headings only.
    """
    # Build block_index -> (sermon_num, para_num) by walking blocks
    block_to_location: list[tuple[int | None, int]] = []  # (sermon_num, para_num)
    current_sermon: int | None = None
    para_in_sermon = 0
    for i, (orig, mod) in enumerate(blocks):
        if is_heading(orig, mod):
            num, _ = parse_sermon_heading(orig)
            if num is not None:
                current_sermon = num
                para_in_sermon = 0
            block_to_location.append((current_sermon, 0))
            continue
        para_in_sermon += 1
        block_to_location.append((current_sermon, para_in_sermon))

    # Find [?] in modern text
    results = []
    for i, (orig, mod) in enumerate(blocks):
        if is_heading(orig, mod):
            continue
        for m in re.finditer(r"\[\?\]", mod):
            start = max(0, m.start() - 40)
            end = min(len(mod), m.end() + 40)
            snippet = mod[start:end].replace("\n", " ").strip()
            loc = block_to_location[i] if i < len(block_to_location) else (None, 0)
            serm, para = loc
            loc_str = f"Sermon {serm}, Paragraph {para}" if serm else f"Paragraph {para}"
            results.append((loc_str, snippet))
    return results


def escape_blockquote(text: str) -> str:
    out = []
    for line in text.splitlines():
        if line.startswith(">"):
            line = "\\" + line
        out.append("> " + line)
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assemble parallel edition, modern-only, and glossary from modernized draft.",
    )
    parser.add_argument(
        "--input",
        default="llm_draft",
        help="Input file: 'llm_draft' (04-modernized/llm_draft.txt), 'reviewed' (04-modernized/reviewed_modern.txt), or a path.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: 05-output under repo root).",
    )
    parser.add_argument(
        "--metadata",
        default=None,
        help="Path to metadata JSON (default: 02-cleaned/metadata.json under repo root).",
    )
    args = parser.parse_args()

    repo_root = get_repo_root()
    output_dir = Path(args.output_dir) if args.output_dir else repo_root / "05-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.input == "llm_draft":
        input_path = repo_root / "04-modernized" / "llm_draft.txt"
    elif args.input == "reviewed":
        input_path = repo_root / "04-modernized" / "reviewed_modern.txt"
    else:
        input_path = Path(args.input)

    if not input_path.exists():
        # Helpful fallback: many runs name files like 04-modernized/draft_<model>.txt
        if args.input == "llm_draft":
            modern_dir = repo_root / "04-modernized"
            candidates = sorted(
                modern_dir.glob("draft_*.txt"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if candidates:
                input_path = candidates[0]
                print(f"Input 'llm_draft' not found; using newest draft: {input_path}")
            else:
                raise SystemExit(f"Input file not found: {input_path}")
        else:
            raise SystemExit(f"Input file not found: {input_path}")

    metadata_path = Path(args.metadata) if args.metadata else repo_root / "02-cleaned" / "metadata.json"
    meta = {}
    if metadata_path.exists():
        try:
            meta = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            meta = {}
    if not meta:
        meta = load_metadata(repo_root)

    content = input_path.read_text(encoding="utf-8")
    blocks = parse_blocks(content)

    doc_title = "Bullinger's Apocalypse Sermons: Parallel Edition"
    if meta.get("title") and isinstance(meta["title"], list) and meta["title"]:
        doc_title = meta["title"][0][:80] + ("..." if len(meta["title"][0]) > 80 else "")
    orig_date = meta.get("date", "1561")
    author = ""
    if meta.get("author") and isinstance(meta["author"], list) and meta["author"]:
        author = meta["author"][0]

    # Build heading info and paragraph numbering for each block
    heading_info: list[tuple[int | None, str, int]] = []  # (sermon_num, title, block_idx)
    current_sermon: int | None = None
    current_title = ""
    para_in_sermon = 0
    for i, (orig, mod) in enumerate(blocks):
        if is_heading(orig, mod):
            num, title, extra = parse_sermon_heading_extra(orig)
            if num is not None:
                current_sermon = num
                current_title = title
            else:
                current_title = title
            heading_info.append((current_sermon, current_title, i))
        else:
            para_in_sermon += 1

    # Parallel edition
    parallel_lines = [
        "# Bullinger's Apocalypse Sermons: Parallel Edition",
        "",
    ]
    if author:
        parallel_lines.append(f"*{author}*")
        parallel_lines.append("")
    parallel_lines.append("---")
    parallel_lines.append("")

    current_sermon = None
    current_title = ""
    para_in_sermon = 0
    for i, (orig, mod) in enumerate(blocks):
        if is_heading(orig, mod):
            num, title, extra = parse_sermon_heading_extra(orig)
            if num is not None:
                current_sermon = num
                current_title = title
                parallel_lines.append(f"## Sermon {num}: {title}")
            else:
                parallel_lines.append(f"## {title}")
            parallel_lines.append("")
            if extra:
                para_in_sermon += 1
                parallel_lines.append(f"### Paragraph {para_in_sermon}")
                parallel_lines.append("")
                parallel_lines.append(f"**Original ({orig_date}):**")
                parallel_lines.append("")
                parallel_lines.append(escape_blockquote(extra))
                parallel_lines.append("")
                parallel_lines.append("**Modern English:**")
                parallel_lines.append("")
                parallel_lines.append(extra)
                parallel_lines.append("")
                parallel_lines.append("---")
                parallel_lines.append("")
            continue
        para_in_sermon += 1
        parallel_lines.append(f"### Paragraph {para_in_sermon}")
        parallel_lines.append("")
        parallel_lines.append(f"**Original ({orig_date}):**")
        parallel_lines.append("")
        parallel_lines.append(escape_blockquote(orig))
        parallel_lines.append("")
        parallel_lines.append("**Modern English:**")
        parallel_lines.append("")
        parallel_lines.append(mod if mod else "[missing]")
        parallel_lines.append("")
        parallel_lines.append("---")
        parallel_lines.append("")

    (output_dir / "parallel_edition.md").write_text("\n".join(parallel_lines), encoding="utf-8")

    # Modern only
    modern_lines = [
        "# Bullinger's Apocalypse Sermons",
        "",
    ]
    if author:
        modern_lines.append(f"*{author}*")
        modern_lines.append("")
    modern_lines.append("---")
    modern_lines.append("")

    current_sermon = None
    current_title = ""
    para_in_sermon = 0
    for i, (orig, mod) in enumerate(blocks):
        if is_heading(orig, mod):
            num, title, extra = parse_sermon_heading_extra(orig)
            if num is not None:
                current_sermon = num
                current_title = title
                modern_lines.append(f"## Sermon {num}: {title}")
            else:
                modern_lines.append(f"## {title}")
            modern_lines.append("")
            if extra:
                para_in_sermon += 1
                modern_lines.append(f"### Paragraph {para_in_sermon}")
                modern_lines.append("")
                modern_lines.append(extra)
                modern_lines.append("")
            continue
        para_in_sermon += 1
        modern_lines.append(f"### Paragraph {para_in_sermon}")
        modern_lines.append("")
        modern_lines.append(mod if mod else "")
        modern_lines.append("")

    (output_dir / "modern_only.md").write_text("\n".join(modern_lines), encoding="utf-8")

    # Glossary
    proper_nouns = collect_proper_nouns(blocks)
    flagged = collect_flagged_passages(blocks, heading_info)

    gloss_lines = [
        "# Glossary",
        "",
        "## Proper noun modernizations",
        "",
        "| Original (1561) | Modern |",
        "|-----------------|--------|",
    ]
    for a, b in proper_nouns:
        gloss_lines.append(f"| {a} | {b} |")
    gloss_lines.append("")
    gloss_lines.append("## Passages needing editorial attention")
    gloss_lines.append("")
    gloss_lines.append("Passages containing [?] in the modernized text:")
    gloss_lines.append("")
    for loc, snippet in flagged:
        gloss_lines.append(f"- **{loc}:** {snippet}")
    if not flagged:
        gloss_lines.append("- (None found)")
    gloss_lines.append("")

    (output_dir / "glossary.md").write_text("\n".join(gloss_lines), encoding="utf-8")

    print(f"Wrote {output_dir / 'parallel_edition.md'}")
    print(f"Wrote {output_dir / 'modern_only.md'}")
    print(f"Wrote {output_dir / 'glossary.md'}")


if __name__ == "__main__":
    main()
