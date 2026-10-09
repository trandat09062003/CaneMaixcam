#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chuẩn bị dataset 36 ký tự (0-9, A-Z) từ ảnh thực tế trong dataset_chars/
- Tự động phát hiện nét ký tự và gán nhãn Bounding Box chuẩn YOLO
- Phân chia train/val (85/15)
- Xuất file cấu hình YAML chuẩn Ultralytics YOLO
"""

import os
import sys
import glob
import shutil
import random
import cv2
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

CLASSES = [
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j',
    'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
    'u', 'v', 'w', 'x', 'y', 'z'
]
CLASS_MAP = {c: i for i, c in enumerate(CLASSES)}
for c in 'abcdefghijklmnopqrstuvwxyz':
    CLASS_MAP[c.upper()] = CLASS_MAP[c]

def extract_char_box(img):
    """
    Tự động xác định bounding box của ký tự:
    Phát hiện vùng nét chữ tương phản cao trong khu vực trung tâm màn hình/giấy.
    Trả về [cx, cy, w, h] dạng chuẩn hóa (0.0 - 1.0).
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # Lấy ngưỡng nét tối trên nền sáng (hoặc ngược lại)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 10)

    cnts, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []

    for c in cnts:
        bx, by, bw, bh = cv2.boundingRect(c)
        cx = (bx + bw / 2.0) / w
        cy = (by + bh / 2.0) / h
        norm_w = bw / w
        norm_h = bh / h

        # Ký tự nằm trong vùng trung tâm màn hình, kích thước vừa phải
        if 0.20 < cx < 0.85 and 0.20 < cy < 0.85 and 0.05 < norm_w < 0.65 and 0.05 < norm_h < 0.65:
            # Ưu tiên contour gần tâm màn hình điện thoại (thường lệch nhẹ tâm ảnh)
            dist_to_center = ((cx - 0.55)**2 + (cy - 0.55)**2)**0.5
            area = bw * bh
            candidates.append((dist_to_center, area, (cx, cy, norm_w, norm_h)))

    if candidates:
        # Chọn contour có diện tích hợp lý và gần tâm nhất
        candidates.sort(key=lambda item: (item[0], -item[1]))
        best_box = candidates[0][2]
        # Thêm padding nhẹ xung quanh chữ (5%)
        cx, cy, bw, bh = best_box
        bw = min(1.0, bw * 1.15)
        bh = min(1.0, bh * 1.15)
        return [round(cx, 4), round(cy, 4), round(bw, 4), round(bh, 4)], "contour"

    # Fallback vị trí trung tâm màn hình điện thoại
    return [0.55, 0.55, 0.25, 0.28], "center_fallback"

def build_char_dataset(src_dir, output_dir, val_ratio=0.15, random_seed=42):
    random.seed(random_seed)
    os.makedirs(os.path.join(output_dir, "images", "train"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "images", "val"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "labels", "train"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "labels", "val"), exist_ok=True)

    print("=" * 60)
    print("CHUAN BI DU LIEU 36 KY TU TU:", src_dir)
    print("=" * 60)

    method_stats = {"contour": 0, "center_fallback": 0}
    total_imgs = 0

    for folder_name in sorted(os.listdir(src_dir)):
        folder_path = os.path.join(src_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue

        raw_files = [
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ]

        if not raw_files:
            continue

        cls_key = folder_name.lower()
        if cls_key not in CLASS_MAP:
            print(f"[WARN] Bo qua thu muc khong hop le: {folder_name}")
            continue

        cls_id = CLASS_MAP[cls_key]

        # Phân chia train/val
        random.shuffle(raw_files)
        val_count = max(1, int(len(raw_files) * val_ratio)) if len(raw_files) > 4 else 1
        val_files = raw_files[:val_count]
        train_files = raw_files[val_count:]

        for split, flist in [("train", train_files), ("val", val_files)]:
            for src_path in flist:
                base_name = f"char_{folder_name}_{os.path.basename(src_path)}"
                dest_img = os.path.join(output_dir, "images", split, base_name)
                dest_lbl = os.path.join(output_dir, "labels", split, os.path.splitext(base_name)[0] + ".txt")

                img = cv2.imread(src_path)
                if img is None:
                    continue

                shutil.copy2(src_path, dest_img)
                box, method = extract_char_box(img)
                method_stats[method] += 1

                with open(dest_lbl, "w", encoding="utf-8") as lf:
                    lf.write(f"{cls_id} {box[0]:.4f} {box[1]:.4f} {box[2]:.4f} {box[3]:.4f}\n")

                total_imgs += 1

    # Tạo file chars.yaml
    yaml_path = os.path.join(output_dir, "chars.yaml")
    abs_output = os.path.abspath(output_dir).replace("\\", "/")
    yaml_content = f"""# Cau hinh Dataset 36 Ky Tu (0-9, A-Z) cho Sipeed MaixCAM
path: {abs_output}
train: images/train
val: images/val

names:
"""
    for i, c in enumerate(CLASSES):
        yaml_content += f"  {i}: '{c}'\n"

    with open(yaml_path, "w", encoding="utf-8") as yf:
        yf.write(yaml_content)

    print("\nHOAN TAT CHUAN BI DATASET KY TU:")
    print(f" - Tong so anh: {total_imgs}")
    print(f" - Phat hien contour: {method_stats['contour']}")
    print(f" - Center fallback : {method_stats['center_fallback']}")
    print(f" - File cau hinh    : {yaml_path}")
    print("=" * 60)
    return yaml_path

if __name__ == "__main__":
    src = r"C:\Users\Public\Documents\Altium\08052026\gay_nguoi_mu_maixcam\dataset_chars"
    out = r"C:\Users\Public\Documents\Altium\08052026\gay_nguoi_mu_maixcam\dataset_chars_yolo"
    build_char_dataset(src, out)
