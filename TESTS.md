## Tests for LinkedinCertHelper

This project uses **pytest** with a mix of unit tests, integration tests, Selenium/browser tests, and opt‑in live URL tests.

### Installing test dependencies

All required test dependencies are already listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

### Test layout

- `tests/test_download_certs.py`
  - Unit tests for:
    - `slugify`
    - `provider_from_url`
    - `base_name_for_url`
    - `extension_from_content_type`
    - `find_existing_download`
    - `SKIP_LINKEDIN` configuration flag
- `tests/test_selenium_helpers.py`
  - Unit tests for:
    - `is_linkedin_url` (both Selenium scripts)
    - `provider_from_url`
    - `read_linkedin_rows`
    - `read_non_linkedin_rows`
- `tests/test_integration_requests.py`
  - Integration test for `download_certs.main()`:
    - Uses a temporary CSV with:
      - One Coursera‑style URL
      - One Lynda‑style URL
      - One Udemy‑style URL
      - One bad URL (simulated failure)
    - Monkeypatches `requests.Session.get` to:
      - Return fake PDF/PNG/JPEG bodies for the good URLs
      - Raise an exception for the bad URL
    - Asserts that the corresponding provider directories under `output/` are created and contain at least one file.
- `tests/test_integration_selenium.py`
  - Integration test for `download_certs_selenium_non_linkedin.main()`:
    - Uses a temporary CSV and output directory.
    - Runs Chrome in **headless** mode.
    - Auto‑answers the interactive `input()` prompt.
    - Marked to require an explicit environment flag (`RUN_SELENIUM_INTEGRATION=1`).
- `tests/test_live_from_csv.py`
  - Live test that hits **real** URLs from the real `Certifications.csv`:
    - Picks at most one **non‑LinkedIn** URL per provider from your CSV.
    - Issues real `requests.get` calls and asserts non‑empty responses.
    - Also calls one obviously bad URL and asserts it fails.
    - Opt‑in via `RUN_LIVE_CERT_TESTS=1`.

Pytest markers are configured in `pytest.ini`:

- `integration` – integration or end‑to‑end tests.
- `selenium` – Selenium/browser tests.
- `live` – tests that hit real URLs from `Certifications.csv`.

### Running tests

#### Run the whole suite (unit + integration, default skips live)

```bash
python -m pytest
```

This runs all tests but **skips**:

- Selenium integration test, unless `RUN_SELENIUM_INTEGRATION=1` is set.
- Live URL test, unless `RUN_LIVE_CERT_TESTS=1` is set.

#### Include Selenium integration tests

On PowerShell:

```powershell
$env:RUN_SELENIUM_INTEGRATION="1"
python -m pytest -m "integration or selenium"
```

This will:

- Run integration tests.
- Run the Selenium non‑LinkedIn integration test in headless Chrome.

#### Include live real‑URL tests

On PowerShell:

```powershell
$env:RUN_LIVE_CERT_TESTS="1"
python -m pytest -m "live"
```

This will:

- Read your real `Certifications.csv`.
- Hit one real, non‑LinkedIn URL per provider and verify a non‑empty response.
- Hit one clearly bad URL and verify it fails.

#### Run absolutely everything (including Selenium + live)

On PowerShell:

```powershell
$env:RUN_SELENIUM_INTEGRATION="1"
$env:RUN_LIVE_CERT_TESTS="1"
python -m pytest
```

This runs:

- All unit tests.
- All integration tests.
- Selenium integration (headless Chrome).
- Live real‑URL test against `Certifications.csv`.

