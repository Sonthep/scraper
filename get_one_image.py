"""
get_one_image.py
----------------
Scrape product pages from aolga-hk.com
Output CSV: sku, image_url  (1 row per product, first image only)

Usage:
    python get_one_image.py
    python get_one_image.py --output my_images.csv
"""

import argparse
import csv
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path

BASE_URL = "https://www.aolga-hk.com"

CATEGORIES = [
    ("hair-dryer", "Hair Dryer"),
    ("electric-kettle", "Electric Kettle"),
    ("kettle-tray", "Kettle Tray"),
    ("coffee-machine", "Coffee Machine"),
    ("hotel-minibar", "Hotel Minibar"),
    ("electronic-password-safes", "Room Safes"),
    ("electric-iron", "Electric Iron"),
    ("iron-board-and-holder", "Iron Board and Holder"),
    ("weight-scale", "Weight Scale"),
    ("bluetooth-alarm-clock", "Bluetooth Alarm Clock"),
    ("cosmetic-mirror", "Cosmetic Mirror"),
    ("luggage-rack", "Luggage Rack"),
    ("clothes-hanger", "Clothes Hanger"),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def get_soup(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        print(f"  [ERROR] {url} -> {e}")
        return None


def get_product_links(slug: str) -> list[str]:
    """Return all product page URLs from a category (all pages)."""
    links = []
    page = 1
    while True:
        url = f"{BASE_URL}/{slug}/" if page == 1 else f"{BASE_URL}/{slug}/page/{page}/"
        soup = get_soup(url)
        if not soup:
            break

        items = soup.select("li.product_list_item h3.item_title a")
        if not items:
            break

        for a in items:
            href = a.get("href", "")
            if href and href not in links:
                links.append(href)

        # check next page via pagination
        pages_div = soup.find("div", class_="pages")
        total = 1
        if pages_div:
            parts = pages_div.get_text(strip=True).split("/")
            if len(parts) == 2:
                try:
                    total = int(parts[1].strip())
                except ValueError:
                    pass
        if page >= total:
            break
        page += 1
        time.sleep(0.3)

    return links


def get_model_and_first_image(product_url: str) -> tuple[str, str]:
    """Return (model, first_image_url) from a product page."""
    soup = get_soup(product_url)
    if not soup:
        return "", ""

    # --- model ---
    model = ""
    meta = soup.find("div", class_="product-meta")
    if meta:
        p_tag = meta.find("p")
        if p_tag:
            current = []
            lines = []
            for node in p_tag.contents:
                if getattr(node, "name", None) == "br":
                    lines.append("".join(current).strip())
                    current = []
                else:
                    current.append(str(node))
            if current:
                lines.append("".join(current).strip())
            for line in lines:
                text = BeautifulSoup(line, "lxml").get_text(" ", strip=True)
                if text.lower().startswith("model:"):
                    model = text[6:].strip()
                    break

    # --- first image ---
    image_url = ""
    first_a = soup.select_one("ul.image-items li.image-item a[href]")
    if first_a:
        image_url = first_a["href"]

    return model, image_url


def main():
    parser = argparse.ArgumentParser(description="Scrape model + first image URL from aolga-hk.com")
    parser.add_argument("--output", default="image_product.csv", help="Output CSV filename")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests (seconds)")
    args = parser.parse_args()

    out_path = Path(args.output)
    rows = []

    for slug, category_name in CATEGORIES:
        print(f"\n[{category_name}] กำลังดึง product links...")
        product_links = get_product_links(slug)
        print(f"  พบ {len(product_links)} products")

        for i, url in enumerate(product_links, 1):
            model, image_url = get_model_and_first_image(url)
            # ใช้ model เป็น sku ถ้ามี ไม่งั้นใช้ท้าย URL
            sku = model if model else url.rstrip("/").split("/")[-1]
            print(f"  [{i}/{len(product_links)}] {sku}  {image_url or '(no image)'}")
            rows.append({"sku": sku, "image_url": image_url})
            time.sleep(args.delay)

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["sku", "image_url"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nบันทึก {len(rows)} แถว → {out_path}")


if __name__ == "__main__":
    main()
