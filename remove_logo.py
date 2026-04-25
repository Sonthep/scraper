"""
remove_logo.py  v3
------------------
YOLOv8 (Detection) + Template Matching fallback + LaMa (Inpainting)

ขั้นตอน:
  1. Train model ก่อน (ทำครั้งเดียว):
       python train_logo_detector.py

  2. ลบ logo:
       python remove_logo.py
       python remove_logo.py --input images --output images_clean
       python remove_logo.py --conf 0.20   # ลด confidence ถ้าหาไม่เจอ

ต้องการ:
  pip install ultralytics simple-lama-inpainting
"""

import argparse
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

# ─── Config ──────────────────────────────────────────────────────────────────
DEFAULT_INPUT = "images"
DEFAULT_OUTPUT = "images_clean"
DEFAULT_MODEL = "logo_model.pt"
DEFAULT_TEMPLATE = "logo_template.png"
DEFAULT_CONF = 0.25          # YOLOv8 confidence threshold
DEFAULT_TM_THRESHOLD = 0.60  # Template matching threshold (fallback)
DEFAULT_PADDING = 12         # pixels เพิ่มรอบ bounding box ก่อน inpaint
INPAINT_RADIUS = 7           # fallback (ใช้เมื่อ LaMa ล้มเหลว)
TM_SCALE_START = 0.35
TM_SCALE_STOP  = 2.2
TM_SCALE_STEP  = 0.05       # เหมือนกับ train_logo_detector.py
# ─────────────────────────────────────────────────────────────────────────────


def find_logo_template(image_bgr: np.ndarray, template_bgr: np.ndarray, threshold: float, padding: int):
    """Template matching หลาย scale — คืน mask หรือ None"""
    gray_img = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray_tmpl = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)
    ih, iw = gray_img.shape
    th, tw = gray_tmpl.shape

    best_conf = 0.0
    best_box = None

    scale = TM_SCALE_START
    while scale < TM_SCALE_STOP:
        new_w = int(tw * scale)
        new_h = int(th * scale)
        if new_w >= 5 and new_h >= 5 and new_w <= iw and new_h <= ih:
            tmpl_scaled = cv2.resize(gray_tmpl, (new_w, new_h), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(gray_img, tmpl_scaled, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            if max_val > best_conf:
                best_conf = max_val
                best_box = (max_loc[0], max_loc[1], new_w, new_h)
        scale = round(scale + TM_SCALE_STEP, 4)

    if best_conf >= threshold and best_box is not None:
        x, y, w, h = best_box
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(iw, x + w + padding)
        y2 = min(ih, y + h + padding)
        mask = np.zeros((ih, iw), dtype=np.uint8)
        mask[y1:y2, x1:x2] = 255
        return mask, best_conf
    return None, 0.0


def load_yolo(model_path: str):
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] ไม่พบ ultralytics  รัน: pip install ultralytics")
        sys.exit(1)
    return YOLO(model_path)


def load_lama():
    try:
        from simple_lama_inpainting import SimpleLama
    except ImportError:
        print("[ERROR] ไม่พบ simple-lama-inpainting  รัน: pip install simple-lama-inpainting")
        sys.exit(1)
    return SimpleLama()


def inpaint_lama(lama, image_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """ส่ง image + mask ให้ LaMa แล้วคืน result"""
    img_pil = Image.fromarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))
    mask_pil = Image.fromarray(mask)
    result_pil = lama(img_pil, mask_pil)
    return cv2.cvtColor(np.array(result_pil), cv2.COLOR_RGB2BGR)


