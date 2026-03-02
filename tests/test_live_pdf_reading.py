import os
import pathlib

import pytest


@pytest.mark.integration
@pytest.mark.live
def test_live_pdfs_are_readable_bytes():
    """
    Open all PDFs saved by the live URL test and verify that:
    - At least one PDF file exists under live_test_output/
    - Each can be opened and read as non-empty bytes.

    Note: many provider responses are not real PDFs; the live test simply
    saves the HTTP body with a .pdf extension for manual inspection, so
    this test only validates that the files are present and non-empty.
    """
    if os.getenv("RUN_LIVE_CERT_TESTS") != "1":
        pytest.skip("Set RUN_LIVE_CERT_TESTS=1 to run live PDF reading tests.")

    root = pathlib.Path("live_test_output")
    if not root.exists():
        pytest.skip("No live_test_output directory found; run live URL tests first.")

    pdf_paths = list(root.rglob("*.pdf"))
    assert pdf_paths, "Expected at least one .pdf file in live_test_output/"

    for path in pdf_paths:
        data = path.read_bytes()
        size = len(data)
        print(f"[LIVE-PDF] path={path} bytes={size} head={data[:16]!r}")
        assert size > 0, f"PDF file appears empty: {path}"

