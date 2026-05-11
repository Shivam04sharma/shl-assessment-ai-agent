"""
Run on Windows (outside Docker):
  python scripts/scrape_local.py
"""
import json
import time
from pathlib import Path
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

BASE_URL = "https://www.shl.com"
CATALOG_URL = "https://www.shl.com/products/product-catalog/"


def parse_test_types(cells) -> list:
    if len(cells) < 4:
        return []
    spans = cells[3].find_all("span")
    valid = set("ABCDEKPS")
    return [s.get_text(strip=True) for s in spans if s.get_text(strip=True) in valid]


def has_checkmark(cell) -> bool:
    return "-yes" in str(cell) or "catalogue__circle" in str(cell)


def extract_rows(soup, table_header_keyword) -> list:
    items = []
    for table in soup.find_all("table"):
        th = table.find("th")
        if not th or table_header_keyword.lower() not in th.get_text().lower():
            continue
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if not cells:
                continue
            link = row.find("a", href=True)
            if not link:
                continue
            name = link.get_text(strip=True)
            url = urljoin(BASE_URL, link["href"]).replace(
                "/products/product-catalog/",
                "/solutions/products/product-catalog/"
            )
            if not name or not url.startswith("https://www.shl.com"):
                continue
            test_types = parse_test_types(cells)
            items.append({
                "name": name,
                "url": url,
                "test_type": test_types[0] if test_types else "K",
                "test_types": test_types,
                "remote_testing": has_checkmark(cells[1]) if len(cells) > 1 else False,
                "adaptive": has_checkmark(cells[2]) if len(cells) > 2 else False,
            })
    return items


def scrape():
    all_items = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Load page once, then use JS to paginate
        print("Loading catalog page...")
        page.goto(f"{CATALOG_URL}?type=1", timeout=120000, wait_until="load")
        time.sleep(10)

        start = 0
        while True:
            print(f"  Scraping start={start}...")

            # Navigate to paginated URL
            page.goto(f"{CATALOG_URL}?start={start}&type=1", timeout=120000, wait_until="load")
            time.sleep(10)

            soup = BeautifulSoup(page.content(), "html.parser")
            items = extract_rows(soup, "individual")

            if not items:
                # Try without filter — maybe page structure changed
                items = extract_rows(soup, "")
                if not items:
                    print(f"  No items at start={start}, stopping.")
                    break

            all_items.extend(items)
            print(f"  Got {len(items)} items (total: {len(all_items)})")

            if len(items) < 12:
                print("  Last page reached.")
                break

            start += 12

        # Fetch detail pages for descriptions
        print(f"\nFetching detail pages for {len(all_items)} assessments...")
        for i, item in enumerate(all_items):
            print(f"  [{i+1}/{len(all_items)}] {item['name']}")
            try:
                page.goto(item["url"], timeout=30000, wait_until="load")
                time.sleep(3)
                soup = BeautifulSoup(page.content(), "html.parser")
                for sel in [
                    ".product-detail__description",
                    ".product__description",
                    "[class*='description']",
                    ".product-hero__copy",
                    ".content p",
                    "section p",
                ]:
                    el = soup.select_one(sel)
                    if el:
                        text = el.get_text(separator=" ", strip=True)[:600]
                        if len(text) > 30:
                            item["description"] = text
                            break
            except Exception as e:
                print(f"    Failed: {e}")

        browser.close()

    # Deduplicate
    seen, unique = set(), []
    for item in all_items:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)

    print(f"\nTotal unique: {len(unique)} assessments")
    Path("data").mkdir(exist_ok=True)
    with open("data/catalog.json", "w", encoding="utf-8") as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)
    print("Saved to data/catalog.json")
    if unique:
        print(f"Sample: {unique[0]['name']} | {unique[0]['url']}")


if __name__ == "__main__":
    scrape()
