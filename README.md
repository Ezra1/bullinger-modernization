# Bullinger Apocalypse (and other Early English texts)

This repo was originally built to modernize Heinrich Bullinger's 1561 *Apocalypse* sermons from Early Modern English to modern English, but it’s designed to modernize **any** Early English text to modern English. It uses a pipeline of TEI-XML extraction (from EEBO-TCP sources), VARD2 spelling normalization (Lancaster UCREL), and local LLM modernization via Ollama (draft → critique → conditional revision), then assembles a parallel edition and glossary.

## Directory structure

| Folder | Contents |
|--------|----------|
| **runs/** | Archived, labeled modernization runs. `runs/latest/` points to the most recent archived run. |
| **work/** | Clean workspace for the *next* text. The repo-root pipeline folders below are symlinks into here so scripts work without code changes. |
| **01-raw/** | **Symlink →** `work/01-raw/`. Source TEI-XML and raw extracted text. |
| **02-cleaned/** | **Symlink →** `work/02-cleaned/`. Output of the cleaning step: plain text ready for VARD. |
| **03-normalized/** | **Symlink →** `work/03-normalized/`. VARD2 output: spelling-normalized text. |
| **04-modernized/** | **Symlink →** `work/04-modernized/`. LLM draft/review output: blocks with `[ORIGINAL]`, `[DRAFT]`, `[CRITIQUE]`, `[FINAL]`. |
| **05-output/** | **Symlink →** `work/05-output/`. Final artifacts: `parallel_edition.md`, `modern_only.md`, `glossary.md`. |
| **default/** | VARD2 config (rules, variants, training data, options). |
| **scripts/** | Extraction, cleaning, normalization, modernization, and build scripts. |
| **tests/** | Tests for the pipeline. |

## Download VARD 2

In order to run VARD 2, you will need to download Java. 
You can find the download for VARD 2 here: https://ucrel.lancs.ac.uk/vard/download/

## Get the modernized Bullinger text (this repo’s current deliverable)

- **Modern-only edition**: `runs/latest/05-output/modern_only.md`
- **Parallel edition (original + modern)**: `runs/latest/05-output/parallel_edition.md`
- **Glossary**: `runs/latest/05-output/glossary.md`

## Pipeline stages

1. **Extract** — From TEI-XML: metadata + body text (sermon headings, paragraphs, `[illegible]`, `[note N]`).
2. **Clean** — Prepare for VARD: line-break hyphen rejoining, abbreviation expansion (ye→the, yt→that, wt→with), gap/illegible normalization, Roman numeral dots, whitespace.
3. **Normalize** — Run VARD2 to produce spelling-normalized text.
4. **Modernize** — Run Ollama (draft → critique → conditional revision) on normalized text; optional checkpointing and resumption.
5. **Build parallel edition** — Assemble `parallel_edition.md`, `modern_only.md`, and `glossary.md` from modernized blocks and metadata.

## Scripts

| Script | Purpose |
|--------|---------|
| **extract_tei.py** | Extract metadata and body from EEBO-TCP TEI-XML. Writes `metadata.json`, `raw_extracted.txt`, and `footnotes.txt`. Uses lxml; handles TEI namespace and sermon structure. |
| **clean_text.py** | Clean text for VARD: TEI extraction (if input is XML) or plain-text cleaning only. Rejoins line-break hyphens, expands ye/yt/wt and `&`, normalizes illegible markers and Roman numeral punctuation, normalizes whitespace. |
| **CleanText.java** | Standalone Java version of the TEI cleaner (no external JARs). Same behavior as `clean_text.py` for XML or plain text. See `scripts/README_Java.md`. |
| **modernize_llm.py** | Modernize via local Ollama: draft passage → critique (original vs draft) → conditional revision. Preserves meaning and theological terms; modernizes proper nouns (e.g. Hierom→Jerome). Supports checkpoint/resume and configurable model. |
| **compare_models.py** | Compare draft outputs from multiple models. Reads draft files in `04-modernized/`, extracts `[ORIGINAL]` and `[FINAL]` per paragraph, aligns by index, writes `04-modernized/model_comparison.txt`. |
| **build_parallel.py** | Assemble final output. Reads modernized file (e.g. `llm_draft.txt` or `reviewed_modern.txt`) and `02-cleaned/metadata.json`; writes `05-output/parallel_edition.md`, `modern_only.md`, and `glossary.md`. Prefers `[FINAL]` over `[DRAFT]` over `[MODERN]` for modern text. |

## Prerequisites

- **Python 3** (3.9+ for scripts)
- **lxml**, **requests** (see `requirements.txt`)
- **Java** (for VARD2; Java 8+ for `CleanText.java`)
- **VARD2** (Lancaster University UCREL) for spelling normalization
- **Ollama** (local LLM server for modernization)
- **Pandoc** (optional, for alternate output formats)

## Setup

```bash
cd ~/projects/bullinger-apocalypse
python3 -m venv bullinger-env
source bullinger-env/bin/activate   # Windows: bullinger-env\Scripts\activate
pip install -r requirements.txt
```

## Running the pipeline

The defaults below write into the repo-root pipeline folders (`01-raw/` … `05-output/`), which are symlinks to `work/` to keep the next run clean.

1. **Extract** from TEI (after placing TEI-XML in `01-raw/`):
   ```bash
   python scripts/extract_tei.py 01-raw/your_file.xml -o 02-cleaned
   ```

2. **Clean** (if not done during extract):
   ```bash
   python scripts/clean_text.py 02-cleaned/raw_extracted.txt -o 02-cleaned/cleaned_text.txt
   ```

3. **Normalize** with VARD2 (run VARD2 on `02-cleaned/cleaned_text.txt`, output to `03-normalized/`).

4. **Modernize** with Ollama:
   ```bash
   python scripts/modernize_llm.py 03-normalized/normalized.txt -o 04-modernized/llm_draft.txt --model your-model
   ```

5. **Build** the parallel edition:
   ```bash
   python scripts/build_parallel.py -i 04-modernized/llm_draft.txt -o 05-output
   ```

Optional: run `compare_models.py` to compare drafts from different models before building.

## License

CC0 (public domain). The source text is from the Text Creation Partnership (TCP) and is in the public domain.

## Acknowledgments

- **Text Creation Partnership (TCP)** for the EEBO-TCP transcriptions.
- **VARD2 / Lancaster University UCREL** for the spelling normalization tool.
- **Ollama** for local LLM inference.
