#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/turambar/projects/bullinger/2026-03-18_bullinger-apocalypse"
BOOK="$ROOT/book"
OUTPUT="/home/turambar/projects/bullinger/2026-03-18_bullinger-apocalypse/05-output/bullinger-apocalypse-sermons.pdf"

mkdir -p "$(dirname "$OUTPUT")"

cd "$BOOK"
xelatex -interaction=nonstopmode -halt-on-error -shell-escape main.tex
xelatex -interaction=nonstopmode -halt-on-error -shell-escape main.tex

cp main.pdf "$OUTPUT"
echo "Wrote $OUTPUT"
