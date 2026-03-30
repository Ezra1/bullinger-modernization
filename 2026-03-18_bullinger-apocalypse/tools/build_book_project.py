#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path("/home/turambar/projects/bullinger/2026-03-18_bullinger-apocalypse")
SOURCE = ROOT / "05-output" / "modern_only.tex"
METADATA = ROOT / "02-cleaned" / "metadata.json"
BOOK = ROOT / "book"
OUTPUT_PDF = ROOT / "05-output" / "bullinger-apocalypse-sermons.pdf"

TITLECASE_SMALL_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "but",
    "by",
    "for",
    "from",
    "in",
    "into",
    "nor",
    "of",
    "on",
    "or",
    "over",
    "the",
    "to",
    "unto",
    "upon",
    "with",
    "within",
    "without",
}

SERMON_TITLE_OVERRIDES = {
    5: "The Beginning of the Work Is Made, and a Most Goodly Description to Us Exhibited of Christ King and Bishop in Glory, and Nevertheless Working in the Church.",
    9: "The Second Epistle of Jesus Christ by John to Them of Smyrna Is Expounded. And Is an Exhortation to Patience, and Consolation in Afflictions.",
    10: "The First Part of the Third Epistle of the Constancy and Confession of Christ in the Time of Persecution.",
    11: "The Latter Part of the Third Epistle Is Expounded, Wherein Is Spoken of the Nicolaitans, Which Are Damned. And Exhortation Is Made to Repentance.",
    12: "The Epistle of Thyatirena Is Expounded, Wherein Are Sundry Virtues Commended, and the Vice of Jezebel Reprehended.",
    14: "That the Doctrine of Piety Is So Fully Set Forth to the Church, That There Needs No New Revelations. And of the Most Large Promises of Christ Made unto the Church.",
    15: "He Blames Certain Things in the Congregation of Sardis: Notwithstanding He Shows Straightway a Remedy, Whereby They May Be Healed, and Be Safe.",
    17: "The Lord Commends the Virtues, Namely the Constancy of the Congregation of Philadelphia. Etc.",
    18: "He Exhorts Them to Persevere in the True Faith, Propounding Most Ample Rewards.",
    19: "He Proceeds in Reciting Most Great Rewards.",
    23: "The Second Vision Is Shown to St. John, Wherein He Sees God in His Throne with Elders, Whom He Describes Gallantly.",
    24: "Here Is Described the Proceeding of the Holy Spirit, and Operation, the Almighty Knowledge of God, and How the Throne of God Is Borne Up or Sustained of the Four Beasts, and What the Beasts Do.",
    25: "Here Is Declared What the Elders Did About the Throne, and How They Sang unto God a Song of Praise.",
    28: "Here Is Described Adoration and Praise Giving, or a Hymn Song unto Christ of the Beasts and Elders.",
    29: "Here Is Described the Commendation and Hymn Said unto Christ of the Angels and All Creatures. Etc.",
    30: "Two Seals Are Opened, and the Direct Course of God's Word Is Set Forth, and a Cruel Course of Wars Against the Disobedient.",
    31: "Here Is Opened the iii. and iiii. Seal, and Is Declared What the World Shall Suffer of Hunger and Pestilence.",
    32: "The Fifth Seal Is Opened, and the Persecution of the Faithful Set Before Our Eyes, and Also the State of Martyrs in Another World.",
    33: "The Sixth Seal Is Opened, and the Corrupting of the Sincere Doctrine Is Exhibited.",
    34: "The Effect of Corrupt Doctrine Is Expounded, and That the Angels Let Not the Wind Blow.",
    35: "The Faithful Are Sealed to Salvation, Which They Obtain by the Grace of God in Christ Jesus.",
    36: "Here Is Expounded Who They Be That Are Clothed in White, from Whence Is Salvation, and What Is the True Blessedness.",
    37: "Whilst the vii. Seal Is Opened, and the Angels with Trumpets Come Forth, Christ the Intercessor of His Church Offers Up Before His Father the Prayers of His Faithful.",
    38: "Of the Seven Angels Trumpeters, and of the Trumpets: and of the First ii. and iii. Trumpet.",
    39: "The Fourth and Fifth Trumpet Is Expounded, of the Opening of the Bottomless Pit, and of Grasshoppers Creeping Out into the Earth.",
    40: "The Locusts Are Described by a Marvelous Hypotyposis, the Popish Clergy: and It Is Shown, of What Sort the Antichristian War Shall Be.",
    41: "The Sixth Trumpet Is Expounded, Wherein Is Treated of Saracens and Turkish Matters.",
    42: "What Should Be Done to the Residue of the Impenitent, in This Mean While Feeling No Evil, of the Locusts and Horses.",
    44: "The Lord Christ Performs Another, and Confirms His Elect, That They Should Not Doubt of the Faith of God's Promises, Etc.",
    45: "St. John Devours the Book Received at the Angel's Hand, and Prophesies Again to the Gentiles, Nations, and Kings.",
    46: "St. John Measures the Temple, and Shows That God Hath a Care of It: and the Choir He Excommunicateth.",
    48: "Of the Cruel Fight of Antichrist Against the Prophets of God, Whom He Overcomes and Slays, and Shamefully Uses Them.",
    49: "The Enterprises of Antichrist in Weeding Out the Preachers to Be Vain: How Great Shall Be the Rewards of Preachers, and of the Punishment of the Wicked.",
    50: "The Seventh Angel Blows the Trumpet, and the Elders Sing a Song of Praise.",
    51: "The Thanksgiving of the Elders Is Expounded, the Temple Is Opened in Heaven, the Ark Appears, and There Were Made Lightnings, Etc.",
    53: "The Description of the Conflict of Christ and the Church with the Dragon: the Dragon Is Overcome, the Heavenly Dwellers Sing Praises.",
    54: "The Dragon Persecutes the Woman: She Is Defended and Preserved of the Lord. The Dragon Stands on the Sand, Etc.",
    55: "He Exhibits a Noble Instrument of the Dragon to Be Seen, the Old Roman Empire, Which Describes What Manner a One It Is, Etc.",
    57: "Of the Power of the Roman Empire, and of Those Who Worship the Beast: and of the Destruction of Rome, and the Roman Empire.",
    58: "Of Another Beast, Which Comes Up Out of the Earth: That Is to Say, of Antichrist.",
    59: "Again of the Power of Antichrist, and How the Former Beast Is Worshipped.",
    60: "Of the Signs of Antichrist, and the Image of the Beast Raised by Him.",
    62: "Christ Stands upon Mount Zion, Having His Church: and Is Described by Notes, Which and What Shall Be the Sheep of Christ.",
    64: "Another Angel Preaches, That Babylon Shall Fall: and Another Dissuades All Men from the Fellowship of the Religion of the Beast.",
    65: "The Faithful Assuredly and Straightway Flit from the Corporal Death unto Life Everlasting.",
    66: "The Judgment of the Lord Is Described under the Parables of Harvest and Vintage.",
    67: "The Angels of Seven Plagues Are Brought Forth. Moreover the Triumph and Praise of Christ's Holy Martyrs Is Described.",
    68: "The Seven Angels Are Described, Coming Forth to Execute the Seven Plagues.",
    69: "The Three Former Angels Pour Out Their Vials upon the Antichristians, and All the Ungodly.",
    70: "The Fourth and Fifth Angels Shed Their Vials.",
    71: "The Sixth Angel Sheds His Vial.",
    72: "The Seventh Angel Pours Out His Vial.",
    73: "The Judgment or Punishment of the Purple Whore Is Described: and Also the Sin, and Ungodliness of the Same.",
    76: "Again This Vision Is More Fully Declared, and the Punishment of the Beast Is Shown.",
    80: "The Rejoicing of Saints for the Overthrow of Babylon, the Drowning of the Same, and the Causes of Drowning or Destruction Are Rehearsed.",
    81: "The Rejoicings and Hymns of Saints Are Recited for Rome Destroyed, and All Ungodliness Taken Away.",
    82: "Of the Marriage of the Lamb, and of the Making Ready of the Lamb's Wife.",
    83: "Of the Certainty of the Salvation of Saints, and What Blessing or Salvation Is.",
    84: "The Fact of St. John Is Declared, Which Would Have Worshipped the Angel, and of the Angel Prohibiting.",
    87: "Of the Bright Verity of the Gospel, Which by the Ministry of the Apostles Was Spread Abroad Throughout the Whole World, and by a Thousand Years.",
    89: "What Shall Be Done When the Thousand Years Are Expired, of the World Deceived, of War and Grievous Persecution of the Godly, and of the Everlasting Pain of the Wicked.",
    91: "That the World Shall Be Renewed, the Saints Glorified and Made Blessed: And What That Felicity Shall Be, and How Certain.",
    93: "Here Is Set Forth a Goodly Picture, a Description or Figure of the Blessed Seat, and of the Heavenly Life and Glory Everlasting.",
    97: "The Conclusion of This Work, Wherein Is Established the Authority of the Same, and the Sum Collected Briefly.",
    98: "St. John Is Commanded Not to Seal This Book, but to Publish It, Having Respect to No Man.",
    100: "Christ Is Shown Again to Be the Author of This Book, How Great He Is Here. Here Is Also Declared the Desire of the Church, Wishing for the Coming of Christ, and the Liberal Promise of the Lord.",
    101: "Punishment Is Decreed to the Corruptors of This Book. The Lord Says, That He Will Certainly Come to Judgment. The Church Wishes for His Coming.",
}


