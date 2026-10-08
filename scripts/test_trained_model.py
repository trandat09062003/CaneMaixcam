#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script kiem tra danh gia model moi (vnd_money_v2) tren tap validation
va tren hinh anh mau thuc te.
"""

import os
import sys
import glob

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    weights_path = os.path.join(base_dir, "Gay_Nguoi_Mu", "firmware", "maixcam_app", "models", "vnd_money_v2.pt")
    onnx_path = os.path.join(base_dir, "Gay_Nguoi_Mu", "vnd_money_v2.onnx")

    print("=" * 70)
    print("KIEM TRA VA DANH GIA MO HINH NHAN DIEN TIEN VND_MONEY_V2")
    print("=" * 70)

    from ultralytics import YOLO

    target_model = None
    if os.path.exists(weights_path):
        print(f"[INFO] Su dung weights PyTorch: {weights_path}")
        target_model = YOLO(weights_path)
    elif os.path.exists(onnx_path):
        print(f"[INFO] Su dung model ONNX: {onnx_path}")
        target_model = YOLO(onnx_path)
    else:
        print("[LOI] Chua tim thay weights vnd_money_v2.pt hoac vnd_money_v2.onnx!")
        return

    print(f"Danh sach cac class mo hinh ho tro ({len(target_model.names)}):")
    for k, v in target_model.names.items():
        print(f"  ID {k}: {v} VND")

    # Kiem tra tren 1 anh ngau nhien moi menh gia tu tap val
    val_dir = os.path.join(base_dir, "dataset_money_yolo", "images", "val")
    classes = ['10000', '20000', '50000', '100000', '200000', '500000']

    print("\n[TEST THUC TE TREN TAP VALIDATION]")
    print(f"{'MENH GIA GOC':15s} | {'DU DOAN':15s} | {'DO TIN CAY':12s} | {'KET QUA':10s}")
    print("-" * 60)

    total_correct = 0
    total_tested = 0

    for cls in classes:
        sample_imgs = glob.glob(os.path.join(val_dir, f"{cls}_*.jpg"))
        for img_p in sample_imgs[:3]:  # Test 3 anh moi class
            total_tested += 1
            res = target_model.predict(img_p, conf=0.25, verbose=False)
            pred_label = "None"
            conf_str = "0%"
            is_match = False

            if len(res[0].boxes) > 0:
                best_box = max(res[0].boxes, key=lambda b: float(b.conf[0]))
                cls_id = int(best_box.cls[0])
                pred_label = target_model.names.get(cls_id, str(cls_id))
                conf = float(best_box.conf[0])
                conf_str = f"{conf*100:.1f}%"
                if pred_label == cls:
                    is_match = True
                    total_correct += 1

            status = "DUNG [OK]" if is_match else "SAI"
            print(f"{cls:15s} | {pred_label:15s} | {conf_str:12s} | {status:10s}")

    acc = (total_correct / total_tested * 100) if total_tested > 0 else 0
    print("-" * 60)
    print(f"Tong so mau kiem tra: {total_tested} | Chinh xac: {total_correct}/{total_tested} ({acc:.1f}%)")
    print("=" * 70)

if __name__ == "__main__":
    main()
