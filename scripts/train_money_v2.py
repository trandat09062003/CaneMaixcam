#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SCRIPT HUAN LUYEN MODEL AI NHAN DIEN MENH GIA TIEN POLYMER VND
PHIEN BAN MOI: vnd_money_v2 (KHONG TRUNG / KHONG GHI DE MODEL CU)
================================================================================
Quy trinh thuc hien tu dong:
1. Kiem tra tap du lieu dataset_money_yolo/money.yaml.
2. Huan luyen Ultralytics YOLOv8n (imgsz=320, chuan Sipeed MaixCAM NPU SG2002).
3. Luu weights rieng biet: runs/detect/runs_money/yolov8_money_v2/
4. Xuat file ONNX: Gay_Nguoi_Mu/vnd_money_v2.onnx (opset 11).
5. Tao cau hinh MaixCAM: Gay_Nguoi_Mu/firmware/maixcam_app/models/vnd_money_v2.mud
================================================================================
"""

import os
import sys
import shutil

# Dam bao terminal Windows khong bi loi charmap unicode
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    yaml_file = os.path.join(base_dir, "dataset_money_yolo", "money.yaml")

    print("=" * 70)
    print("  BAT DAU HUAN LUYEN MODEL NHAN DIEN TIEN VND (MODEL V2 MOI)")
    print("=" * 70)

    # 1. Kiem tra dataset
    if not os.path.exists(yaml_file):
        print(f"[LOI] Chua tim thay {yaml_file}!")
        print("Vui long chay: python scripts/prepare_money_dataset.py truoc.")
        return False

    print(f"[1/4] File cau hinh dataset: {yaml_file}")

    # 2. Huan luyen voi Ultralytics YOLOv5 (yolov5nu.pt de dong nhat 100% voi MaixCAM NPU SG2002)
    print("\n[2/4] Khoi dong qua trinh huan luyen YOLOv5n tren dataset tien...")
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[LOI] Chua cai dat ultralytics! Chay: pip install ultralytics")
        return False

    # Base pretrained model YOLOv5n (giong het kien truc cua best.onnx va best_char36.onnx)
    base_pt = os.path.join(base_dir, "yolov5nu.pt")
    if not os.path.exists(base_pt):
        base_pt = "yolov5nu.pt"

    model = YOLO(base_pt)

    # Huan luyen 15 epochs voi batch=32 toi uu toc do CPU
    project_dir = os.path.join(base_dir, "runs", "detect", "runs_money")
    run_name = "yolov5_money_v2"

    results = model.train(
        data=yaml_file,
        epochs=15,
        imgsz=320,
        batch=32,
        device="cpu",
        project=project_dir,
        name=run_name,
        exist_ok=True,
        verbose=True
    )

    trained_best_pt = os.path.join(project_dir, run_name, "weights", "best.pt")
    if not os.path.exists(trained_best_pt):
        print(f"[LOI] Khong tim thay weights sau khi train tai: {trained_best_pt}")
        return False

    print(f"\n[THANH CONG] Huan luyen hoan tat! Best weights: {trained_best_pt}")

    # 3. Xuat model ra ONNX (opset 11, chuan bi cho MaixHub SG2002 TPU-MLIR)
    print("\n[3/4] Xuat sang dinh dang ONNX (opset 11, imgsz 320x320, YOLOv5n)...")
    trained_model = YOLO(trained_best_pt)
    onnx_exported = trained_model.export(
        format="onnx",
        imgsz=320,
        opset=11,
        simplify=True
    )

    # Sao luu ONNX sang cac vi tri chuan voi ten moi vnd_money_v2.onnx
    dest_onnx_root = os.path.join(base_dir, "Gay_Nguoi_Mu", "vnd_money_v2.onnx")
    dest_onnx_app = os.path.join(base_dir, "Gay_Nguoi_Mu", "firmware", "maixcam_app", "models", "vnd_money_v2.onnx")
    dest_pt_app = os.path.join(base_dir, "Gay_Nguoi_Mu", "firmware", "maixcam_app", "models", "vnd_money_v2.pt")

    os.makedirs(os.path.dirname(dest_onnx_app), exist_ok=True)
    shutil.copy2(onnx_exported, dest_onnx_root)
    shutil.copy2(onnx_exported, dest_onnx_app)
    shutil.copy2(trained_best_pt, dest_pt_app)

    print(f" -> Da luu ONNX tai: {dest_onnx_root}")
    print(f" -> Da luu ONNX tai: {dest_onnx_app}")
    print(f" -> Da luu PyTorch PT tai: {dest_pt_app}")

    # 4. Sinh file cau hinh .mud cho MaixPy (model_type = yolov5)
    print("\n[4/4] Tao file cau hinh vnd_money_v2.mud cho MaixCAM (model_type=yolov5)...")
    mud_content = """[basic]
type = cvimodel
model = vnd_money_v2.cvimodel

[extra]
model_type = yolov5
type = detector
input_type = rgb
labels = 10000, 20000, 50000, 100000, 200000, 500000
mean = 0, 0, 0
scale = 0.00392156862745098, 0.00392156862745098, 0.00392156862745098
"""
    mud_path = os.path.join(base_dir, "Gay_Nguoi_Mu", "firmware", "maixcam_app", "models", "vnd_money_v2.mud")
    with open(mud_path, "w", encoding="utf-8") as f:
        f.write(mud_content)

    print(f" -> Da tao file MUD tai: {mud_path}")

    print("\n" + "=" * 70)
    print("HOAN TAT TOAN BO TIEN TRINH!")
    print("=" * 70)
    print("Cac file model moi da tao thanh cong (KHONG trung voi model cu):")
    print(f"1. Weights PyTorch : {dest_pt_app}")
    print(f"2. File ONNX       : {dest_onnx_root}")
    print(f"3. File MUD MaixCAM: {mud_path}")
    print("\nHUONG DAN CONVERT SANG FILE .CVIMODEL CHO PHAN CUNG SIPEED MAIXCAM:")
    print("1. Truy cap trang web MaixHub: https://maixhub.com/model/convert")
    print("2. Chon phan cung: 'MaixCAM' (Chip Sophgo SG2002 / CV181x)")
    print("3. Tai len file ONNX: " + dest_onnx_root)
    print("4. Chon loai model: YOLOv5 (Resolution: 320x320)  <-- DONG NHAT VOI MODEL CHU")
    print("5. Nhan Convert, tai file zip ve may va giai nen.")
    print("6. Doi ten file .cvimodel thanh: 'vnd_money_v2.cvimodel'")
    print("7. Chep file vao thu muc: Gay_Nguoi_Mu/firmware/maixcam_app/models/")
    print("=" * 70)
    return True

if __name__ == "__main__":
    main()
