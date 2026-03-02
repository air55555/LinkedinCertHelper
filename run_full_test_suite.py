import os
import sys

import pytest


def main() -> int:
    # Enable Selenium integration and live real-URL tests.
    os.environ["RUN_SELENIUM_INTEGRATION"] = "1"
    os.environ["RUN_LIVE_CERT_TESTS"] = "1"

    # Run pytest against the current project with stdout shown (-s)
    # so live URL test details are visible in the console.
    return pytest.main(["-s"])


if __name__ == "__main__":
    raise SystemExit(main())

