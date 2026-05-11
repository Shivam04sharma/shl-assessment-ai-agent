import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.catalog.scraper import scrape_catalog as scrape_with_fallback


def main():
    print("=" * 50)
    print("SHL Catalog Scraper")
    print("=" * 50)

    catalog = scrape_with_fallback()

    if not catalog:
        print("ERROR: No assessments scraped. Check website structure.")
        sys.exit(1)

    Path("data").mkdir(exist_ok=True)
    out_path = "data/catalog.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(catalog)} assessments to {out_path}")
    print("\nSample entries:")
    for item in catalog[:3]:
        print(f"  - {item['name']} | Type: {item['test_type']} | {item['url']}")


if __name__ == "__main__":
    main()