def detect_logo(img: np.ndarray, yolo, template, conf: float, tm_threshold: float, padding: int):
    """ตรวจหา logo — คืน (mask, method_tag) หรือ (None, '')"""
    ih, iw = img.shape[:2]

    results = yolo(img, conf=conf, verbose=False)
    boxes = results[0].boxes

    if boxes is not None and len(boxes) > 0:
        mask = np.zeros((ih, iw), dtype=np.uint8)
        for box in boxes.xyxy:
            x1, y1, x2, y2 = map(int, box.tolist())
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(iw, x2 + padding)
            y2 = min(ih, y2 + padding)
            mask[y1:y2, x1:x2] = 255
        conf_val = float(boxes.conf[0])
        return mask, f"YOLO conf={conf_val:.2f}"

    if template is not None:
        mask, tm_conf = find_logo_template(img, template, tm_threshold, padding)
        if mask is not None:
            return mask, f"TM conf={tm_conf:.2f}"

    return None, ""


def main() -> None:
    parser = argparse.ArgumentParser(description="ลบ logo ด้วย YOLOv8 + LaMa")
    parser.add_argument("--input",        default=DEFAULT_INPUT,        help=f"โฟลเดอร์รูปต้นฉบับ (default: {DEFAULT_INPUT})")
    parser.add_argument("--output",       default=DEFAULT_OUTPUT,       help=f"โฟลเดอร์รูป output (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--model",        default=DEFAULT_MODEL,        help=f"YOLOv8 model path (default: {DEFAULT_MODEL})")
    parser.add_argument("--template",     default=DEFAULT_TEMPLATE,     help=f"Template png สำหรับ fallback (default: {DEFAULT_TEMPLATE})")
    parser.add_argument("--conf",         type=float, default=DEFAULT_CONF,         help=f"YOLOv8 confidence threshold (default: {DEFAULT_CONF})")
    parser.add_argument("--tm-threshold", type=float, default=DEFAULT_TM_THRESHOLD, help=f"Template matching threshold (default: {DEFAULT_TM_THRESHOLD})")
    parser.add_argument("--padding",      type=int,   default=DEFAULT_PADDING,      help=f"pixels เพิ่มรอบ box (default: {DEFAULT_PADDING})")
    parser.add_argument("--scan-only",    action="store_true", help="สแกนเฉพาะ ไม่ inpaint")
    parser.add_argument("--output-clean", default=None, help="โฟลเดอร์สำหรับรูปที่ไม่มี logo (default: <output>_no_logo)")
    args = parser.parse_args()

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"[ERROR] ไม่พบ model: {model_path}")
        print("       รัน: python train_logo_detector.py  ก่อน")
        sys.exit(1)

    template_path = Path(args.template)
    template = None
    if template_path.exists():
        template = cv2.imread(str(template_path))
        print(f"Template fallback    : {template_path}")
    else:
        print(f"[WARN] ไม่พบ template: {template_path}  (จะใช้เฉพาะ YOLO)")

    in_dir    = Path(args.input)
    out_dir   = Path(args.output)
    clean_dir = Path(args.output_clean) if args.output_clean else Path(str(out_dir) + "_no_logo")
    if not in_dir.exists():
        print(f"[ERROR] ไม่พบโฟลเดอร์: {in_dir}")
        sys.exit(1)

    exts = {".jpg", ".jpeg", ".png", ".webp"}
    images = sorted(f for f in in_dir.iterdir() if f.suffix.lower() in exts)
    if not images:
        print(f"[ERROR] ไม่พบรูปใน {in_dir}")
        sys.exit(1)

    print(f"Loading YOLOv8 model  : {model_path}")
    yolo = load_yolo(str(model_path))

    # ─── Phase 1: SCAN ──────────────────────────────────────────────────────
    print(f"\n{'='*55}")
    print(f"  Phase 1: สแกน {len(images)} รูป (YOLO + Template Matching)")
    print(f"{'='*55}")

    has_logo:    list[tuple[Path, np.ndarray, str]] = []   # (path, mask, tag)
    no_logo:     list[Path] = []
    scan_errors: list[Path] = []

    for i, img_path in enumerate(images, 1):
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"[{i:>3}/{len(images)}] [ERROR] โหลดไม่ได้: {img_path.name}")
            scan_errors.append(img_path)
            continue

        mask, tag = detect_logo(img, yolo, template, args.conf, args.tm_threshold, args.padding)
        if mask is not None:
            has_logo.append((img_path, mask, tag))
            print(f"[{i:>3}/{len(images)}] มี logo  [{tag}]  {img_path.name}")
        else:
            no_logo.append(img_path)
            print(f"[{i:>3}/{len(images)}] ไม่มี logo        {img_path.name}")

    print(f"\n{'='*55}")
    print(f"  สแกนเสร็จสิ้น")
    print(f"  มี logo      : {len(has_logo):>4} รูป  → จะ inpaint → {out_dir}")
    print(f"  ไม่มี logo   : {len(no_logo):>4} รูป  → คัดลอก  → {clean_dir}")
    print(f"  โหลดไม่ได้   : {len(scan_errors):>4} รูป")
    print(f"{'='*55}")

    if args.scan_only:
        print("\n[--scan-only] หยุดที่ Phase 1  ไม่ inpaint")
        return

    # ─── Phase 2a: COPY รูปที่ไม่มี logo ────────────────────────────────────
    if no_logo:
        clean_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n  Phase 2a: คัดลอก {len(no_logo)} รูป (ไม่มี logo) → {clean_dir}/")
        print("-" * 55)
        for i, img_path in enumerate(no_logo, 1):
            dest = clean_dir / img_path.name
            if dest.exists():
                print(f"[{i:>3}/{len(no_logo)}] ข้าม (มีอยู่แล้ว): {img_path.name}")
            else:
                shutil.copy2(str(img_path), str(dest))
                print(f"[{i:>3}/{len(no_logo)}] คัดลอก  {img_path.name}")

    if not has_logo:
        print("\nไม่มีรูปที่ต้อง inpaint — จบ")
        return

    # ─── Phase 2b: INPAINT (เฉพาะรูปที่มี logo) ─────────────────────────────
    print(f"\n  Phase 2b: ลบ logo {len(has_logo)} รูป (LaMa inpainting)")
    print(f"  Output : {out_dir}/")
    print("-" * 55)

    print("Loading LaMa model    : (อาจ download อัตโนมัติครั้งแรก ~200MB)")
    lama = load_lama()
    out_dir.mkdir(parents=True, exist_ok=True)

    done = skipped = err = 0
    total = len(has_logo)

    for i, (img_path, mask, method_tag) in enumerate(has_logo, 1):
        out_path = out_dir / img_path.name

        if out_path.exists():
            print(f"[{i:>3}/{total}] ข้าม (มีอยู่แล้ว): {img_path.name}")
            skipped += 1
            continue

        img = cv2.imread(str(img_path))
        if img is None:
            print(f"[{i:>3}/{total}] [ERROR] โหลดไม่ได้: {img_path.name}")
            err += 1
            continue

        try:
            result = inpaint_lama(lama, img, mask)
            cv2.imwrite(str(out_path), result)
            print(f"[{i:>3}/{total}] ลบสำเร็จ [LaMa/{method_tag}]  {img_path.name}")
            done += 1
        except Exception as e:
            result = cv2.inpaint(img, mask, INPAINT_RADIUS, cv2.INPAINT_TELEA)
            cv2.imwrite(str(out_path), result)
            print(f"[{i:>3}/{total}] ลบสำเร็จ [CV2/{method_tag}]  {img_path.name}  ({e})")
            done += 1

    print()
    print("=" * 55)
    print(f"  ลบ logo สำเร็จ : {done} รูป")
    print(f"  ข้าม           : {skipped} รูป  (มีอยู่แล้ว)")
    print(f"  ผิดพลาด        : {err} รูป")
    print(f"  คัดลอก (ไม่มี logo) : {len(no_logo)} รูป  → {clean_dir.resolve()}/")
    print(f"  บันทึก (ลบ logo)    : {out_dir.resolve()}/")


if __name__ == "__main__":
    main()