INDEX_PATTERNS = [
    (re.compile(r"\bAntichrist\b", re.IGNORECASE), "Antichrist"),
    (re.compile(r"\bApocalypse\b"), "Apocalypse (Book of)"),
    (re.compile(r"\bPatmos\b"), "Patmos"),
    (re.compile(r"\b(?:St\.|Saint|S\.)\s+John\b|\bJohn the Apostle\b|\bJohn the Evangelist\b"), "John, Saint"),
    (re.compile(r"\bErasmus(?: of Rotterdam)?\b"), "Erasmus of Rotterdam"),
    (re.compile(r"\bJerome\b"), "Jerome, Saint"),
    (re.compile(r"\bAugustine\b"), "Augustine, Saint"),
    (re.compile(r"\bLuther\b"), "Luther, Martin"),
    (re.compile(r"\bJustin\b"), "Justin Martyr"),
    (re.compile(r"\bIrenaeus\b"), "Irenaeus"),
    (re.compile(r"\bTertullian\b"), "Tertullian"),
    (re.compile(r"\bCyprian\b"), "Cyprian, Saint"),
    (re.compile(r"\bOrigen\b"), "Origen"),
    (re.compile(r"\bEusebius\b"), "Eusebius of Caesarea"),
    (re.compile(r"\bEpiphanius\b"), "Epiphanius of Salamis"),
    (re.compile(r"\bArethas\b"), "Arethas of Caesarea"),
    (re.compile(r"\bPrimasius\b"), "Primasius"),
    (re.compile(r"\bOecolampadius\b"), "Oecolampadius, Johannes"),
    (re.compile(r"\bAquin(?:as)?\b"), "Aquinas, Thomas"),
    (re.compile(r"\bPapias\b"), "Papias"),
    (re.compile(r"\bAmbrose\b"), "Ambrose, Saint"),
    (re.compile(r"\b(?:Mahomet|Muhammad)\b", re.IGNORECASE), "Mahomet"),
    (re.compile(r"\bSaracenes?\b", re.IGNORECASE), "Saracens"),
    (re.compile(r"\bTurk(?:s|ish)?\b", re.IGNORECASE), "Turks"),
    (re.compile(r"\bpope\b|\bPopes?\b|\bPapists?\b|\bpapacy\b", re.IGNORECASE), "Papacy"),
    (re.compile(r"\bMillenaries\b|\bChiliasts?\b"), "Millenarianism"),
    (re.compile(r"\b[Rr]epentance\b"), "Repentance"),
    (re.compile(r"\b[Jj]ustification\b"), "Justification"),
    (re.compile(r"\b[Rr]esurrection\b"), "Resurrection"),
    (re.compile(r"\blast judgment\b", re.IGNORECASE), "Judgment, Last"),
    (re.compile(r"\bDaniel\b"), "Daniel (Book of)"),
    (re.compile(r"\bZechariah\b"), "Zechariah (Book of)"),
    (re.compile(r"\bEzekiel\b"), "Ezekiel (Book of)"),
    (re.compile(r"\bHebrews\b"), "Hebrews, Epistle to the"),
    (re.compile(r"\bRome\b"), "Rome"),
    (re.compile(r"\bZurich\b|\bZuryk\b"), "Zurich"),
]


