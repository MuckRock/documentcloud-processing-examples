# DocumentCloud processing examples

This repository captures the inputs and outputs for DocumentCloud's processing pipeline. When you upload a file to DocumentCloud, we both transform the original file and extract data from it.

- text is extracted, or generated via OCR
- OCR text is re-embedded in the original file
- non-PDF files (like Word documents) are converted to PDF
- an image is generated for each page, in five sizes
- position text is generated as a JSON file
- page text is generated as a plain text file and a JSON file
- page text is generated for each individual page

We also index generated text in Solr, so you can search across documents and within a single document.

## Workflow

Creating new examples requires an original document, because our processing pipeline creates a new PDF. This file will be uploaded to DocumentCloud with given settings, and a folder with outputs will be created once processing is finished.

All of this is handled by `process.py`. New files should be added to the `input` directory, with an optional JSON file containing upload settings.

```
.
├── input
│   ├── pressure_cooking.json # optional settings file
│   ├── pressure_cooking.pdf # input file
│   └── README.md
├── output
│   ├── pressure_cooking # output files will land here
│   └── README.md
└── README.md
```

## Upload settings

The optional `input/<basename>.json` holds the settings the file is uploaded with, as a JSON object. It's passed straight through to
`client.documents.upload()` as keyword arguments, so the keys are the DocumentCloud API's document fields. A missing, empty, or `{}` settings file means the document is uploaded with API defaults.

| Setting              | Type          | Default                | What it does                                                                                                             |
| -------------------- | ------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `title`              | string        | filename, no extension | The document's title. The slug used to name output files is derived from it.                                             |
| `access`             | string        | `"private"`            | `"public"`, `"private"`, or `"organization"`. Public documents' assets are served from S3; private ones through the API. |
| `language`           | string        | `"eng"`                | Three-letter language code, used to pick the OCR language (e.g. `"spa"`, `"fra"`).                                       |
| `force_ocr`          | bool          | `false`                | OCR every page even if the file already has an embedded text layer.                                                      |
| `ocr_engine`         | string        | `"tess4"`              | `"tess4"` (Tesseract) or `"textract"`.                                                                                   |
| `original_extension` | string        | from the filename      | The original file's type, for when the filename doesn't carry a usable extension.                                        |
| `description`        | string        | `""`                   | Free text describing the document.                                                                                       |
| `source`             | string        | `""`                   | Where the document came from.                                                                                            |
| `related_article`    | string        | `""`                   | URL of an article the document accompanies.                                                                              |
| `published_url`      | string        | `""`                   | URL of the page the document is embedded on.                                                                             |
| `publish_at`         | string        | `null`                 | ISO 8601 timestamp; the document goes public then.                                                                       |
| `data`               | object        | `{}`                   | Key/value tags, each value a list of strings.                                                                            |
| `projects`           | array of ints | `[]`                   | Project ids to add the document to.                                                                                      |
| `revision_control`   | bool          | `false`                | Keep revisions of the original file.                                                                                     |
| `delayed_index`      | bool          | `false`                | Hold off on indexing the text in Solr.                                                                                   |

Anything else in the file is ignored by the client.

```json
{
  "access": "public",
  "force_ocr": true,
  "language": "eng",
  "source": "Executive Office of the President",
  "data": { "tag": ["staff", "salaries"] }
}
```

Note that `access` defaults to `"private"`. Examples in this repo should set `"access": "public"` so their assets are reachable without credentials.

## Running it

[`process.py`](process.py) does the upload and download. It needs `DC_USERNAME` and `DC_PASSWORD` in the environment — in Actions, from repository secrets.

```
uv run process.py                      # every input without an output folder
uv run process.py input/example.pdf    # just one file
uv run process.py --force input/example.pdf  # re-upload and overwrite
```

In CI, [`.github/workflows/process.yml`](.github/workflows/process.yml) runs it
on any push to `main` that touches `input/`, and commits the generated outputs
back to the repository. It reads the `DC_USERNAME` and `DC_PASSWORD` repository
secrets, and can also be started by hand from the Actions tab, optionally with
`--force`.
