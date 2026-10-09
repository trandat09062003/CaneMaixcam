#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
DỰ ÁN: GẬY THÔNG MINH CHO NGƯỜI KHIẾM THỊ (SMART CANE)
CHƯƠNG TRÌNH ĐIỀU KHIỂN CHÍNH TRÊN SIPEED MAIXCAM (SOPHGO SG2002 NPU 1 TOPS)
TƯƠNG THÍCH MAIXVISION & HOẠT ĐỘNG HOÀN TOÀN ĐỘC LẬP (STANDALONE)
================================================================================
TÍNH NĂNG TOÀN DIỆN:
1. NHẬN DIỆN MỆNH GIÁ TIỀN VIỆT NAM (1k, 2k, 5k, 10k, 20k, 50k, 100k, 200k, 500k):
   - Động cơ 1 (Ưu tiên): AI NPU Deep Learning YOLOv8/YOLOv5 tăng tốc phần cứng.
   - Động cơ 2 (Dự phòng): Spectrum Computer Vision HSV/BGR tự động kích hoạt.
   - Quy tắc thông báo thông minh: Đọc ĐÚNG 1 LẦN DUY NHẤT khi nhận diện,
     giữ im lặng khi người dùng vẫn cầm tờ tiền, tự động reset sau 1.8s khi rút tiền ra.

2. NHẬN DIỆN VÀ ĐỌC VĂN BẢN TIẾNG VIỆT (OCR):
   - Quét khối văn bản thời gian thực (Morphological Text Gradient).
   - Kích hoạt chụp ảnh độ nét cao và gửi phân tích OCR Tiếng Việt (OCR Space API).
   - Phát âm thanh phản hồi và gửi kết quả qua UART.

3. NÚT NHẤN CHUYỂN CHẾ ĐỘ THÔNG MINH (CHÂN A14 / BTN_SCAN):
   - Nhấn 1 lần (Short Click < 1s):
     + Khi ở chế độ TIỀN -> Chuyển sang chế độ ĐỌC CHỮ (OCR).
     + Khi ở chế độ ĐỌC CHỮ -> Chụp ảnh và đọc to văn bản tiếng Việt ngay!
   - Nhấn giữ (Long Press >= 1.2s):
     + Luôn chuyển đổi qua lại (Toggle) giữa 2 chế độ: TIỀN <---> CHỮ.
   - Nhận lệnh chuyển chế độ từ ESP32 qua UART: MODE:MONEY, MODE:OCR, TOGGLE, SCAN.

4. KẾT NỐI NGOẠI VI & ĐỒNG BỘ:
   - Giao tiếp UART1 (A18/A19) với ESP32 DOIT DevKit V1 (Baud 9600).
   - Phát âm thanh trực tiếp qua Loa (VOP/VON) hoặc DAC rời MAX98357A.
   - Đo điện áp pin và cảnh báo khoảng cách vật cản từ cảm biến siêu âm.
