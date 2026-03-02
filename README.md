## LinkedinCertHelper

Python tools to download and archive your certificates listed in a LinkedIn “Certifications” export CSV.

### Project structure

- `Certifications.csv` – CSV exported from LinkedIn (must contain at least `Name` and `Url` columns).
- `download_certs.py` – Requests-based downloader (non‑LinkedIn only by default).
- `download_certs_selenium_chrome.py` – Selenium/Chrome downloader for **LinkedIn** certificates (PDFs).
- `download_certs_selenium_non_linkedin.py` – Selenium/Chrome downloader for **non‑LinkedIn** certificates (PDFs).
- `selenium_output/` – PDFs produced by the Selenium scripts.
- `output/` – Files produced by the requests script.
- `tests/` – Pytest suite (unit, integration, Selenium, and live‑URL tests).

### Setup

1. Create and activate a virtual environment (optional but recommended).
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Place your exported LinkedIn certifications CSV in the project root as:

```text
Certifications.csv
```

It must have at least the columns:

- `Name`
- `Url`

### Downloading certificates (requests)

This script uses `requests` and is best for providers that do **not** strictly require login (Coursera, Lynda, Udemy, Hackerrank, etc.).

```bash
python download_certs.py
```

Behavior:

- Reads `Certifications.csv`.
- Uses `Name` for the base filename (slugified).
- Groups files by provider in `output/<provider>/`.
- Chooses extension from `Content-Type` (`.pdf`, `.png`, `.jpg`, otherwise `.html`).
- **Skips LinkedIn URLs** by default (`SKIP_LINKEDIN = True`).
- Skips any file that already exists for that certificate.

### Downloading LinkedIn certificates (Selenium + Chrome)

Use this script for **LinkedIn** certificates. It opens Chrome via Selenium and prints each page to PDF.

```bash
python download_certs_selenium_chrome.py
```

What it does:

- Reads `Certifications.csv`, filters **only** LinkedIn (`linkedin.com` / `lnkd.in`) URLs.
- Uses `Name` for filenames under `selenium_output/linkedin/`.
- Opens Chrome (controlled by Selenium).
- Lets you log in once, then visits each URL and saves the page as a PDF using the Chrome DevTools `printToPDF` API.
- Skips PDFs that already exist.

### Downloading non‑LinkedIn certificates with Selenium

If you prefer Selenium/PDFs for everything else:

```bash
python download_certs_selenium_non_linkedin.py
```

Behavior:

- Reads `Certifications.csv`, filters out LinkedIn URLs.
- Groups by provider under `selenium_output/<provider>/`.
- Uses `Name` for filenames.
- Opens Chrome, lets you log in where needed (Coursera, etc.), then prints each page to PDF.
- Skips PDFs that already exist.

### Configuration knobs

All scripts expose simple constants at the top that you can tweak:

- `CSV_PATH` – path to the input CSV (default `Certifications.csv`).
- `OUTPUT_DIR` / `selenium_output` – base output directories.
- `MIN_DELAY_SECONDS` / `MAX_DELAY_SECONDS` – random delay range between requests/page loads.
- `SKIP_LINKEDIN` (in `download_certs.py`) – whether to skip LinkedIn in the requests-based script.
- `HEADLESS` (Selenium scripts) – set to `True` to run Chrome headless.

### Running tests (including full suite)

Basic test run:

```bash
python -m pytest
```

Full suite including Selenium integration and live real-URL checks (PowerShell):

```powershell
$env:RUN_SELENIUM_INTEGRATION="1"
$env:RUN_LIVE_CERT_TESTS="1"
python -m pytest
```


