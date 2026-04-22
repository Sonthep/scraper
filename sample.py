import csv, re, time, requests, unicodedata
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"}

def clean(text: str) -> str:
    """Remove non-breaking spaces, bullet artifacts and normalize unicode."""
    text = unicodedata.normalize("NFKC", text)   # normalise \xa0, \u2022 etc.
    text = text.replace("\xa0", " ")              # non-breaking space -> space
    text = re.sub(r"[^\x20-\x7E\u0E00-\u0E7F]", " ", text)  # keep ASCII + Thai only
    text = re.sub(r" {2,}", " ", text).strip()
    return text

def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def get_detail(url):
    result = {
        "model": "", "specification": "", "color": "", "feature": "",
        "spec_model": "", "spec_color": "", "spec_feature": "",
        "spec_rated_power": "", "spec_voltage": "", "spec_frequency": "",
        "spec_cable_length": "", "spec_product_size": "", "spec_gift_box_size": "",
        "spec_carton_size": "", "spec_package_standard": "",
        "spec_net_weight": "", "spec_gross_weight": "",
    }
    soup = get_soup(url)
    meta = soup.find("div", class_="product-meta")
    if meta:
        p_tag = meta.find("p")
        if p_tag:
            # Collect lines split by <br/> tags
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
                    # Map common keys to fixed column names
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
    return result

soup = get_soup("https://www.aolga-hk.com/hair-dryer/")
items = soup.select("li.product_list_item")[:5]
products = []
for item in items:
    a = item.select_one("h3.item_title a")
    img = item.select_one("span.item_img img")
    p = {
        "category": "Hair Dryer",
        "name": a.get_text(strip=True) if a else "",
        "image_url": img["src"] if img else "",
        "product_url": a["href"] if a else "",
    }
    print("Fetching:", p["name"])
    detail = get_detail(p["product_url"])
    p.update(detail)
    products.append(p)
    time.sleep(0.5)

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


def build_html(p: dict) -> str:
    """Build HTML <li> pattern from product data."""
    lines = []

    # Feature bullet points — split by semicolon
    feature_text = p.get("spec_feature") or p.get("feature") or ""
    if feature_text:
        bullets = [f.strip() for f in re.split(r";|；", feature_text) if f.strip()]
        for b in bullets:
            lines.append(f"<li>{b}</li>")

    # Technical Specifications paragraph
    lines.append(
        '<p style="margin-top: 26px; margin-bottom: 26px; font-size: 16px; '
        'font-weight: 400; line-height: 24px;">Technical Specifications:</p>'
    )

    # Spec rows
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


with open("aolga_sample.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for p in products:
        p["html_content"] = build_html(p)
        w.writerow(p)

print("\nDone! Saved aolga_sample.csv")
for p in products:
    print("\n" + "="*60)
    print(p["name"])
    print(p["html_content"])
