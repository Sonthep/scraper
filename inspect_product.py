import requests
from bs4 import BeautifulSoup

r = requests.get(
    "https://www.aolga-hk.com/high-speed-hair-dryer-gf-10-product/",
    headers={"User-Agent": "Mozilla/5.0"}
)
soup = BeautifulSoup(r.text, "lxml")

# Find all tables on page
tables = soup.find_all("table")
print(f"Total tables found: {len(tables)}")
for i, tbl in enumerate(tables):
    print(f"\n=== Table {i} ===")
    for tr in tbl.find_all("tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
        print(" | ".join(cells))
