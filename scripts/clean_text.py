#!/usr/bin/env python3
"""
Clean text from Michigan Digital Library (EEBO-TCP) TEI XML for use with VARD.

Use this script on any TEI XML file from the Text Creation Partnership
(Michigan/EEBO-TCP) to extract body text, remove typographic artifacts, and
produce plain text ready for VARD (Variant Detector) or other normalization.

  python clean_text.py document.xml
  python clean_text.py document.xml -o ready_for_vard.txt
  python clean_text.py already_extracted.txt -o cleaned.txt

If the input is .xml, the script extracts body text from TEI (all
<head> as ## headings, <p> as paragraphs, <gap> -> [illegible], <note> -> [note N]).
If the input is plain text, it only runs the cleaning stages.

Cleaning stages:
  1. Line-break hyphen rejoining (∣, ¦ removed and word rejoined)
  2. Abbreviation expansion (ye->the, yt->that, wt->with, & -> and)
  3. Gap/illegible marker normalization -> [illegible]
  4. Roman numeral dot normalization (.xii. -> xii.)
  5. Whitespace normalization

Requires: Python 3.9+. For XML input, lxml is required: pip install lxml
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Callable

# Unicode line-break hyphen characters (mid-word breaks from typesetting)
LINE_BREAK_HYPHENS = "\u2223\u00A6"  # ∣ (DIVIDES), ¦ (BROKEN BAR)

# Early Modern English abbreviations: token -> expansion (word-boundary replacement)
ABBREVIATIONS = {
    "ye": "the",
    "yt": "that",
    "wt": "with",
}

# Gap/illegible markers to normalize to [illegible]
GAP_PATTERNS = [
    (re.compile(r"•"), "[illegible]"),
    (re.compile(r"〈◊〉"), "[illegible]"),
    (re.compile(r"\[\s*illegible\s*\]", re.IGNORECASE), "[illegible]"),
]

# Punctuation that should not have space before (excluding leading-dot Roman numerals)
PUNCT_NO_SPACE_BEFORE = r".,;:!?\])"

# Roman numeral letters only (for .xii. style references)
ROMAN_NUMERAL_RE = re.compile(r"\s*\.([xvidclm]+)[.,]", re.IGNORECASE)

# TEI namespace (EEBO-TCP / Michigan DL)
TEI_NS = "http://www.tei-c.org/ns/1.0"


def _tei_qname(local: str) -> str:
    return f"{{{TEI_NS}}}{local}"


# --- Generic TEI extraction (works with any EEBO-TCP / Michigan TEI body) ---


def _extract_tei_body(path: Path) -> str:
    """
    Parse TEI XML and return extracted body text as a single string.
    Uses lxml; raises ImportError if lxml not installed, SystemExit on parse error.
    """
    try:
        from lxml import etree
    except ImportError:
        raise SystemExit(
            "XML input requires lxml. Install with: pip install lxml"
        ) from None

    parser = etree.XMLParser(recover=True, remove_blank_text=False)
    try:
        tree = etree.parse(str(path), parser)
    except etree.XMLSyntaxError as e:
        raise SystemExit(f"Invalid XML in {path}: {e}") from None

    root = tree.getroot()
    BODY = _tei_qname("body")
    DIV = _tei_qname("div")
    HEAD = _tei_qname("head")
    P = _tei_qname("p")
    GAP = _tei_qname("gap")
    NOTE = _tei_qname("note")
    G = _tei_qname("g")
    PB = _tei_qname("pb")
    HI = _tei_qname("hi")
    SEG = _tei_qname("seg")

    def element_text_only(el) -> str:
        """Recursively concatenate text and tail; skip g, pb."""
        parts = []
        if el.text:
            parts.append(el.text)
        for child in el:
            if child.tag in (G, PB):
                if child.tail:
                    parts.append(child.tail)
                continue
            parts.append(element_text_only(child))
            if child.tail:
                parts.append(child.tail)
        return "".join(parts)

    def normalize_space(s: str) -> str:
        return re.sub(r"\s+", " ", (s or "").strip())

    note_counter = [0]

    def inline_text_and_tail(el) -> str:
        """Walk element: gap->[illegible], note->[note N], keep text from hi/seg."""
        out = []
        if el.text:
            out.append(el.text)
        for child in el:
            if child.tag == GAP:
                out.append("[illegible]")
                if child.tail:
                    out.append(child.tail)
                continue
            if child.tag == NOTE:
                note_counter[0] += 1
                out.append(f"[note {note_counter[0]}]")
                if child.tail:
                    out.append(child.tail)
                continue
            if child.tag in (G, PB):
                if child.tail:
                    out.append(child.tail)
                continue
            out.append(inline_text_and_tail(child))
            if child.tail:
                out.append(child.tail)
        return "".join(out)

    def paragraph_text(p_el) -> str:
        return normalize_space(inline_text_and_tail(p_el))

    def head_text(el) -> str:
        return normalize_space(element_text_only(el))

    def walk_body(el, lines: list) -> None:
        """Emit ## for heads, paragraph text for <p>, recurse into divs."""
        for child in el:
            if child.tag == HEAD:
                lines.append("## " + head_text(child))
                lines.append("")
            elif child.tag == P:
                para = paragraph_text(child)
                if para:
                    lines.append(para)
                    lines.append("")
            elif child.tag == DIV:
                walk_body(child, lines)

    body = root.find(f".//{BODY}")
    if body is None:
        return ""

    lines = []
    walk_body(body, lines)
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) if lines else ""


