import csv

rows = []
with open('image_product.csv', newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        urls = row['image_url'].split(',')
        for i, url in enumerate(urls):
            url = url.strip()
            if not url:
                continue
            sku = row['sku'] if i == 0 else f"{row['sku']}_{i+1}"
            rows.append({'sku': sku, 'image_url': url})

with open('image_product_split.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=['sku', 'image_url'])
    writer.writeheader()
    writer.writerows(rows)

print(f'Done: {len(rows)} rows written to image_product_split.csv')
for r in rows[:6]:
    print(r)
