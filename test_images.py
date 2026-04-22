import csv, re, time, unicodedata, requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def get_soup(url):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml")

# Test 3 products from different categories
test_urls = [
    ("Hotel Thermoelectric Minibar CB-40SAFN", "https://www.aolga-hk.com/hotel-thermoelectric-minibar-cb-40safn-product/"),
    ("High Speed Hair Dryer GF-10", "https://www.aolga-hk.com/high-speed-hair-dryer-gf-10-product/"),
    ("Electric Kettle EKS07228E-3", "https://www.aolga-hk.com/electric-kettle-eks07228e-3-product/"),
]

for name, url in test_urls:
    print(f"\n=== {name} ===")
    soup = get_soup(url)
    seen = set()
    images = []
    for a in soup.select("ul.image-items li.image-item a[href]"):
        href = a["href"]
        if href and href not in seen:
            seen.add(href)
            images.append(href)
    print(f"  {len(images)} image(s):")
    for img in images:
        print(f"    {img}")
