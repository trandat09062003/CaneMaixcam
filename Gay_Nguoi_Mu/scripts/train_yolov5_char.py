#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SCRIPT HUẤN LUYỆN YOLOV5 CHO 36 KÝ TỰ (0-9, A-Z) & XUẤT ONNX CHO MAIXCAM
================================================================================
CÁC BƯỚC THỰC HIỆN:
1. Tự động sinh dữ liệu ký tự tổng hợp (nếu chưa có).
2. Tải pre-trained model yolov5nu.pt của Ultralytics.
3. Huấn luyện 30 epochs ở độ phân giải 320x320 (chuẩn Sipeed MaixCAM).
4. Xuất file best.onnx (opset 11) chuẩn bị nạp lên MaixHub.
================================================================================
"""

import os
import sys

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_dir = os.path.join(base_dir, "..", "char_dataset")
    yaml_file = os.path.join(dataset_dir, "chars.yaml")

    # 1. Kiểm tra hoặc sinh dữ liệu
    if not os.path.exists(yaml_file):
        print("[1/3] Chua co du lieu, tien hanh sinh dataset ky tu...")
        from generate_char_dataset import create_dataset
        create_dataset(output_dir=dataset_dir, num_train=1000, num_val=200)
    else:
        print(f"[1/3] Da tim thay file cau hinh: {yaml_file}")

    # 2. Huấn luyện với Ultralytics
    print("\n[2/3] Bat dau huan luyen YOLOv5n...")
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[LOI] Vui long cai dat ultralytics: pip install ultralytics")
        return

    # Sử dụng YOLOv5 Nano (nhẹ nhất, tối ưu nhất cho NPU 1 TOPS)
    model = YOLO("yolov5nu.pt")

    results = model.train(
        data=yaml_file,
        epochs=30,
        imgsz=320,
        batch=16,
        workers=2,
        project="runs_chars",
        name="yolov5_char36"
    )

    # 3. Xuất ra ONNX
    print("\n[3/3] Xuat model sang dinh dang ONNX cho MaixHub...")
    best_pt = os.path.join("runs_chars", "yolov5_char36", "weights", "best.pt")
    if os.path.exists(best_pt):
        trained_model = YOLO(best_pt)
        onnx_file = trained_model.export(format="onnx", imgsz=320, opset=11)
        print("=" * 60)
        print(f" [THANH CONG] File ONNX da duoc luu tai:\n   -> {onnx_file}")
        print("=" * 60)
        print("\nHUONG DAN CONVERT SANG MAIXCAM CVIMODEL TRÊN MAIXHUB:")
        print("1. Truy cap https://maixhub.com/model/convert")
        print("2. Chon phan cung: 'MaixCAM' (Chip Sophgo SG2002 / CV181x)")
        print("3. Upload file best.onnx vua tao")
        print("4. Chon loai model: YOLOv5 (Resolution: 320x320)")
        print("5. Tai file zip ve, doi ten file .cvimodel thanh 'char_ocr.cvimodel'")
        print("6. Copy vao thu muc Gay_Nguoi_Mu/firmware/maixcam_app/models/")
        print("=" * 60)
    else:
        print(f"[CANH BAO] Khong tim thay {best_pt}")

if __name__ == "__main__":
    main()
