import pathlib

from download_certs import (
    SKIP_LINKEDIN,
    base_name_for_url,
    extension_from_content_type,
    find_existing_download,
    provider_from_url,
    slugify,
)


def test_slugify_basic():
    assert slugify("Google Data Analytics") == "Google_Data_Analytics"
    # Ensure non-alphanumerics become underscores and letters/digits are preserved
    result = slugify("C++ / Python & ML")
    assert "C" in result and "Python" in result and "ML" in result


def test_provider_from_url_known_hosts():
    assert provider_from_url("https://www.coursera.org/learn/test") == "coursera"
    assert provider_from_url("https://www.linkedin.com/learning/xyz") == "linkedin"
    assert provider_from_url("https://lnkd.in/short") == "linkedin"
    assert provider_from_url("https://www.lynda.com/course") == "lynda"
    assert provider_from_url("https://www.udemy.com/course") == "udemy"


def test_base_name_for_url_prefers_display_name():
    url = "https://example.com/path/to/cert"
    base = base_name_for_url(url, 1, "My Fancy Cert")
    assert base == "My_Fancy_Cert"


def test_base_name_for_url_fallback_to_url_path():
    url = "https://example.com/path/to/cert"
    base = base_name_for_url(url, 5, None)
    assert base.startswith("path_to_cert")


def test_extension_from_content_type_mapping():
    assert extension_from_content_type("application/pdf") == ".pdf"
    assert extension_from_content_type("image/jpeg") == ".jpg"
    assert extension_from_content_type("image/png") == ".png"
    # default
    assert extension_from_content_type(None) == ".html"
    assert extension_from_content_type("text/html; charset=utf-8") == ".html"


def test_find_existing_download(tmp_path: pathlib.Path):
    out_dir = tmp_path
    # Create existing PDF
    existing = out_dir / "Cert_Name.pdf"
    existing.write_bytes(b"dummy")

    found = find_existing_download(out_dir, "Cert_Name")
    assert found == existing

    not_found = find_existing_download(out_dir, "Other_Name")
    assert not_found is None


def test_skip_linkedin_flag_enabled():
    # This ensures the script is configured not to hit LinkedIn with requests
    assert SKIP_LINKEDIN is True

