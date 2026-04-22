"""
AOLGA HK Product Scraper
Scrapes all products from https://www.aolga-hk.com/
Saves results to aolga_products.csv
"""

import csv
import re
import time
import unicodedata
import requests
from bs4 import BeautifulSoup

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


def clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[^\x20-\x7E\u0E00-\u0E7F]", " ", text)
    text = re.sub(r" {2,}", " ", text).strip()
    return text


def get_soup(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        print(f"  [ERROR] {url} -> {e}")
        return None


def get_total_pages(soup: BeautifulSoup) -> int:
    """Detect total number of pages from pagination."""
    # Structure: <div class="pages">Page X / Y</div>
    pages_div = soup.find("div", class_="pages")
    if pages_div:
        text = pages_div.get_text(strip=True)  # e.g. "Page 1 / 5"
        parts = text.split("/")
        if len(parts) == 2:
            try:
                return int(parts[1].strip())
            except ValueError:
                pass
    # Fallback: look for page links
    page_links = soup.select("div.pages a")
    numbers = []
    for a in page_links:
        txt = a.get_text(strip=True)
        if txt.isdigit():
            numbers.append(int(txt))
    return max(numbers) if numbers else 1


def get_detail(url: str) -> dict:
    """Visit product page and return all spec fields."""
    result = {
        "model": "", "specification": "", "color": "", "feature": "",
        "spec_model": "", "spec_color": "", "spec_feature": "",
        "spec_rated_power": "", "spec_voltage": "", "spec_frequency": "",
        "spec_cable_length": "", "spec_product_size": "", "spec_gift_box_size": "",
        "spec_carton_size": "", "spec_package_standard": "",
        "spec_net_weight": "", "spec_gross_weight": "",
        "image_urls": [],
    }
    if not url:
        return result
    soup = get_soup(url)
    if not soup:
        return result

    meta = soup.find("div", class_="product-meta")
    if meta:
        p_tag = meta.find("p")
        if p_tag:
            lines = []
            current = []
            for node in p_tag.contents:
                if getattr(node, "name", None) == "br":
                    lines.append("".join(current).strip())
                    current = []
                else:
                    current.append(str(node))
            if current:
                lines.append("".join(current).strip())
            for line in lines:
                line = clean(BeautifulSoup(line, "lxml").get_text(" ", strip=True))
                low = line.lower()
                if low.startswith("model:"):
                    result["model"] = line[6:].strip()
                elif low.startswith("specification:"):
                    result["specification"] = line[14:].strip()
                elif low.startswith("color:"):
                    result["color"] = line[6:].strip()
                elif low.startswith("feature:"):
                    result["feature"] = line[8:].strip()

    builder = soup.find("div", class_="fl-builder-content")
    if builder:
        tbl = builder.find("table")
        if tbl:
            for tr in tbl.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                if len(cells) >= 2:
                    key = clean(cells[0].get_text(" ", strip=True)).lower()
                    val = clean(cells[1].get_text(" ", strip=True))
                    if "model" in key:
                        result["spec_model"] = val
                    elif "color" in key:
                        result["spec_color"] = val
                    elif "feature" in key:
                        result["spec_feature"] = val
                    elif "cable" in key:
                        result["spec_cable_length"] = val
                    elif "rated power" in key or "power" in key:
                        result["spec_rated_power"] = val
                    elif "voltage" in key:
                        result["spec_voltage"] = val
                    elif "frequency" in key:
                        result["spec_frequency"] = val
                    elif "product size" in key:
                        result["spec_product_size"] = val
                    elif "gift" in key or "gife" in key:
                        result["spec_gift_box_size"] = val
                    elif "carton" in key:
                        result["spec_carton_size"] = val
                    elif "package" in key:
                        result["spec_package_standard"] = val
                    elif "net weight" in key:
                        result["spec_net_weight"] = val
                    elif "gross weight" in key:
                        result["spec_gross_weight"] = val
    # Collect all product images from ul.image-items li.image-item a[href]
    if soup:
        seen = set()
        for a in soup.select("ul.image-items li.image-item a[href]"):
            href = a["href"]
            if href and href not in seen:
                seen.add(href)
                result["image_urls"].append(href)

    return result


def build_html(p: dict) -> str:
    """Build HTML <li> pattern from product data."""
    lines = []
    feature_text = p.get("spec_feature") or p.get("feature") or ""
    if feature_text:
        bullets = [f.strip() for f in re.split(r";|\uff1b", feature_text) if f.strip()]
        for b in bullets:
            lines.append(f"<li>{b}</li>")
    lines.append(
        '<p style="margin-top: 26px; margin-bottom: 26px; font-size: 16px; '
        'font-weight: 400; line-height: 24px;">Technical Specifications:</p>'
    )
    spec_fields = [
        ("Model", p.get("spec_model") or p.get("model")),
        ("Color", p.get("spec_color") or p.get("color")),
        ("Specification", p.get("specification")),
        ("Rated Power", p.get("spec_rated_power")),
        ("Voltage", p.get("spec_voltage")),
        ("Rated Frequency", p.get("spec_frequency")),
        ("Length of Power Cable", p.get("spec_cable_length")),
        ("Product Size", p.get("spec_product_size")),
        ("Gift Box Size", p.get("spec_gift_box_size")),
        ("Master Carton Size", p.get("spec_carton_size")),
        ("Package Standard", p.get("spec_package_standard")),
        ("Net Weight", p.get("spec_net_weight")),
        ("Gross Weight", p.get("spec_gross_weight")),
    ]
    for label, val in spec_fields:
        if val and val.strip().strip("/").strip():
            lines.append(f"<li>{label}: {val}</li>")
    return "\n".join(lines)


def parse_products(soup: BeautifulSoup, category_name: str) -> list[dict]:
    products = []
    items = soup.select("li.product_list_item")

    for item in items:
        # Name & product URL
        name_tag = item.select_one("h3.item_title a")
        name = name_tag.get_text(strip=True) if name_tag else ""
        product_url = name_tag["href"] if name_tag and name_tag.get("href") else ""

        # Image
        img_tag = item.select_one("span.item_img img")
        image_url = ""
        if img_tag:
            image_url = img_tag.get("src") or img_tag.get("data-src") or ""

        if name:
            products.append({
                "category": category_name,
                "name": name,
                "image_url": image_url,
                "product_url": product_url,
            })

    return products


def scrape_category(slug: str, category_name: str) -> list[dict]:
    all_products = []
    page = 1

    while True:
        if page == 1:
            url = f"{BASE_URL}/{slug}/"
        else:
            url = f"{BASE_URL}/{slug}/page/{page}/"

        print(f"  Fetching: {url}")
        soup = get_soup(url)
        if not soup:
            break

        products = parse_products(soup, category_name)
        if not products:
            print(f"  No products found on page {page}, stopping.")
            break

        all_products.extend(products)
        print(f"  Page {page}: {len(products)} products")

        total_pages = get_total_pages(soup)
        if page >= total_pages:
            break

        page += 1
        time.sleep(1)  # polite delay

    return all_products


def save_to_csv(products: list[dict], filename: str = "aolga_products.csv"):
    if not products:
        print("No products to save.")
        return

    fieldnames = [
        "category", "name", "model", "specification", "color", "feature",
        "spec_model", "spec_color", "spec_feature",
        "spec_rated_power", "spec_voltage", "spec_frequency",
        "spec_cable_length", "spec_product_size", "spec_gift_box_size",
        "spec_carton_size", "spec_package_standard",
        "spec_net_weight", "spec_gross_weight",
        "html_content",
        "image_url", "product_url",
    ]
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(products)

    print(f"\nSaved {len(products)} products to '{filename}'")


def main():
    all_products = []

    for slug, category_name in CATEGORIES:
        print(f"\n[{category_name}]")
        products = scrape_category(slug, category_name)
        all_products.extend(products)
        print(f"  Total so far: {len(all_products)}")

    # Visit each product page to get detailed info
    print(f"\nFetching details for {len(all_products)} products...")
    for i, product in enumerate(all_products, 1):
        print(f"  [{i}/{len(all_products)}] {product['name']}")
        detail = get_detail(product["product_url"])
        image_urls = detail.pop("image_urls", [])
        product.update(detail)
        if image_urls:
            product["image_url"] = ",".join(image_urls)
        product["html_content"] = build_html(product)
        time.sleep(0.5)  # polite delay

    save_to_csv(all_products)
    print("\nDone!")


if __name__ == "__main__":
    main()
