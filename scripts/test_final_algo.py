import cv2
import numpy as np

VND_PROFILES = {
    "500000": {
        "name": "Nam tram nghin dong",
        "sound": "nam_tram_nghin_dong.mp3",
        "h_min": 82, "h_max": 102,
        "s_min": 32, "s_max": 255,
        "v_min": 35, "v_max": 245,
        "is_polymer": True,
        "pixel_check": lambda r, g, b: (b >= 0.88 * r) and (g >= 0.88 * r)
    },
    "200000": {
        "name": "Hai tram nghin dong",
        "sound": "hai_tram_nghin_dong.mp3",
        "h_min": 0,   "h_max": 15,
        "h_min2": 166, "h_max2": 180,
        "s_min": 42,  "s_max": 255,
        "v_min": 40,  "v_max": 245,
        "is_polymer": True,
        "pixel_check": lambda r, g, b: (r >= 1.12 * g) and (r >= 1.12 * b)
    },
    "100000": {
        "name": "Mot tram nghin dong",
        "sound": "mot_tram_nghin_dong.mp3",
        "h_min": 38, "h_max": 80,
        "s_min": 32, "s_max": 255,
        "v_min": 35, "v_max": 240,
        "is_polymer": True,
        "pixel_check": lambda r, g, b: (g >= 1.02 * r) and (g >= 1.02 * b)
    },
    "50000": {
        "name": "Nam muoi nghin dong",
        "sound": "nam_muoi_nghin_dong.mp3",
        "h_min": 135, "h_max": 166,
        "s_min": 32,  "s_max": 255,
        "v_min": 40,  "v_max": 250,
        "is_polymer": True,
        "pixel_check": lambda r, g, b: (r >= 1.02 * g) and (b >= 0.85 * g)
    },
    "20000": {
        "name": "Hai muoi nghin dong",
        "sound": "hai_muoi_nghin_dong.mp3",
        "h_min": 103, "h_max": 132,
        "s_min": 42,  "s_max": 255,
        "v_min": 40,  "v_max": 250,
        "is_polymer": True,
        "pixel_check": lambda r, g, b: (b >= 1.05 * r)
    },
    "10000": {
        "name": "Muoi nghin dong",
        "sound": "muoi_nghin_dong.mp3",
        "h_min": 16, "h_max": 35,
        "s_min": 45, "s_max": 255,
        "v_min": 40, "v_max": 240,
        "is_polymer": True,
        "pixel_check": lambda r, g, b: (r >= 1.05 * b) and (g >= 0.95 * b)
    },
    "5000": {
        "name": "Nam nghin dong",
        "sound": "nam_nghin_dong.mp3",
        "h_min": 96, "h_max": 126,
        "s_min": 20, "s_max": 75,
        "v_min": 45, "v_max": 220,
        "is_polymer": False,
        "pixel_check": lambda r, g, b: (b >= 0.95 * r)
    },
    "2000": {
        "name": "Hai nghin dong",
        "sound": "hai_nghin_dong.mp3",
        "h_min": 12, "h_max": 32,
        "s_min": 20, "s_max": 65,
        "v_min": 45, "v_max": 220,
        "is_polymer": False,
        "pixel_check": lambda r, g, b: (r >= 1.05 * b)
    },
    "1000": {
        "name": "Mot nghin dong",
        "sound": "mot_nghin_dong.mp3",
        "h_min": 70, "h_max": 105,
        "s_min": 10, "s_max": 55,
        "v_min": 45, "v_max": 220,
        "is_polymer": False,
        "pixel_check": lambda r, g, b: True
    }
}

KERNEL_MORPH_5 = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

def detect_banknote_cv_fallback(cv_img):
    try:
        h_img, w_img = cv_img.shape[:2]
        
        # Vùng tương tác trung tâm (75% rộng, 75% cao)
        margin_x = int(w_img * 0.125)
        margin_y = int(h_img * 0.125)
        roi_bgr = cv_img[margin_y:h_img - margin_y, margin_x:w_img - margin_x]
        roi_hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
        roi_gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)

        candidates = []

        for label, prof in VND_PROFILES.items():
            if "h_min2" in prof:
                m1 = cv2.inRange(roi_hsv, np.array([prof["h_min"], prof.get("s_min", 40), prof.get("v_min", 40)]),
                                          np.array([prof["h_max"], prof.get("s_max", 255), prof.get("v_max", 255)]))
                m2 = cv2.inRange(roi_hsv, np.array([prof["h_min2"], prof.get("s_min", 40), prof.get("v_min", 40)]),
                                          np.array([prof["h_max2"], prof.get("s_max", 255), prof.get("v_max", 255)]))
                mask = cv2.bitwise_or(m1, m2)
            else:
                mask = cv2.inRange(roi_hsv, np.array([prof["h_min"], prof.get("s_min", 40), prof.get("v_min", 40)]),
                                         np.array([prof["h_max"], prof.get("s_max", 255), prof.get("v_max", 255)]))

            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, KERNEL_MORPH_5)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                continue

            c = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(c)

            if area < 1000:
                continue

            bx, by, bw, bh = cv2.boundingRect(c)
            cluster_mask = mask[by:by+bh, bx:bx+bw]
            matched_pixels = cv2.countNonZero(cluster_mask)

            if matched_pixels < 800:
                continue

            density = float(matched_pixels) / float(bw * bh)
            if density < 0.14:
                continue

            # Kiểm tra độ sắc nét/hoa văn chi tiết (Loại bỏ da tay, tường phẳng, bàn trơn)
            roi_cluster_gray = roi_gray[by:by+bh, bx:bx+bw]
            lap_var = cv2.Laplacian(roi_cluster_gray, cv2.CV_64F).var()
            if lap_var < 35.0:
                continue

            roi_cluster_bgr = roi_bgr[by:by+bh, bx:bx+bw]
            mean_b = float(np.mean(roi_cluster_bgr[:, :, 0][cluster_mask > 0]))
            mean_g = float(np.mean(roi_cluster_bgr[:, :, 1][cluster_mask > 0]))
            mean_r = float(np.mean(roi_cluster_bgr[:, :, 2][cluster_mask > 0]))

            pixel_check = prof.get("pixel_check", None)
            if pixel_check and not pixel_check(mean_r, mean_g, mean_b):
                continue

            ratio = float(bw) / float(bh) if bw > bh else float(bh) / float(bw)
            shape_weight = 1.25 if (1.2 <= ratio <= 3.4) else 1.0

            is_poly = prof.get("is_polymer", True)
            poly_weight = 1.3 if is_poly else 0.95

            score = float(matched_pixels) * density * shape_weight * poly_weight

            candidates.append({
                "label": label,
                "name": prof["name"],
                "sound": prof.get("sound", ""),
                "box": (bx + margin_x, by + margin_y, bw, bh),
                "score": score,
                "matched_px": matched_pixels,
                "source": "SPECTRUM_CV"
            })

        if not candidates:
            return None

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[0]
    except Exception as e:
        return None

if __name__ == "__main__":
    img = cv2.imread('scripts/sample_note.jpg')
    res = detect_banknote_cv_fallback(img)
    print("Banknote:", res['label'] if res else "None")

    skin = np.ones((480, 640, 3), dtype=np.uint8)
    skin[:, :] = (140, 160, 200)
    print("Skin hand:", detect_banknote_cv_fallback(skin))
