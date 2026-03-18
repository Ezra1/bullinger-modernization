#!/usr/bin/env python3
"""
Extract metadata and body text from EEBO-TCP TEI-XML (Bullinger, Apocalypse sermons).

Parses TEI using lxml.etree, handles the TEI namespace, and writes:
- metadata.json: title, author, date, publication info
- raw_extracted.txt: body text with sermon headings, paragraphs, [illegible], [note X.Y]
- footnotes.txt: note contents keyed by ID
"""

import argparse
import json
import re
from pathlib import Path
from typing import Callable

from lxml import etree

# TEI namespace used in EEBO-TCP documents
TEI_NS = "http://www.tei-c.org/ns/1.0"
NS_MAP = {"tei": TEI_NS}


def _qname(local: str) -> str:
    """Return Clark notation qualified name for a TEI element."""
    return f"{{{TEI_NS}}}{local}"


# Qualified names for TEI elements we use
TEI = _qname("TEI")
TEI_HEADER = _qname("teiHeader")
FILE_DESC = _qname("fileDesc")
TITLE_STMT = _qname("titleStmt")
TITLE = _qname("title")
AUTHOR = _qname("author")
EDITION_STMT = _qname("editionStmt")
EDITION = _qname("edition")
DATE = _qname("date")
PUBLICATION_STMT = _qname("publicationStmt")
PUBLISHER = _qname("publisher")
PUB_PLACE = _qname("pubPlace")
BODY = _qname("body")
DIV = _qname("div")
HEAD = _qname("head")
P = _qname("p")
NOTE = _qname("note")
GAP = _qname("gap")
HI = _qname("hi")
SEG = _qname("seg")
G = _qname("g")
PB = _qname("pb")
SOURCE_DESC = _qname("sourceDesc")
BIBL_FULL = _qname("biblFull")
EXTENT = _qname("extent")
IDNO = _qname("idno")
AVAILABILITY = _qname("availability")


def parse_tei(path: Path) -> etree._Element:
    """
    Parse a TEI-XML file and return the root element.

    Uses lxml.etree; the document must declare the TEI namespace.
    """
    parser = etree.XMLParser(recover=True, remove_blank_text=False)
    tree = etree.parse(str(path), parser)
    return tree.getroot()


def extract_metadata(root: etree._Element) -> dict:
    """
    Extract metadata from the teiHeader into a plain dict.

    Collects: title(s), author(s), date (edition and source), publication
    (publisher, place, date, idno, availability) from fileDesc and sourceDesc.
    """
    meta = {
        "title": [],
        "author": [],
        "date": None,
        "publication": {},
    }

    header = root.find(TEI_HEADER)
    if header is None:
        return meta

    fd = header.find(FILE_DESC)
    if fd is None:
        return meta

    # titleStmt
    ts = fd.find(TITLE_STMT)
    if ts is not None:
        for t in ts.findall(TITLE):
            if t.text or len(t):
                text = _element_text_only(t)
                if text.strip():
                    meta["title"].append(text.strip())
        for a in ts.findall(AUTHOR):
            if a.text or len(a):
                text = _element_text_only(a)
                if text.strip():
                    meta["author"].append(text.strip())

    # editionStmt / date (e.g. 1561)
    es = fd.find(EDITION_STMT)
    if es is not None:
        edition = es.find(EDITION)
        if edition is not None:
            d = edition.find(DATE)
            if d is not None and (d.text or d.get("when")):
                meta["date"] = (d.text or "").strip() or d.get("when", "").strip()

    # publicationStmt (TCP)
    ps = fd.find(PUBLICATION_STMT)
    if ps is not None:
        pub = {}
        p_el = ps.find(PUBLISHER)
        if p_el is not None:
            pub["publisher"] = _element_text_only(p_el).strip()
        pp = ps.find(PUB_PLACE)
        if pp is not None:
            pub["pubPlace"] = _element_text_only(pp).strip()
        for d in ps.findall(DATE):
            if d.get("when") or (d.text and d.text.strip()):
                pub["date"] = (d.text or "").strip() or d.get("when", "")
                break
        idnos = []
        for idno in ps.findall(IDNO):
            typ = idno.get("type")
            val = (idno.text or "").strip()
            if val:
                idnos.append({"type": typ, "value": val})
        if idnos:
            pub["idno"] = idnos
        av = ps.find(AVAILABILITY)
        if av is not None:
            p_av = av.find(P)
            if p_av is not None:
                pub["availability"] = _element_text_only(p_av).strip()[:500]
        meta["publication"] = pub

    # sourceDesc / biblFull (original edition)
    sd = fd.find(SOURCE_DESC)
    if sd is not None:
        bf = sd.find(BIBL_FULL)
        if bf is not None:
            orig = {}
            ts_bf = bf.find(TITLE_STMT)
            if ts_bf is not None:
                titles = [(_element_text_only(t).strip()) for t in ts_bf.findall(TITLE) if _element_text_only(t).strip()]
                if titles:
                    orig["title"] = titles[0] if len(titles) == 1 else titles
            for a in bf.findall(AUTHOR):
                text = _element_text_only(a).strip()
                if text:
                    orig.setdefault("author", []).append(text)
            ps_bf = bf.find(PUBLICATION_STMT)
            if ps_bf is not None:
                p_el = ps_bf.find(PUBLISHER)
                if p_el is not None:
                    orig["publisher"] = _element_text_only(p_el).strip()
                pp = ps_bf.find(PUB_PLACE)
                if pp is not None:
                    orig["pubPlace"] = _element_text_only(pp).strip()
                for d in ps_bf.findall(DATE):
                    if d.text and d.text.strip():
                        orig["date"] = d.text.strip()
                        break
            if orig:
                meta["sourceDesc"] = orig

    return meta


