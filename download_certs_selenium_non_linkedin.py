import base64
import csv
import os
import pathlib
import time
from random import uniform
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


CSV_PATH = "Certifications.csv"       # input CSV
URL_COLUMN = "Url"                    # URL column name
NAME_COLUMN = "Name"                  # display name column
OUTPUT_DIR = "selenium_output"        # where PDFs will be saved
MIN_DELAY_SECONDS = 1.0               # min delay between pages
MAX_DELAY_SECONDS = 5.0               # max delay between pages
HEADLESS = False                      # set True to run without visible window


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

    return slugify(host or "other")


def is_linkedin_url(url: str) -> bool:
    host = (urlparse(url).netloc or "").lower()
    return "linkedin.com" in host or "lnkd.in" in host


def read_non_linkedin_rows(csv_path: str) -> List[Tuple[str, str, str]]:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    rows: List[Tuple[str, str, str]] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [col for col in (URL_COLUMN, NAME_COLUMN) if col not in reader.fieldnames]
        if missing:
            raise ValueError(f"CSV must have columns {missing}. Columns found: {reader.fieldnames}")

        for row in reader:
            url = (row.get(URL_COLUMN) or "").strip()
            name = (row.get(NAME_COLUMN) or "").strip()
            if not url or is_linkedin_url(url):
                continue
            provider = provider_from_url(url)
            rows.append((name or "Certificate", url, provider))

    return rows


def build_driver() -> webdriver.Chrome:
    options = Options()
    if HEADLESS:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")

    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd("Page.enable", {})
    return driver


def save_current_page_as_pdf(driver: webdriver.Chrome, out_path: pathlib.Path) -> None:
    pdf_obj = driver.execute_cdp_cmd(
        "Page.printToPDF",
        {
            "printBackground": True,
            "landscape": False,
        },
    )
    pdf_data = base64.b64decode(pdf_obj["data"])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(pdf_data)


def main() -> None:
    try:
        rows = read_non_linkedin_rows(CSV_PATH)
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        return

    if not rows:
        print("No non-LinkedIn URLs found in CSV.")
        return

    print(f"Found {len(rows)} non-LinkedIn URLs.")
    print("A Chrome window will open. Log into any providers (Coursera, etc.) if needed,")
    print("then return to this terminal and press Enter to start capturing PDFs.")

    driver: Optional[webdriver.Chrome] = None
    try:
        driver = build_driver()

        input("After logging in where needed in the opened Chrome window, press Enter here to continue...")

        total = len(rows)
        for idx, (name, url, provider) in enumerate(rows, start=1):
            print(f"[{idx}/{total}] Opening {url}")

            base_output = pathlib.Path(OUTPUT_DIR) / provider
            filename = slugify(name) or f"{provider}_cert_{idx}"
            out_path = base_output / f"{filename}.pdf"

            if out_path.exists():
                print(f"Skipping (already exists): {out_path}")
                continue

            driver.get(url)
            time.sleep(8)

            try:
                save_current_page_as_pdf(driver, out_path)
                print(f"Saved PDF -> {out_path}")
            except Exception as e:
                print(f"Failed to save PDF for {url}: {e}")

            delay = uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
            print(f"Sleeping for {delay:.2f} seconds...")
            time.sleep(delay)

    finally:
        if driver is not None:
            driver.quit()


if __name__ == "__main__":
    main()

