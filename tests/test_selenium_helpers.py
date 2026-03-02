import textwrap

from download_certs_selenium_chrome import is_linkedin_url as is_linkedin_url_chrome, slugify as slugify_chrome, read_linkedin_rows
from download_certs_selenium_non_linkedin import (
    is_linkedin_url as is_linkedin_url_non_linkedin,
    provider_from_url,
    read_non_linkedin_rows,
    slugify as slugify_non_linkedin,
)


def test_is_linkedin_url_detections():
    url_li = "https://www.linkedin.com/learning/some-course"
    url_short = "https://lnkd.in/abcd"
    url_other = "https://www.coursera.org/learn/test"

    assert is_linkedin_url_chrome(url_li)
    assert is_linkedin_url_chrome(url_short)
    assert not is_linkedin_url_chrome(url_other)

    assert is_linkedin_url_non_linkedin(url_li)
    assert is_linkedin_url_non_linkedin(url_short)
    assert not is_linkedin_url_non_linkedin(url_other)


def test_slugify_consistent_across_modules():
    text = "Data Science 101!"
    assert slugify_chrome(text) == slugify_non_linkedin(text)


def test_read_linkedin_rows_filters_only_linkedin(tmp_path):
    csv_path = tmp_path / "certs.csv"
    csv_path.write_text(
        textwrap.dedent(
            """\
            Name,Url
            LinkedIn Course,https://www.linkedin.com/learning/course-1
            Short Link,https://lnkd.in/abcd
            Coursera Course,https://www.coursera.org/learn/x
            """
        ),
        encoding="utf-8",
    )

    rows = read_linkedin_rows(str(csv_path))
    # Only the two LinkedIn rows should be present
    assert len(rows) == 2
    names = {name for name, _ in rows}
    assert "LinkedIn Course" in names
    assert "Short Link" in names


def test_read_non_linkedin_rows_filters_out_linkedin(tmp_path):
    csv_path = tmp_path / "certs.csv"
    csv_path.write_text(
        textwrap.dedent(
            """\
            Name,Url
            LinkedIn Course,https://www.linkedin.com/learning/course-1
            Coursera Course,https://www.coursera.org/learn/x
            Udemy Course,https://www.udemy.com/course/y
            """
        ),
        encoding="utf-8",
    )

    rows = read_non_linkedin_rows(str(csv_path))
    # Only Coursera and Udemy should be present
    providers = {provider for _, _, provider in rows}
    assert "coursera" in providers
    assert "udemy" in providers
    # Ensure no rows for LinkedIn
    for _, url, _ in rows:
        assert "linkedin.com" not in url