def load_input(path: Path) -> str:
    """Load text from path. If path is .xml, extract TEI body; else read as UTF-8."""
    suffix = path.suffix.lower()
    if suffix == ".xml":
        return _extract_tei_body(path)
    return path.read_text(encoding="utf-8")


# --- Cleaning stages (unchanged logic) ---


def apply_stage(
    lines: list[tuple[int, str]],
    stage_name: str,
    func: Callable[[str], tuple[str, list[tuple[str, str]]]],
) -> tuple[list[tuple[int, str]], list[tuple[str, int, str, str]]]:
    """Apply a per-line transform; func returns (new_line, [(before, after), ...])."""
    result = []
    log_entries = []
    for line_num, line in lines:
        new_line, changes = func(line)
        result.append((line_num, new_line))
        for before, after in changes:
            log_entries.append((stage_name, line_num, before, after))
    return result, log_entries


def stage1_line_break_rejoin(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Remove line-break hyphen chars and rejoin; log each join."""
    log = []
    char_class = re.escape(LINE_BREAK_HYPHENS)
    pattern = re.compile(f"[{char_class}]\\n?")
    for m in pattern.finditer(text):
        log.append((m.group(0).replace("\n", "\\n"), ""))
    out = pattern.sub("", text)
    return out, log


def stage2_abbreviations(line: str) -> tuple[str, list[tuple[str, str]]]:
    """Expand EME abbreviations using word boundaries."""
    log = []
    out = line
    for abbr, expansion in ABBREVIATIONS.items():
        pattern = re.compile(rf"\b{re.escape(abbr)}\b")
        for m in pattern.finditer(out):
            log.append((m.group(0), expansion))
        out = pattern.sub(expansion, out)
    amp_pattern = re.compile(r" & ")
    for m in amp_pattern.finditer(out):
        log.append((" & ", " and "))
    out = amp_pattern.sub(" and ", out)
    return out, log


def stage3_gap_normalization(line: str) -> tuple[str, list[tuple[str, str]]]:
    """Normalize gap/illegible markers to [illegible]."""
    log = []
    out = line
    for pat, repl in GAP_PATTERNS:
        for m in pat.finditer(out):
            if m.group(0) != repl:
                log.append((m.group(0), repl))
        out = pat.sub(repl, out)
    return out, log


def stage3b_roman_numeral_dots(line: str) -> tuple[str, list[tuple[str, str]]]:
    """Normalize .xii. -> xii. etc.; ensure single space before."""
    log = []

    def repl(m):
        num = m.group(1)
        tail = m.group(0)[-1]
        old = m.group(0)
        new = f" {num}{tail}"
        log.append((old, new))
        return new

    out = ROMAN_NUMERAL_RE.sub(repl, line)
    out = re.sub(r"  +", " ", out).strip()
    return out, log


def stage4_whitespace(line: str) -> tuple[str, list[tuple[str, str]]]:
    """Collapse spaces, remove space before punctuation, strip."""
    log = []
    original = line
    s = re.sub(r" +", " ", line)
    s = re.sub(r" +([.,;:!?\]\)])", r"\1", s)
    s = s.strip()
    if s != original:
        log.append((original, s))
    return s, log


def run_all_stages(text: str) -> tuple[str, list[tuple[str, int, str, str]]]:
    """Run all cleaning stages. Returns (cleaned_text, log_entries)."""
    all_log = []

    text, log1 = stage1_line_break_rejoin(text)
    for before, after in log1:
        all_log.append(("line_break_rejoin", 0, before, after))

    lines = [(i, ln) for i, ln in enumerate(text.split("\n"), start=1)]

    lines, log2 = apply_stage(lines, "abbreviation", stage2_abbreviations)
    all_log.extend(log2)

    lines, log3 = apply_stage(lines, "gap_normalization", stage3_gap_normalization)
    all_log.extend(log3)

    lines, log3b = apply_stage(lines, "roman_numeral_dots", stage3b_roman_numeral_dots)
    all_log.extend(log3b)

    lines, log4 = apply_stage(lines, "whitespace", stage4_whitespace)
    all_log.extend(log4)

    cleaned = "\n".join(line for _, line in lines)
    para_before = cleaned
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    if cleaned != para_before:
        all_log.append(("paragraph_blank", 0, "multiple blanks", "single blank"))

    return cleaned, all_log


def write_log(log_entries: list[tuple[str, int, str, str]], path: Path) -> None:
    """Write detailed log: stage, line number, before/after."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("stage\tline\tbefore\tafter\n")
        for stage, line_num, before, after in log_entries:
            before_esc = before.replace("\t", " ").replace("\n", " ")
            after_esc = after.replace("\t", " ").replace("\n", " ")
            f.write(f"{stage}\t{line_num}\t{before_esc}\t{after_esc}\n")


def summarize(log_entries: list[tuple[str, int, str, str]]) -> dict[str, int]:
    counts = {}
    for stage, *_ in log_entries:
        counts[stage] = counts.get(stage, 0) + 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract and clean Michigan Digital Library (EEBO-TCP) TEI XML or plain text for VARD.",
        epilog="Example: python clean_text.py mybook.xml -o mybook_cleaned_for_vard.txt",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Input file: .xml (TEI) or .txt (plain text)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output cleaned text path (default: <input_stem>_cleaned_for_vard.txt)",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=None,
        help="Optional: write detailed change log to this file",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}")

    if args.input.suffix.lower() == ".xml":
        print("Extracting body text from TEI XML...", file=sys.stderr)
    text = load_input(args.input)
    cleaned, log_entries = run_all_stages(text)

    out_path = args.output
    if out_path is None:
        out_path = args.input.with_stem(args.input.stem + "_cleaned_for_vard").with_suffix(".txt")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(cleaned, encoding="utf-8")

    if args.log is not None:
        write_log(log_entries, args.log)
        print(f"Log: {args.log}", file=sys.stderr)

    counts = summarize(log_entries)
    print("Cleaning summary:")
    print(f"  Hyphens rejoined:        {counts.get('line_break_rejoin', 0)}")
    print(f"  Abbreviations expanded:  {counts.get('abbreviation', 0)}")
    print(f"  Gap markers normalized:  {counts.get('gap_normalization', 0)}")
    print(f"  Roman numeral dots:      {counts.get('roman_numeral_dots', 0)}")
    print(f"  Whitespace changes:      {counts.get('whitespace', 0)}")
    print(f"  Paragraph blank fixes:   {counts.get('paragraph_blank', 0)}")
    print(f"  Total modifications:     {len(log_entries)}")
    print(f"  Output: {out_path}")


if __name__ == "__main__":
    main()
