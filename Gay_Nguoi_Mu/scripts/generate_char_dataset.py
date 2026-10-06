#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SCRIPT TỰ ĐỘNG SINH DỮ LIỆU & HUẤN LUYỆN YOLOV5 NHẬN DIỆN 36 KÝ TỰ (0-9, A-Z)
DÀNH CHO SIPEED MAIXCAM (SOPHGO SG2002 NPU 1 TOPS)
================================================================================
TÍNH NĂNG:
1. Sinh ảnh tổng hợp chứa các chữ cái in (A-Z) và số (0-9) ngẫu nhiên.
2. Tự động gán nhãn Bounding Box chuẩn YOLO (36 classes: 0..9 và a..z).
3. Đa dạng hóa: nhiều kiểu font (Arial, Tahoma, Verdana, Times, Consolas), màu sắc,
   nền vân, góc nghiêng, nhiễu sáng tối, mô phỏng camera thực tế.
4. Hỗ trợ xuất file dataset/chars.yaml và script huấn luyện YOLOv5n.
================================================================================
"""

import os
import sys
import random
import glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

CLASSES = [
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j',
    'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
    'u', 'v', 'w', 'x', 'y', 'z'
]

CHAR_TO_CLASS = {c: i for i, c in enumerate(CLASSES)}
for c in 'abcdefghijklmnopqrstuvwxyz':
    CHAR_TO_CLASS[c.upper()] = CHAR_TO_CLASS[c]

def get_font_paths():
    font_names = ['arial.ttf', 'tahoma.ttf', 'verdana.ttf', 'calibri.ttf', 'times.ttf', 'consola.ttf']
    windir = os.environ.get('WINDIR', 'C:\\Windows')
    fonts = []
    for fn in font_names:
        p = os.path.join(windir, 'Fonts', fn)
        if os.path.exists(p):
            fonts.append(p)
    return fonts or ['arial.ttf']

def random_background(width, height):
    bg_type = random.choice(['solid_light', 'solid_dark', 'gradient', 'noise', 'pattern'])
    if bg_type == 'solid_light':
        col = (random.randint(200, 255), random.randint(200, 255), random.randint(200, 255))
        return Image.new('RGB', (width, height), col), (random.randint(10, 80), random.randint(10, 80), random.randint(10, 80))
    elif bg_type == 'solid_dark':
        col = (random.randint(20, 60), random.randint(20, 60), random.randint(20, 60))
        return Image.new('RGB', (width, height), col), (random.randint(190, 255), random.randint(190, 255), random.randint(190, 255))
    elif bg_type == 'gradient':
        c1 = np.array([random.randint(180, 255), random.randint(180, 255), random.randint(180, 255)])
        c2 = np.array([random.randint(120, 200), random.randint(120, 200), random.randint(120, 200)])
        x = np.linspace(0, 1, width)
        y = np.linspace(0, 1, height)
        xx, yy = np.meshgrid(x, y)
        grad = np.dstack([xx * c1[i] + (1 - xx) * c2[i] for i in range(3)]).astype(np.uint8)
        return Image.fromarray(grad), (random.randint(10, 50), random.randint(10, 50), random.randint(10, 50))
    else:
        arr = np.random.randint(180, 240, (height, width, 3), dtype=np.uint8)
        return Image.fromarray(arr), (random.randint(0, 40), random.randint(0, 40), random.randint(0, 40))

def generate_sample(img_w=320, img_h=320, font_paths=None):
    if not font_paths:
        font_paths = get_font_paths()

    img, text_color = random_background(img_w, img_h)
    draw = ImageDraw.Draw(img)

    num_chars = random.randint(1, 6)
    chars = []
    for _ in range(num_chars):
        chars.append(random.choice(list(CHAR_TO_CLASS.keys())))

    font_path = random.choice(font_paths)
    font_size = random.randint(28, 60)
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        font = ImageFont.load_default()

    boxes = []
    # Vẽ các ký tự thành chuỗi ngang
    char_widths = []
    char_heights = []
    for ch in chars:
        bbox = font.getbbox(ch)
        char_widths.append(bbox[2] - bbox[0])
        char_heights.append(bbox[3] - bbox[1])

    spacing = random.randint(6, 18)
    total_w = sum(char_widths) + spacing * (num_chars - 1)
    max_h = max(char_heights) if char_heights else 30

    if total_w > img_w - 40:
        scale = (img_w - 40) / total_w
        font_size = max(18, int(font_size * scale))
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            font = ImageFont.load_default()
        char_widths = []
        char_heights = []
        for ch in chars:
            bbox = font.getbbox(ch)
            char_widths.append(bbox[2] - bbox[0])
            char_heights.append(bbox[3] - bbox[1])
        spacing = random.randint(4, 12)
        total_w = sum(char_widths) + spacing * (num_chars - 1)
        max_h = max(char_heights) if char_heights else 20

    start_x = random.randint(15, max(16, img_w - total_w - 15))
    start_y = random.randint(15, max(16, img_h - max_h - 25))

    cur_x = start_x
    for i, ch in enumerate(chars):
        cw = char_widths[i]
        ch_h = char_heights[i]
        # Dao động y ngẫu nhiên một chút
        char_y = start_y + random.randint(-3, 3)
        draw.text((cur_x, char_y), ch, fill=text_color, font=font)

        pad = 2
        x1 = max(0, cur_x - pad)
        y1 = max(0, char_y - pad)
        x2 = min(img_w - 1, cur_x + cw + pad)
        y2 = min(img_h - 1, char_y + ch_h + pad)

        cls_id = CHAR_TO_CLASS[ch]
        # YOLO format: cls_id, cx, cy, w, h (normalized)
        cx = ((x1 + x2) / 2.0) / img_w
        cy = ((y1 + y2) / 2.0) / img_h
        w_norm = (x2 - x1) / img_w
        h_norm = (y2 - y1) / img_h

        if w_norm > 0.02 and h_norm > 0.02:
            boxes.append((cls_id, cx, cy, w_norm, h_norm))

        cur_x += cw + spacing

    # Áp dụng một chút blur hoặc nhiễu nhẹ
    if random.random() < 0.25:
        img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.3, 0.8)))

    return img, boxes

def create_dataset(output_dir="char_dataset", num_train=1200, num_val=240):
    print(f"[DATASET] Tao thu muc tai: {output_dir}")
    os.makedirs(f"{output_dir}/images/train", exist_ok=True)
    os.makedirs(f"{output_dir}/images/val", exist_ok=True)
    os.makedirs(f"{output_dir}/labels/train", exist_ok=True)
    os.makedirs(f"{output_dir}/labels/val", exist_ok=True)

    font_paths = get_font_paths()
    print(f"[DATASET] Tim thay {len(font_paths)} font chu he thong: {font_paths}")

    # Sinh tập Train
    print(f"[DATASET] Dang sinh {num_train} anh train...")
    for i in range(num_train):
        img, boxes = generate_sample(320, 320, font_paths)
        img_p = f"{output_dir}/images/train/sample_{i:05d}.jpg"
        lbl_p = f"{output_dir}/labels/train/sample_{i:05d}.txt"
        img.save(img_p, quality=85)
        with open(lbl_p, "w") as f:
            for b in boxes:
                f.write(f"{b[0]} {b[1]:.6f} {b[2]:.6f} {b[3]:.6f} {b[4]:.6f}\n")

    # Sinh tập Val
    print(f"[DATASET] Dang sinh {num_val} anh val...")
    for i in range(num_val):
        img, boxes = generate_sample(320, 320, font_paths)
        img_p = f"{output_dir}/images/val/sample_{i:05d}.jpg"
        lbl_p = f"{output_dir}/labels/val/sample_{i:05d}.txt"
        img.save(img_p, quality=85)
        with open(lbl_p, "w") as f:
            for b in boxes:
                f.write(f"{b[0]} {b[1]:.6f} {b[2]:.6f} {b[3]:.6f} {b[4]:.6f}\n")

    # Tạo file chars.yaml cho Ultralytics YOLO
    abs_out = os.path.abspath(output_dir).replace('\\', '/')
    yaml_content = f"""path: {abs_out}
train: images/train
val: images/val

nc: 36
names: {CLASSES}
"""
    yaml_p = f"{output_dir}/chars.yaml"
    with open(yaml_p, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    print(f"\n[DATASET HOAN TAT] File cau hinh: {yaml_p}")
    print(f"Tong so anh train: {num_train}, anh val: {num_val}")
    print("\nLENH HUAN LUYEN YOLOV5:")
    print(f"  yolo task=detect mode=train model=yolov5nu.pt data={yaml_p} epochs=30 imgsz=320 batch=16")
    print("\nLENH XUAT ONNX DE UPLOAD MAIXHUB:")
    print("  yolo export model=runs/detect/train/weights/best.pt format=onnx imgsz=320 opset=11")

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "char_dataset")
    create_dataset(out, num_train=600, num_val=120)
