#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chuẩn bị dataset tiền Polymer (10k, 20k, 50k, 100k, 200k, 500k) cho YOLO:
- Lọc bỏ file rỗng / file hỏng
- Tự động gán nhãn bounding box (kết hợp pre-trained ONNX + contour + center box)
- Phân chia train/val (85/15)
- Xuất file cấu hình YAML chuẩn Ultralytics YOLO
"""

import os
import glob
import shutil
import random
import cv2
import numpy as np

CLASSES = ['10000', '20000', '50000', '100000', '200000', '500000']
CLASS_MAP = {c: i for i, c in enumerate(CLASSES)}

def is_valid_image(path):
    """Kiểm tra file ảnh có hợp lệ, không bị lỗi và kích thước > 1KB"""
    try:
        if not os.path.exists(path) or os.path.getsize(path) < 1024:
            return False
        with open(path, 'rb') as f:
            header = f.read(16)
            if not header.startswith(b'\xff\xd8'):  # JPEG SOI marker
                return False
        img = cv2.imread(path)
        return img is not None and img.shape[0] > 50 and img.shape[1] > 50
    except Exception:
        return False

def get_bounding_box(img, img_path, detector=None):
    """
    Xác định bounding box của tờ tiền:
    1. Pre-trained ONNX detector
    2. Contour detection
    3. Center box fallback
    Trả về [x_center, y_center, w, h] dạng chuẩn hóa (0.0 - 1.0)
    """
    h, w = img.shape[:2]

    # 1. Thử detector cũ nếu có
    if detector is not None:
        try:
            res = detector.predict(img_path, conf=0.10, verbose=False)
            if len(res[0].boxes) > 0:
                best = max(res[0].boxes, key=lambda b: float(b.conf[0]))
                xywhn = best.xywhn[0].tolist()
                cx, cy, bw, bh = xywhn
                # Kiểm tra box hợp lý
                if bw >= 0.15 and bh >= 0.15 and cx > 0.05 and cx < 0.95 and cy > 0.05 and cy < 0.95:
                    return [round(cx, 4), round(cy, 4), round(bw, 4), round(bh, 4)], "onnx"
        except Exception:
            pass

    # 2. Thử contour tiền dựa trên độ bão hòa màu và biên
    try:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        # Tờ tiền thường có màu bão hòa hơn background tường/bàn xám
        sat = hsv[:, :, 1]
        _, thresh = cv2.threshold(sat, 30, 255, cv2.THRESH_BINARY)
        # Morphology làm liền khối
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        cnts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_cnts = [c for c in cnts if cv2.contourArea(c) > (w * h * 0.12)]
        if valid_cnts:
            c = max(valid_cnts, key=cv2.contourArea)
            bx, by, bw, bh = cv2.boundingRect(c)
            cx = (bx + bw / 2.0) / w
            cy = (by + bh / 2.0) / h
            return [round(cx, 4), round(cy, 4), round(bw / w, 4), round(bh / h, 4)], "contour"
    except Exception:
        pass

    # 3. Fallback: Khung trung tâm bao trọn vị trí cầm tiền
    return [0.5, 0.52, 0.65, 0.85], "center_fallback"

def build_dataset(src_dir, output_dir, val_ratio=0.15, random_seed=42):
    random.seed(random_seed)
    os.makedirs(os.path.join(output_dir, "images", "train"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "images", "val"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "labels", "train"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "labels", "val"), exist_ok=True)

    # Thử nạp pre-trained ONNX detector để hỗ trợ gán nhãn
    detector = None
    try:
        from ultralytics import YOLO
        onnx_model_path = os.path.abspath("Gay_Nguoi_Mu/best.onnx")
        if os.path.exists(onnx_model_path):
            detector = YOLO(onnx_model_path)
            print(f"[INFO] Da nap pre-trained detector: {onnx_model_path}")
    except Exception as e:
        print(f"[WARN] Khong the nap pre-trained detector ({e}), su dung contour + center fallback.")

    stats = {"train": {c: 0 for c in CLASSES}, "val": {c: 0 for c in CLASSES}}
    method_stats = {"onnx": 0, "contour": 0, "center_fallback": 0}

    print("\n[TIEN TRINH] Dang quet va chuan hoa du lieu tu:", src_dir)

    for cls_name in CLASSES:
        cls_dir = os.path.join(src_dir, cls_name)
        if not os.path.exists(cls_dir):
            print(f"[CANH BAO] Khong tim thay thu muc {cls_dir}")
            continue

        raw_files = []
        for root, _, files in os.walk(cls_dir):
            for f in files:
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    raw_files.append(os.path.join(root, f))

        # Lọc ảnh hợp lệ
        valid_files = [f for f in raw_files if is_valid_image(f)]
        print(f" -> Menh gia {cls_name:6s}: {len(valid_files)}/{len(raw_files)} anh hop le (loai {len(raw_files) - len(valid_files)} loi)")

        # Phân chia train/val
        random.shuffle(valid_files)
        val_count = max(1, int(len(valid_files) * val_ratio))
        val_files = valid_files[:val_count]
        train_files = valid_files[val_count:]

        cls_id = CLASS_MAP[cls_name]

        for split, flist in [("train", train_files), ("val", val_files)]:
            for src_path in flist:
                base_name = f"{cls_name}_{os.path.basename(src_path)}"
                dest_img = os.path.join(output_dir, "images", split, base_name)
                dest_lbl = os.path.join(output_dir, "labels", split, os.path.splitext(base_name)[0] + ".txt")

                # Copy ảnh
                shutil.copy2(src_path, dest_img)

                # Đọc ảnh để gán nhãn box
                img = cv2.imread(dest_img)
                box, method = get_bounding_box(img, dest_img, detector=detector)
                method_stats[method] += 1

                # Ghi nhãn YOLO: class_id cx cy w h
                with open(dest_lbl, "w", encoding="utf-8") as lf:
                    lf.write(f"{cls_id} {box[0]:.4f} {box[1]:.4f} {box[2]:.4f} {box[3]:.4f}\n")

                stats[split][cls_name] += 1

    # Tạo file money.yaml
    yaml_path = os.path.join(output_dir, "money.yaml")
    abs_output = os.path.abspath(output_dir).replace("\\", "/")
    yaml_content = f"""# Cau hinh Dataset Nhan Dien Menh Gia Tien Polymer VND
path: {abs_output}
train: images/train
val: images/val

names:
"""
    for i, c in enumerate(CLASSES):
        yaml_content += f"  {i}: '{c}'\n"

    with open(yaml_path, "w", encoding="utf-8") as yf:
        yf.write(yaml_content)

    print("\n" + "=" * 60)
    print("KET QUA CHUAN BI DATASET:")
    print("=" * 60)
    total_train = sum(stats["train"].values())
    total_val = sum(stats["val"].values())
    print(f"Tong so anh Train: {total_train}")
    print(f"Tong so anh Val  : {total_val}")
    print(f"Phuong phap gan nhan:")
    print(f" - ONNX Detector: {method_stats['onnx']}")
    print(f" - Contour CV   : {method_stats['contour']}")
    print(f" - Center Box   : {method_stats['center_fallback']}")
    print(f"File cau hinh: {yaml_path}")
    print("=" * 60)
    return yaml_path

if __name__ == "__main__":
    src = r"C:\Users\Public\Documents\Altium\08052026\gay_nguoi_mu_maixcam\dataset_money"
    out = r"C:\Users\Public\Documents\Altium\08052026\gay_nguoi_mu_maixcam\dataset_money_yolo"
    build_dataset(src, out)
