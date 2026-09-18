#!/usr/bin/env python3
"""Upload files from `input/` to DocumentCloud and save the generated outputs.

For each input file, the document is uploaded with the settings in its sibling
`<basename>.json` (default settings if there isn't one), and once processing
finishes every generated artifact is downloaded into `output/<basename>/`.

Credentials come from the environment:

    DC_USERNAME
    DC_PASSWORD

Usage:

    uv run process.py                      # every input without an output dir
    uv run process.py input/example.pdf    # one file
    uv run process.py --force input/example.pdf
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from documentcloud import DocumentCloud
from documentcloud.documents import IMAGE_SIZES
from documentcloud.exceptions import APIError, DoesNotExistError

ROOT = Path(__file__).parent
INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"

# Processing is asynchronous; poll the document until it leaves a pending state
POLL_INTERVAL = 5
POLL_TIMEOUT = 30 * 60
DONE_STATUSES = {"success", "error", "nofile"}


def get_client():
    """Build an authenticated client from environment credentials"""
    username = os.environ.get("DC_USERNAME")
    password = os.environ.get("DC_PASSWORD")
    if not (username and password):
        sys.exit("Set DC_USERNAME and DC_PASSWORD in the environment")
    return DocumentCloud(username=username, password=password)


def find_inputs():
    """Input files are everything in `input/` but the README and settings files"""
    return sorted(
        path
        for path in INPUT_DIR.iterdir()
        if path.is_file()
        and path.suffix.lower() != ".json"
        and path.name.lower() != "readme.md"
        and not path.name.startswith(".")
    )


def load_settings(path):
    """Read upload settings from `<basename>.json`, if there is one"""
    settings_path = path.with_suffix(".json")
    if not settings_path.exists():
        return {}
    text = settings_path.read_text().strip()
    if not text:
        return {}
    settings = json.loads(text)
    if not isinstance(settings, dict):
        sys.exit(f"{settings_path} must contain a JSON object of upload settings")
    return settings


def wait_for_processing(client, document):
    """Poll until processing finishes, returning the refreshed document"""
    deadline = time.monotonic() + POLL_TIMEOUT
    while True:
        document = client.documents.get(document.id)
        if document.status in DONE_STATUSES:
            break
        if time.monotonic() > deadline:
            raise TimeoutError(
                f"document {document.id} still {document.status} "
                f"after {POLL_TIMEOUT}s"
            )
        print(f"  status: {document.status}")
        time.sleep(POLL_INTERVAL)

    if document.status != "success":
        errors = "\n".join(e.get("message", "") for e in document.get_errors())
        raise RuntimeError(
            f"document {document.id} finished with status "
            f"{document.status}\n{errors}"
        )
    return document


def fetch(client, url):
    """Fetch an asset, returning None if it was never generated"""
    # private assets are served through the API, which needs our credentials;
    # public ones come straight from the asset bucket
    if urlparse(url).netloc == urlparse(client.base_uri).netloc:
        try:
            return client.get(url, full_url=True).content
        except DoesNotExistError:
            return None
    response = client.documents.asset_get(url)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.content


def asset_urls(document):
    """Every asset DocumentCloud generates for a document"""
    yield document.pdf_url
    yield document.full_text_url
    yield document.json_text_url
    for page in range(1, document.page_count + 1):
        yield document.get_page_text_url(page)
        yield document.get_page_position_json_url(page)
        for size in IMAGE_SIZES:
            yield document.get_image_url(page=page, size=size)


def save_outputs(client, document, dest):
    """Download the metadata and all generated assets into `dest`"""
    dest.mkdir(parents=True, exist_ok=True)

    # the raw API representation, named for the DocumentCloud id
    metadata = client.get(f"documents/{document.id}/").json()
    (dest / f"{document.id}.json").write_text(json.dumps(metadata, indent=2) + "\n")

    for url in asset_urls(document):
        # assets are flattened into one directory: the `pages/` segment is dropped
        name = url.rsplit("/", 1)[-1]
        content = fetch(client, url)
        if content is None:
            # position JSON is only generated for some OCR paths
            print(f"  skipped {name} (not generated)")
            continue
        (dest / name).write_bytes(content)
        print(f"  saved {name}")


def process(client, path, force=False):
    """Upload one input file and save everything the pipeline generates"""
    dest = OUTPUT_DIR / path.stem
    if dest.exists() and not force:
        print(f"{path.name}: {dest.relative_to(ROOT)} exists, skipping")
        return

    settings = load_settings(path)
    print(f"{path.name}: uploading with settings {settings}")
    document = client.documents.upload(str(path), **settings)
    print(f"  uploaded as {document.id}, waiting for processing")

    document = wait_for_processing(client, document)
    print(f"  processed: {document.canonical_url}")
    save_outputs(client, document, dest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="input files to process (default: everything in input/)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-upload even if an output directory already exists",
    )
    args = parser.parse_args()

    paths = args.files or find_inputs()
    if not paths:
        sys.exit("No input files found")

    client = get_client()
    for path in paths:
        if not path.exists():
            sys.exit(f"{path} does not exist")
        try:
            process(client, path, force=args.force)
        except (APIError, RuntimeError, TimeoutError) as exc:
            sys.exit(f"{path.name}: {exc}")


if __name__ == "__main__":
    main()
