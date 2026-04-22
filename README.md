# AOLGA HK Product Scraper

ดึงข้อมูลสินค้าทั้งหมดจาก [aolga-hk.com](https://www.aolga-hk.com/) และบันทึกลงไฟล์ CSV

---

## ไฟล์ในโปรเจกต์

| ไฟล์ | หน้าที่ |
|------|---------|
| `scraper.py` | ตัวหลัก — ดึงสินค้าทั้ง 13 หมวด 151 รายการ บันทึกลง `aolga_products.csv` |
| `aolga_products.csv` | ผลลัพธ์ — ข้อมูลสินค้าครบทุกรายการ |
| `sample.py` | ทดสอบกับสินค้า 5 รายการแรก (Hair Dryer) |
| `aolga_sample.csv` | ผลลัพธ์จาก `sample.py` |
| `check_images.py` | ตรวจสอบ HTML structure ของรูปสินค้า |
| `test_images.py` | ทดสอบการดึง URL รูปจาก product page |

---

## วิธีใช้งาน

### ติดตั้ง dependencies

```bash
python -m venv .venv
.venv\Scripts\activate
pip install requests beautifulsoup4 lxml
```

### รัน scraper

```bash
python scraper.py
```

ผลลัพธ์จะถูกบันทึกที่ `aolga_products.csv`

---

## โครงสร้าง CSV Output

| Column | ตัวอย่าง | หมายเหตุ |
|--------|---------|----------|
| `category` | `Hair Dryer` | ชื่อหมวดสินค้า |
| `name` | `High Speed Hair Dryer GF-10` | ชื่อสินค้า |
| `model` | `GF-10` | จาก Short Description |
| `specification` | `220V-240V~, 50Hz, 1600W` | จาก Short Description |
| `color` | `Black` | จาก Short Description |
| `feature` | `High speed motor; Quiet design` | จาก Short Description |
| `spec_model` | `GF-10` | จาก Spec Table |
| `spec_color` | `Black` | จาก Spec Table |
| `spec_feature` | `High speed motor; Quiet design` | จาก Spec Table |
| `spec_rated_power` | `1600W` | จาก Spec Table |
| `spec_voltage` | `220-240V` | จาก Spec Table |
| `spec_frequency` | `50/60Hz` | จาก Spec Table |
| `spec_cable_length` | `1.8M` | จาก Spec Table |
| `spec_product_size` | `210×75×135mm` | จาก Spec Table |
| `spec_gift_box_size` | `230×90×155mm` | จาก Spec Table |
| `spec_carton_size` | `480×240×320mm` | จาก Spec Table |
| `spec_package_standard` | `6 pcs/ctn` | จาก Spec Table |
| `spec_net_weight` | `0.45kg` | จาก Spec Table |
| `spec_gross_weight` | `0.55kg` | จาก Spec Table |
| `html_content` | `<li>Feature 1</li>...` | HTML สำหรับใส่เว็บ |
| `image_url` | `https://cdn.../1.jpg,https://cdn.../2.jpg` | URL รูปทุกรูป คั่นด้วย `,` |
| `product_url` | `https://www.aolga-hk.com/...` | ลิงก์หน้าสินค้า |

---

## หมวดสินค้าทั้งหมด (13 หมวด)

| หมวด | URL Slug | จำนวนสินค้า |
|------|----------|------------|
| Hair Dryer | `hair-dryer` | 30 |
| Electric Kettle | `electric-kettle` | 19 |
| Kettle Tray | `kettle-tray` | 7 |
| Coffee Machine | `coffee-machine` | 6 |
| Hotel Minibar | `hotel-minibar` | 30 |
| Room Safes | `electronic-password-safes` | 16 |
| Electric Iron | `electric-iron` | 5 |
| Iron Board and Holder | `iron-board-and-holder` | 4 |
| Weight Scale | `weight-scale` | 8 |
| Bluetooth Alarm Clock | `bluetooth-alarm-clock` | 2 |
| Cosmetic Mirror | `cosmetic-mirror` | 12 |
| Luggage Rack | `luggage-rack` | 5 |
| Clothes Hanger | `clothes-hanger` | 7 |
| **รวม** | | **151** |

---

## โครงสร้าง `html_content`

ใช้สำหรับนำไปใส่ในเว็บโดยตรง รูปแบบ:

```html
<li>Feature 1</li>
<li>Feature 2</li>
<p style="margin-top: 26px; ...">Technical Specifications:</p>
<li>Model: GF-10</li>
<li>Color: Black</li>
<li>Specification: 220V-240V~, 50Hz, 1600W</li>
<li>Rated Power: 1600W</li>
<li>Length of Power Cable: 1.8M</li>
...
```

> Feature bullets แยกจาก spec table  
> ค่าที่ว่างเปล่าหรือเป็น `/` จะถูกข้ามไปไม่แสดง

---

## หมายเหตุ

- **Encoding**: CSV บันทึกด้วย `utf-8-sig` (เปิดด้วย Excel ได้ถูกต้อง)
- **Image URLs**: ดึงจากหน้า product detail (`ul.image-items`) ได้ทุกรูป คั่นด้วย `,`
- **Coffee Machine page/2**: เว็บมี bug แสดง pagination แต่ URL จริงคืน 404 — scraper จัดการให้อัตโนมัติ
- **Delay**: มี `time.sleep()` ระหว่าง request เพื่อไม่ให้ load เซิร์ฟเวอร์มากเกินไป