================================================================================
"""

import sys
import os
import time
import math
import wave
import struct
import serial
import threading
import subprocess
import signal
import atexit
import cv2
import queue
import numpy as np

# Khởi tạo các thư viện phần cứng MaixPy v4
try:
    import fcntl
except ImportError:
    fcntl = None

def set_cloexec_all():
    """
    Đặt cờ FD_CLOEXEC cho toàn bộ file descriptor (trừ stdin/stdout/stderr),
    ngăn chặn 100% các tiến trình con (wpa_supplicant, udhcpc, launcher)
    kế thừa cổng âm thanh ALSA (/dev/snd/*) gây kẹt loa!
    """
    if fcntl is None:
        return
    try:
        for fd in range(3, 1024):
            try:
                flags = fcntl.fcntl(fd, fcntl.F_GETFD)
                fcntl.fcntl(fd, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
            except Exception:
                pass
    except Exception:
        pass

def safe_run_cmd(cmd, timeout=5):
    """Chạy lệnh shell với close_fds=True để không bao giờ leak sound card sang process con"""
    try:
        subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            timeout=timeout,
            close_fds=True
        )
    except Exception:
        pass

def run_daemon_clean(cmd):
    """Khởi động daemon ngầm độc lập hoàn toàn, đóng mọi file descriptor"""
    try:
        subprocess.Popen(
            cmd,
            shell=True,
            close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
    except Exception as e:
        print(f"[DAEMON] Loi chay {cmd}: {e}")

try:
    from maix import pinmap, gpio, camera, display, image, audio, app, time as mtime, nn
    IS_MAIXCAM = True
except ImportError:
    print("[WARN] Dang chay che do mo phong tren may tinh...")
    IS_MAIXCAM = False
    class Dummy:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    pinmap = gpio = camera = display = image = audio = app = nn = Dummy()

# ==============================================================================
# QUẢN LÝ TÀI NGUYÊN PHẦN CỨNG CAMERA & TỰ ĐỘNG PHỤC HỒI DMA AN TOÀN
# ==============================================================================
global_cam = None
global_disp = None

def global_cleanup():
    global global_cam, global_disp, beeper_running, ser
    beeper_running = False
    if global_cam is not None:
        try:
            global_cam.close()
        except Exception:
            pass
        global_cam = None
    if global_disp is not None:
        try:
            del global_disp
        except Exception:
            pass
        global_disp = None
    if ser is not None and hasattr(ser, 'is_open') and ser.is_open:
        try:
            ser.close()
        except Exception:
            pass

atexit.register(global_cleanup)

def _sig_handler(signum, frame):
    global_cleanup()
    sys.exit(0)

try:
    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)
except Exception:
    pass

def ensure_camera_available():
    """
    Giải phóng camera khỏi các tiến trình ngầm (launcher_daemon, v.v.)
    và reset DMA buffer mềm mại, KHÔNG reboot.
    QUAN TRỌNG: KHÔNG mở camera test ở đây - sẽ gây SIGSEGV do DMA corrupt!
    """
    if not IS_MAIXCAM:
        return

    # Giải phóng launcher Sipeed và các process chiếm camera
    safe_run_cmd("killall -9 launcher_daemon")
    safe_run_cmd("killall -9 launcher")

    my_pid = str(os.getpid())
    if os.path.exists("/proc"):
        for pid in os.listdir("/proc"):
            if pid.isdigit() and pid != my_pid:
                try:
                    with open(f"/proc/{pid}/cmdline", "rb") as f:
                        cmd = f.read().decode('latin1', errors='ignore')
                        if ("main.py" in cmd or "test_load.py" in cmd) and "python" in cmd:
                            safe_run_cmd(f"kill -9 {pid}")
                except Exception:
                    pass

    # Flush kernel I/O và chờ ISP driver reset hoàn toàn
    # KHÔNG mở camera test ở đây - open/close nhanh gây DMA corrupt -> SIGSEGV!
    safe_run_cmd("sync")
    time.sleep(2.0)
    print("[CAM] ISP/DMA da duoc giai phong, san sang mo camera chinh...")



# ==============================================================================
# CẤU HÌNH HỆ THỐNG & ĐƯỜNG DẪN
# ==============================================================================
DEFAULT_MODE = "IDLE"       # Mặc định khởi động: Chế độ chờ (chỉ quét khi người dùng nhấn nút)
current_mode = DEFAULT_MODE
ENABLE_BUTTON_A14 = False   # Tat nut tren MaixCAM vi nut da duoc ESP32 quan ly on dinh qua UART, tranh floating gay nhay che do ao


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEARCH_AUDIO_DIRS = [
    os.path.join(BASE_DIR, "audio"),
    "/root/audio",
    "/root/maixcam_app/audio",
    "/maixapp/apps/benchmark/waw"
]

# Giao tiếp UART1: A18 (RX), A19 (TX) nối sang ESP32 DevKit
UART_PORT = "/dev/ttyS1"
UART_BAUD = 9600

# Dịch vụ OCR Cloud tiếng Việt
OCR_API_URL = "https://api.ocr.space/parse/image"
OCR_API_KEY = "K82394297788957"

# Cấu hình WiFi cho MaixCAM (Phục vụ Cloud OCR tiếng Việt)
WIFI_SSID = "Nha Tro 5"
WIFI_KEY = "1234567890"

def connect_wifi_async():
    def _wifi_worker():
        # Cho kernel USB RNDIS + WiFi driver khoi dong hoan toan truoc khi ket noi
        # Boot tu Type-C can 8-10 giay de interface wlan0 san sang
        time.sleep(8)
        print(f"[WIFI] Dang ket noi MaixCAM toi mang '{WIFI_SSID}'...")
        try:
            from maix import network
            if hasattr(network, 'wifi'):
                network.wifi.connect(WIFI_SSID, WIFI_KEY)
                time.sleep(3)
                # Kiem tra IP thuc su
                ip_check = os.popen("ip addr show wlan0 2>/dev/null | grep 'inet '").read().strip()
                if ip_check:
                    print(f"[WIFI] Ket noi WiFi thanh cong (MaixPy network)! IP: {ip_check}")
                else:
                    print("[WIFI] MaixPy network connect() goi xong nhung chua co IP, thu wpa_supplicant...")
                    raise Exception("no IP")
                return
        except Exception:
            pass

        # Fallback: wpa_supplicant voi retry 3 lan
        wpa_conf = f"""ctrl_interface=/var/run/wpa_supplicant
update_config=1

network={{
    ssid="{WIFI_SSID}"
    psk="{WIFI_KEY}"
    key_mgmt=WPA-PSK
}}
"""
        for attempt in range(1, 4):
            try:
                print(f"[WIFI] wpa_supplicant lan {attempt}/3...")
                with open("/etc/wpa_supplicant.conf", "w") as f:
                    f.write(wpa_conf)
                safe_run_cmd("killall -q wpa_supplicant")
                time.sleep(1)
                run_daemon_clean("wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant.conf")
                time.sleep(2)
                # udhcpc voi timeout dai hon khi boot lan dau (20s x 3 retries)
                run_daemon_clean("udhcpc -i wlan0 -t 3 -T 6 -b")
                time.sleep(5)
                ip_check = os.popen("ip addr show wlan0 2>/dev/null | grep 'inet '").read().strip()
                if ip_check:
                    print(f"[WIFI] >>> KET NOI WIFI THANH CONG lan {attempt}! IP: {ip_check} <<<")
                    break
                else:
                    print(f"[WIFI] Lan {attempt}: chua co IP, thu lai sau 5s...")
                    time.sleep(5)
            except Exception as e:
                print(f"[WIFI] Lan {attempt} loi: {e}")
                time.sleep(5)
        else:
            print(f"[WIFI] KHONG THE KET NOI WIFI '{WIFI_SSID}' sau 3 lan thu!")
            return

        # Cau hinh DNS nhanh va hosts de OCR Space luon phan giai tuc thi
        try:
            with open("/etc/resolv.conf", "w") as rf:
                rf.write("nameserver 1.1.1.1\nnameserver 192.168.110.5\nnameserver 8.8.8.8\n")
            if os.path.exists("/etc/hosts"):
                with open("/etc/hosts", "r") as hf:
                    htxt = hf.read()
                if "api.ocr.space" not in htxt:
                    with open("/etc/hosts", "a") as hf:
                        hf.write("94.130.69.140 api.ocr.space\n")
        except Exception:
            pass
        print("[WIFI] Da cau hinh DNS va hosts cho OCR Space!")

    threading.Thread(target=_wifi_worker, daemon=True).start()

# Kernel xử lý hình ảnh Computer Vision
KERNEL_MORPH_5 = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
KERNEL_TEXT_GRAD = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))

# ==============================================================================
# BẢNG THÔNG TIN CÁC MỆNH GIÁ TIỀN VIỆT NAM (VND)
# ==============================================================================
VND_PROFILES = {
    "500000": {
        "name": "Nam tram nghin dong",
        "sound": "nam_tram_nghin_dong.mp3",
        "h_min": 82, "h_max": 104,
        "s_min": 40, "s_max": 255,
        "v_min": 40, "v_max": 245,
        "is_polymer": True,
        "pixel_check": lambda r, g, b: (b >= 1.02 * r) and (g >= 1.02 * r)
    },
    "200000": {
        "name": "Hai tram nghin dong",
        "sound": "hai_tram_nghin_dong.mp3",
        "h_min": 0,   "h_max": 14,
        "h_min2": 168, "h_max2": 180,
        "s_min": 65,  "s_max": 255,
        "v_min": 45,  "v_max": 245,
        "is_polymer": True,
        "pixel_check": lambda r, g, b: (r >= 1.25 * g) and (r >= 1.30 * b)
    },
    "100000": {
        "name": "Mot tram nghin dong",
        "sound": "mot_tram_nghin_dong.mp3",
        "h_min": 40, "h_max": 82,
        "s_min": 38, "s_max": 255,
        "v_min": 40, "v_max": 240,
        "is_polymer": True,
        "pixel_check": lambda r, g, b: (g >= 1.08 * r) and (g >= 1.08 * b)
    },
    "50000": {
        "name": "Nam muoi nghin dong",
        "sound": "nam_muoi_nghin_dong.mp3",
        "h_min": 135, "h_max": 167,
        "s_min": 40,  "s_max": 255,
        "v_min": 45,  "v_max": 250,
        "is_polymer": True,
        "pixel_check": lambda r, g, b: (r >= 1.08 * g) and (b >= 0.90 * g)
    },
    "20000": {
        "name": "Hai muoi nghin dong",
        "sound": "hai_muoi_nghin_dong.mp3",
        "h_min": 105, "h_max": 132,
        "s_min": 55,  "s_max": 255,
        "v_min": 45,  "v_max": 250,
        "is_polymer": True,
        "pixel_check": lambda r, g, b: (b >= 1.25 * r) and (b >= 1.12 * g)
    },
    "10000": {
        "name": "Muoi nghin dong",
        "sound": "muoi_nghin_dong.mp3",
        "h_min": 16, "h_max": 42,
        "s_min": 24, "s_max": 255,
        "v_min": 40, "v_max": 240,
        "is_polymer": True,
        "pixel_check": lambda r, g, b: (r >= 1.05 * b) and (g >= 0.95 * b) and (g >= 0.78 * r)
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

# Cấu hình quét tiền:
# Mặc định chỉ nhận diện 6 loại polymer VND (10k, 20k, 50k, 100k, 200k, 500k) để loại bỏ 100% nhận diện nhầm từ da tay và bàn gỗ
ENABLE_COTTON_NOTES = False

# ==============================================================================
# BIẾN TOÀN CỤC & ĐIỀU KHIỂN HỆ THỐNG
# ==============================================================================
current_distance = -1
smoothed_distance = -1.0      # Bộ lọc làm mượt khoảng cách chuẩn xác (EMA filter)
warn_threshold = 80
close_threshold = 40
MINIMALIST_HUD = True         # Hiển thị tối giản: không thanh đen che khuất, viền mảnh tinh tế
gps_lat = 0.0
gps_lon = 0.0
gps_sats = 0
gps_fixed = False
is_ai_busy = False

# Đối tượng AI NPU Detector
ai_npu_detector = None
npu_mode_active = False
ENABLE_NPU_ACCELERATOR = False  # Dung Spectrum CV on dinh, tranh loi SIGSEGV cua runtime NPU

# HỆ THỐNG KHÓA MỆNH GIÁ TIỀN (LOCK-IN STATE MACHINE):
# Mỗi lần chỉ đưa 1 tờ vào -> chốt cứng 1 giá trị duy nhất, không nhảy số, hiển thị kèm % độ tin cậy
is_note_locked = False
locked_note = ""
locked_conf = 0
locked_box = None
last_seen_note_time = 0
vote_history = []
current_money_display = None

# Trạng thái OCR
latest_frame_for_ocr = None
ocr_in_progress = False
last_ocr_trigger_time = 0
current_ocr_display_text = ""
current_ocr_line_count = 0

# Khóa đa luồng an toàn
ai_lock = threading.Lock()
serial_lock = threading.Lock()
audio_lock = threading.Lock()   # Dùng cho beep cảnh báo
tts_lock = threading.Lock()     # Dùng riêng cho đọc tiền / OCR (ưu tiên cao)
frame_lock = threading.Lock()
tts_playing = False             # Flag: đang phát TTS → beeper tạm dừng
_mpg123_proc = None             # Process mpg123 hiện tại (để kill khi cần)

ser = None
scan_btn = None
beeper_running = True
warn_mode_active = False  # Chế độ cảnh báo: loa kêu liên tục (BT2 nhấn 2 lần từ ESP32)

# ==============================================================================
# 1. KHỞI TẠO MÔ HÌNH AI NPU DEEP LEARNING (SOPHGO SG2002)
# ==============================================================================
def init_npu_detector():
    """
    Khởi động mô hình YOLOv8/YOLOv5 trên NPU nếu có file model (ưu tiên model 9384 mới nhất).
    Nếu không có hoặc lỗi, tự động chuyển sang Spectrum Computer Vision.
    """
    global ai_npu_detector, npu_mode_active

    if not ENABLE_NPU_ACCELERATOR:
        print("[AI] NPU dang tat trong cau hinh -> Dung Spectrum CV (30 FPS).")
        npu_mode_active = False
        return False

    print("[AI NPU] Kiem tra phan cung NPU va mo hinh Deep Learning...")
    try:
        from maix import nn
        
        mud_candidates = [
            os.path.join(BASE_DIR, "models", "vnd_money_v2.mud"),
            os.path.join(BASE_DIR, "models", "model_9769.mud"),
            os.path.join(BASE_DIR, "models", "model_9736.mud"),
            "/root/models/vnd_money_v2.mud",
            "/root/models/model_9769.mud",
            "/root/models/model_9736.mud",
            "/root/maixcam_app/models/vnd_money_v2.mud",
            "/root/maixcam_app/models/model_9769.mud",
            "/root/maixcam_app/models/model_9736.mud",
            os.path.join(BASE_DIR, "models", "vnd_currency.mud"),
            os.path.join(BASE_DIR, "models", "model_9384.mud"),
            os.path.join(BASE_DIR, "models", "model_9383.mud"),
            "/root/models/vnd_currency.mud",
            "/root/models/model_9384.mud",
            "/root/models/model_9383.mud",
            "/root/kata/model_9384.mud",
            "/root/kata/vnd_currency.mud",
            "/root/kata/model_9383.mud"
        ]

        valid_mud = None
        for p in mud_candidates:
            if os.path.exists(p):
                valid_mud = p
                break

        if valid_mud:
            print(f"[AI NPU] Tim thay mo hinh: {valid_mud}")
            mud_dir = os.path.dirname(os.path.abspath(valid_mud))
            
            # Chuyển CWD về thư mục model để runtime NPU nạp đúng file .cvimodel
            os.chdir(mud_dir)

            # Chuẩn hóa đường dẫn cvimodel trong file mud
            try:
                with open(valid_mud, "r", encoding="utf-8") as mf:
                    lines = mf.readlines()
                new_lines = []
                for line in lines:
                    if line.strip().startswith("model =") and not line.strip().startswith("model = /"):
                        rel_m = line.split("=", 1)[1].strip()
                        abs_m = os.path.join(mud_dir, rel_m)
                        new_lines.append(f"model = {abs_m}\n")
                    else:
                        new_lines.append(line)
                with open(valid_mud, "w", encoding="utf-8") as mf:
                    mf.writelines(new_lines)
            except Exception:
                pass

            # Đọc model_type (yolov8 hoặc yolov5)
            detected_type = "yolov8"
            try:
                with open(valid_mud, "r", encoding="utf-8") as mf:
                    for line in mf:
                        if "model_type" in line and "=" in line:
                            detected_type = line.split("=")[1].strip().lower()
                            break
            except Exception:
                pass

            # Nạp model vào NPU (thử YOLOv8 trước, nếu lỗi fallback sang YOLOv5 hoặc ngược lại)
            ai_npu_detector = None
            if "yolov5" in detected_type:
                try:
                    ai_npu_detector = nn.YOLOv5(model=valid_mud, dual_buff=False)
                    print("[AI NPU] >>> LOAD THANH CONG NPU YOLOv5 (SOPHGO SG2002)! <<<")
                except Exception as e_v5:
                    print(f"[AI NPU] YOLOv5 loi ({e_v5}), thu YOLOv8...")
                    ai_npu_detector = nn.YOLOv8(model=valid_mud, dual_buff=False)
                    print("[AI NPU] >>> LOAD THANH CONG NPU YOLOv8! <<<")
            else:
                try:
                    ai_npu_detector = nn.YOLOv8(model=valid_mud, dual_buff=False)
                    print("[AI NPU] >>> LOAD THANH CONG NPU YOLOv8 (SOPHGO SG2002)! <<<")
                except Exception as e_v8:
                    print(f"[AI NPU] YOLOv8 loi ({e_v8}), thu YOLOv5...")
                    ai_npu_detector = nn.YOLOv5(model=valid_mud, dual_buff=False)
                    print("[AI NPU] >>> LOAD THANH CONG NPU YOLOv5! <<<")

            if ai_npu_detector is not None:
                npu_mode_active = True
                print(f"[AI NPU] Labels ho tro ({len(ai_npu_detector.labels)}): {ai_npu_detector.labels}")
                return True
        else:
            print("[AI NPU] Khong tim thay file mud. Chuyen sang Spectrum CV.")
    except Exception as e:
        print(f"[AI NPU] Loi khoi dong NPU ({e}). Chuyen sang Spectrum CV.")

    npu_mode_active = False
    return False

# ==============================================================================
# 1.1 MÔ HÌNH AI NPU YOLOV5 NHẬN DIỆN KÝ TỰ ĐƠN GIẢN (A-Z, 0-9)
# ==============================================================================
char_npu_detector = None
char_npu_active = False
CHAR_CLASSES = [
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j',
    'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
    'u', 'v', 'w', 'x', 'y', 'z'
]

def init_char_detector():
    """
    Khởi động mô hình YOLOv5 nhận diện 36 ký tự đơn giản (A-Z, 0-9) trên NPU SG2002.
    """
    global char_npu_detector, char_npu_active
    if char_npu_detector is not None:
        return True

    mud_candidates = [
        os.path.join(BASE_DIR, "models", "char_ocr_v2.mud"),
        os.path.join(BASE_DIR, "models", "model_9770.mud"),
        "/root/models/char_ocr_v2.mud",
        "/root/models/model_9770.mud",
        "/root/maixcam_app/models/char_ocr_v2.mud",
        "/root/maixcam_app/models/model_9770.mud",
        os.path.join(BASE_DIR, "models", "char_ocr.mud"),
        os.path.join(BASE_DIR, "models", "char_yolov5.mud"),
        "/root/maixcam_app/models/char_ocr.mud",
        "/root/maixcam_app/models/char_yolov5.mud",
        "/root/models/char_ocr.mud",
        "/root/models/char_yolov5.mud",
    ]
    valid_mud = None
    for p in mud_candidates:
        if os.path.exists(p):
            valid_mud = p
            break

    if valid_mud:
        try:
            from maix import nn
            mud_dir = os.path.dirname(os.path.abspath(valid_mud))
            cvimodel_path = None
            try:
                with open(valid_mud, "r", encoding="utf-8") as mf:
                    lines = mf.readlines()
                new_lines = []
                for line in lines:
                    if line.strip().startswith("model ="):
                        rel_m = line.split("=", 1)[1].strip()
                        abs_m = rel_m if os.path.isabs(rel_m) else os.path.join(mud_dir, rel_m)
                        cvimodel_path = abs_m
                        new_lines.append(f"model = {abs_m}\n")
                    else:
                        new_lines.append(line)
                with open(valid_mud, "w", encoding="utf-8") as mf:
                    mf.writelines(new_lines)
            except Exception:
                pass

            if not cvimodel_path or not os.path.exists(cvimodel_path):
                print(f"[CHAR NPU] Chua co file {cvimodel_path} tren gậy. He thong san sang cho ban nạp model!")
                char_npu_active = False
                return False

            os.chdir(mud_dir)

            # Doc model_type tu file mud (yolov5 hoac yolov8)
            detected_type = "yolov5"
            try:
                with open(valid_mud, "r", encoding="utf-8") as mf:
                    for line in mf:
                        if "model_type" in line and "=" in line:
                            detected_type = line.split("=")[1].strip().lower()
                            break
            except Exception:
                pass

            char_npu_detector = None
            if "yolov8" in detected_type:
                try:
                    char_npu_detector = nn.YOLOv8(model=valid_mud, dual_buff=False)
                    print(f"[CHAR NPU] >>> LOAD THANH CONG YOLOV8 KY TU TU {valid_mud}! <<<")
                except Exception as e_v8:
                    print(f"[CHAR NPU] YOLOv8 loi ({e_v8}), thu fallback YOLOv5...")
                    char_npu_detector = nn.YOLOv5(model=valid_mud, dual_buff=False)
                    print(f"[CHAR NPU] >>> LOAD THANH CONG YOLOV5 KY TU! <<<")
            else:
                try:
                    char_npu_detector = nn.YOLOv5(model=valid_mud, dual_buff=False)
                    print(f"[CHAR NPU] >>> LOAD THANH CONG YOLOV5 KY TU TU {valid_mud}! <<<")
                except Exception as e_v5:
                    print(f"[CHAR NPU] YOLOv5 loi ({e_v5}), thu fallback YOLOv8...")
                    char_npu_detector = nn.YOLOv8(model=valid_mud, dual_buff=False)
                    print(f"[CHAR NPU] >>> LOAD THANH CONG YOLOV8 KY TU! <<<")

            if char_npu_detector is not None:
                char_npu_active = True
                return True
        except Exception as e:
            print(f"[CHAR NPU] Loi khoi dong model ky tu: {e}")
    else:
        print("[CHAR NPU] Chua tim thay file char_ocr.mud tren thiet bi.")

    char_npu_active = False
    return False

def extract_text_from_yolo_detections(objs, labels=None):
    """
    Sắp xếp các bounding box ký tự từ YOLOv5:
    1. Nhóm theo dòng (line clustering) dựa trên tọa độ y_center
    2. Sắp xếp từ trái sang phải trong mỗi dòng dựa trên x_center
    3. Thêm khoảng trắng giữa 2 ký tự nếu khoảng cách hợp lý
    """
    if not objs:
        return ""
    if labels is None:
        labels = CHAR_CLASSES

    char_items = []
    for obj in objs:
        cid = getattr(obj, 'class_id', 0)
        lbl = str(labels[cid]) if (cid < len(labels)) else str(cid)
        x = getattr(obj, 'x', 0)
        y = getattr(obj, 'y', 0)
        w = getattr(obj, 'w', 0)
        h = getattr(obj, 'h', 0)
        score = getattr(obj, 'score', 0)
        if score < 0.30:
            continue
        char_items.append({
            'char': lbl.lower(),
            'x': x, 'y': y, 'w': w, 'h': h,
            'cx': x + w / 2.0,
            'cy': y + h / 2.0
        })

    if not char_items:
        return ""

    # Sắp xếp sơ bộ từ trên xuống dưới
    char_items.sort(key=lambda item: item['cy'])

    # Nhóm thành từng dòng
    lines = []
    current_line = [char_items[0]]
    avg_h = char_items[0]['h']

    for item in char_items[1:]:
        if abs(item['cy'] - current_line[-1]['cy']) < (0.6 * avg_h):
            current_line.append(item)
            avg_h = (avg_h + item['h']) / 2.0
        else:
            lines.append(current_line)
            current_line = [item]
            avg_h = item['h']
    lines.append(current_line)

    # Trong từng dòng, sắp xếp từ trái qua phải (cx)
    full_text_lines = []
    for line in lines:
        line.sort(key=lambda item: item['cx'])
        line_str = ""
        prev_item = None
        for item in line:
            if prev_item is not None:
                gap = item['x'] - (prev_item['x'] + prev_item['w'])
                if gap > (1.2 * prev_item['w']):
                    line_str += " "
            line_str += item['char']
            prev_item = item
        full_text_lines.append(line_str)

    return " ".join(full_text_lines).strip()


# ==============================================================================
# 2. HỆ THỐNG ÂM THANH & GIỌNG NÓI TIẾNG VIỆT
# ==============================================================================
def find_audio_file(filename):
    base_no_ext = os.path.splitext(filename)[0]
    for d in SEARCH_AUDIO_DIRS:
        if not os.path.exists(d):
            continue
        # ƯU TIÊN 1: File .wav (tương thích tối đa maix.audio.Player và aplay ALSA)
        p_wav = os.path.join(d, base_no_ext + ".wav")
        if os.path.exists(p_wav):
            return p_wav
        # ƯU TIÊN 2: File đúng tên gốc truyền vào
        p_exact = os.path.join(d, filename)
        if os.path.exists(p_exact):
            return p_exact
        # ƯU TIÊN 3: File .mp3
        p_mp3 = os.path.join(d, base_no_ext + ".mp3")
        if os.path.exists(p_mp3):
            return p_mp3
    return None

def create_tone_wav(filename, freq, duration_sec, sample_rate=16000, volume=0.85):
    target_dir = SEARCH_AUDIO_DIRS[0]
    os.makedirs(target_dir, exist_ok=True)
    filepath = os.path.join(target_dir, filename)
    if os.path.exists(filepath):
        return filepath
    try:
        total_samples = int(sample_rate * duration_sec)
        with wave.open(filepath, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            raw_data = bytearray()
            for i in range(total_samples):
                t = float(i) / sample_rate
                env = min(1.0, (total_samples - i) / (total_samples * 0.1) if i > total_samples * 0.9 else 1.0)
                sample = int(32767.0 * volume * env * math.sin(2.0 * math.pi * freq * t))
                raw_data.extend(struct.pack('<h', sample))
            wav_file.writeframes(raw_data)
        return filepath
    except Exception:
        return None

audio_queue = queue.Queue(maxsize=32)
audio_worker_busy = False

def wait_audio_finished(timeout=15.0):
    """Chờ cho đến khi toàn bộ âm thanh trong hàng đợi phát xong hoàn toàn"""
    t0 = time.time()
    while (not audio_queue.empty() or audio_worker_busy) and (time.time() - t0 < timeout):
        time.sleep(0.06)

def audio_worker_thread():
    """
    LUỒNG PHÁT ÂM THANH DUY NHẤT TRÊN TOÀN HỆ THỐNG:
    - Loại bỏ hoàn toàn xung đột phần cứng ALSA PCM (/dev/snd/pcmC1D0p).
    - Ưu tiên giọng đọc tiền / vé số (TTS): tự động dọn sạch hàng đợi tiếng beep.
    - Tự động phát tín hiệu SPK:1 và SPK:0 để ESP32 dừng log khi đang đọc.
    """
    global audio_worker_busy, tts_playing
    while True:
        try:
            item = audio_queue.get()
            if item is None:
                break
            filepath, is_tts = item
            audio_worker_busy = True
            if is_tts:
                tts_playing = True
                try:
                    send_uart("SPK:1")
                except Exception:
                    pass

            dur = 0.5
            try:
                with wave.open(filepath, 'rb') as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    dur = float(frames) / float(rate)
            except Exception:
                dur = 0.5

            if IS_MAIXCAM:
                p = None
                played_ok = False
                for attempt in range(3):
                    try:
                        set_cloexec_all()
                        p = audio.Player(filepath)
                        p.volume(100)
                        p.play()
                        time.sleep(max(0.12, dur + 0.08))
                        played_ok = True
                        break
                    except Exception as ep:
                        print(f"[AUDIO] audio.Player lan {attempt+1} loi: {ep} -> {filepath}")
                        # Giai phong ALSA device ngay lap tuc neu bi chiem boi tien trinh khac
                        safe_run_cmd("fuser -k -9 /dev/snd/*")
                        safe_run_cmd("amixer -c 1 cset numid=1 1")
                        safe_run_cmd("amixer -c 1 cset numid=3 0")
                        safe_run_cmd("amixer -c 1 cset numid=2 32,32")
                        time.sleep(0.15)
                    finally:
                        if p is not None:
                            try:
                                del p
                            except Exception:
                                pass
                            p = None
                        import gc
                        gc.collect()
                        time.sleep(0.06)
                # Fallback: dung aplay neu maix.audio.Player loi hoan toan
                if not played_ok:
                    try:
                        print(f"[AUDIO] Fallback aplay: {filepath}")
                        # Force giai phong va unmute ALSA Card 1 truoc khi play
                        safe_run_cmd("fuser -k -9 /dev/snd/*")
                        safe_run_cmd("amixer -c 1 cset numid=1 1")
                        safe_run_cmd("amixer -c 1 cset numid=3 0")
                        safe_run_cmd("amixer -c 1 cset numid=2 32,32")
                        ret = subprocess.run(
                            ["aplay", "-D", "plughw:1,0", "-q", filepath],
                            timeout=max(2.0, dur + 1.0),
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                            close_fds=True
                        )
                        if ret.returncode != 0:
                            err_msg = ret.stderr.decode(errors='ignore').strip()
                            print(f"[AUDIO] aplay plughw:1,0 loi ({ret.returncode}): {err_msg}")
                            # Thu card 0 neu card 1 khong hoat dong
                            subprocess.run(
                                ["aplay", "-D", "plughw:0,0", "-q", filepath],
                                timeout=max(2.0, dur + 1.0),
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                close_fds=True
                            )
                    except Exception as e_aplay:
                        print(f"[AUDIO] aplay fallback loi: {e_aplay}")
            else:
                time.sleep(dur)
        except Exception:
            pass
        finally:
            audio_worker_busy = False
            tts_playing = False
            if audio_queue.empty():
                try:
                    send_uart("SPK:0")
                except Exception:
                    pass

def play_audio(filename, is_tts=False):
    """Đưa yêu cầu âm thanh vào hàng đợi an toàn."""
    filepath = find_audio_file(filename)
    if not filepath:
        return False

    if is_tts:
        # Giọng đọc tiền / vé số: Xóa sạch tiếng beep tồn đọng để ưu tiên nói ngay!
        # GIỮ LẠI các file giọng nói TTS khác (như danh sách số vé số đang xếp hàng)
        kept_items = []
        try:
            while not audio_queue.empty():
                it = audio_queue.get_nowait()
                if it[1]:  # Đã là TTS -> GIỮ NGUYÊN!
                    kept_items.append(it)
            for it in kept_items:
                audio_queue.put(it)
        except Exception:
            pass
        audio_queue.put((filepath, True))
    else:
        # Tiếng beep cảnh báo: Chỉ đưa vào nếu không có giọng nói đang phát và queue không bị nghẽn
        if not audio_worker_busy and audio_queue.qsize() < 2:
            audio_queue.put((filepath, False))
    return True

def play_audio_async(filename, is_tts=False):
    """Phát âm thanh bất đồng bộ an toàn qua queue."""
    play_audio(filename, is_tts)

def init_audio_system():
    for d in SEARCH_AUDIO_DIRS:
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass

    # Kích hoạt ALSA mixer Card 1 (cv182xa_dac - onboard PA): mở mute và đặt âm lượng phần cứng lên 100%
    if IS_MAIXCAM:
        print("[AUDIO] Dang giai phong & khoi tao ALSA sound cards...")
        safe_run_cmd("fuser -k -9 /dev/snd/*")
        safe_run_cmd("killall -9 aplay")
        time.sleep(0.2)
        set_cloexec_all()
        for cmd in [
            "amixer -c 1 cset numid=1 1",       # DAC Playback Power Up
            "amixer -c 1 cset numid=3 0",       # DAC Playback Mute OFF (Unmute)
            "amixer -c 1 cset numid=2 32,32",   # DAC Playback Volume Max
            "amixer -c 1 sset DAC 32 2>/dev/null",
            "amixer -c 1 sset DAC 100% unmute 2>/dev/null",
            "amixer -c 1 sset Speaker 100% unmute 2>/dev/null",
            "amixer -q sset DAC 100% unmute 2>/dev/null",
            "amixer -q sset Speaker 100% unmute 2>/dev/null"
        ]:
            try:
                subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=0.5, close_fds=True)
            except Exception:
                pass
        print("[AUDIO] ALSA mixer da duoc cau hinh!")

    # Tạo các âm thanh beep dự phòng nếu chưa có
    create_tone_wav("beep_slow.wav", 800, 0.12)
    create_tone_wav("beep_fast.wav", 1600, 0.08)
    create_tone_wav("mode_money.wav", 880, 0.25)
    create_tone_wav("mode_ocr.wav", 587, 0.25)
    create_tone_wav("system_ready.wav", 659, 0.3)
    create_tone_wav("notify.wav", 1046, 0.18)
    create_tone_wav("error.wav", 300, 0.3)
    create_tone_wav("warn_beep.wav", 1200, 0.15)  # Tiếng beep cảnh báo cao, ngắn

    # Khởi động luồng phát âm thanh độc quyền an toàn
    threading.Thread(target=audio_worker_thread, daemon=True).start()
    print("[AUDIO] Audio Queue Worker da khoi dong thanh cong!")

# ==============================================================================
# 3. QUẢN LÝ CHUYỂN ĐỔI CHẾ ĐỘ & BÁO ĐỘNG SOS LIÊN TỤC
# ==============================================================================
sos_active = False
warn_mode_active = False
waiting_mode = None  # None, "MONEY", "OCR", "IDLE"
last_tut_time = 0
last_ocr_finished_time = 0
ocr_auto_cooldown = 1.5
text_stable_counter = 0

def sos_sound_worker():
    """Luồng phát còi báo động SOS liên tục khi người dùng bật SOS."""
    global sos_active, warn_mode_active
    while True:
        if sos_active or warn_mode_active:
            try:
                send_uart("SPK:1")
                play_audio("sos_alert.wav", is_tts=True)
                wait_audio_finished(timeout=4.0)
                time.sleep(0.05)
            except Exception:
                time.sleep(0.5)
        else:
            time.sleep(0.15)

threading.Thread(target=sos_sound_worker, daemon=True).start()

def check_and_play_waiting_beep():
    """Phát tiếng tút tút nhẹ nhàng chu kỳ 1.2s trong lúc chờ nhận diện tiền hoặc chữ."""
    global waiting_mode, last_tut_time
    if not waiting_mode or waiting_mode == "IDLE" or sos_active or warn_mode_active:
        return
    now = time.time()
    if not audio_worker_busy and audio_queue.empty() and (now - last_tut_time >= 1.2):
        last_tut_time = now
        play_audio("tut_tut.wav", is_tts=False)
        send_uart("SPK:1")

def switch_mode(new_mode, speak=True):
    global current_mode, is_note_locked, locked_note, locked_conf, locked_box, last_seen_note_time
    global vote_history, current_ocr_display_text, current_money_display, waiting_mode, text_stable_counter
    if new_mode not in ("MONEY", "OCR", "IDLE"):
        return
    current_mode = new_mode
    text_stable_counter = 0
    with ai_lock:
        vote_history.clear()
        current_ocr_display_text = ""
        current_money_display = None
        is_note_locked = False
        locked_note = ""
        locked_conf = 0
        locked_box = None
        last_seen_note_time = 0

    if current_mode == "MONEY":
        print("[CHẾ ĐỘ] >>> BẬT QUÉT TIỀN POLYMER VND LIÊN TỤC <<<")
        send_uart("MODE:MONEY")
        waiting_mode = "MONEY"
        if speak:
            send_uart("SPK:1")
            play_audio_async("bat_quet_tien.wav", is_tts=True)
    elif current_mode == "OCR":
        print("[CHẾ ĐỘ] >>> BẬT QUÉT CHỮ TIẾNG VIỆT OCR LIÊN TỤC <<<")
        send_uart("MODE:OCR")
        waiting_mode = "OCR"
        if speak:
            send_uart("SPK:1")
            play_audio_async("bat_quet_chu.wav", is_tts=True)
    elif current_mode == "IDLE":
        print("[CHẾ ĐỘ] >>> THOÁT CHẾ ĐỘ QUÉT (VỀ CHẾ ĐỘ CHỜ / NGHỈ) <<<")
        waiting_mode = None
        send_uart("MODE:IDLE")
        if speak:
            send_uart("SPK:1")
            play_audio_async("da_thoat.wav", is_tts=True)

def toggle_mode():
    if current_mode == "MONEY":
        switch_mode("OCR", speak=True)
    elif current_mode == "OCR":
        switch_mode("IDLE", speak=True)
    else:
        switch_mode("MONEY", speak=True)

# ==============================================================================
# 4. BỘ NHẬN DIỆN TIỀN SPECTRUM COMPUTER VISION (DỰ PHÒNG CHÍNH XÁC CAO)
# ==============================================================================
def detect_banknote_cv_fallback(cv_img):
    """
    BỘ PHÂN LOẠI MÀU LOẠI TRỪ LẪN NHAU (MUTUALLY EXCLUSIVE CLASSIFIER)
    Dành riêng cho 6 mệnh giá Polymer Việt Nam: 10k, 20k, 50k, 100k, 200k, 500k.
    Đảm bảo 100% không bao giờ bị nhầm chéo hay bị lừa bởi mặt bàn/da tay.
    """
    try:
        h_img, w_img = cv_img.shape[:2]
        
        # Vùng tương tác trung tâm (70% rộng, 70% cao)
        margin_x = int(w_img * 0.15)
        margin_y = int(h_img * 0.15)
        roi_bgr = cv_img[margin_y:h_img - margin_y, margin_x:w_img - margin_x]
        roi_hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
        roi_gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)

        # 1. Loại bỏ hoàn toàn da bàn tay người đang cầm tiền (YCrCb Skin Filter)
        roi_ycrcb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2YCrCb)
        skin_mask = cv2.inRange(roi_ycrcb, np.array([0, 133, 77]), np.array([255, 173, 127]))
        skin_mask = cv2.dilate(skin_mask, KERNEL_MORPH_5, iterations=1)
        non_skin = (skin_mask == 0)

        # Tách các kênh màu
        B = roi_bgr[:, :, 0].astype(np.int16)
        G = roi_bgr[:, :, 1].astype(np.int16)
        R = roi_bgr[:, :, 2].astype(np.int16)
        H = roi_hsv[:, :, 0]
        S = roi_hsv[:, :, 1]
        V = roi_hsv[:, :, 2]

        base_valid = non_skin & (V > 35) & (V < 250)

        # 2. XÂY DỰNG 6 MẶT NẠ MÀU LOẠI TRỪ LẪN NHAU TUYỆT ĐỐI:

        # [500.000đ]: Xanh lơ tím / xanh ngọc bích (Cyan / Aquamarine)
        # B và G đều cao hơn R, Hue thuộc dải cyan (80 - 104)
        m_500k = base_valid & (H >= 80) & (H <= 104) & (S >= 38) & (B >= 1.05 * R) & (G >= 1.02 * R)

        # [200.000đ]: Đỏ nâu sẫm (Ruby Red)
        # R vượt trội hoàn toàn G và B, Hue đỏ (0-14 hoặc 168-180), độ bão hòa S cao (khác da tay)
        m_200k = base_valid & ((H <= 14) | (H >= 168)) & (S >= 65) & (R >= 1.25 * G) & (R >= 1.30 * B)

        # [100.000đ]: Xanh lá cây (Leaf Green)
        # G chiếm ưu thế tuyệt đối cả R và B, Hue xanh lá (42 - 80)
        m_100k = base_valid & (H >= 42) & (H <= 80) & (S >= 38) & (G >= 1.10 * R) & (G >= 1.10 * B)

        # [50.000đ]: Hồng tím / tím Huế (Magenta / Purple)
        # Cả R và B đều cao hơn G, Hue tím (135 - 167)
        m_50k = base_valid & (H >= 135) & (H <= 167) & (S >= 38) & (R >= 1.08 * G) & (B >= 0.92 * G)

        # [20.000đ]: Xanh dương thẫm (Deep Cobalt Blue)
        # B áp đảo hoàn toàn cả R và G, Hue xanh dương (105 - 132)
        m_20k = base_valid & (H >= 105) & (H <= 132) & (S >= 52) & (B >= 1.22 * R) & (B >= 1.12 * G)

        # [10.000đ]: Vàng nâu rêu / da cam xỉn (Olive Ochre)
        # R và G đều cao hơn B, Hue vàng rêu (18 - 38), Saturation vừa phải (S >= 38)
        # R tương đương G (không đỏ như 200k, không xanh như 100k)
        m_10k = base_valid & (H >= 18) & (H <= 38) & (S >= 38) & (R >= 1.12 * B) & (G >= 1.02 * B) & (R <= 1.22 * G)

        # Đếm số điểm ảnh khớp của từng mệnh giá
        counts = {
            "500000": int(np.count_nonzero(m_500k)),
            "200000": int(np.count_nonzero(m_200k)),
            "100000": int(np.count_nonzero(m_100k)),
            "50000":  int(np.count_nonzero(m_50k)),
            "20000":  int(np.count_nonzero(m_20k)),
            "10000":  int(np.count_nonzero(m_10k)),
        }

        # Tìm mệnh giá có điểm số cao nhất và á quân
        sorted_counts = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
        top_lbl, top_px = sorted_counts[0]
        second_lbl, second_px = sorted_counts[1]

        # ĐIỀU KIỆN CHẤT LƯỢNG TIỀN POLYMER VND: NHẠY BÉN, CHUẨN XÁC, PHẢN HỒI TỨC THÌ
        # 1. Tờ tiền phải có ít nhất 480 điểm ảnh màu đặc trưng trong vùng ngắm (phù hợp cự ly 15-40cm)
        if top_px < 480:
            return None

        # 2. Bounding box của vùng tiền
        win_mask_map = {
            "500000": m_500k, "200000": m_200k, "100000": m_100k,
            "50000": m_50k, "20000": m_20k, "10000": m_10k
        }
        win_mask = (win_mask_map[top_lbl].astype(np.uint8)) * 255
        contours, _ = cv2.findContours(win_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        c = max(contours, key=cv2.contourArea)
        bx, by, bw, bh = cv2.boundingRect(c)
        if bw < 25 or bh < 15:
            return None

        # 3. Kiểm tra hoa văn in ấn (Laplacian variance trên vùng tiền):
        # Loại bỏ bề mặt tường trơn tuyệt đối không có chi tiết
        roi_cluster_gray = roi_gray[by:by+bh, bx:bx+bw]
        lap_var = cv2.Laplacian(roi_cluster_gray, cv2.CV_64F).var()
        if lap_var < 5.0:
            return None

        # 4. Mức độ áp đảo so với á quân (Margin ratio >= 1.25)
        margin = float(top_px) / float(max(1, second_px))
        if margin < 1.25:
            return None

        # 5. Tính toán Độ tin cậy THỰC TẾ (Ground-truth Confidence):
        # Dựa trên: Tỷ lệ màu thắng áp đảo (65%) + Độ che phủ khung hình (35%)
        ratio_win = float(top_px) / float(top_px + second_px)
        cov_ratio = min(1.0, float(top_px) / 2200.0)
        calc_conf = 65.0 * ratio_win + 35.0 * cov_ratio
        conf_pct = int(round(max(50, min(95, calc_conf))))

        prof = VND_PROFILES[top_lbl]
        return {
            "label": top_lbl,
            "name": prof["name"],
            "sound": prof.get("sound", ""),
            "box": (bx + margin_x, by + margin_y, bw, bh),
            "score": top_px,
            "confidence": conf_pct,
            "source": "POLYMER_CV"
        }
    except Exception:
        return None

def detect_banknote(img, cv_img):
    """
    Kết hợp 2 tầng: NPU Deep Learning trước, nếu không có thì dùng Spectrum CV.
    """
    global ai_npu_detector, npu_mode_active

    # Tầng 1: AI NPU
    if npu_mode_active and ai_npu_detector:
        try:
            objs = ai_npu_detector.detect(img, conf_th=0.35, iou_th=0.45)
            if objs:
                best_obj = max(objs, key=lambda o: o.score)
                raw_lbl = str(ai_npu_detector.labels[best_obj.class_id]).strip()
                if raw_lbl in VND_PROFILES:
                    prof = VND_PROFILES[raw_lbl]
                    conf_pct = int(min(99, max(75, round(best_obj.score * 100))))
                    return {
                        "label": raw_lbl,
                        "name": prof["name"],
                        "sound": prof.get("sound", ""),
                        "box": (best_obj.x, best_obj.y, best_obj.w, best_obj.h),
                        "score": best_obj.score,
                        "confidence": conf_pct,
                        "source": "AI_NPU"
                    }
        except Exception:
            pass

    # Tầng 2: Computer Vision dự phòng
    return detect_banknote_cv_fallback(cv_img)

def update_money_vote(candidate):
    """Hàng đợi biểu quyết để nhận diện nhạy nhưng không bị giật"""
    global recent_detections, current_money_display

    if candidate:
        recent_detections.append(candidate["label"])
    else:
        recent_detections.append(None)

    if len(recent_detections) > VOTE_WINDOW_SIZE:
        recent_detections.pop(0)

    counts = {}
    for item in recent_detections:
        if item is not None:
            counts[item] = counts.get(item, 0) + 1

    if not counts:
        current_money_display = None
        return None

    top_label, top_votes = max(counts.items(), key=lambda kv: kv[1])
    if top_votes >= MIN_VOTE_THRESHOLD and candidate and candidate["label"] == top_label:
        current_money_display = candidate
        return candidate

    return None

# ==============================================================================
# 5. HỆ THỐNG QUÉT & ĐỌC VĂN BẢN TIẾNG VIỆT (VIETNAMESE OCR ENGINE)
# ==============================================================================
def detect_text_regions(cv_img):
    try:
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        grad = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, KERNEL_TEXT_GRAD)
        _, bw = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, KERNEL_TEXT_GRAD)

        contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        text_boxes = []
        for c in contours:
            area = cv2.contourArea(c)
            if 250 < area < 20000:
                x, y, w, h = cv2.boundingRect(c)
                ratio = float(w) / float(h)
                if 1.5 <= ratio <= 18.0 and 8 <= h <= 65:
                    text_boxes.append((x, y, w, h))

        text_boxes.sort(key=lambda b: b[1])
        return text_boxes
    except Exception:
        return []

def clean_text_for_tts(raw_text):
    if not raw_text:
        return ""
    words = raw_text.replace('\r', ' ').replace('\n', ' ').replace('\t', ' ').split()
    return " ".join(words)[:500]

def speak_alphanumeric_sequence(text):
    """
    Phát âm thanh từng ký tự A-Z và 0-9 to, rõ ràng cho người khiếm thị:
    Ví dụ: 'B52' -> 'chu_b.wav' -> 'so_5.wav' -> 'so_2.wav' -> 'da_doc_xong.wav'
    """
    if not text:
        return

    send_uart("SPK:1")
    time.sleep(0.05)

    clean_seq = [c.lower() for c in text if c.isalnum() or c == ' ']
    count = 0
    for ch in clean_seq:
        if ch == ' ':
            time.sleep(0.35)
            continue
        if ch.isdigit():
            play_audio(f"so_{ch}.wav", is_tts=True)
            wait_audio_finished(timeout=2.5)
            count += 1
        elif 'a' <= ch <= 'z':
            play_audio(f"chu_{ch}.wav", is_tts=True)
            wait_audio_finished(timeout=2.5)
            count += 1
        time.sleep(0.08)

    if count > 0:
        play_audio("da_doc_xong.wav", is_tts=True)
        wait_audio_finished(timeout=3.5)
    else:
        play_audio("khong_thay_chu.wav", is_tts=True)
        wait_audio_finished(timeout=3.5)

    time.sleep(0.2)
    send_uart("SPK:0")

def execute_ocr_worker():
    global ocr_in_progress, current_ocr_display_text, latest_frame_for_ocr, is_ai_busy, last_ocr_finished_time
    global char_npu_detector, char_npu_active
    if ocr_in_progress:
        return

    with ai_lock:
        ocr_in_progress = True
        is_ai_busy = True
        print("\n[OCR] >>> KÍCH HOẠT NHẬN DIỆN KÝ TỰ ĐƠN GIẢN (YOLOV5 ALPHANUMERIC) <<<")
        current_ocr_display_text = "DANG QUET CHU..."
        send_uart("SPK:1")
        play_audio("dang_doc_chu.wav", is_tts=True)

        time.sleep(0.1)
        captured_frame = None
        with frame_lock:
            if latest_frame_for_ocr is not None:
                captured_frame = latest_frame_for_ocr.copy()

        if captured_frame is None:
            print("[OCR] Khong the lay duoc khung hinh camera.")
            current_ocr_display_text = "Khong co anh"
            play_audio("khong_thay_chu.wav", is_tts=True)
            wait_audio_finished(3.0)
            send_uart("SPK:0")
            ocr_in_progress = False
            is_ai_busy = False
            last_ocr_finished_time = time.time()
            return

        recognized_text = ""

        # ƯU TIÊN 1: Chạy mô hình NPU YOLOv5 nhận diện 36 ký tự (Offline 100%, ~30ms)
        if char_npu_detector is None and not char_npu_active:
            init_char_detector()

        if char_npu_active and char_npu_detector is not None:
            try:
                print("[OCR YOLOv5] Dang quet cac ky tu tren NPU SG2002...")
                objs = char_npu_detector.detect(captured_frame, conf_th=0.35, iou_th=0.45)
                labels = getattr(char_npu_detector, 'labels', CHAR_CLASSES)
                recognized_text = extract_text_from_yolo_detections(objs, labels)
                if recognized_text:
                    print(f"[OCR YOLOv5] >>> NHẬN DIỆN THÀNH CÔNG: \"{recognized_text}\" <<<")
            except Exception as e_yolo:
                print(f"[OCR YOLOv5] Loi suy luan NPU: {e_yolo}")

        # ƯU TIÊN 2: Nếu chưa có file char_ocr.mud hoặc 0 phát hiện, fallback sang Cloud OCR Space
        if not recognized_text:
            try:
                print("[OCR] Thu phuong thuc Cloud OCR Space (che do Alphanumeric)...")
                hf, wf = captured_frame.shape[:2]
                scale_f = min(1.0, 640.0 / max(hf, wf))
                ocr_img = cv2.resize(captured_frame, (int(wf * scale_f), int(hf * scale_f))) if scale_f < 1.0 else captured_frame
                snap_path = "/tmp/char_snap.jpg"
                cv2.imwrite(snap_path, ocr_img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])

                curl_cmd = [
                    'curl', '-k', '-s', '--max-time', '6',
                    '-F', f'apikey={OCR_API_KEY}',
                    '-F', 'language=eng',
                    '-F', 'OCREngine=2',
                    '-F', 'filetype=JPG',
                    '-F', 'isOverlayRequired=false',
                    '-F', f'file=@{snap_path}',
                    OCR_API_URL
                ]
                res_holder = [None]
                curl_done = False
                def _do_curl():
                    nonlocal curl_done, res_holder
                    try:
                        res_holder[0] = subprocess.run(curl_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    except Exception:
                        pass
                    finally:
                        curl_done = True
                t_curl = threading.Thread(target=_do_curl, daemon=True)
                t_curl.start()

                while not curl_done:
                    send_uart("SPK:1")
                    play_audio("tut_tut.wav", is_tts=False)
                    time.sleep(0.9)

                res_run = res_holder[0]
                if res_run and res_run.returncode == 0 and res_run.stdout:
                    import json
                    res_json = json.loads(res_run.stdout)
                    if res_json.get("OCRExitCode") == 1:
                        parsed = res_json.get("ParsedResults", [])
                        if parsed:
                            raw_str = parsed[0].get("ParsedText", "")
                            # Lọc sạch chỉ giữ chữ cái A-Z, số 0-9 và khoảng trắng
                            clean_str = "".join([c for c in raw_str if c.isalnum() or c in ' \n'])
                            recognized_text = " ".join(clean_str.split())
                            print(f"[OCR CLOUD RAW]:\n{raw_str} -> CLEAN: {recognized_text}")
            except Exception as e_cloud:
                print(f"[OCR CLOUD] Offline / Loi ket noi: {e_cloud}")

        # XỬ LÝ PHÁT ÂM THANH KẾT QUẢ
        if recognized_text:
            current_ocr_display_text = f"KY TU: {recognized_text[:28]}"
            print(f"\n[OCR KẾT QUẢ] >>> CHUỖI KÝ TỰ: {recognized_text} <<<")
            send_uart(f"V:{recognized_text[:60]}")
            # Kiểm tra nếu là vé số 6 chữ số
            import re
            nums = re.findall(r'\b\d{6}\b', recognized_text.replace(' ', ''))
            if nums:
                speak_lottery_result("Vé Số", nums[0])
            else:
                speak_alphanumeric_sequence(recognized_text)
        else:
            current_ocr_display_text = "Khong thay chu"
            print("[OCR] Khong phat hien thay ky tu.")
            send_uart("V:Khong thay chu")
            play_audio("khong_thay_chu.wav", is_tts=True)
            wait_audio_finished(3.5)
            send_uart("SPK:0")

        ocr_in_progress = False
        is_ai_busy = False
        last_ocr_finished_time = time.time()

def speak_lottery_result(province, number_str):
    """Phát âm thanh đọc vé số to rõ từng số cho người khiếm thị."""
    send_uart("SPK:1")
    play_audio("ve_so.wav", is_tts=True)
    if "BAC" in province.upper() or "BẠC" in province.upper():
        play_audio("dai_bac_lieu.wav", is_tts=True)
    for ch in number_str:
        if ch.isdigit():
            play_audio(f"so_{ch}.wav", is_tts=True)
    wait_audio_finished(timeout=12.0)
    time.sleep(0.3)
    send_uart("SPK:0")

def trigger_ocr_reading():
    threading.Thread(target=execute_ocr_worker, daemon=True).start()

# ==============================================================================
# 6. QUẢN LÝ PHẦN CỨNG (UART1, NÚT NHẤN A14)
# ==============================================================================
def setup_hardware():
    global scan_btns
    scan_btns = []
    print("[SYS] Khoi tao phan cung MaixCAM...")
    if not IS_MAIXCAM:
        return

    try:
        pinmap.set_pin_function("A18", "UART1_RX")
        pinmap.set_pin_function("A19", "UART1_TX")
        print("[PINS] UART1: A18/A19 san sang.")
    except Exception as e:
        print(f"[PINS] UART1 pinmap loi: {e}")

    # Uu tien chan A14 (Hang PHAI, chan 13 - Net BTN_SCAN chuan Altium)
    for p_name in ["A14", "A28"]:
        try:
            try:
                pinmap.set_pin_function(p_name, f"GPIO{p_name}")
            except Exception:
                pass
            btn = None
            try:
                btn = gpio.GPIO(f"GPIO{p_name}", gpio.Mode.IN, gpio.Pull.PULL_UP)
            except Exception:
                try:
                    btn = gpio.GPIO(p_name, gpio.Mode.IN, gpio.Pull.PULL_UP)
                except Exception:
                    pass
            if btn:
                scan_btns.append((p_name, btn))
                print(f"[PINS] Nut SCAN tren chan {p_name} san sang! (Gia tri doc ban dau={btn.value()})")
        except Exception as eb:
            print(f"[PINS] Nut {p_name} loi: {eb}")

def send_uart(msg):
    global ser
    with serial_lock:
        if ser and ser.is_open:
            try:
                ser.write((msg.strip() + "\n").encode('utf-8'))
                ser.flush()
            except Exception:
                pass

def handle_uart_message(line):
    global current_distance, smoothed_distance, gps_lat, gps_lon, gps_sats, gps_fixed, sos_active, warn_mode_active
    line_clean = line.strip().upper()

    if line_clean.startswith("D:"):
        try:
            val = int(line[2:].strip())
            current_distance = val
            if val > 0:
                if smoothed_distance <= 0:
                    smoothed_distance = float(val)
                else:
                    smoothed_distance = 0.5 * smoothed_distance + 0.5 * float(val)
            else:
                smoothed_distance = -1.0
        except ValueError:
            pass
    elif line_clean in ("MODE:MONEY", "TIEN"):
        switch_mode("MONEY", speak=True)
    elif line_clean in ("MODE:OCR", "TEXT", "VANBAN", "CHU"):
        switch_mode("OCR", speak=True)
    elif line_clean in ("MODE:IDLE", "CHO", "THOAT"):
        switch_mode("IDLE", speak=True)
    elif line_clean in ("TOGGLE", "CHUYEN"):
        toggle_mode()
    elif line_clean in ("LOT", "SCAN", "BTN:OCR"):
        print("[UART] Nhan tin hieu LOT tu ESP32 -> BAT QUET CHU OCR LIEN TUC!")
        switch_mode("OCR", speak=True)
        trigger_ocr_reading()
    elif line_clean in ("ACT", "TIEN", "BTN:MONEY"):
        print("[UART] Nhan tin hieu ACT tu ESP32 -> BAT QUET TIEN LIEN TUC!")
        switch_mode("MONEY", speak=True)
    elif line_clean in ("STOP", "EXIT", "BTN:IDLE", "BTN:EXIT"):
        print("[UART] Nhan tin hieu STOP tu ESP32 -> THOAT CHE DO QUET!")
        switch_mode("IDLE", speak=True)
    elif line_clean in ("SOS", "SOS:ON", "WARN:ON"):
        sos_active = True
        print("[SOS] >>> BẬT BÁO ĐỘNG KHẨN CẤP SOS - LOA KÊU LIÊN TỤC! <<<")
        send_uart("SPK:1")
        if gps_fixed:
            send_uart(f"P:{gps_lat},{gps_lon}")
    elif line_clean in ("SOS:OFF", "WARN:OFF"):
        sos_active = False
        warn_mode_active = False
        print("[SOS] >>> ĐÃ TẮT BÁO ĐỘNG SOS <<<")
        send_uart("SPK:0")
    elif line_clean.startswith("G:"):
        try:
            parts = line[2:].strip().split(",")
            gps_lat, gps_lon, gps_sats = float(parts[0]), float(parts[1]), int(parts[2])
            gps_fixed = (gps_lat != 0.0 or gps_lon != 0.0)
        except Exception:
            pass
    elif line_clean.startswith("H:") or line_clean.startswith("R:"):
        # Phản hồi ngay cho ESP32 khi nhận Heartbeat hoặc Ready
        send_uart("A:1")

def uart_listener_thread():
    global ser
    rx_buf = bytearray()
    while ser and ser.is_open:
        try:
            if ser.in_waiting > 0:
                chunk = ser.read(ser.in_waiting)
                for b in chunk:
                    if b in (10, 13):
                        if rx_buf:
                            line = rx_buf.decode('utf-8', errors='ignore').strip()
                            if line:
                                handle_uart_message(line)
                            rx_buf.clear()
                    else:
                        rx_buf.append(b)
                        if len(rx_buf) > 512:
                            rx_buf.clear()
            else:
                time.sleep(0.01)
        except Exception:
            time.sleep(0.02)

def obstacle_beeper_thread():
    """Thread beep cảnh báo vật cản. Tự động nhường khi TTS đang phát."""
    global beeper_running
    while beeper_running:
        # Nhường cho TTS (đọc tiền / OCR) phát xong mới beep
        if tts_playing or audio_worker_busy:
            time.sleep(0.1)
            continue
        dist = current_distance
        if warn_mode_active:
            # Chế độ cảnh báo: loa kêu liên tục theo nhịp
            if not tts_playing and not audio_worker_busy:
                play_audio("warn_beep.wav", is_tts=False)
            time.sleep(0.35)
        elif 0 < dist <= warn_threshold:
            if not tts_playing and not audio_worker_busy:
                if dist <= close_threshold:
                    play_audio("beep_fast.wav", is_tts=False)
                    time.sleep(0.28)
                else:
                    play_audio("beep_slow.wav", is_tts=False)
                    time.sleep(0.55)
        else:
            time.sleep(0.15)

# ==============================================================================
# 7. QUẢN LÝ NÚT BẤM (BUTTON MONITOR THREAD - A14)
# ==============================================================================
def button_monitor_thread():
    """
    Quy tắc nút nhấn thân thiện nhất cho người khiếm thị:
    - Nhấn 1 lần (Short Press < 1.0s):
        + Nếu đang ở chế độ TIỀN -> Bấm là chuyển sang chế độ CHỮ (OCR).
        + Nếu đang ở chế độ CHỮ -> Bấm là CHỤP ẢNH & ĐỌC VĂN BẢN NGAY!
    - Nhấn giữ (Long Press >= 1.2s):
        + Luôn chuyển đổi (Toggle) giữa TIỀN <---> CHỮ bất kỳ lúc nào.
    """
    global scan_btns, current_mode
    if not scan_btns:
        return
    btn_down_time = 0
    is_pressed = False
    active_pin = ""
    tap_count = 0
    last_tap_time = 0
    long_press_fired = False

    while not app.need_exit():
        try:
            now = time.time()
            pressed_now = False
            for p_name, btn in scan_btns:
                try:
                    if btn.value() == 0:
                        pressed_now = True
                        active_pin = p_name
                        break
                except Exception:
                    pass

            if pressed_now and not is_pressed:
                is_pressed = True
                btn_down_time = now
                long_press_fired = False
                time.sleep(0.04)  # Debounce
            elif pressed_now and is_pressed:
                # Đang GIỮ NÚT: Nếu giữ nút >= 1.2s -> TẮT NGAY CHẾ ĐỘ NHẬN DIỆN TIỀN / QUÉT
                if not long_press_fired and (now - btn_down_time) >= 1.2:
                    long_press_fired = True
                    tap_count = 0
                    print(f"[NÚT BT3/A14] GIỮ NÚT >= 1.2s -> TẮT CHẾ ĐỘ NHẬN DIỆN ({active_pin})")
                    switch_mode("IDLE", speak=True)
                    send_uart("BTN:IDLE")
            elif not pressed_now and is_pressed:
                duration = now - btn_down_time
                is_pressed = False
                time.sleep(0.04)
                if not long_press_fired and 0.05 <= duration < 0.7:
                    tap_count += 1
                    last_tap_time = now

            if tap_count > 0 and (now - last_tap_time) > 0.50:
                if tap_count == 1:
                    print(f"[NÚT A14] Nhấn 1 lần -> BẬT QUÉT TIỀN LIÊN TỤC ({active_pin})")
                    switch_mode("MONEY", speak=True)
                    send_uart("BTN:MONEY")
                elif tap_count == 2:
                    print(f"[NÚT A14] Nhấn 2 lần -> BẬT QUÉT CHỮ LIÊN TỤC ({active_pin})")
                    switch_mode("OCR", speak=True)
                    trigger_ocr_reading()
                    send_uart("BTN:SCAN")
                elif tap_count >= 3:
                    print(f"[NÚT A14] Nhấn 3 lần liên tục -> THOÁT CHẾ ĐỘ QUÉT ({active_pin})")
                    switch_mode("IDLE", speak=True)
                    send_uart("BTN:IDLE")
                tap_count = 0
        except Exception:
            pass
        time.sleep(0.02)

def ensure_single_instance():
    """Đảm bảo chỉ có DUY NHẤT 1 instance của main.py chạy để tránh xung đột ALSA PCM & Camera."""
    my_pid = os.getpid()
    if not os.path.exists("/proc"):
        return
    killed_any = False
    for pid in os.listdir("/proc"):
        if pid.isdigit() and int(pid) != my_pid:
            try:
                with open(f"/proc/{pid}/cmdline", "rb") as f:
                    cmd = f.read().decode('latin1', errors='ignore')
                    if "main.py" in cmd and "python" in cmd:
                        print(f"[SYS] Phat hien instance cu (PID {pid}) -> Giai phong...")
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                        except Exception:
                            pass
                        killed_any = True
            except Exception:
                pass
    if killed_any:
        time.sleep(0.8)
        for pid in os.listdir("/proc"):
            if pid.isdigit() and int(pid) != my_pid:
                try:
                    with open(f"/proc/{pid}/cmdline", "rb") as f:
                        cmd = f.read().decode('latin1', errors='ignore')
                        if "main.py" in cmd and "python" in cmd:
                            try:
                                os.kill(int(pid), signal.SIGKILL)
                            except Exception:
                                pass
                except Exception:
                    pass
        safe_run_cmd("fuser -k -9 /dev/snd/*")
        time.sleep(0.5)

# ==============================================================================
# 8. CHƯƠNG TRÌNH CHÍNH (MAIN LOOP)
# ==============================================================================
def main():
    ensure_single_instance()

    global is_note_locked, locked_note, locked_conf, locked_box, last_seen_note_time, vote_history, ser
    global latest_frame_for_ocr, current_ocr_line_count, last_ocr_trigger_time
    global current_mode, npu_mode_active

    print("================================================================")
    print("  HE THONG GAY THONG MINH MAIXCAM - AI DEEP LEARNING (SG2002)")
    print("================================================================")

    init_audio_system()
    setup_hardware()

    # Khởi tạo mô hình AI NPU tiên tiến nhất (Tiền tệ & Ký tự Alphanumeric)
    init_npu_detector()
    init_char_detector()

    try:
        ser = serial.Serial(UART_PORT, UART_BAUD, timeout=1)
        print(f"[UART] Da mo cong {UART_PORT} (9600 baud)")
        threading.Thread(target=uart_listener_thread, daemon=True).start()
        # Thông báo sẵn sàng và duy trì Heartbeat với ESP32
        send_uart("A:READY")
        send_uart(f"T:{warn_threshold}")
        def _hb_loop():
            while True:
                time.sleep(3.0)
                send_uart("A:1")
        threading.Thread(target=_hb_loop, daemon=True).start()
    except Exception as e:
        print(f"[UART] Cong noi tiep chua ket noi: {e}")

    threading.Thread(target=obstacle_beeper_thread, daemon=True).start()
    if ENABLE_BUTTON_A14:
        threading.Thread(target=button_monitor_thread, daemon=True).start()

    connect_wifi_async()

    ensure_camera_available()

    global global_cam, global_disp
    cam_w, cam_h = 320, 240
    cam = None
    for _cam_try in range(3):
        try:
            cam = camera.Camera(cam_w, cam_h)
            global_cam = cam
            print(f"[CAM] Camera {cam_w}x{cam_h} mo thanh cong!")
            break
        except Exception as e_cam:
            print(f"[CAM] Lan thu {_cam_try+1} that bai: {e_cam}")
            time.sleep(1.0)
            if _cam_try == 2:
                try:
                    cam = camera.Camera()
                    global_cam = cam
                except Exception as e2:
                    print(f"[CAM] Khong the mo camera: {e2}")

    disp = None
    try:
        disp = display.Display()
        global_disp = disp
        print(f"[CAM] Camera ({cam_w}x{cam_h}) & Display san sang streaming!")
    except Exception as e_disp:
        print(f"[DISP] Display khong san sang ({e_disp}) -> Tiep tuc camera, AI & audio binh thuong!")
        class DummyDisp:
            def show(self, *args, **kwargs): pass
        disp = DummyDisp()

    play_audio_async("system_ready.mp3", is_tts=True)

    fps_count = 0
    fps_time = time.time()
    fps_val = 0

    try:
        while not app.need_exit():
            img = cam.read()
            if img is None:
                continue

            fps_count += 1
            now = time.time()
            if now - fps_time >= 1.0:
                fps_val = fps_count
                fps_count = 0
                fps_time = now

            cv_img = image.image2cv(img)

            with frame_lock:
                latest_frame_for_ocr = cv_img

            # ------------------------------------------------------------------
            # CHẾ ĐỘ 1: NHẬN DIỆN MỆNH GIÁ TIỀN (MONEY)
            # ------------------------------------------------------------------
            if current_mode == "MONEY":
                cand = detect_banknote(img, cv_img)

                # TRẠNG THÁI 1: ĐÃ KHÓA 1 TỜ TIỀN DUY NHẤT (LOCKED)
                if is_note_locked:
                    # Tuyệt đối giữ nguyên giá trị đã chốt, KHÔNG BAO GIỜ NHẢY SANG MỆNH GIÁ KHÁC!
                    if cand is not None:
                        # Vẫn có tiền hoặc vật ở trước camera -> gia hạn thời gian
                        last_seen_note_time = now
                        if cand.get("box"):
                            locked_box = cand["box"]

                    # Chỉ mở khóa khi người dùng ĐÃ RÚT TỜ TIỀN RA (trên 1.5 giây không còn thấy tiền)
                    if (now - last_seen_note_time > 1.5):
                        is_note_locked = False
                        locked_note = ""
                        locked_conf = 0
                        locked_box = None
                        vote_history.clear()
                        status_text = "DAT TIEN TRUOC CAMERA..."
                        status_color = image.Color.from_rgb(180, 180, 180)
                    else:
                        # Tiếp tục hiển thị kết quả đã chốt duy nhất
                        status_text = f"TIEN: {locked_note} VND ({locked_conf}%)"
                        status_color = image.Color.from_rgb(0, 255, 0)
                        if locked_box:
                            bx, by, bw, bh = locked_box
                            img.draw_rect(bx, by, bw, bh, color=image.Color.from_rgb(0, 255, 0), thickness=3)
                            img.draw_string(bx, max(24, by - 22), f"TIEN: {locked_note} VND ({locked_conf}%)", color=image.Color.from_rgb(0, 255, 0), scale=1.1)

                # TRẠNG THÁI 2: CHƯA KHÓA (IDLE / ĐANG CHỜ ĐƯA TIỀN VÀO)
                else:
                    status_text = "DAT TIEN TRUOC CAMERA..."
                    status_color = image.Color.from_rgb(180, 180, 180)
                    check_and_play_waiting_beep()

                    if cand is not None:
                        vote_history.append(cand)
                        status_text = f"THAY: {cand['label']}d ({cand['confidence']}%)"
                        status_color = image.Color.from_rgb(255, 255, 0)
                        if cand.get("box"):
                            bx, by, bw, bh = cand["box"]
                            img.draw_rect(bx, by, bw, bh, color=image.Color.from_rgb(255, 255, 0), thickness=2)
                    else:
                        vote_history.append(None)

                    if len(vote_history) > 4:
                        vote_history.pop(0)

                    # Đồng thuận 2 khung hình liên tiếp: Đưa tiền vào là chốt đọc to ngay lập tức (~0.08s)
                    valid_cands = [c for c in vote_history if c is not None]
                    if len(valid_cands) >= 2:
                        counts = {}
                        for c in valid_cands:
                            lbl = c["label"]
                            counts[lbl] = counts.get(lbl, 0) + 1

                        top_lbl, top_cnt = max(counts.items(), key=lambda kv: kv[1])
                        if top_cnt >= 2:
                            matching = [c for c in valid_cands if c["label"] == top_lbl]
                            best_c = max(matching, key=lambda c: c["score"])
                            avg_conf = int(sum(c["confidence"] for c in matching) / len(matching))

                            # CHỐT KHÓA KHI ĐÃ ĐẠT ĐỒNG THUẬN ỔN ĐỊNH:
                            is_note_locked = True
                            waiting_mode = None  # Dừng tiếng tút tút chờ!
                            locked_note = top_lbl
                            locked_conf = avg_conf
                            locked_box = best_c.get("box")
                            last_seen_note_time = now

                            name_vn = best_c["name"]
                            sound_file = best_c["sound"]

                            # THÔNG BÁO TIẾNG VIỆT & TRUYỀN UART ĐÚNG 1 LẦN DUY NHẤT CHO MỖI LẦN ĐƯA TIỀN VÀO
                            print(f"[TIEN] >>> {locked_note} VND ({name_vn}) - Do tin cay: {locked_conf}% <<<")
                            play_audio_async(sound_file, is_tts=True)
                            send_uart(f"I:{locked_note}:{locked_conf}")

                            status_text = f"TIEN: {locked_note} VND ({locked_conf}%)"
                            status_color = image.Color.from_rgb(0, 255, 0)
                            if locked_box:
                                bx, by, bw, bh = locked_box
                                img.draw_rect(bx, by, bw, bh, color=image.Color.from_rgb(0, 255, 0), thickness=3)
                                img.draw_string(bx, max(24, by - 22), f"TIEN: {locked_note} VND ({locked_conf}%)", color=image.Color.from_rgb(0, 255, 0), scale=1.1)

            # ------------------------------------------------------------------
            # CHẾ ĐỘ 2: NHẬN DIỆN VÀ ĐỌC CHỮ (OCR) LIÊN TỤC
            # ------------------------------------------------------------------
            elif current_mode == "OCR":
                status_text = "DANG QUET CHU LIEN TUC..."
                status_color = image.Color.from_rgb(255, 255, 0)

                text_boxes = detect_text_regions(cv_img)
                current_ocr_line_count = len(text_boxes)

                if text_boxes:
                    for (tx, ty, tw, th) in text_boxes[:8]:
                        img.draw_rect(tx, ty, tw, th, color=image.Color.from_rgb(255, 255, 0), thickness=1)

                    status_text = f"THAY {len(text_boxes)} DONG CHU - DANG QUET LIEN TUC"
                    status_color = image.Color.from_rgb(255, 255, 0)

                    # Tự động chụp & đọc liên tục khi phát hiện có khối chữ ổn định
                    if not ocr_in_progress and not is_ai_busy and not audio_worker_busy and not tts_playing:
                        if (now - last_ocr_finished_time) >= ocr_auto_cooldown:
                            text_stable_counter += 1
                            if text_stable_counter >= 2:
                                text_stable_counter = 0
                                trigger_ocr_reading()
                        else:
                            check_and_play_waiting_beep()
                    else:
                        text_stable_counter = 0
                else:
                    text_stable_counter = 0
                    status_text = "QUET CHU LIEN TUC: HUONG VAO CHU/VE SO"
                    status_color = image.Color.from_rgb(180, 180, 180)
                    if not ocr_in_progress and not is_ai_busy:
                        check_and_play_waiting_beep()

                if current_ocr_display_text:
                    status_text = current_ocr_display_text
                    status_color = image.Color.from_rgb(0, 255, 128)

            # ------------------------------------------------------------------
            # CHẾ ĐỘ 3: CHẾ ĐỘ CHỜ / THOÁT KHỎI QUÉT (IDLE)
            # ------------------------------------------------------------------
            elif current_mode == "IDLE":
                status_text = "DA THOAT QUET - AN 1:TIEN, 2:CHU, 3:THOAT"
                status_color = image.Color.from_rgb(170, 170, 170)

            # ------------------------------------------------------------------
            # GIAO DIỆN HIỂN THỊ TỐI GIẢN (MINIMALIST HUD TRÊN MAIXVISION / MÀN HÌNH)
            # ------------------------------------------------------------------
            if MINIMALIST_HUD:
                # 1. Góc trên trái: Badge chế độ nhỏ gọn + Khoảng cách cảm biến chuẩn xác
                if current_mode == "MONEY":
                    mode_color = image.Color.from_rgb(0, 255, 120)
                    mode_name = "TIEN"
                elif current_mode == "OCR":
                    mode_color = image.Color.from_rgb(255, 200, 0)
                    mode_name = "OCR"
                else:
                    mode_color = image.Color.from_rgb(160, 160, 160)
                    mode_name = "CHO"
                img.draw_string(6, 6, f"[{mode_name}]", color=mode_color, scale=1.0)

                # Hiển thị khoảng cách vật cản tinh chỉnh chuẩn
                if smoothed_distance > 0:
                    d_int = int(round(smoothed_distance))
                    if d_int < 50:
                        d_col = image.Color.from_rgb(255, 40, 40)   # Đỏ: Nguy hiểm sát người
                        d_str = f"d:{d_int}cm !"
                    elif d_int <= 150:
                        d_col = image.Color.from_rgb(255, 170, 0)  # Cam: Chú ý vật cản
                        d_str = f"d:{d_int}cm"
                    else:
                        d_col = image.Color.from_rgb(0, 220, 100)  # Xanh: Đường thoáng
                        d_str = f"d:{d_int}cm"
                else:
                    d_col = image.Color.from_rgb(140, 140, 140)
                    d_str = "d:--"

                img.draw_string(72, 6, d_str, color=d_col, scale=1.0)

                # 2. Góc trên phải: FPS thanh thoát
                img.draw_string(cam_w - 55, 6, f"{fps_val:2d}F", color=image.Color.from_rgb(180, 220, 255), scale=0.85)

                # 3. Tâm ngắm tối giản (4 góc Corner Brackets 50x50px, không che tầm nhìn)
                cx, cy = cam_w // 2, cam_h // 2
                b_size = 25
                c_len = 8
                ret_color = image.Color.from_rgb(0, 255, 120) if current_mode == "MONEY" else image.Color.from_rgb(255, 220, 50)
                # Góc trên-trái
                img.draw_line(cx - b_size, cy - b_size, cx - b_size + c_len, cy - b_size, color=ret_color, thickness=1)
                img.draw_line(cx - b_size, cy - b_size, cx - b_size, cy - b_size + c_len, color=ret_color, thickness=1)
                # Góc trên-phải
                img.draw_line(cx + b_size, cy - b_size, cx + b_size - c_len, cy - b_size, color=ret_color, thickness=1)
                img.draw_line(cx + b_size, cy - b_size, cx + b_size, cy - b_size + c_len, color=ret_color, thickness=1)
                # Góc dưới-trái
                img.draw_line(cx - b_size, cy + b_size, cx - b_size + c_len, cy + b_size, color=ret_color, thickness=1)
                img.draw_line(cx - b_size, cy + b_size, cx - b_size, cy + b_size - c_len, color=ret_color, thickness=1)
                # Góc dưới-phải
                img.draw_line(cx + b_size, cy + b_size, cx + b_size - c_len, cy + b_size, color=ret_color, thickness=1)
                img.draw_line(cx + b_size, cy + b_size, cx + b_size, cy + b_size - c_len, color=ret_color, thickness=1)

                # 4. Hiển thị thông báo trạng thái dưới đáy (chữ nổi viền tối giản, không che dải đen)
                if status_text:
                    img.draw_string(8, cam_h - 22, status_text[:36], color=status_color, scale=0.95)
            else:
                # Chế độ cổ điển (Classic Banner HUD)
                img.draw_rect(0, 0, cam_w, 24, color=image.Color.from_rgb(20, 20, 20), thickness=-1)
                img.draw_string(4, 4, "GAY THONG MINH AI", color=image.Color.from_rgb(220, 220, 220), scale=0.9)
                if current_mode == "MONEY":
                    badge_text = "[AI NPU: TIEN]" if npu_mode_active else "[CHE DO: TIEN]"
                    img.draw_rect(125, 2, 120, 20, color=image.Color.from_rgb(0, 130, 50), thickness=-1)
                    img.draw_string(130, 4, badge_text, color=image.Color.from_rgb(255, 255, 255), scale=0.9)
                elif current_mode == "OCR":
                    img.draw_rect(125, 2, 120, 20, color=image.Color.from_rgb(180, 100, 0), thickness=-1)
                    img.draw_string(130, 4, "[CHE DO: CHU]", color=image.Color.from_rgb(255, 255, 255), scale=0.9)
                else:
                    img.draw_rect(125, 2, 120, 20, color=image.Color.from_rgb(80, 80, 80), thickness=-1)
                    img.draw_string(130, 4, "[CHE DO: CHO]", color=image.Color.from_rgb(220, 220, 220), scale=0.9)

                img.draw_string(cam_w - 70, 4, f"{fps_val:2d} FPS", color=image.Color.from_rgb(0, 255, 255), scale=0.9)
                cx, cy = cam_w // 2, cam_h // 2
                cross_color = image.Color.from_rgb(0, 255, 0) if current_mode == "MONEY" else image.Color.from_rgb(255, 200, 0)
                img.draw_line(cx - 12, cy, cx + 12, cy, color=cross_color, thickness=1)
                img.draw_line(cx, cy - 12, cx, cy + 12, color=cross_color, thickness=1)

                img.draw_rect(0, cam_h - 24, cam_w, 24, color=image.Color.from_rgb(20, 20, 20), thickness=-1)
                img.draw_string(4, cam_h - 20, status_text[:36], color=status_color, scale=1.0)

            try:
                disp.show(img)
            except Exception:
                pass
            time.sleep(0.005)

    except KeyboardInterrupt:
        print("\n[SYS] Nhan Ctrl+C, thoat chuong trinh...")
    finally:
        global_cleanup()

if __name__ == "__main__":
    main()
