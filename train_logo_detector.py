"""
train_logo_detector.py
----------------------
1. รัน template matching บนรูปทั้งหมดใน images/
2. สร้าง YOLO-format dataset จากรูปที่ detect ได้
3. Train YOLOv8n
4. บันทึก model เป็น logo_model.pt

ต้องการ:
  pip install ultralytics

วิธีใช้:
  python train_logo_detector.py
  python train_logo_detector.py --images images --template logo_template.png --threshold 0.58 --epochs 80
"""

import argparse
import random
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

# ─── Config ──────────────────────────────────────────────────────────────────
DEFAULT_IMAGES = "images"
DEFAULT_TEMPLATE = "logo_template.png"
DEFAULT_THRESHOLD = 0.60
DEFAULT_EPOCHS = 60
DEFAULT_BATCH = 8
DEFAULT_IMGSZ = 640
DATASET_DIR = Path("yolo_dataset")
MODEL_OUT = Path("logo_model.pt")
VAL_SPLIT = 0.20
PADDING_RATIO = 0.15  # ขยาย bounding box เพิ่ม 15% รอบนอก
# ─────────────────────────────────────────────────────────────────────────────


def find_logo(
    image: np.ndarray,
    template: np.ndarray,
    threshold: float,
) -> tuple:
    """Template matching หลาย scale — คืน (loc, size, conf)"""
    gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_tmpl = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    tmpl_h, tmpl_w = gray_tmpl.shape
    img_h, img_w = gray_img.shape

    best_val = 0.0
    best_loc = None
    best_size = None

    for scale in np.arange(0.35, 2.2, 0.05):
        rw = int(tmpl_w * scale)
        rh = int(tmpl_h * scale)
        if rw < 5 or rh < 5 or rw > img_w or rh > img_h:
            continue
        resized = cv2.resize(gray_tmpl, (rw, rh), interpolation=cv2.INTER_AREA)
        result = cv2.matchTemplate(gray_img, resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val > best_val:
            best_val = max_val
            best_loc = max_loc
            best_size = (rw, rh)

    if best_val >= threshold and best_loc is not None:
        return best_loc, best_size, best_val
    return None, None, best_val


def main() -> None:
    parser = argparse.ArgumentParser(description="Train YOLOv8 logo detector")
    parser.add_argument("--images", default=DEFAULT_IMAGES)
    parser.add_argument("--template", default=DEFAULT_TEMPLATE)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    parser.add_argument("--batch", type=int, default=DEFAULT_BATCH)
    parser.add_argument("--imgsz", type=int, default=DEFAULT_IMGSZ)
    args = parser.parse_args()

    # โหลด template
    tmpl_path = Path(args.template)
    if not tmpl_path.exists():
        print(f"[ERROR] ไม่พบ template: {tmpl_path}")
        sys.exit(1)
    template = cv2.imread(str(tmpl_path))

    # หาไฟล์รูป
    in_dir = Path(args.images)
    if not in_dir.exists():
        print(f"[ERROR] ไม่พบโฟลเดอร์: {in_dir}")
        sys.exit(1)

    exts = {".jpg", ".jpeg", ".png", ".webp"}
    images = sorted(f for f in in_dir.iterdir() if f.suffix.lower() in exts)

    if not images:
        print(f"[ERROR] ไม่พบรูปใน {in_dir}")
        sys.exit(1)

    # ─── Phase 1: Auto-label ───────────────────────────────────────────────
    print(f"Phase 1: Template matching บน {len(images)} รูป  (threshold={args.threshold})")
    labeled = []

    for img_path in images:
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        ih, iw = img.shape[:2]

        loc, size, conf = find_logo(img, template, args.threshold)

        if loc and size:
            x, y = loc
            w, h = size

            # ขยาย bounding box เพิ่ม padding รอบนอก
            pad_x = int(w * PADDING_RATIO)
            pad_y = int(h * PADDING_RATIO)
            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(iw, x + w + pad_x)
            y2 = min(ih, y + h + pad_y)

            # YOLO normalized format
            cx = (x1 + x2) / 2 / iw
            cy = (y1 + y2) / 2 / ih
            nw = (x2 - x1) / iw
            nh = (y2 - y1) / ih

            labeled.append((img_path, cx, cy, nw, nh, conf))
            print(f"  FOUND  conf={conf:.2f}  {img_path.name}")

    print(f"\nLabeled: {len(labeled)} รูป")

    if len(labeled) < 10:
        print("[ERROR] labeled images น้อยเกินไป ลอง --threshold 0.55")
        sys.exit(1)

    # ─── Phase 2: สร้าง dataset ────────────────────────────────────────────
    print("\nPhase 2: สร้าง YOLO dataset...")

    random.shuffle(labeled)
    n_val = max(1, int(len(labeled) * VAL_SPLIT))
    splits = {
        "train": labeled[n_val:],
        "val": labeled[:n_val],
    }

    # ล้างและสร้าง folder ใหม่
    if DATASET_DIR.exists():
        shutil.rmtree(DATASET_DIR)

    for split_name in ("train", "val"):
        (DATASET_DIR / "images" / split_name).mkdir(parents=True, exist_ok=True)
        (DATASET_DIR / "labels" / split_name).mkdir(parents=True, exist_ok=True)

    for split_name, items in splits.items():
        for img_path, cx, cy, nw, nh, _ in items:
            shutil.copy2(img_path, DATASET_DIR / "images" / split_name / img_path.name)
            lbl_path = DATASET_DIR / "labels" / split_name / (img_path.stem + ".txt")
            with open(lbl_path, "w") as f:
                f.write(f"0 {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}\n")

    # dataset.yaml
    yaml_path = DATASET_DIR / "dataset.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(
            {
                "path": str(DATASET_DIR.resolve()).replace("\\", "/"),
                "train": "images/train",
                "val": "images/val",
                "nc": 1,
                "names": ["logo"],
            },
            f,
            default_flow_style=False,
        )

    print(f"  Train: {len(splits['train'])} รูป")
    print(f"  Val  : {len(splits['val'])} รูป")
    print(f"  Dataset: {DATASET_DIR.resolve()}/")

    # ─── Phase 3: Train YOLOv8 ─────────────────────────────────────────────
    print(f"\nPhase 3: Training YOLOv8n  epochs={args.epochs}  batch={args.batch}")
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] ไม่พบ ultralytics  รัน: pip install ultralytics")
        sys.exit(1)

    model = YOLO("yolov8n.pt")
    model.train(
        data=str(yaml_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project="yolo_runs",
        name="logo_detector",
        exist_ok=True,
        patience=20,
        augment=True,
        verbose=True,
    )

    # Copy best model
    best = Path("yolo_runs/logo_detector/weights/best.pt")
    if best.exists():
        shutil.copy2(best, MODEL_OUT)
        print(f"\nModel บันทึกที่: {MODEL_OUT.resolve()}")
    else:
        print("[ERROR] ไม่พบ best.pt")
        sys.exit(1)

    print("\nเสร็จแล้ว! รัน remove_logo.py ได้เลย")


if __name__ == "__main__":
    main()
