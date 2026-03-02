import csv
import os
import pathlib
import time
from random import uniform
from typing import Optional
from urllib.parse import urlparse

import requests


CSV_PATH = "Certifications.csv"      # path to your CSV file
URL_COLUMN = "Url"                   # column name that holds the URLs (from Certifications.csv)
NAME_COLUMN = "Name"                 # column name used for filenames
OUTPUT_DIR = "output"                # folder to save downloaded files
MIN_DELAY_SECONDS = 1.0              # minimum delay between requests
MAX_DELAY_SECONDS = 5.0              # maximum delay between requests
SKIP_LINKEDIN = True                 # LinkedIn URLs require Selenium/login; skip here


def slugify(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in text)[:100]


def provider_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()

    if "coursera.org" in host:
        return "coursera"
    if "linkedin.com" in host or "lnkd.in" in host:
        return "linkedin"
    if "lynda.com" in host:
        return "lynda"
    if "udemy.com" in host:
        return "udemy"

    # fallback: use hostname as folder name
    return slugify(host or "other")


def base_name_for_url(url: str, index: int, display_name: Optional[str]) -> str:
    # Prefer a cleaned-up version of the certificate Name column when available
    if display_name:
        base = slugify(display_name)
    else:
        parsed = urlparse(url)
        base = slugify(parsed.path.strip("/") or f"cert_{index}")
    return base or f"cert_{index}"


def extension_from_content_type(content_type: Optional[str]) -> str:
    # choose extension from content_type, fallback to .html
    ext = ".html"
    if content_type:
        if "pdf" in content_type:
            ext = ".pdf"
        elif "jpeg" in content_type or "jpg" in content_type:
            ext = ".jpg"
        elif "png" in content_type:
            ext = ".png"
    return ext


def find_existing_download(out_dir: pathlib.Path, base_name: str) -> Optional[pathlib.Path]:
    for ext in (".pdf", ".png", ".jpg", ".html"):
        p = out_dir / f"{base_name}{ext}"
        if p.exists():
            return p
    return None


def download_url(session: requests.Session, url: str, index: int, display_name: Optional[str]) -> None:
    provider = provider_from_url(url)
    if SKIP_LINKEDIN and provider == "linkedin":
        print(f"[{index}] Skipping LinkedIn URL (use Selenium): {url}")
        return

    out_dir = pathlib.Path(OUTPUT_DIR) / provider
    os.makedirs(out_dir, exist_ok=True)

    base_name = base_name_for_url(url, index, display_name)
    existing = find_existing_download(out_dir, base_name)
    if existing is not None:
        print(f"[{index}] Skipping (already exists): {existing}")
        return

    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"[{index}] Failed to fetch {url}: {e}")
        return

    content_type = resp.headers.get("Content-Type", "").lower()
    ext = extension_from_content_type(content_type)
    out_path = out_dir / f"{base_name}{ext}"

    if out_path.exists():
        print(f"[{index}] Skipping (already exists): {out_path}")
        return

    with open(out_path, "wb") as f:
        f.write(resp.content)

    print(f"[{index}] Saved {url} -> {out_path}")


def main() -> None:
    if not os.path.exists(CSV_PATH):
        print(f"CSV file not found: {CSV_PATH}")
        return

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [col for col in (URL_COLUMN, NAME_COLUMN) if col not in reader.fieldnames]
        if missing:
            print(f"CSV must have columns {missing}. Columns found: {reader.fieldnames}")
            return

        # Materialize rows so we can both scan and then download
        rows = list(reader)

        # First pass: scan URLs and create provider directories
        providers = set()
        for row in rows:
            url = (row.get(URL_COLUMN) or "").strip()
            if not url:
                continue
            provider = provider_from_url(url)
            if SKIP_LINKEDIN and provider == "linkedin":
                continue
            providers.add(provider)

        base_output = pathlib.Path(OUTPUT_DIR)
        for provider in sorted(providers):
            dir_path = base_output / provider
            os.makedirs(dir_path, exist_ok=True)
            print(f"Ensured directory: {dir_path}")

        # Second pass: actually download
        with requests.Session() as session:
            for idx, row in enumerate(rows, start=1):
                url = (row.get(URL_COLUMN) or "").strip()
                if not url:
                    continue
                name = (row.get(NAME_COLUMN) or "").strip()
                download_url(session, url, idx, name or None)
                delay = uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
                print(f"Sleeping for {delay:.2f} seconds...")
                time.sleep(delay)


if __name__ == "__main__":
    main()