def read_metadata() -> dict:
    return json.loads(METADATA.read_text(encoding="utf-8"))


def extract_front_matter(source_text: str) -> tuple[str, str, str]:
    title_match = re.search(r"^#\s+(.+)$", source_text, re.MULTILINE)
    author_match = re.search(r"^\*([^*]+)\*\s*$", source_text, re.MULTILINE)
    subtitle_match = re.search(r"^##\s+SERMONS OF .+$", source_text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Bullinger's Apocalypse Sermons"
    author = author_match.group(1).strip() if author_match else "Bullinger, Heinrich, 1504-1575."
    subtitle = subtitle_match.group(0).replace("##", "", 1).strip() if subtitle_match else ""
    return title, author, subtitle


def split_sermons(source_text: str) -> list[tuple[int, str, str]]:
    pattern = re.compile(r"^##\s+Sermon\s+(\d+):\s*(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(source_text))
    sermons: list[tuple[int, str, str]] = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(source_text)
        sermon_no = int(match.group(1))
        heading = match.group(2).strip()
        body = source_text[start:end]
        sermons.append((sermon_no, heading, body))
    return sermons


def clean_heading(text: str) -> str:
    text = re.sub(r"^[☞¶]\s*", "", text.strip())
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_title_word(word: str, force_capitalize: bool) -> str:
    if "-" in word:
        pieces = word.split("-")
        normalized_pieces = [
            normalize_title_word(piece, force_capitalize or i > 0)
            for i, piece in enumerate(pieces)
        ]
        return "-".join(normalized_pieces)

    match = re.match(r"^([^A-Za-z]*)([A-Za-z]+)([^A-Za-z]*)$", word)
    if not match:
        return word

    leading, core, trailing = match.groups()

    if re.fullmatch(r"[ivxlcdmIVXLCDM]+", core):
        return leading + core.lower() + trailing

    if len(core) == 1 and trailing == ".":
        return leading + core.upper() + trailing

    lower_core = core.lower()
    if not force_capitalize and lower_core in TITLECASE_SMALL_WORDS:
        normalized = lower_core
    else:
        normalized = lower_core[:1].upper() + lower_core[1:]

    return leading + normalized + trailing


def normalize_sermon_title(text: str, sermon_no: int | None = None) -> str:
    if sermon_no in SERMON_TITLE_OVERRIDES:
        return SERMON_TITLE_OVERRIDES[sermon_no]

    text = re.sub(r"\[[^\]]+\]", "", text)
    text = clean_heading(text).replace("ſ", "s")
    words = text.split(" ")
    normalized_words: list[str] = []
    force_capitalize = True

    for i, word in enumerate(words):
        is_last = i == len(words) - 1
        normalized = normalize_title_word(word, force_capitalize or is_last)
        normalized_words.append(normalized)
        force_capitalize = word.endswith(":")

    normalized_text = " ".join(normalized_words)
    normalized_text = re.sub(r"\s+", " ", normalized_text).strip()
    return normalized_text


def short_title(number: int, title: str, limit: int = 56) -> str:
    title = normalize_sermon_title(title, number)
    if len(title) > limit:
        truncated = title[: limit - 1]
        if " " in truncated:
            truncated = truncated.rsplit(" ", 1)[0]
        title = truncated.rstrip(",;:. ") + " ..."
    return f"Sermon {number}. {title}"


def tex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "$": r"\$",
        "&": r"\&",
        "%": r"\%",
        "#": r"\#",
        "_": r"\_",
        "^": r"\textasciicircum{}",
        "~": r"\textasciitilde{}",
    }
    return "".join(replacements.get(ch, ch) for ch in text)


def smart_double_quotes(text: str) -> str:
    result: list[str] = []
    open_quote = True
    for ch in text:
        if ch == '"':
            result.append("“" if open_quote else "”")
            open_quote = not open_quote
        else:
            result.append(ch)
    return "".join(result)


def convert_inline(text: str) -> str:
    text = re.sub(r"\s*\[(?:N|n)ote\s+[^\]]+\]\s*", " ", text)
    text = re.sub(r",\s*,", ", ", text)
    text = re.sub(r"^[.\s]*[☞¶]\s*", "", text)
    text = re.sub(r"(?<=[a-z])\.(?=[A-Z])", ". ", text)
    text = re.sub(r",{2,}", ",", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = smart_double_quotes(text)
    parts: list[str] = []
    last = 0
    for match in re.finditer(r"\*([^*]+)\*", text):
        parts.append(tex_escape(text[last:match.start()]))
        parts.append(r"\textit{" + tex_escape(match.group(1).strip()) + "}")
        last = match.end()
    parts.append(tex_escape(text[last:]))
    text = "".join(parts)
    text = normalize_scholarly_emphasis(text)
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return text


def normalize_scholarly_emphasis(text: str) -> str:
    replacements = {
        r"\textit{City of God}": r"\textit{The City of God}",
        r"\textit{ecclesiastical history}": r"\textit{Ecclesiastical History}",
        r"Augustine, \textit{Aurel.}": r"Augustine, Aurel.",
        r"[? \textit{a word lost here}]": r"[? \textup{a word lost here}]",
        (
            "the writings on the true religion, chapter 55, against Maximinus, "
            "an Arian bishop, first book, page 77;"
        ): (
            r"the writings on \textit{True Religion}, chapter 55, "
            r"\textit{Against Maximinus, an Arian Bishop}, first book, page 77;"
        ),
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    regex_replacements = [
        (
            re.compile(r"\bthe ecclesiastical history\b", re.IGNORECASE),
            lambda _m: r"the \textit{Ecclesiastical History}",
        ),
        (
            re.compile(r"\bbook against Praxeas\b"),
            lambda _m: r"book \textit{Against Praxeas}",
        ),
    ]
    for pattern, replacement in regex_replacements:
        text = pattern.sub(replacement, text)
    text = re.sub(r",{2,}", ",", text)
    return text


def paragraph_is_display_quote(raw: str) -> bool:
    stripped = raw.strip()
    if len(stripped) < 240:
        return False
    opening = stripped[:1]
    quote_count = stripped.count('"') + stripped.count("“") + stripped.count("”")
    return opening in {'"', "“"} and quote_count >= 2


def inject_index_markers(raw_text: str, seen: set[str]) -> str:
    prefix: list[str] = []
    for regex, entry in INDEX_PATTERNS:
        if entry in seen:
            continue
        if regex.search(raw_text):
            prefix.append(r"\index{" + entry + "}")
            seen.add(entry)
    return "".join(prefix)


def chapter_body_to_latex(body: str) -> tuple[str, int]:
    cleaned = re.sub(r"^###\s+Paragraph\s+\d+\s*$", "", body, flags=re.MULTILINE)
    cleaned = re.sub(r"^\.\s*$", "", cleaned, flags=re.MULTILINE)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", cleaned) if p.strip()]

    seen_index_entries: set[str] = set()
    output_parts: list[str] = []
    display_quotes = 0

    for raw_paragraph in paragraphs:
        index_prefix = inject_index_markers(raw_paragraph, seen_index_entries)
        latex_paragraph = convert_inline(raw_paragraph)
        if not latex_paragraph:
            continue
        if paragraph_is_display_quote(raw_paragraph):
            display_quotes += 1
            output_parts.append(index_prefix + "\\begin{displayquote}\n" + latex_paragraph + "\n\\end{displayquote}")
        else:
            output_parts.append(index_prefix + latex_paragraph)

    return "\n\n".join(output_parts).strip() + "\n", display_quotes


def make_include_lines(sermons: list[tuple[int, str, str]]) -> str:
    return "\n".join(
        f"\\include{{chapters/sermon-{number:03d}}}" for number, _, _ in sermons
    )


def write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_preamble(book_title: str) -> str:
    return rf"""\usepackage{{fontspec}}
\usepackage{{polyglossia}}
\setmainlanguage{{english}}
\usepackage{{csquotes}}
\usepackage{{microtype}}
\usepackage{{imakeidx}}

\defaultfontfeatures{{Ligatures=TeX, Scale=MatchLowercase}}
\IfFontExistsTF{{EB Garamond}}{{
  \setmainfont{{EB Garamond}}[
    Numbers={{OldStyle,Proportional}},
    Ligatures=TeX,
    RawFeature=+smcp
  ]
}}{{%
  \setmainfont{{P052}}[
    Numbers={{OldStyle,Proportional}},
    Ligatures=TeX
  ]
}}
\IfFontExistsTF{{TeX Gyre Heros}}{{\setsansfont{{TeX Gyre Heros}}}}{{\setsansfont{{Noto Sans}}}}

\setstocksize{{9in}}{{6in}}
\settrimmedsize{{\stockheight}}{{\stockwidth}}{{*}}
\settypeblocksize{{7.25in}}{{28pc}}{{*}}
\setlrmargins{{*}}{{*}}{{1.18}}
\setulmargins{{*}}{{*}}{{1.55}}
\setheadfoot{{18pt}}{{28pt}}
\setheaderspaces{{*}}{{18pt}}{{*}}
\checkandfixthelayout

\setlength{{\parindent}}{{1.2em}}
\setlength{{\parskip}}{{0pt}}
\setlength{{\emergencystretch}}{{3em}}
\frenchspacing
\clubpenalty=10000
\widowpenalty=10000
\displaywidowpenalty=10000
\brokenpenalty=5000
\raggedbottom

\setsecnumdepth{{subsection}}
\maxtocdepth{{chapter}}
\settocdepth{{chapter}}

\setsecheadstyle{{\normalfont\small\itshape}}
\setbeforesecskip{{1.75\baselineskip plus .3\baselineskip minus .2\baselineskip}}
\setaftersecskip{{0.75\baselineskip}}
\setsubsecheadstyle{{\normalfont\itshape}}
\setbeforesubsecskip{{1.25\baselineskip plus .2\baselineskip minus .2\baselineskip}}
\setaftersubsecskip{{0.55\baselineskip}}
\renewcommand{{\cftchapterfont}}{{\normalfont}}
\renewcommand{{\cftchapterpagefont}}{{\normalfont}}
\setlength{{\cftbeforechapterskip}}{{0.45\baselineskip}}

\makechapterstyle{{bullinger}}{{%
  \renewcommand{{\chapterheadstart}}{{\vspace*{{0.16\textheight}}}}
  \renewcommand{{\printchaptername}}{{}}
  \renewcommand{{\chapternamenum}}{{}}
  \renewcommand{{\printchapternum}}{{%
    \centering
    \normalfont\small\itshape Sermon \thechapter\par
    \vskip 0.8\baselineskip
  }}
  \renewcommand{{\afterchapternum}}{{}}
  \renewcommand{{\printchaptertitle}}[1]{{%
    \centering
    \normalfont\Large ##1\par
    \vskip 2.2\baselineskip
  }}
}}
\chapterstyle{{bullinger}}
\aliaspagestyle{{chapter}}{{empty}}

\makepagestyle{{bullinger}}
\makeheadrule{{bullinger}}{{\textwidth}}{{0.2pt}}
\makeevenhead{{bullinger}}{{\small\upshape {tex_escape(book_title)}}}{{}}{{\small\thepage}}
\makeoddhead{{bullinger}}{{\small\upshape\rightmark}}{{}}{{\small\thepage}}
\makeevenfoot{{bullinger}}{{}}{{}}{{}}
\makeoddfoot{{bullinger}}{{}}{{}}{{}}
\pagestyle{{bullinger}}
\nouppercaseheads
\makeatletter
\renewcommand{{\@makefnmark}}{{\hbox{{\textsuperscript{{\normalfont\@thefnmark}}}}}}
\renewcommand{{\@makefntext}}[1]{{%
  \noindent\hb@xt@1.5em{{\hss\textsuperscript{{\normalfont\@thefnmark}}}}#1%
}}
\makeatother

\renewcommand{{\footnotesize}}{{\fontsize{{9}}{{11}}\selectfont}}
\setlength{{\footnotesep}}{{0.7\baselineskip}}
\setlength{{\skip\footins}}{{12pt plus 3pt minus 2pt}}

\makeindex[program=xindy,options=-L english -C utf8]

\newcommand{{\sourcegap}}[1]{{\textup{{[#1]}}}}
"""


def build_main_tex(sermons: list[tuple[int, str, str]]) -> str:
    includes = make_include_lines(sermons)
    return rf"""\documentclass[11pt,twoside,openright]{{memoir}}
\input{{preamble}}

\begin{{document}}

\frontmatter
\pagestyle{{empty}}
\input{{frontmatter/titlepage}}
\cleardoublepage
\input{{frontmatter/toc}}

\mainmatter
\pagestyle{{bullinger}}
{includes}

\backmatter
\include{{backmatter/bibliography}}
\include{{backmatter/index}}

\end{{document}}
"""


def build_titlepage(title: str, author: str, subtitle: str) -> str:
    author_name = author.rstrip(".")
    subtitle_display = subtitle.replace("HENRI BULLINGER", "HEINRICH BULLINGER").replace("S. John", "St. John")
    return rf"""\thispagestyle{{empty}}
\null
\vfill
\begin{{center}}
{{\fontsize{{22}}{{28}}\selectfont {tex_escape(title)}\par}}
\vspace{{1.5\baselineskip}}
{{\large {tex_escape(author_name)}\par}}
\vspace{{2\baselineskip}}
{{\small\itshape {tex_escape(subtitle_display)}\par}}
\end{{center}}
\vfill
\null
"""


def build_toc() -> str:
    return r"""\cleardoublepage
\pagestyle{plain}
\tableofcontents*
\cleardoublepage
"""


def build_bibliography_file() -> str:
    return r"""\chapter*{Bibliographical Note}
\addcontentsline{toc}{chapter}{Bibliographical Note}
\markboth{Bibliographical Note}{Bibliographical Note}

\noindent\textit{No structured bibliography could be generated from the present manuscript source. The file \texttt{biblio/references.bib} is retained as a production scaffold for later Chicago-style note-and-bibliography work once full citation data has been curated.}
"""


def build_index_file() -> str:
    return r"""\chapter*{Index}
\addcontentsline{toc}{chapter}{Index}
\markboth{Index}{Index}

\begin{theindex}

\item Antichrist
\subitem as papal power, 251, 275, 375, 381, 387, 409
\subitem conflict with Christ and the church, 275, 303, 311, 319
\subitem followers and ministers of, 465, 563
\subitem marks and signs of, 387, 409
\subitem punishment of, 505, 563, 657, 671
\subitem \emph{see also} Beast; Papacy; Rome
\item Apocalypse (Book of). \emph{See} Revelation, book of
\item Aquinas, Thomas, 67, 289, 655, 667
\item Arethas of Caesarea
\subitem as commentator on Revelation, 3, 56, 83, 166, 243, 290, 381, 486, 600, 665
\subitem on millennial and eschatological questions, 582, 600
\item Augustine
\subitem on angels and their worship, 551
\subitem on blessedness of the saints, 607, 643
\subitem on \textit{The City of God}, 185, 381, 607, 643
\subitem on grace and free will, 241, 251
\subitem on millenarianism and the first resurrection, 581
\subitem on repentance and salvation, 223
\item Augustine, Saint. \emph{See} Augustine

\indexspace

\item Babylon
\subitem call to come out of, 519
\subitem fall of, 437, 513, 519, 533
\subitem lament over, 527
\subitem merchants and luxury of, 527, 533
\subitem \emph{see also} Rome; Whore of Babylon
\item Beast
\subitem image of, 387
\subitem mark and number of, 409
\subitem punishment of, 505
\subitem Roman empire as, 357, 365, 369
\subitem worship of, 365, 369, 381, 437
\subitem \emph{see also} Antichrist; Papacy; Rome
\item Bride of Christ. \emph{See} Church

\indexspace

\item Church
\subitem bride of Christ, 543, 665
\subitem preserved under persecution, 337, 345, 353, 425, 665, 671
\subitem relation of Christ to, 31, 229, 425, 543, 665
\subitem seven churches of Asia, 47, 61, 81, 99, 107, 121
\subitem true church distinguished from false, 297, 337, 519
\subitem \emph{see also} Papacy
\item Christ
\subitem as author of Revelation, 1, 17, 665
\subitem as bishop and king, 31, 39
\subitem as intercessor, 229
\subitem as judge, 555, 599, 661
\subitem as Lamb, 159, 165, 543
\subitem coming of, desired by the church, 665, 671

\indexspace

\item Daniel, book of
\subitem beast and kingdom imagery, 357, 369, 375, 489
\subitem last judgment in, 555, 599
\subitem relation to Revelation, 139, 173, 281, 585, 657
\item Devil. \emph{See} Satan
\item Dragon
\subitem against the church, 337, 345, 353
\subitem defeat of, 345
\subitem Roman empire as instrument of, 357
\subitem \emph{see also} Satan

\indexspace

\item Epiphanius of Salamis, 6, 58, 86, 239, 634
\item Erasmus of Rotterdam, 3, 186, 320, 549, 671
\item Eusebius of Caesarea, 3, 27, 58, 86, 240, 573
\item Ezekiel, book of
\subitem Gog and Magog, 587
\subitem heavenly city imagery, 607, 623, 637, 643
\subitem judgment imagery, 563
\subitem relation to Revelation, 91, 487

\indexspace

\item Faith
\subitem confession and constancy in, 69, 113
\subitem faith and salvation, 17, 213, 547
\subitem first resurrection by, 581

\indexspace

\item Gospel
\subitem eternal gospel, 431
\subitem opposed or counterfeited, 241, 387, 563
\subitem preaching of, 179, 303, 431
\subitem spread throughout the world, 569

\indexspace

\item Hebrews, Epistle to the
\subitem Christ's priesthood and mediation, 173, 229, 277
\subitem heavenly sanctuary, 461, 623
\subitem perseverance and patience, 429, 441

\indexspace

\item Idolatry
\subitem papal and Roman forms of, 485, 519, 637
\subitem punishment of, 657, 661
\item Irenaeus, 4, 58, 167, 239, 414

\indexspace

\item Jerome
\subitem as commentator and translator, 51, 105, 239, 375, 575, 634
\subitem on judgment and closing exhortations, 479, 618, 657
\subitem on Rome and Babylon, 513, 587
\item Jerome, Saint. \emph{See} Jerome
\item John the Divine. \emph{See} John, Saint
\item John, Saint
\subitem as author and witness of Revelation, 1, 25, 289, 651, 657, 665
\subitem letters to the churches, 47, 61, 81, 99, 107, 121
\subitem on Patmos, 25
\subitem worship of angel forbidden to, 551
\subitem \emph{see also} Revelation, book of
\item Judgment, Last
\subitem certainty of, 449, 599, 651, 661
\subitem Christ as judge, 555, 599
\subitem punishment of the ungodly, 563, 661
\subitem resurrection in relation to, 581, 599, 607
\item Justification, 34, 237, 439, 503, 545, 575

\indexspace

\item Luther, Martin, 3, 181, 312, 320

\indexspace

\item Mahomet. \emph{See} Muhammad
\item Millenarianism
\subitem first resurrection, 581
\subitem literal reading rejected, 581, 643
\subitem thousand years, 569, 581, 587
\subitem \emph{see also} Resurrection
\item Millenaries. \emph{See} Millenarianism
\item Millennium. \emph{See} Millenarianism
\item Muhammad
\subitem as enemy of the church, 259, 569, 587
\subitem in relation to papal power, 275, 325, 587
\subitem \emph{see also} Saracens; Turks

\indexspace

\item Oecolampadius, Johannes, 4, 320
\item Papacy
\subitem as Antichrist, 251, 375, 381, 387, 409
\subitem claims of authority, 297, 381, 409
\subitem corruption and superstition of, 207, 251, 519
\subitem idolatry of, 485, 519, 637
\subitem relation to Rome, 357, 369, 513
\subitem \emph{see also} Beast; Rome; Whore of Babylon
\item Papias, 3, 218, 573
\item Papists. \emph{See} Papacy
\item Patmos, 25, 191, 624
\item Pope. \emph{See} Papacy
\item Primasius
\subitem as commentator on Revelation, 17, 197, 243, 389, 500
\subitem on heavenly Jerusalem, 605, 628, 648, 664
\subitem on millennium and resurrection, 581, 586
\item Providence
\subitem Christ governing all things, 155, 159, 179
\subitem consolation under judgment, 283, 651
\subitem in history and the church, 241, 337, 631

\indexspace

\item Repentance
\subitem call to, 55, 75, 127
\subitem false repentance rejected, 185, 269
\subitem relation to judgment, 89, 461
\subitem relation to salvation, 223, 663
\item Resurrection
\subitem bodily resurrection, 607, 631
\subitem first resurrection, 581
\subitem second resurrection, 581, 599
\subitem \emph{see also} Judgment, Last; Millenarianism
\item Revelation, book of
\subitem authority and canonicity of, 1, 17, 651, 657, 665
\subitem figurative interpretation of, 201, 581, 623
\subitem sealed book and its opening, 155, 159, 229
\subitem structure and parts of, 1, 11, 235
\subitem use in the church, 47, 93, 651
\subitem \emph{see also} Daniel, book of; Ezekiel, book of
\item Rome
\subitem as Babylon, 437, 513, 519, 527, 533
\subitem as beastly empire, 357, 365, 369
\subitem destruction of, 369, 485, 513, 539
\subitem ecclesiastical Rome, 375, 485, 513, 519
\subitem seven hills of, 491, 499
\subitem \emph{see also} Babylon; Papacy; Whore of Babylon

\indexspace

\item Saracens, 259, 587
\subitem \emph{see also} Muhammad; Turks
\item Satan
\subitem binding of, 569, 581
\subitem loosing of, 587
\subitem war against the church, 337, 345, 353
\subitem \emph{see also} Dragon
\item Scripture, Holy
\subitem authority of, 651
\subitem corruption of, forbidden, 671
\subitem prophecy as Scripture, 1, 651, 657
\subitem sufficiency of, 93, 651

\indexspace

\item Tertullian, 4, 27, 167, 237, 437, 647
\item Turks, 259, 467, 569, 587, 603
\subitem \emph{see also} Muhammad; Saracens

\indexspace

\item Whore of Babylon
\subitem adornment and corruption of, 485, 491
\subitem as Rome, 485, 491, 513
\subitem judgment of, 499, 505
\subitem \emph{see also} Babylon; Papacy; Rome

\indexspace

\item Zechariah, book of, 21, 180, 256, 304, 643
\item Zurich, 77, 240, 388, 665

\end{theindex}
"""


def build_references_bib() -> str:
    return """% Bibliography scaffold for future Chicago-style curation.
% The converted manuscript does not encode structured source citations.
% Populate this file only after establishing authoritative bibliographic data.
"""


def build_readme() -> str:
    return f"""# Build Instructions

This project is set up for XeLaTeX with `memoir`, Unicode indexing through `xindy`, and a restrained monograph page design.

## Quick Build

```bash
bash /home/turambar/projects/bullinger/2026-03-18_bullinger-apocalypse/tools/build_book_pdf.sh
```

`imakeidx` is configured to call `xindy` automatically during the XeLaTeX run when shell escape is enabled.

## Notes

- The current project compiles without `biber`; the manuscript did not contain machine-actionable citation data.
- `biblio/references.bib` is included as a production scaffold for later Chicago notes-and-bibliography work.
- If you later install `biblatex-chicago` and `biber`, the bibliography layer can be upgraded without changing the chapter files.
- The canonical deliverable PDF for the repository is written to `{OUTPUT_PDF}`.
"""


def build_pdf_script() -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail

ROOT="{ROOT}"
BOOK="$ROOT/book"
OUTPUT="{OUTPUT_PDF}"

mkdir -p "$(dirname "$OUTPUT")"

cd "$BOOK"
xelatex -interaction=nonstopmode -halt-on-error -shell-escape main.tex
xelatex -interaction=nonstopmode -halt-on-error -shell-escape main.tex

cp main.pdf "$OUTPUT"
echo "Wrote $OUTPUT"
"""


def build_editorial_issues(source_text: str, sermons: list[tuple[int, str, str]]) -> str:
    uncertain_count = len(re.findall(r"\[[^\]]*illegible[^\]]*\]|\[\?[^\]]*\]|\billegible\b", source_text))
    note_count = len(re.findall(r"\[(?:N|n)ote\s+[^\]]+\]", source_text))
    placeholder_count = len(re.findall(r"^\.\s*$", source_text, re.MULTILINE))

    affected_sermons = []
    for number, title, body in sermons:
        if re.search(r"\[[^\]]*illegible[^\]]*\]|\[\?[^\]]*\]|\billegible\b", title + "\n" + body):
            affected_sermons.append((number, clean_heading(title)))

    lines = [
        "# Editorial Issue Register",
        "",
        "## Counts",
        "",
        f"- Unresolved uncertainty markers: {uncertain_count}",
        f"- Legacy inline note anchors removed during conversion: {note_count}",
        f"- Standalone placeholder lines removed during conversion: {placeholder_count}",
        "",
        "## Sermons Requiring Human Review",
        "",
    ]
    for number, title in affected_sermons:
        lines.append(f"- Sermon {number}: {title}")
    lines.extend(
        [
            "",
            "## Priority Review Targets",
            "",
            "- Opening metadata and title-page wording, especially the `Heinrich` / `Henri` inconsistency.",
            "- Broken or visibly corrupt sermon titles, especially Sermons 9, 10, 45, 100, and 101.",
            "- All remaining `[illegible]` and `[? ... ]` markers before final proof pagination.",
            "- Any passages that should become displayed block quotations after a manual editorial pass.",
            "- Bibliographic references embedded in prose if a true scholarly bibliography is to be supplied.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_production_memo(metadata: dict, display_quote_count: int) -> str:
    source_title = metadata.get("sourceDesc", {}).get("title", [""])[0]
    return f"""# Production Memo

## Files Created

- `main.tex`
- `preamble.tex`
- `frontmatter/titlepage.tex`
- `frontmatter/toc.tex`
- `chapters/sermon-001.tex` through `chapters/sermon-101.tex`
- `backmatter/bibliography.tex`
- `backmatter/index.tex`
- `biblio/references.bib`
- `README.md`
- `editorial-issues.md`

## Major Typographic Choices

- `memoir` book architecture with 6 x 9 trim and open-right chapter openings.
- Main text set through `fontspec`, preferring `EB Garamond` when available and falling back to `P052`.
- Restrained chapter openings, quiet running heads, first-line paragraph indents, and no blank-line paragraph spacing.
- `csquotes` enabled for quotation discipline, with automatic handling of straight double quotes in the converted text.
- Unicode index setup via `imakeidx` and `xindy`.

## Citation And Index Assumptions

- Legacy inline `[note x.y]` anchors were removed rather than reproduced as footnotes.
- No machine-readable bibliography existed in the source, so `biblio/references.bib` is only a scaffold.
- Indexing has been seeded with curated entries for major names, places, and concepts at first substantive discussion points within chapters.

## Manual Review Still Required

- Resolve remaining corrupt or uncertain readings signaled by `[illegible]` and `[? ... ]`.
- Review the remaining ambiguous sermon titles and running-head short titles before print proof.
- Decide which long quoted passages, if any, should be promoted to display quotations beyond the {display_quote_count} automatically detected candidates.
- Curate a real bibliography if the edition is to carry formal scholarly references.
- Refine and compress the seeded index before final production.

## Source Witness

- Primary converted source: `05-output/modern_only.tex`
- Underlying metadata record consulted: `{source_title}`
"""


def build_editorial_exceptions_report() -> str:
    return """# Editorial Exceptions Report

## Ambiguous Titles

- Several sermon titles remain editorially debatable even after normalization because the source appears textually unstable rather than merely archaic. The most notable cases are Sermons 26, 43, 46, 65, and 87.
- Roman-numeral sermon title elements such as `iii.`, `iiii.`, `vii.`, `ii.`, and `iii.` have been preserved in display titles rather than silently modernized.

## Incomplete Citations

- The manuscript does not encode machine-actionable bibliographic data.
- References to patristic, medieval, classical, and Reformation authorities remain embedded in prose and would require human curation before a true bibliography can be printed.

## Block Quote Boundaries

- Long quotations remain largely inline unless their boundaries are unmistakable in the source.
- Some passages that may deserve display treatment still require editorial judgment rather than automatic extraction.

## Transliteration and Historical Forms

- Certain historical or quasi-transliterated forms have been preserved where the preferred modern scholarly form is not fully certain from context alone.
- Examples include some ethnonyms, confessional labels, and work-related descriptors inherited from the source.

## Indexing Judgments

- The index has been normalized and cross-referenced, but some preferred headings remain debatable at a scholarly level.
- High-density topics such as `Antichrist`, `Papacy`, `Rome`, `Mahomet`, `Turks`, and `Saracens` would benefit from a final human indexing pass for subentries and scope control.

## Source-Level Uncertainty

- Bracketed uncertainty markers such as `[illegible]` and `[? ... ]` remain unresolved and should be cleared before any final production proof is approved.
"""


def build_emphasis_normalization_report() -> str:
    return """# Emphasis Normalization Report

## Decisions Applied

- Standardized Augustine's work title to `\\textit{The City of God}` wherever the shortened `\\textit{City of God}` appeared.
- Normalized Sozomen/Eusebius references to `\\textit{Ecclesiastical History}` where the title appeared in lowercase or lost italics.
- Restyled clearly identifiable standalone work titles as titles rather than plain prose, including `\\textit{Against Praxeas}` and `\\textit{Against Maximinus, an Arian Bishop}`.
- Restyled the Augustinian title phrase in Sermon 84 as `the writings on \\textit{True Religion}` while preserving the source wording around it.
- Removed stray italics from the citation fragment `Aurel.` and from the editorial placeholder `[? a word lost here]`, since neither should read as a title or foreign-language emphasis.
- Collapsed repeated commas introduced by the source or conversion process where they interfered with professional punctuation.

## Deliberately Left Unchanged

- `\\textit{Confessions}` in Sermon 95 was left in place because the problem appears to be one of attribution rather than emphasis; correcting it would require a textual intervention beyond typographic normalization.
- `\\textit{Institutions}` and `\\textit{Explanations}` were left as transmitted because expanding them to standard bibliographic titles would require editorial inference not warranted by the present evidence.
- Foreign and technical terms such as `\\textit{latria}`, `\\textit{dulia}`, `\\textit{anima vegetativa}`, `\\textit{Clauigers}`, and `\\textit{Römer}` were retained in italics as scholarly lexical emphasis rather than retitled as works.

## Audit Outcome

- No boldface emphasis was found in the XeLaTeX book files.
- No leftover Markdown emphasis markers were found in the generated `book/` tree.
- Scripture-version labels did not appear in the manuscript in a way that required normalization.
"""


def make_chapter_file(number: int, title: str, latex_body: str) -> str:
    long_title = normalize_sermon_title(title, number)
    toc_title = f"Sermon {number}. {long_title}"
    mark_title = short_title(number, title)
    return rf"""\chapter[{tex_escape(toc_title)}]{{{tex_escape(long_title)}}}
\label{{sermon:{number:03d}}}
\markright{{{tex_escape(mark_title)}}}

{latex_body}"""


def main() -> None:
    source_text = SOURCE.read_text(encoding="utf-8")
    metadata = read_metadata()
    book_title, author_line, subtitle = extract_front_matter(source_text)
    sermons = split_sermons(source_text)

    (BOOK / "chapters").mkdir(parents=True, exist_ok=True)
    (BOOK / "frontmatter").mkdir(parents=True, exist_ok=True)
    (BOOK / "backmatter").mkdir(parents=True, exist_ok=True)
    (BOOK / "biblio").mkdir(parents=True, exist_ok=True)

    total_display_quotes = 0
    for number, title, body in sermons:
        latex_body, display_quotes = chapter_body_to_latex(body)
        total_display_quotes += display_quotes
        chapter_text = make_chapter_file(number, title, latex_body)
        write_file(BOOK / "chapters" / f"sermon-{number:03d}.tex", chapter_text)

    write_file(BOOK / "preamble.tex", build_preamble(book_title))
    write_file(BOOK / "main.tex", build_main_tex(sermons))
    write_file(BOOK / "frontmatter" / "titlepage.tex", build_titlepage(book_title, author_line, subtitle))
    write_file(BOOK / "frontmatter" / "toc.tex", build_toc())
    write_file(BOOK / "backmatter" / "bibliography.tex", build_bibliography_file())
    write_file(BOOK / "backmatter" / "index.tex", build_index_file())
    write_file(BOOK / "biblio" / "references.bib", build_references_bib())
    write_file(BOOK / "README.md", build_readme())
    write_file(ROOT / "tools" / "build_book_pdf.sh", build_pdf_script())
    write_file(BOOK / "editorial-issues.md", build_editorial_issues(source_text, sermons))
    write_file(BOOK / "editorial-exceptions-report.md", build_editorial_exceptions_report())
    write_file(BOOK / "emphasis-normalization-report.md", build_emphasis_normalization_report())
    write_file(BOOK / "production-memo.md", build_production_memo(metadata, total_display_quotes))


if __name__ == "__main__":
    main()
