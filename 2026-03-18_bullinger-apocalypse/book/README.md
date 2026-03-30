# Build Instructions

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
- The canonical deliverable PDF for the repository is written to `/home/turambar/projects/bullinger/2026-03-18_bullinger-apocalypse/05-output/bullinger-apocalypse-sermons.pdf`.
