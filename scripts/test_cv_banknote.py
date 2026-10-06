import zipfile
import cv2
import numpy as np
import sys
import os

sys.path.append(os.path.abspath('Gay_Nguoi_Mu/firmware/maixcam_app'))
from main import detect_banknote_cv_fallback, VND_PROFILES

zip_path = 'Gay_Nguoi_Mu/calibration_images.zip'
with zipfile.ZipFile(zip_path, 'r') as z:
    names = z.namelist()
    detected_count = 0
    for name in names:
        data = z.read(name)
        arr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        cand = detect_banknote_cv_fallback(img)
        res = cand['label'] if cand else 'FAILED'
        score = f"{cand['score']:.2f}" if cand else "-"
        print(f"{name[:35]:35s} -> {res:10s} (score: {score})")
        if cand:
            detected_count += 1
    print(f"\nTotal Detected: {detected_count}/{len(names)} ({detected_count/len(names)*100:.1f}%)")
