import time
import json
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

BASE_URL = "https://www.shl.com"
CATALOG_URL = "https://www.shl.com/solutions/products/product-catalog/"

TEST_TYPE_COLS = ["A", "B", "C", "D", "E", "K", "M", "P", "S"]

JOB_SOLUTION_KEYWORDS = ["solution", "short form", "job focused", "focus assessment"]


def _is_job_solution(name: str) -> bool:
    n = name.lower()
    return any(kw in n for kw in JOB_SOLUTION_KEYWORDS)


def _has_checkmark(cell) -> bool:
    from bs4 import BeautifulSoup
    inner = str(cell)
    text = cell.get_text(strip=True)
    return any([
        "catalogue__circle" in inner,
        "fa-check" in inner,
        "icon-tick" in inner,
        "checkmark" in inner.lower(),
        "✔" in text,
        "✓" in text,
        bool(cell.find("span", class_=True)),
    ])


def _parse_test_types(cells: List) -> List[str]:
    types = []
    for i, col_type in enumerate(TEST_TYPE_COLS):
        cell_idx = i + 3
        if cell_idx < len(cells) and _has_checkmark(cells[cell_idx]):
            types.append(col_type)
    return types


def _scrape_with_playwright() -> List[Dict]:
    from playwright.sync_api import sync_playwright
    from bs4 import BeautifulSoup

    all_items = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        start = 0
        page_size = 12

        print(f"Scraping SHL catalog from: {CATALOG_URL}")

        while True:
            url = f"{CATALOG_URL}?start={start}&type=1"
            print(f"  Fetching listing page start={start}...")

            try:
                page.goto(url, timeout=60000, wait_until="networkidle")
                page.wait_for_selector("table", timeout=15000)
            except Exception as e:
                print(f"  Page load failed at start={start}: {e}")
                break

            soup = BeautifulSoup(page.content(), "html.parser")
            table = (
                soup.find("table", class_=lambda c: c and "catalogue" in c.lower())
                or soup.find("table")
            )

            if not table:
                print(f"  No table found at start={start}, stopping.")
                break

            tbody = table.find("tbody") or table
            rows = tbody.find_all("tr")
            items = []

            for row in rows:
                cells = row.find_all("td")
                if not cells:
                    continue
                link = row.find("a", href=True)
                if not link:
                    continue

                name = link.get_text(strip=True)
                href = link["href"]
                url_item = urljoin(BASE_URL, href)

                if not name or not url_item.startswith("https://www.shl.com"):
                    continue
                if _is_job_solution(name):
                    continue

                # Fix URL to use correct path
                url_item = url_item.replace(
                    "/products/product-catalog/",
                    "/solutions/products/product-catalog/"
                )

                remote_testing = _has_checkmark(cells[1]) if len(cells) > 1 else False
                adaptive = _has_checkmark(cells[2]) if len(cells) > 2 else False
                test_types = _parse_test_types(cells)
                primary_type = test_types[0] if test_types else "K"

                items.append({
                    "name": name,
                    "url": url_item,
                    "test_type": primary_type,
                    "test_types": test_types,
                    "remote_testing": remote_testing,
                    "adaptive": adaptive,
                })

            if not items:
                print(f"  No items at start={start}, stopping pagination.")
                break

            all_items.extend(items)
            print(f"  Got {len(items)} items (total so far: {len(all_items)})")

            if len(items) < page_size:
                break

            start += page_size
            time.sleep(0.5)

        browser.close()

    return all_items


def _scrape_detail_pages(items: List[Dict]) -> List[Dict]:
    from playwright.sync_api import sync_playwright
    from bs4 import BeautifulSoup

    print(f"\nFetching detail pages for {len(items)} assessments...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for i, item in enumerate(items):
            print(f"  [{i+1}/{len(items)}] {item['name']}")
            try:
                page.goto(item["url"], timeout=30000, wait_until="domcontentloaded")
                soup = BeautifulSoup(page.content(), "html.parser")

                for sel in [
                    ".product-detail__description",
                    ".product__description",
                    "[class*='description']",
                    ".product-hero__copy",
                    "section p",
                    ".content p",
                ]:
                    el = soup.select_one(sel)
                    if el:
                        item["description"] = el.get_text(separator=" ", strip=True)[:600]
                        break

            except Exception as e:
                print(f"    Detail page failed: {e}")

            time.sleep(0.3)

        browser.close()

    return items


def scrape_catalog() -> List[Dict]:
    # Install playwright browsers if needed
    import subprocess, sys
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium", "--with-deps"],
        capture_output=True
    )

    items = _scrape_with_playwright()

    if not items:
        return []

    # Deduplicate
    seen = set()
    unique = []
    for item in items:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)

    print(f"\nTotal unique assessments: {len(unique)}")

    unique = _scrape_detail_pages(unique)

    print(f"\nScraping complete: {len(unique)} assessments")
    return unique
