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


def is_linkedin_url(url: str) -> bool:
    host = (urlparse(url).netloc or "").lower()
    return "linkedin.com" in host or "lnkd.in" in host


def read_linkedin_rows(csv_path: str) -> List[Tuple[str, str]]:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    rows: List[Tuple[str, str]] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [col for col in (URL_COLUMN, NAME_COLUMN) if col not in reader.fieldnames]
        if missing:
            raise ValueError(f"CSV must have columns {missing}. Columns found: {reader.fieldnames}")

        for row in reader:
            url = (row.get(URL_COLUMN) or "").strip()
            name = (row.get(NAME_COLUMN) or "").strip()
            if not url or not is_linkedin_url(url):
                continue
            rows.append((name or "LinkedIn Certificate", url))

    return rows


def build_driver() -> webdriver.Chrome:
    options = Options()
    if HEADLESS:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")

    options.add_argument("--start-maximized")

    # Let Selenium Manager locate ChromeDriver automatically
    driver = webdriver.Chrome(options=options)

    # Enable the Page domain for printToPDF
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
        linkedin_rows = read_linkedin_rows(CSV_PATH)
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        return

    if not linkedin_rows:
        print("No LinkedIn URLs found in CSV.")
        return

    base_output = pathlib.Path(OUTPUT_DIR) / "linkedin"
    base_output.mkdir(parents=True, exist_ok=True)

    print(f"Found {len(linkedin_rows)} LinkedIn URLs.")
    print("A Chrome window will open. Please log into LinkedIn if prompted,")
    print("then return to this terminal and press Enter to start capturing PDFs.")

    driver: Optional[webdriver.Chrome] = None
    try:
        driver = build_driver()

        # Give user a chance to log in once
        input("After logging into LinkedIn in the opened Chrome window, press Enter here to continue...")

        for idx, (name, url) in enumerate(linkedin_rows, start=1):
            print(f"[{idx}/{len(linkedin_rows)}] Opening {url}")
            filename = slugify(name) or f"linkedin_cert_{idx}"
            out_path = base_output / f"{filename}.pdf"

            if out_path.exists():
                print(f"Skipping (already exists): {out_path}")
                continue

            driver.get(url)

            # Basic wait for page to load; adjust if needed
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

