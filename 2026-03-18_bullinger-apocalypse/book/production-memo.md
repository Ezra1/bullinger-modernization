# Production Memo

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
- Decide which long quoted passages, if any, should be promoted to display quotations beyond the 0 automatically detected candidates.
- Curate a real bibliography if the edition is to carry formal scholarly references.
- Refine and compress the seeded index before final production.

## Source Witness

- Primary converted source: `05-output/modern_only.tex`
- Underlying metadata record consulted: `A hundred sermons vpo[n] the Apocalips of Iesu Christe reueiled in dede by thangell of the Lorde: but seen or receyued and written by thapostle and Eua[n]gelist. S. Iohn: compiled by the famous and godly learned man, Henry Bullinger, chief pastor of the congregation of Zuryk. Newly set forth and allowed, according to the order appoynted in the Quenes maiesties, iniuntions. Thargument, wurthines, commoditie, and vse of this worke, thou shalt fynd in the preface: after which thou hast a most exact table to leade thee into all the princypall matters conteyned therin.`
