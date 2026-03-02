import os
import csv
import pathlib

import pytest
import requests

from download_certs import provider_from_url, slugify


@pytest.mark.integration
@pytest.mark.live
def test_live_real_certs_from_csv():
    """
    Hit a small sample of real certificate URLs from the real Certifications.csv.

    This test is opt-in and will be skipped unless RUN_LIVE_CERT_TESTS=1 is set.
    It:
    - Picks at most one URL per provider from the real CSV (including LinkedIn).
    - Makes a real HTTP request to each and asserts we get a non-empty body.
    - Saves each body as a PDF file under live_test_output/<provider>/.
    - Also hits one obviously bad URL and asserts it fails.
    """
    if os.getenv("RUN_LIVE_CERT_TESTS") != "1":
        pytest.skip("Set RUN_LIVE_CERT_TESTS=1 to run live certificate URL tests.")

    csv_path = pathlib.Path("Certifications.csv")
    if not csv_path.exists():
        pytest.skip(f"Real CSV not found at {csv_path}")

    providers_sample = {}

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "Url" not in reader.fieldnames:
            pytest.skip(f"'Url' column not found in {csv_path}, columns: {reader.fieldnames}")

        for row in reader:
            url = (row.get("Url") or "").strip()
            if not url:
                continue
            provider = provider_from_url(url)
            if provider not in providers_sample:
                providers_sample[provider] = url

    assert providers_sample, "Did not find any non-LinkedIn URLs in Certifications.csv"

    # Base folder where live test cert bodies will be stored
    live_out_root = pathlib.Path("live_test_output")
    live_out_root.mkdir(parents=True, exist_ok=True)

    # Real calls for one URL per provider
    for idx, (provider, url) in enumerate(providers_sample.items(), start=1):
        print(f"[LIVE] Testing provider={provider} url={url}")
        resp = requests.get(url, timeout=20)
        size = len(resp.content or b"")
        content_type = resp.headers.get("Content-Type")
        print(
            f"[LIVE] provider={provider} status={resp.status_code} "
            f"bytes={size} content_type={content_type}"
        )

        # Basic assertions: no 5xx, non-empty body
        assert resp.status_code < 500, f"{provider} URL returned error status: {resp.status_code}"
        assert size > 0, f"{provider} URL returned empty body"

        # Save the body into a provider-specific folder for manual inspection
        provider_dir = live_out_root / provider
        provider_dir.mkdir(parents=True, exist_ok=True)

        # Save all live bodies with .pdf extension for easier inspection,
        # regardless of actual content-type.
        filename = slugify(f"{provider}_{idx}") + ".pdf"
        out_path = provider_dir / filename
        with out_path.open("wb") as fh:
            fh.write(resp.content)
        print(f"[LIVE] Saved body to {out_path}")

    # One intentionally bad URL that should fail
    bad_url = "https://this-domain-should-not-exist-1234567890.example"
    print(f"[LIVE] Testing bad URL={bad_url}")
    with pytest.raises(Exception):
        requests.get(bad_url, timeout=10)

