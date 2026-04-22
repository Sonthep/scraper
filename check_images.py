import requests
from bs4 import BeautifulSoup

url = "https://www.aolga-hk.com/hotel-thermoelectric-minibar-cb-40safn-product/"
r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
soup = BeautifulSoup(r.text, "lxml")

print("=== <a href> linking to globalso image files ===")
for a in soup.find_all("a", href=True):
    href = a["href"]
    if "globalso" in href and any(href.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]):
        print("href:", href)
        print("  parent:", a.parent.name, a.parent.get("class", ""))
        print("  grandparent:", a.parent.parent.name, a.parent.parent.get("class", ""))
        print("  HTML:", str(a)[:300])
        print()
