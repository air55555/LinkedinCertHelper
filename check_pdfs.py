import csv
import pathlib
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from pypdf import PdfReader

from download_certs import CSV_PATH, NAME_COLUMN, URL_COLUMN, provider_from_url, slugify


# Owner name to look for on certificates (your name)
# This should match exactly how it appears on LinkedIn certificates.
CERT_OWNER_NAME = "Alexandr Romashko"


@dataclass
class CertRow:
    name: str
    name_norm: str
    slug: str
    provider: str
    url: str


def is_probably_pdf(path: pathlib.Path) -> bool:
    try:
        with path.open("rb") as f:
            header = f.read(5)
        return header == b"%PDF-"
    except OSError:
        return False


def load_cert_rows(csv_path: pathlib.Path) -> List[CertRow]:
    rows: List[CertRow] = []
    if not csv_path.exists():
        print(f"[WARN] CSV not found at {csv_path}, PDF scoring will be limited.")
        return rows

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in (NAME_COLUMN, URL_COLUMN) if c not in reader.fieldnames]
        if missing:
            print(f"[WARN] CSV missing columns {missing}, found {reader.fieldnames}")
            return rows

        for row in reader:
            name = (row.get(NAME_COLUMN) or "").strip()
            url = (row.get(URL_COLUMN) or "").strip()
            if not name or not url:
                continue
            provider = provider_from_url(url)
            rows.append(
                CertRow(
                    name=name,
                    name_norm=normalize_text(name),
                    slug=slugify(name),
                    provider=provider,
                    url=url,
                )
            )

    return rows


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def normalize_word_set(text: str) -> set:
    return {w for w in re.split(r"\W+", text) if w}


def extract_pdf_text_with_pages(
    path: pathlib.Path, max_pages: int = 3
) -> Tuple[str, List[str]]:
    """
    Return:
    - normalized combined text across first max_pages pages
    - list of raw text per page (for position reporting)
    """
    try:
        reader = PdfReader(str(path))
        pages = min(max_pages, len(reader.pages))
        parts: List[str] = []
        page_texts: List[str] = []
        for i in range(pages):
            try:
                raw = reader.pages[i].extract_text() or ""
            except Exception:
                raw = ""
            page_texts.append(raw)
            parts.append(raw)
        full_text = normalize_text(" ".join(parts))
        return full_text, page_texts
    except Exception as e:
        print(f"[ERROR] Failed to read PDF {path}: {e}")
        return "", []


def extract_image_stats(path: pathlib.Path) -> Tuple[int, int, int]:
    """
    Rough image stats for the first page:
    - number of images
    - width/height of the largest image (by area)

    This is a proxy for "certificate background image present".
    """
    try:
        reader = PdfReader(str(path))
        if not reader.pages:
            return 0, 0, 0
        page = reader.pages[0]
        images: List[Tuple[int, int]] = []

        resources = page.get("/Resources", {})
        xobjects = resources.get("/XObject") or {}

        for name, xobj in getattr(xobjects, "items", lambda: [])():
            try:
                if xobj.get("/Subtype") == "/Image":
                    w = int(xobj.get("/Width", 0))
                    h = int(xobj.get("/Height", 0))
                    if w > 0 and h > 0:
                        images.append((w, h))
            except Exception:
                continue

        if not images:
            return 0, 0, 0

        max_w, max_h = max(images, key=lambda wh: wh[0] * wh[1])
        return len(images), max_w, max_h
    except Exception as e:
        print(f"[ERROR] Failed to inspect images in {path}: {e}")
        return 0, 0, 0


def find_phrase_position(
    page_texts: List[str], phrase: str
) -> Optional[Tuple[int, int, int]]:
    """
    Find the first occurrence of phrase (case-insensitive) across pages.
    Returns (page_index, line_index, char_index_in_line), or None.
    """
    phrase_l = phrase.lower()
    for page_idx, raw in enumerate(page_texts):
        lower = (raw or "").lower()
        pos = lower.find(phrase_l)
        if pos == -1:
            continue

        before = raw[:pos]
        line_idx = before.count("\n")
        last_nl = before.rfind("\n")
        if last_nl == -1:
            char_idx = pos
        else:
            char_idx = pos - (last_nl + 1)
        return page_idx, line_idx, char_idx

    return None


def match_cert_for_pdf(path: pathlib.Path, cert_rows: List[CertRow]) -> Optional[CertRow]:
    if not cert_rows:
        return None

    filename_slug = path.stem.lower()

    # 1) Exact slug match
    for row in cert_rows:
        if filename_slug == row.slug.lower():
            return row

    # 2) Slug contained in filename or vice versa
    for row in cert_rows:
        s = row.slug.lower()
        if s and (s in filename_slug or filename_slug in s):
            return row

    return None


def score_pdf_against_cert(text: str, cert: CertRow) -> int:
    if not text:
        return 0

    # 100 if full normalized name is present
    if cert.name_norm and cert.name_norm in text:
        return 100

    # Otherwise, compute word overlap score
    name_words = {w for w in re.split(r"\W+", cert.name_norm) if w}
    if not name_words:
        return 0

    text_words = {w for w in re.split(r"\W+", text) if w}
    if not text_words:
        return 0

    overlap = name_words & text_words
    return int(100 * len(overlap) / len(name_words))


