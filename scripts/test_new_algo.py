import zipfile
import cv2
import numpy as np

# Color definitions for Vietnamese Banknotes in OpenCV HSV (H: 0-180, S: 0-255, V: 0-255)
VND_SPECTRUM = {
    "500000": {
        "name": "Nam tram nghin dong",
        "h_min": 82, "h_max": 102,
        "s_min": 35, "s_max": 255,
        "v_min": 35, "v_max": 245,
        "is_polymer": True,
        # Check on matching pixels only
        "pixel_check": lambda r, g, b: (b > 0.92 * r) and (g > 0.90 * r)
    },
    "200000": {
        "name": "Hai tram nghin dong",
        "h_min": 0,   "h_max": 14,
        "h_min2": 168, "h_max2": 180,
        "s_min": 45,  "s_max": 255,
        "v_min": 40,  "v_max": 245,
        "is_polymer": True,
        "pixel_check": lambda r, g, b: (r > 1.15 * g) and (r > 1.15 * b)
    },
    "100000": {
        "name": "Mot tram nghin dong",
        "h_min": 38, "h_max": 80,
        "s_min": 35, "s_max": 255,
        "v_min": 35, "v_max": 240,
        "is_polymer": True,
        "pixel_check": lambda r, g, b: (g > 1.02 * r) and (g > 1.02 * b)
    },
    "50000": {
        "name": "Nam muoi nghin dong",
        "h_min": 136, "h_max": 167,
        "s_min": 35,  "s_max": 255,
        "v_min": 40,  "v_max": 250,
        "is_polymer": True,
        "pixel_check": lambda r, g, b: (r > 1.02 * g) and (b > 0.88 * g)
    },
    "20000": {
        "name": "Hai muoi nghin dong",
        "h_min": 103, "h_max": 132,
        "s_min": 45,  "s_max": 255,
        "v_min": 40,  "v_max": 250,
        "is_polymer": True,
        "pixel_check": lambda r, g, b: (b > 1.08 * r)
    },
    "10000": {
        "name": "Muoi nghin dong",
        "h_min": 16, "h_max": 35,
        "s_min": 45, "s_max": 255,
        "v_min": 40, "v_max": 240,
        "is_polymer": True,
        "pixel_check": lambda r, g, b: (r > 1.05 * b) and (g > 0.95 * b)
    },
    "5000": {
        "name": "Nam nghin dong",
        "h_min": 96, "h_max": 128,
        "s_min": 18, "s_max": 75,
        "v_min": 45, "v_max": 220,
        "is_polymer": False,
        "pixel_check": lambda r, g, b: (b >= 0.95 * r)
    },
    "2000": {
        "name": "Hai nghin dong",
        "h_min": 12, "h_max": 33,
        "s_min": 18, "s_max": 65,
        "v_min": 45, "v_max": 220,
        "is_polymer": False,
        "pixel_check": lambda r, g, b: (r > 1.05 * b)
    },
    "1000": {
        "name": "Mot nghin dong",
        "h_min": 70, "h_max": 105,
        "s_min": 10, "s_max": 55,
        "v_min": 45, "v_max": 220,
        "is_polymer": False,
        "pixel_check": lambda r, g, b: True
    }
}

KERNEL_3 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
KERNEL_5 = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

def test_detect_banknote(cv_img):
    h_img, w_img = cv_img.shape[:2]
    # Crop central area where the user holds the money (80% width, 80% height)
    margin_x = int(w_img * 0.10)
    margin_y = int(h_img * 0.10)
    roi_bgr = cv_img[margin_y:h_img - margin_y, margin_x:w_img - margin_x]
    roi_hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
    roi_h, roi_w = roi_hsv.shape[:2]

    scores = {}
    best_boxes = {}

    for label, prof in VND_SPECTRUM.items():
        if "h_min2" in prof:
            m1 = cv2.inRange(roi_hsv, np.array([prof["h_min"], prof["s_min"], prof["v_min"]]),
                                      np.array([prof["h_max"], prof["s_max"], prof["v_max"]]))
            m2 = cv2.inRange(roi_hsv, np.array([prof["h_min2"], prof["s_min"], prof["v_min"]]),
                                      np.array([prof["h_max2"], prof["s_max"], prof["v_max"]]))
            mask = cv2.bitwise_or(m1, m2)
        else:
            mask = cv2.inRange(roi_hsv, np.array([prof["h_min"], prof["s_min"], prof["v_min"]]),
                                     np.array([prof["h_max"], prof["s_max"], prof["v_max"]]))

        # Filter noise and bridge gaps between print patterns on note
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, KERNEL_5)
        
        # Find contours of this color
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue

        # Get largest cluster of this color
        c = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(c)

        # Minimum cluster size: at least 1500 pixels
        if area < 1500:
            continue

        bx, by, bw, bh = cv2.boundingRect(c)
        roi_cluster_bgr = roi_bgr[by:by+bh, bx:bx+bw]
        cluster_mask = mask[by:by+bh, bx:bx+bw]

        # Check color validity on matched pixels
        matched_pixels = cv2.countNonZero(cluster_mask)
        if matched_pixels < 1200:
            continue

        # Density of matched pixels in the cluster bounding box
        density = float(matched_pixels) / float(bw * bh)
        if density < 0.18:
            continue

        # Mean color of MATCHING pixels only
        mean_b = float(np.mean(roi_cluster_bgr[:, :, 0][cluster_mask > 0]))
        mean_g = float(np.mean(roi_cluster_bgr[:, :, 1][cluster_mask > 0]))
        mean_r = float(np.mean(roi_cluster_bgr[:, :, 2][cluster_mask > 0]))

        pixel_check = prof.get("pixel_check", None)
        if pixel_check and not pixel_check(mean_r, mean_g, mean_b):
            continue

        # Aspect ratio bonus if elongated like a bill
        ratio = float(bw) / float(bh) if bw > bh else float(bh) / float(bw)
        shape_bonus = 1.2 if (1.2 <= ratio <= 3.5) else 1.0

        score = float(matched_pixels) * shape_bonus
        if prof.get("is_polymer", True):
            score *= 1.25  # Prioritize polymer

        scores[label] = score
        # Global bounding box on original image
        best_boxes[label] = (bx + margin_x, by + margin_y, bw, bh)

    if not scores:
        return None

    # Sort candidates by score
    sorted_cand = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    winner_label, winner_score = sorted_cand[0]

    # If there's a runner-up, winner must dominate
    if len(sorted_cand) > 1:
        runner_up_label, runner_up_score = sorted_cand[1]
        # Distinguish between 500k and 20k or 10k and 200k
        if winner_score < 1.35 * runner_up_score:
            # Check saturation / color distinction
            pass

    prof = VND_SPECTRUM[winner_label]
    return {
        "label": winner_label,
        "name": prof["name"],
        "sound": f"{winner_label}.mp3",
        "box": best_boxes[winner_label],
        "score": winner_score
    }

# Run test on calibration images
zip_path = 'Gay_Nguoi_Mu/calibration_images.zip'
with zipfile.ZipFile(zip_path, 'r') as z:
    names = z.namelist()
    correct = 0
    total = len(names)
    for name in names:
        data = z.read(name)
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        cand = test_detect_banknote(img)
        lbl = cand["label"] if cand else "NONE"
        score = f"{cand['score']:.0f}" if cand else "-"
        print(f"{name[:35]:35s} -> {lbl:8s} (score: {score})")
        if lbl == "1000":
            correct += 1
    print(f"\nAccuracy on 1000 VND calibration images: {correct}/{total} ({correct/total*100:.1f}%)")
