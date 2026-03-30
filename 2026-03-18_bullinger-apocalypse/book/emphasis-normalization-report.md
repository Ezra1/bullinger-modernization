# Emphasis Normalization Report

## Decisions Applied

- Standardized Augustine's work title to `\textit{The City of God}` wherever the shortened `\textit{City of God}` appeared.
- Normalized Sozomen/Eusebius references to `\textit{Ecclesiastical History}` where the title appeared in lowercase or lost italics.
- Restyled clearly identifiable standalone work titles as titles rather than plain prose, including `\textit{Against Praxeas}` and `\textit{Against Maximinus, an Arian Bishop}`.
- Restyled the Augustinian title phrase in Sermon 84 as `the writings on \textit{True Religion}` while preserving the source wording around it.
- Removed stray italics from the citation fragment `Aurel.` and from the editorial placeholder `[? a word lost here]`, since neither should read as a title or foreign-language emphasis.
- Collapsed repeated commas introduced by the source or conversion process where they interfered with professional punctuation.

## Deliberately Left Unchanged

- `\textit{Confessions}` in Sermon 95 was left in place because the problem appears to be one of attribution rather than emphasis; correcting it would require a textual intervention beyond typographic normalization.
- `\textit{Institutions}` and `\textit{Explanations}` were left as transmitted because expanding them to standard bibliographic titles would require editorial inference not warranted by the present evidence.
- Foreign and technical terms such as `\textit{latria}`, `\textit{dulia}`, `\textit{anima vegetativa}`, `\textit{Clauigers}`, and `\textit{Römer}` were retained in italics as scholarly lexical emphasis rather than retitled as works.

## Audit Outcome

- No boldface emphasis was found in the XeLaTeX book files.
- No leftover Markdown emphasis markers were found in the generated `book/` tree.
- Scripture-version labels did not appear in the manuscript in a way that required normalization.
