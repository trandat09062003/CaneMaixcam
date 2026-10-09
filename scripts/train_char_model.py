#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SCRIPT HUAN LUYEN MODEL AI NHAN DIEN 36 KY TU (0-9, A-Z) CHO MAIXCAM
Ho tro ca YOLOv5n va YOLOv8n (Mac dinh YOLOv5n nhe va on dinh nhat cho NPU)
================================================================================
"""

import os
import sys
import shutil
import argparse

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def train_char(model_type="yolov5n", epochs=20, batch=16):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    yaml_file = os.path.join(base_dir, "dataset_chars_yolo", "chars.yaml")

    print("=" * 70)
    print(f"  HUAN LUYEN MO HINH NHAN DIEN 36 KY TU VOI {model_type.upper()}")
    print("=" * 70)

    if not os.path.exists(yaml_file):
        print(f"[LOI] Chua tim thay {yaml_file}!")
        print("Vui long chay: python scripts/prepare_char_dataset_real.py truoc.")
        return False

    from ultralytics import YOLO

    # Chon model goc
    if "v8" in model_type:
        base_pt = os.path.join(base_dir, "yolov8n.pt")
        arch_name = "yolov8"
    else:
        base_pt = os.path.join(base_dir, "yolov5nu.pt")
        arch_name = "yolov5"

    if not os.path.exists(base_pt):
        base_pt = f"{model_type}.pt"

    print(f"[1/4] Su dung base weights: {base_pt}")
    model = YOLO(base_pt)

    project_dir = os.path.join(base_dir, "runs", "detect", "runs_chars")
    run_name = f"{arch_name}_chars36_real"

    print(f"[2/4] Bat dau train {epochs} epochs (batch={batch}, imgsz=320)...")
    results = model.train(
        data=yaml_file,
        epochs=epochs,
        imgsz=320,
        batch=batch,
        device="cpu",
        project=project_dir,
        name=run_name,
        exist_ok=True,
        verbose=True
    )

    trained_best_pt = os.path.join(project_dir, run_name, "weights", "best.pt")
    if not os.path.exists(trained_best_pt):
        print(f"[LOI] Khong tim thay {trained_best_pt}!")
        return False

    print(f"\n[THANH CONG] Huan luyen xong! Weights tai: {trained_best_pt}")

    # 3. Xuat ONNX
    print(f"\n[3/4] Xuat ONNX opset 11 cho {arch_name.upper()}...")
    trained_model = YOLO(trained_best_pt)
    onnx_file = trained_model.export(
        format="onnx",
        imgsz=320,
        opset=11,
        simplify=True
    )

    # Copy luu tru rieng biet (khong ghi de model cu)
    dest_onnx_root = os.path.join(base_dir, "Gay_Nguoi_Mu", "char_ocr_v2.onnx")
    dest_onnx_models = os.path.join(base_dir, "Gay_Nguoi_Mu", "firmware", "maixcam_app", "models", "char_ocr_v2.onnx")
    dest_pt_models = os.path.join(base_dir, "Gay_Nguoi_Mu", "firmware", "maixcam_app", "models", "char_ocr_v2.pt")

    shutil.copy2(onnx_file, dest_onnx_root)
    shutil.copy2(onnx_file, dest_onnx_models)
    shutil.copy2(trained_best_pt, dest_pt_models)

    # 4. Tao file MUD tuong ung
    labels_str = "0, 1, 2, 3, 4, 5, 6, 7, 8, 9, a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z"
    mud_content = f"""[basic]
type = cvimodel
model = char_ocr_v2.cvimodel

[extra]
model_type = {arch_name}
type = detector
input_type = rgb
labels = {labels_str}
mean = 0, 0, 0
scale = 0.00392156862745098, 0.00392156862745098, 0.00392156862745098
"""
    mud_path = os.path.join(base_dir, "Gay_Nguoi_Mu", "firmware", "maixcam_app", "models", "char_ocr_v2.mud")
    with open(mud_path, "w", encoding="utf-8") as f:
        f.write(mud_content)

    print(f" -> Da luu ONNX: {dest_onnx_root}")
    print(f" -> Da luu MUD : {mud_path}")
    print("\n" + "=" * 70)
    print("HOAN TAT! HUONG DAN CONVERT TREN MAIXHUB:")
    print("1. Truy cap https://maixhub.com/model/convert")
    print("2. Chon phan cung: 'MaixCAM' (Sophgo SG2002)")
    print(f"3. Upload file: {dest_onnx_root}")
    if arch_name == "yolov5":
        print("4. Chon loai model: 'YOLOv5u Detect' hoac 'YOLOv5' (Input: 320x320)")
    else:
        print("4. Chon loai model: 'YOLOv8' (Input: 320x320)")
    print("5. Calibration: Upload Gay_Nguoi_Mu/calibration_images.zip")
    print("6. Convert -> Tai zip -> Doi ten file .cvimodel thanh 'char_ocr.cvimodel'")
    print("7. Chep vao Gay_Nguoi_Mu/firmware/maixcam_app/models/")
    print("=" * 70)
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--arch", choices=["yolov5", "yolov8"], default="yolov5", help="Chon kien truc model (yolov5 hoac yolov8)")
    parser.add_argument("--epochs", type=int, default=15, help="So epoch huan luyen")
    parser.add_argument("--batch", type=int, default=16, help="Kich thuoc batch")
    args = parser.parse_args()
    train_char(model_type=args.arch, epochs=args.epochs, batch=args.batch)
