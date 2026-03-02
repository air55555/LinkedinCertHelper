import os
import textwrap

import pytest

import download_certs_selenium_non_linkedin as scn


@pytest.mark.integration
@pytest.mark.selenium
def test_selenium_non_linkedin_integration(tmp_path, monkeypatch):
    """
    Integration test for the Selenium non-LinkedIn downloader.

    This test is skipped unless RUN_SELENIUM_INTEGRATION=1 is set in the environment,
    because it requires a local Chrome installation and will open a real browser.
    """
    if os.getenv("RUN_SELENIUM_INTEGRATION") != "1":
        pytest.skip("Set RUN_SELENIUM_INTEGRATION=1 to run Selenium integration tests.")

    csv_path = tmp_path / "Certifications.csv"
    csv_path.write_text(
        textwrap.dedent(
            """\
            Name,Url
            Example Cert,https://example.com/
            """
        ),
        encoding="utf-8",
    )

    out_dir = tmp_path / "selenium_output"

    # Redirect script config into tmp directory and speed up delays
    monkeypatch.setattr(scn, "CSV_PATH", str(csv_path))
    monkeypatch.setattr(scn, "OUTPUT_DIR", str(out_dir))
    monkeypatch.setattr(scn, "MIN_DELAY_SECONDS", 0.0)
    monkeypatch.setattr(scn, "MAX_DELAY_SECONDS", 0.1)
    monkeypatch.setattr(scn, "HEADLESS", True)

    # Avoid interactive input in tests
    monkeypatch.setattr("builtins.input", lambda *_args, **_kwargs: "")

    scn.main()

    files = list(out_dir.rglob("*.pdf"))
    assert files, "Expected at least one PDF file to be created by Selenium downloader"