def score_linkedin_pdf(
    text: str,
    cert: CertRow,
    image_count: int,
    max_w: int,
    max_h: int,
    page_texts: List[str],
) -> Tuple[int, Dict[str, int]]:
    """
    LinkedIn-specific scoring with a prescoring gate:
    - Prescoring requires ALL of:
      * Exact header phrase "LinkedIn Learning Certificate of Completion"
      * "Certificate recipient" line that includes CERT_OWNER_NAME
      * The phrase "Completion date"
      If any of these are missing, the PDF is treated as a failed cert and
      scoring stops with 0.

    - If prescoring passes, we then score:
      * Course/cert name match (base score)
      * Presence of the word 'certificate' / 'certification'
      * Presence of the owner's name (CERT_OWNER_NAME)
      * Presence of LinkedIn branding ('linkedin learning' or 'linkedin')
      * Presence of a large background image (proxy for the cert template)
    """
    # Prescoring phrases (raw and normalized)
    header_phrase_raw = "LinkedIn Learning Certificate of Completion"
    owner_phrase_raw = f"Certificate recipient {CERT_OWNER_NAME}"
    completion_phrase_raw = "Completion date"

    header_phrase = normalize_text(header_phrase_raw)
    owner_norm = normalize_text(CERT_OWNER_NAME)
    owner_line_phrase = normalize_text(owner_phrase_raw)
    completion_phrase = normalize_text(completion_phrase_raw)

    has_header = header_phrase in text
    has_owner_line = owner_line_phrase in text
    has_completion = completion_phrase in text

    prescore_pass = has_header and has_owner_line and has_completion
    if not prescore_pass:
        header_pos = find_phrase_position(page_texts, header_phrase_raw)
        owner_pos = find_phrase_position(page_texts, owner_phrase_raw)
        completion_pos = find_phrase_position(page_texts, completion_phrase_raw)
        # Hard fail: do not trust this as a valid LinkedIn certificate image.
        return 0, {
            "prescore_pass": 0,
            "header_phrase": 100 if has_header else 0,
            "owner_line": 100 if has_owner_line else 0,
            "completion_date": 100 if has_completion else 0,
            "header_pos": header_pos,
            "owner_pos": owner_pos,
            "completion_pos": completion_pos,
        }

    # If prescoring passes, continue with text- and image-based scoring.
    base = score_pdf_against_cert(text, cert)

    has_owner = owner_norm in text if owner_norm else False
    has_cert_word = "certificate" in text or "certification" in text
    has_brand = "linkedin learning" in text or "linkedin" in text

    owner_score = 100 if has_owner else 0
    cert_word_score = 100 if has_cert_word else 0
    brand_score = 100 if has_brand else 0

    # Image presence / size as proxy for a proper certificate background.
    # Very rough: treat any reasonably large image as a "certificate image".
    has_large_image = image_count > 0 and (max_w * max_h) >= 500_000
    image_score = 100 if has_large_image else 0

    # Weighted composite:
    # 40% course/cert name, 20% owner name, 15% 'certificate' word,
    # 10% LinkedIn brand, 15% large certificate image present.
    total = int(
        round(
            0.40 * base
            + 0.20 * owner_score
            + 0.15 * cert_word_score
            + 0.10 * brand_score
            + 0.15 * image_score
        )
    )

    header_pos = find_phrase_position(page_texts, header_phrase_raw)
    owner_pos = find_phrase_position(page_texts, owner_phrase_raw)
    completion_pos = find_phrase_position(page_texts, completion_phrase_raw)

    return total, {
        "prescore_pass": 100,
        "header_phrase": 100,
        "owner_line": 100,
        "completion_date": 100,
        "header_pos": header_pos,
        "owner_pos": owner_pos,
        "completion_pos": completion_pos,
        "name_match": base,
        "owner_name": owner_score,
        "certificate_word": cert_word_score,
        "linkedin_brand": brand_score,
        "image_present": image_score,
        "image_count": image_count,
        "image_max_w": max_w,
        "image_max_h": max_h,
    }


def scan_dir(root: pathlib.Path, cert_rows: List[CertRow]) -> None:
    if not root.exists():
        print(f"[SKIP] {root} does not exist.")
        return

    pdfs = list(root.rglob("*.pdf"))
    if not pdfs:
        print(f"[INFO] No PDFs found under {root}")
        return

    print(f"[INFO] Found {len(pdfs)} PDFs under {root}")

    stats_ok = stats_bad = 0
    scores: List[int] = []

    for path in sorted(pdfs):
        pdf_ok = is_probably_pdf(path)
        matched_cert = match_cert_for_pdf(path, cert_rows)

        image_count = max_w = max_h = 0
        if pdf_ok:
            image_count, max_w, max_h = extract_image_stats(path)
            text, page_texts = extract_pdf_text_with_pages(path)
        else:
            text = ""
            page_texts = []

        score = 0
        details: Dict[str, int] = {}
        if matched_cert:
            if matched_cert.provider == "linkedin":
                score, details = score_linkedin_pdf(
                    text, matched_cert, image_count, max_w, max_h, page_texts
                )
            else:
                score = score_pdf_against_cert(text, matched_cert)

        status = "PDF " if pdf_ok else "NON "
        cname = matched_cert.name if matched_cert else "??"
        extra = (
            f" details={details}"
            if matched_cert and matched_cert.provider == "linkedin"
            else ""
        )
        print(f"[SCAN] {status}score={score:3d} file={path} cert={cname}{extra}")

        if pdf_ok:
            stats_ok += 1
        else:
            stats_bad += 1
        scores.append(score)

    avg_score = sum(scores) / len(scores) if scores else 0.0
    print(
        f"[SUMMARY] {root}: {stats_ok} probable PDFs, {stats_bad} non-PDFs, "
        f"avg name-match score={avg_score:.1f}"
    )


def main() -> None:
    csv_path = pathlib.Path(CSV_PATH)
    cert_rows = load_cert_rows(csv_path)

    # Check PDFs produced by Selenium scripts
    scan_dir(pathlib.Path("selenium_output"), cert_rows)

    # Check PDFs produced by live tests
    scan_dir(pathlib.Path("live_test_output"), cert_rows)


if __name__ == "__main__":
    main()


