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

All of this runs within Github Actions. New files should be added to the `input` directory, with an optional JSON file containing upload settings.

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
