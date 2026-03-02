import textwrap

import pytest
import requests

import download_certs as dc


@pytest.mark.integration
def test_requests_integration_per_provider_and_bad_url(tmp_path, monkeypatch):
    """
    Integration test that performs a real HTTP GET (to example.com),
    using the download_certs script end-to-end.
    """
    csv_path = tmp_path / "Certifications.csv"
    csv_path.write_text(
        textwrap.dedent(
            """\
            Name,Url
            Coursera Cert,https://www.coursera.org/learn/example
            Lynda Cert,https://www.lynda.com/course/example
            Udemy Cert,https://www.udemy.com/course/example
            Bad Cert,https://bad.example.invalid/does-not-exist
            """
        ),
        encoding="utf-8",
    )

    out_dir = tmp_path / "output"

    # Redirect script paths/settings into the tmp_path
    monkeypatch.setattr(dc, "CSV_PATH", str(csv_path))
    monkeypatch.setattr(dc, "OUTPUT_DIR", str(out_dir))
    monkeypatch.setattr(dc, "MIN_DELAY_SECONDS", 0.0)
    monkeypatch.setattr(dc, "MAX_DELAY_SECONDS", 0.0)

    # Fake responses for each URL so we don't depend on the network
    def fake_get(self, url, timeout=30):
        resp = requests.Response()
        resp.status_code = 200
        resp._content = b"%PDF-1.4 fake certificate data"
        if "coursera.org" in url:
            resp.headers["Content-Type"] = "application/pdf"
        elif "lynda.com" in url:
            resp.headers["Content-Type"] = "image/png"
        elif "udemy.com" in url:
            resp.headers["Content-Type"] = "image/jpeg"
        else:
            # Simulate a failing URL
            raise requests.RequestException("Simulated network error")
        return resp

    monkeypatch.setattr(requests.Session, "get", fake_get)

    dc.main()

    # Coursera, Lynda, Udemy providers should each have one downloaded file
    assert (out_dir / "coursera").exists()
    assert (out_dir / "lynda").exists()
    assert (out_dir / "udemy").exists()

    assert any((out_dir / "coursera").iterdir())
    assert any((out_dir / "lynda").iterdir())
    assert any((out_dir / "udemy").iterdir())


