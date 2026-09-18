# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A corpus of example inputs and outputs for DocumentCloud's processing pipeline — not a library. Each example is an original document in `input/` plus the full set of artifacts DocumentCloud generates for it in `output/<document-basename>/`.

Uploading a file to DocumentCloud produces: extracted or OCR'd text, a re-OCR'd PDF, PDF conversion for non-PDF originals, page images in five sizes, positional text JSON, whole-document text (`.txt` and `.json`), and per-page text. Generated text is also indexed in Solr.

## State of the repo

No Python source and no GitHub Actions workflow yet — the repo holds one committed example and the scaffolding around it. The README describes an intended workflow that still needs to be built:

1. A file is added to `input/`, optionally with a sibling `<basename>.json` of upload settings (see `input/pressure_cooking.json`, currently `{}`).
2. GitHub Actions uploads it to DocumentCloud with those settings.
3. Once processing finishes, the generated artifacts are downloaded into `output/<basename>/`.

`output/pressure_cooking/` is the one worked example, and it is complete: a 1-page PDF with metadata, full text, JSON text, page text, positional text, and all five page images.

## Naming and asset layout

The output directory is named for the **input file's basename** (`pressure_cooking`, underscores), but the files inside it are named for the **DocumentCloud slug** derived from the title (`pressure-cooking`, hyphens). Don't assume they match.

```
output/pressure_cooking/
├── 28657965.json                    # document metadata, named for the DocumentCloud id
├── pressure-cooking.pdf
├── pressure-cooking.txt             # full text
├── pressure-cooking.txt.json        # per-page text
├── pressure-cooking-p1.txt          # page text, 1-indexed
├── pressure-cooking-p1.position.json  # per-word positions
├── pressure-cooking-p1-thumbnail.gif
├── pressure-cooking-p1-small.gif
├── pressure-cooking-p1-normal.gif
├── pressure-cooking-p1-large.gif
└── pressure-cooking-p1-xlarge.gif
```

Assets are flattened into the one directory: the `pages/` path segment from the API is dropped.

Assets live under the `asset_url` from the metadata, at these paths ([API docs](https://help.muckrock.com/API-19ef889269638147bbb7d8cc8af8e0fc), "Static Assets"):

| Asset          | Path under `asset_url`                           |
| -------------- | ------------------------------------------------ |
| Document       | `documents/{id}/{slug}.pdf`                      |
| Full text      | `documents/{id}/{slug}.txt`                      |
| JSON text      | `documents/{id}/{slug}.txt.json`                 |
| Page text      | `documents/{id}/pages/{slug}-p{n}.txt`           |
| Page positions | `documents/{id}/pages/{slug}-p{n}.position.json` |
| Page image     | `documents/{id}/pages/{slug}-p{n}-{size}.gif`    |

Page images are GIF, at five widths: `thumbnail` 60px, `small` 180px, `normal` 700px, `large` 1000px, `xlarge` 2000px (heights scale with the page). Page numbers are 1-indexed in asset filenames but **0-indexed inside the JSON**. Position JSON is optional — the docs say it is only generated for some OCR paths — and is a flat array with one object per word. Beyond the documented `text` and `x1/x2/y1/y2` (0–1 fractions of page size, with y measured from the top), the real files also carry `upright` (bool) and `direction` (e.g. `"ltr"`), which the API docs do not mention.

`.txt.json` is `{"updated": <unix ts>, "pages": [...]}`, optionally with `is_import: true` for documents migrated from legacy DocumentCloud. Each page object has `page` (0-indexed), `contents`, `ocr` (OCR engine version), and `updated`. The example here has only `page` and `contents`.

The metadata JSON is the API's document representation — `id`, `slug`, `status` ("success" when processing finished), `page_count`, `page_spec` (ListCrunch-encoded page dimensions), `canonical_url`, `asset_url` — and is what a download step should use to construct the paths above.

## Environment

Python >= 3.13, managed with uv (`uv.lock` is committed). The only direct dependency is `python-documentcloud`.

```
uv sync          # install deps into .venv
uv run <script>  # run against the project env
```

The DocumentCloud client (`documentcloud.DocumentCloud`) needs credentials; in Actions these must come from repository secrets. `client.documents.upload(path, **settings)` takes the settings JSON as kwargs; `upload_directory()` exists but drops `title`, so per-file upload is the better fit for keeping the basename convention.

## Binary files

`.gitattributes` tracks `*.pdf` and `*.gif` with Git LFS, which covers everything the pipeline generates. Page images dominate an example: the five GIFs for this single page total ~890KB, against 44KB for the PDF and 113KB for all the text and JSON. A multi-page document will add tens of MB of LFS objects per example. Position JSON is the bulky non-LFS file — 105KB for 553 words on one page — so it lands in Git proper.
