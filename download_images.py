"""
Image Downloader
----------------
อ่าน CSV ที่มี column 'sku' และ 'image_url' (คั่นด้วย ,)
แล้ว download รูปบันทึกลงโฟลเดอร์ images/

ชื่อไฟล์:
  - รูปเดียว  → images/{sku}.jpg
  - หลายรูป  → images/{sku}_1.jpg, images/{sku}_2.jpg, ...

วิธีใช้:
  python download_images.py                        # ใช้ไฟล์ default
  python download_images.py myfile.csv             # ระบุไฟล์ CSV เอง
  python download_images.py myfile.csv images_out  # ระบุ output folder ด้วย
"""

import csv
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

# ─── Config ──────────────────────────────────────────────────────────────────
DEFAULT_CSV = "data/image_product.csv"
DEFAULT_OUT = "images"
DELAY = 0.3  # วินาที ระหว่าง request
TIMEOUT = 20
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
# ─────────────────────────────────────────────────────────────────────────────


def get_ext(url: str) -> str:
    """ดึง extension จาก URL เช่น .jpg .png"""
    path = urlparse(url).path
    ext = Path(path).suffix.lower()
    return ext if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"} else ".jpg"


def download_image(url: str, save_path: Path) -> bool:
    """Download รูปจาก URL บันทึกที่ save_path คืนค่า True ถ้าสำเร็จ"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True)
        resp.raise_for_status()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"    [ERROR] {e}")
        return False


def main():
    # รับ argument
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DEFAULT_CSV)
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(DEFAULT_OUT)

    if not csv_path.exists():
        print(f"[ERROR] ไม่พบไฟล์: {csv_path}")
        sys.exit(1)

    # อ่าน CSV
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    # ตรวจสอบ column
    if not rows:
        print("[ERROR] CSV ว่างเปล่า")
        sys.exit(1)

    cols = rows[0].keys()
    if "sku" not in cols:
        print(f"[ERROR] ไม่พบ column 'sku' ใน CSV (มี: {', '.join(cols)})")
        sys.exit(1)
    if "image_url" not in cols:
        print(f"[ERROR] ไม่พบ column 'image_url' ใน CSV (มี: {', '.join(cols)})")
        sys.exit(1)

    print(f"CSV    : {csv_path}  ({len(rows)} rows)")
    print(f"Output : {out_dir}/")
    print("-" * 50)

    total_ok = 0
    total_skip = 0
    total_err = 0

    for i, row in enumerate(rows, 1):
        sku = row["sku"].strip()
        raw_urls = row.get("image_url", "").strip()

        if not sku or not raw_urls:
            print(f"[{i}/{len(rows)}] ข้าม (sku หรือ image_url ว่าง)")
            total_skip += 1
            continue

        urls = [u.strip() for u in raw_urls.split(",") if u.strip()]

        print(f"[{i}/{len(rows)}] {sku}  ({len(urls)} รูป)")

        for j, url in enumerate(urls, 1):
            # ตั้งชื่อไฟล์
            ext = get_ext(url)
            if len(urls) == 1:
                filename = f"{sku}{ext}"
            else:
                filename = f"{sku}_{j}{ext}"

            save_path = out_dir / filename

            # ข้ามถ้ามีอยู่แล้ว
            if save_path.exists():
                print(f"  [{j}] ข้าม (มีอยู่แล้ว): {filename}")
                total_skip += 1
                continue

            print(f"  [{j}] {filename}", end=" ... ", flush=True)
            ok = download_image(url, save_path)
            if ok:
                size_kb = save_path.stat().st_size / 1024
                print(f"OK ({size_kb:.1f} KB)")
                total_ok += 1
            else:
                total_err += 1

            time.sleep(DELAY)

    print()
    print("=" * 50)
    print(f"  สำเร็จ : {total_ok} รูป")
    print(f"  ข้าม   : {total_skip} รูป")
    print(f"  ผิดพลาด: {total_err} รูป")
    print(f"  บันทึกที่: {out_dir.resolve()}/")


if __name__ == "__main__":
    main()
