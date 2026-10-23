#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script đóng gói Dataset (Tiền VND & Ký tự 36 OCR) thành file .ZIP để tải lên Google Colab
Đồng thời tự động điều chỉnh file .yaml sang chuẩn đường dẫn Google Colab (/content/...)
"""

import os
import sys
import zipfile
import shutil

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def pack_folder(src_folder, zip_filename, yaml_name, colab_dest_dir, class_list):
    print("=" * 65)
    print(f"[*] Dang chuan bi dong goi: {os.path.basename(src_folder)}")
    
    if not os.path.exists(src_folder):
        print(f"[LOI] Khong tim thay thu muc: {src_folder}")
        return False
        
    # Tạo nội dung YAML chuẩn hóa cho Colab (đường dẫn /content/...)
    yaml_lines = [
        f"# YAML Cau hinh cho Google Colab - MaixCAM",
        f"path: {colab_dest_dir}",
        f"train: images/train",
        f"val: images/val",
        "",
        "names:"
    ]
    for idx, cls in enumerate(class_list):
        yaml_lines.append(f"  {idx}: '{cls}'")
    colab_yaml_content = "\n".join(yaml_lines) + "\n"
    
    # Ghi tạm file YAML Colab
    temp_yaml_path = os.path.join(src_folder, yaml_name)
    with open(temp_yaml_path, "w", encoding="utf-8") as f:
        f.write(colab_yaml_content)
        
    zip_path = os.path.join(BASE_DIR, zip_filename)
    print(f"[*] Dang tao file nén: {zip_path} ...")
    
    img_count = 0
    lbl_count = 0
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(src_folder):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, BASE_DIR)
                zipf.write(file_path, arcname=rel_path)
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    img_count += 1
                elif file.lower().endswith('.txt') and 'labels' in rel_path:
                    lbl_count += 1
                    
    zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"[+] Thanh cong! {zip_filename}:")
    print(f"    - Dung luong: {zip_size_mb:.2f} MB")
    print(f"    - So anh: {img_count}")
    print(f"    - So nhan: {lbl_count}")
    return True

def main():
    print("=================================================================")
    print("        DONG GOI DATASET SANG FILE ZIP CHO GOOGLE COLAB          ")
    print("=================================================================")
    
    # 1. Dataset Tiền VND
    money_classes = ['10000', '20000', '50000', '100000', '200000', '500000']
    pack_folder(
        src_folder=os.path.join(BASE_DIR, "dataset_money_yolo"),
        zip_filename="dataset_money_yolo.zip",
        yaml_name="money.yaml",
        colab_dest_dir="/content/dataset_money_yolo",
        class_list=money_classes
    )
    
    # 2. Dataset Ký tự 36 (0-9, A-Z)
    char_classes = [
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
        'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j',
        'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
        'u', 'v', 'w', 'x', 'y', 'z'
    ]
    pack_folder(
        src_folder=os.path.join(BASE_DIR, "dataset_chars_yolo"),
        zip_filename="dataset_chars_yolo.zip",
        yaml_name="chars.yaml",
        colab_dest_dir="/content/dataset_chars_yolo",
        class_list=char_classes
    )
    
    print("=" * 65)
    print("[*] Da hoan tat dong goi!")
    print(f"File 1: {os.path.join(BASE_DIR, 'dataset_money_yolo.zip')}")
    print(f"File 2: {os.path.join(BASE_DIR, 'dataset_chars_yolo.zip')}")
    print("Ban chi can upload file .zip nay truc tiep len Google Colab hoac Google Drive.")
    print("=================================================================")

if __name__ == "__main__":
    main()