def _element_text_only(el: etree._Element) -> str:
    """Recursively concatenate text and tail from element and children, stripping inline tags (e.g. hi, g)."""
    parts = []
    if el.text:
        parts.append(el.text)
    for child in el:
        if child.tag in (G, PB):
            if child.tail:
                parts.append(child.tail)
            continue
        parts.append(_element_text_only(child))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def _normalize_space(s: str) -> str:
    """Collapse whitespace to single spaces and strip."""
    return re.sub(r"\s+", " ", (s or "").strip())


def _inline_text_and_tail(
    el: etree._Element,
    note_id_callback: Callable[[str, str], None],
    sermon_num: int,
    note_counter: list,
) -> str:
    """
    Walk element and children, handling .text and .tail; return concatenated string.

    - gap -> [illegible]
    - note -> [note sermon_num.n] and pass content to note_id_callback
    - hi, seg -> recurse (strip formatting, keep text)
    - g, pb -> skip (no output)
    """
    out = []
    if el.text:
        out.append(el.text)

    for child in el:
        tag = child.tag
        if tag == GAP:
            out.append("[illegible]")
            if child.tail:
                out.append(child.tail)
            continue
        if tag == NOTE:
            note_counter[0] += 1
            nid = f"{sermon_num}.{note_counter[0]}"
            note_text = _element_text_only(child)
            note_id_callback(nid, _normalize_space(note_text))
            out.append(f"[note {nid}]")
            if child.tail:
                out.append(child.tail)
            continue
        if tag in (G, PB):
            if child.tail:
                out.append(child.tail)
            continue
        # hi, seg, and any other inline: recurse and keep text
        out.append(
            _inline_text_and_tail(child, note_id_callback, sermon_num, note_counter)
        )
        if child.tail:
            out.append(child.tail)

    return "".join(out)


def _collect_paragraph_text(
    p_el: etree._Element,
    note_id_callback: callable,
    sermon_num: int,
    note_counter: list,
) -> str:
    """Collect text from a <p> element, handling mixed content and notes."""
    return _normalize_space(
        _inline_text_and_tail(p_el, note_id_callback, sermon_num, note_counter)
    )


def _head_text(el: etree._Element) -> str:
    """Get plain text of a head element (strip hi, g, etc.)."""
    return _normalize_space(_element_text_only(el))


def extract_body(root: etree._Element, notes_dict: dict) -> str:
    """
    Extract body text from the TEI root.

    - body/div[@type='sermons']: main section; its head becomes ##, each
      div[@type='sermon'] gets ## head and its <p> become paragraphs.
    - gap -> [illegible], note -> [note sermon_n.n] and stored in notes_dict.
    - hi/seg stripped to plain text.
    Returns markdown-ish text (headings, blank-line-separated paragraphs).
    """
    # TEI structure is root > text > body (body not direct child of root)
    body = root.find(f".//{BODY}")
    if body is None:
        return ""

    lines = []
    note_counter = [0]  # mutable so inner calls can increment

    def register_note(nid: str, text: str) -> None:
        notes_dict[nid] = text

    # This file uses body > div type="sermons" > div n="N" type="sermon"
    for div in body.findall(DIV):
        if div.get("type") != "sermons":
            continue
        head_el = div.find(HEAD)
        if head_el is not None:
            lines.append("## " + _head_text(head_el))
            lines.append("")

        for sermon_div in div.findall(DIV):
            if sermon_div.get("type") != "sermon":
                continue
            note_counter[0] = 0
            sermon_num = sermon_div.get("n") or "0"
            try:
                sermon_num = int(sermon_num)
            except ValueError:
                sermon_num = 0

            sh = sermon_div.find(HEAD)
            if sh is not None:
                lines.append("## " + _head_text(sh))
                lines.append("")

            for p_el in sermon_div.findall(P):
                para = _collect_paragraph_text(
                    p_el, register_note, sermon_num, note_counter
                )
                if para:
                    lines.append(para)
                    lines.append("")

    # drop trailing blank line
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) if lines else ""


def write_metadata(meta: dict, out_path: Path) -> None:
    """Write metadata dict to a JSON file."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def write_footnotes(notes_dict: dict, out_path: Path) -> None:
    """Write footnotes to a text file with IDs (e.g. [note 1.1] ...)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for nid in sorted(notes_dict.keys(), key=_footnote_sort_key):
            f.write(f"[note {nid}]\n")
            f.write(notes_dict[nid] + "\n\n")


def _footnote_sort_key(nid: str):
    """Sort note IDs numerically: 1.1, 1.2, 2.1, ..."""
    parts = nid.split(".")
    try:
        return (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
    except ValueError:
        return (0, 0)


def write_body_text(text: str, out_path: Path) -> None:
    """Write extracted body text to a file."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract metadata and body from EEBO-TCP TEI-XML (Bullinger Apocalypse)."
    )
    parser.add_argument(
        "input",
        type=Path,
        nargs="?",
        default=Path("01-raw/B11837.xml"),
        help="Input TEI-XML file path",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("02-cleaned"),
        help="Output directory for metadata.json, raw_extracted.txt, footnotes.txt",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}")

    root = parse_tei(args.input)
    if root.tag != TEI:
        raise SystemExit("Root element is not TEI.")

    meta = extract_metadata(root)
    notes_dict = {}
    body_text = extract_body(root, notes_dict)

    out_dir = args.output_dir
    write_metadata(meta, out_dir / "metadata.json")
    write_footnotes(notes_dict, out_dir / "footnotes.txt")
    write_body_text(body_text, out_dir / "raw_extracted.txt")


if __name__ == "__main__":
    main()
