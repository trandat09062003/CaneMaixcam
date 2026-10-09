# Hệ Thống Gậy Thông Minh Hỗ Trợ Người Khiếm Thị (Smart Cane)

Dự án thiết kế và triển khai thiết bị gậy thông minh hỗ trợ người khiếm thị di chuyển và sinh hoạt độc lập. Hệ thống kết hợp bộ đôi xử lý: **Sipeed MaixCAM Lite** (xử lý thị giác máy tính Edge AI, nhận diện tiền tệ, nhận diện ký tự và phát âm thanh) và **ESP32 DOIT DevKit V1** (quản lý cảm biến khoảng cách, định vị GPS và truyền thông khẩn cấp 4G LTE).

---

## 1. Kiến Trúc Phần Cứng & Phân Chia Tác Vụ

```
[ Camera MIPI CSI ] ────────> [ Sipeed MaixCAM Lite (U2) ] ────────> [ Loa 4Ω 3W (VOP/VON) ]
                                 (Sophgo SG2002 - 1 TOPS)
                                      │        ▲
                           UART1      │        │  UART1
                        (/dev/ttyS1)  ▼        │  (GPIO16/17)
                              [ ESP32 DevKit V1 (U3) ]
                                  │       │       │
                                  ▼       ▼       ▼
                            [AJ-SR04M] [NEO-6M] [A7680C 4G]
                            (Siêu âm)   (GPS)   (Telegram)
```

### 1.1. Khối xử lý trung tâm U2: Sipeed MaixCAM Lite (Linux / MaixPy v4)
* **Bộ xử lý trung tâm**: SoC Sophgo SG2002 (lõi đơn ARM Cortex-A53 1.0 GHz kết hợp nhân RISC-V 1.0 GHz), tích hợp NPU 1.0 TOPS @ INT8.
* **Cảm biến hình ảnh**: Camera MIPI CSI thu nhận khung hình trực tiếp.
* **Mô hình AI nhận diện tiền tệ**: Kiến trúc **YOLOv5n** (`vnd_money_v2.cvimodel`), 6 mệnh giá tiền polymer Việt Nam (10.000đ, 20.000đ, 50.000đ, 100.000đ, 200.000đ, 500.000đ), chạy trực tiếp trên NPU với độ trễ ~30ms, tốc độ ~30 FPS ở độ phân giải 320x320.
* **Mô hình AI nhận diện ký tự OCR offline**: Kiến trúc **YOLOv5n** (`char_ocr_v2.cvimodel`), nhận diện 36 ký tự (số `0-9` và chữ cái `a-z`) phục vụ đọc biển báo, nhãn sản phẩm và vé số không phụ thuộc Internet.
* **OCR Cloud tiếng Việt (Fallback)**: Khi người dùng yêu cầu đọc tài liệu/văn bản dài, hệ thống chụp ảnh nén và gửi tới API OCR Space thông qua kết nối WiFi.
* **Phát âm thanh trực tiếp**: Giải mã và phát file âm thanh giọng đọc tiếng Việt trực tiếp qua mạch khuếch đại công suất onboard (chân differential VOP/VON nối loa 4Ω 3W).
* **Đo điện áp pin**: Cầu phân áp 300kΩ / 100kΩ đưa tín hiệu pin 18650 vào chân ADC để cảnh báo pin yếu.
* **Giao tiếp liên bo mạch**: Cổng UART1 (`/dev/ttyS1`, Baud 9600, chân A18-RX, A19-TX) kết nối trực tiếp với ESP32.

### 1.2. Khối ngoại vi & cứu hộ U3: ESP32 DOIT DevKit V1 (Arduino C++)
* **Cảm biến khoảng cách**: AJ-SR04M (đầu dò siêu âm chống nước) quét liên tục chướng ngại vật phía trước theo 2 mức ngưỡng (cảnh báo 40-80cm, dừng khẩn cấp <40cm).
* **Định vị vệ tinh**: Module GPS NEO-6M / ATGM336H đọc dữ liệu NMEA thời gian thực qua Serial2 (GPIO16/17).
* **Truyền thông 4G LTE**: Module SIMCom A7680C điều khiển bằng tập lệnh AT qua Serial1 (GPIO26/27), tự động kết nối Internet và gửi dữ liệu cảnh báo khẩn cấp.
* **Nút bấm & Cứu hộ**: Giám sát nút SOS, nút chuyển chế độ, quản lý LED tín hiệu và gửi tọa độ Google Maps về Telegram người thân khi xảy ra sự cố.

### 1.3. Khối quản lý nguồn
* **IC quản lý nguồn**: IP5306 tích hợp sạc/xả pin Li-ion 18650, tự động kích boost 5V/2A cấp cho toàn bộ hệ thống.
* **Nút bấm nguồn BT1**: Nhấn 1 lần để bật nguồn, nhấn giữ 3-5 giây để tắt nguồn, nhấn đúp để xem dung lượng pin hiển thị qua 4 LED vạch.

---

## 2. Cấu Trúc Thư Mục Dự Án

```text
gay_nguoi_mu_maixcam/
├── gaynguoimu/                               # Thiết kế phần cứng Altium Designer
│   ├── gaynguoimu.PrjPcb                     # Dự án mạch in Altium
│   ├── Sheet2.SchDoc                         # Sơ đồ nguyên lý (Schematic)
│   ├── PCB3.PcbDoc                           # Bản vẽ mạch in (PCB Layout)
│   └── gaynguoimu.BomDoc                     # Bảng danh mục linh kiện (BOM)
│
├── Gay_Nguoi_Mu/                             # Mã nguồn nhúng & tài nguyên thực thi
│   ├── firmware/
│   │   ├── esp32_periph/                     # Mã nguồn Arduino C++ cho ESP32 (U3)
│   │   │   ├── esp32_periph.ino              # Vòng lặp điều khiển chính
│   │   │   ├── gps_module.h                  # Giải mã bản tin GPS NMEA
│   │   │   ├── sim_module.h                  # Xử lý AT Command SIM A7680C & Telegram
│   │   │   └── pins.h                        # Khai báo cấu hình chân GPIO ESP32
│   │   │
│   │   └── maixcam_app/                      # Ứng dụng Python chính trên MaixCAM (U2)
│   │       ├── main.py                       # Core app: Camera, NPU, UART, Audio, Cloud OCR
│   │       ├── audio/                        # Thư mục âm thanh giọng nói tiếng Việt (.mp3, .wav)
│   │       │   ├── system_ready.mp3          # Âm báo khởi động hoàn tất
│   │       │   ├── battery_low.mp3           # Cảnh báo pin yếu
│   │       │   ├── muoi_nghin_dong.mp3       # Âm báo mệnh giá tiền
│   │       │   ├── so_0.wav ... so_9.wav     # Âm báo đọc số
│   │       │   └── chu_a.wav ... chu_z.wav   # Âm báo đọc ký tự
│   │       └── models/                       # File mô hình NPU đã lượng tử hóa (.cvimodel, .mud)
│   │           ├── vnd_money_v2.cvimodel     # Model YOLOv5n nhận diện tiền (mới)
│   │           ├── vnd_money_v2.mud          # File cấu hình nhãn & scale tiền v2
│   │           ├── char_ocr_v2.cvimodel      # Model YOLOv5n nhận diện 36 ký tự (mới)
│   │           ├── char_ocr_v2.mud           # File cấu hình nhãn & scale ký tự v2
│   │           ├── vnd_currency.cvimodel     # Model tiền gốc dự phòng
│   │           └── vnd_currency.mud
│   │
│   ├── vnd_money_v2.onnx                     # ONNX tiền tệ chuẩn Opset 11 (320x320)
│   ├── char_ocr_v2.onnx                      # ONNX 36 ký tự chuẩn Opset 11 (320x320)
│   ├── best.onnx                             # ONNX tiền tệ gốc
│   ├── best_char36.onnx                      # ONNX ký tự gốc
│   └── calibration_images.zip                # Tập 100 ảnh mẫu phục vụ lượng tử hóa INT8
│
├── dataset_money/                            # Dữ liệu ảnh thực tế 6 mệnh giá tiền polymer
│   ├── 10000/                                # 10.000 VNĐ (mặt trước / mặt sau)
│   ├── 20000/                                # 20.000 VNĐ
│   ├── 50000/                                # 50.000 VNĐ
│   ├── 100000/                               # 100.000 VNĐ
│   ├── 200000/                               # 200.000 VNĐ
│   └── 500000/                               # 500.000 VNĐ
│
├── dataset_chars/                            # Dữ liệu ảnh thực tế 36 lớp ký tự (0-9, A-Z)
│
├── scripts/                                  # Công cụ chuẩn bị dữ liệu, huấn luyện và kiểm thử
│   ├── prepare_money_dataset.py              # Tiền xử lý, lọc lỗi và tự động gán nhãn dataset tiền
│   ├── train_money_v2.py                     # Huấn luyện YOLOv5n tiền tệ và xuất ONNX/MUD
│   ├── prepare_char_dataset_real.py          # Trích xuất contour và gán nhãn dataset ký tự
│   ├── train_char_model.py                   # Huấn luyện YOLOv5n 36 ký tự và xuất ONNX/MUD
│   ├── test_trained_model.py                 # Kiểm thử độ chính xác mô hình trên tập validation
│   └── deploy_to_maixcam.py                  # Script đồng bộ firmware lên MaixCAM qua SSH
│
├── summary.txt                               # Bảng đối chiếu nối chân phần cứng chi tiết
└── README.md                                 # Tài liệu kỹ thuật dự án
```

---

## 3. Sơ Đồ Đấu Nối Phần Cứng (Hardware Pinout)

Chi tiết nối dây giữa MaixCAM, ESP32, IP5306, cảm biến siêu âm, GPS, module SIM và nút bấm được quy định chuẩn tại:

👉 **[summary.txt](file:///c:/Users/Public/Documents/Altium/08052026/gay_nguoi_mu_maixcam/summary.txt)**

### Tóm tắt giao tiếp chính:
| Tín hiệu | Chân Sipeed MaixCAM (U2) | Chân ESP32 DevKit (U3) | Chức năng |
| :--- | :--- | :--- | :--- |
| **UART1_TX** | A19 (TXD1) | GPIO16 (RX2) | MaixCAM gửi trạng thái / lệnh sang ESP32 |
| **UART1_RX** | A18 (RXD1) | GPIO17 (TX2) | ESP32 gửi sự kiện nút bấm / khoảng cách sang MaixCAM |
| **GND** | Chân GND bo mạch | Chân GND bo mạch | Nối chung mass toàn hệ thống |
| **VOP / VON** | Cổng Speaker Out | — | Đầu ra khuếch đại công suất nối trực tiếp loa 4Ω 3W |
| **ADC Pin** | Chân ADC onboard | — | Đo điện áp qua cầu chia 300k/100k nối cực dương cell 18650 |

---

## 4. Các Mô Hình Edge AI Trên NPU Sophgo SG2002

Cả hai mô hình đều được chuẩn hóa theo cùng một kiến trúc **YOLOv5n** để đảm bảo tính đồng nhất, tốc độ suy luận nhanh và tương thích hoàn toàn với trình biên dịch TPU-MLIR của chip Sophgo SG2002:

| Mô hình | Tệp ONNX xuất ra | Tệp cấu hình MaixPy | Tệp nhị phân NPU | Số lớp Conv | Kích thước Input | Kích thước Output |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Tiền tệ (VND)** | `vnd_money_v2.onnx` | `vnd_money_v2.mud` | `vnd_money_v2.cvimodel` | 76 | `[1, 3, 320, 320]` | `[1, 10, 2100]` *(4 box + 6 nhãn)* |
| **Ký tự (OCR 36)** | `char_ocr_v2.onnx` | `char_ocr_v2.mud` | `char_ocr_v2.cvimodel` | 76 | `[1, 3, 320, 320]` | `[1, 40, 2100]` *(4 box + 36 nhãn)* |

### Thứ tự nhãn (Labels mapping):
* **Tiền tệ (6 class)**: `10000`, `20000`, `50000`, `100000`, `200000`, `500000`.
* **Ký tự (36 class)**: `0, 1, 2, 3, 4, 5, 6, 7, 8, 9, a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z`.

---

## 5. Quy Trình Huấn Luyện & Chuyển Đổi Mô Hình

### 5.1. Huấn luyện mô hình tiền tệ
```bash
# Bước 1: Gán nhãn tự động dữ liệu ảnh trong dataset_money/
python scripts/prepare_money_dataset.py

# Bước 2: Huấn luyện YOLOv5n và xuất ONNX chuẩn Opset 11
python scripts/train_money_v2.py
```

### 5.2. Huấn luyện mô hình nhận diện ký tự
```bash
# Bước 1: Gán nhãn bounding box từ ảnh trong dataset_chars/
python scripts/prepare_char_dataset_real.py

# Bước 2: Huấn luyện YOLOv5n 36 ký tự và xuất ONNX
python scripts/train_char_model.py
```

### 5.3. Chuyển đổi sang .cvimodel trên MaixHub
1. Truy cập công cụ chuyển đổi trực tuyến: [https://maixhub.com/model/convert](https://maixhub.com/model/convert)
2. Chọn phần cứng mục tiêu: **MaixCAM** (Chip Sophgo SG2002 / CV181x).
3. Tải lên tệp ONNX:
   * Cho mô hình tiền: chọn `Gay_Nguoi_Mu/vnd_money_v2.onnx`
   * Cho mô hình ký tự: chọn `Gay_Nguoi_Mu/char_ocr_v2.onnx`
4. Chọn loại mô hình: **YOLOv5** (hoặc `YOLOv5u Detect`), độ phân giải `320x320`.
5. Tải lên tệp hiệu chuẩn: `Gay_Nguoi_Mu/calibration_images.zip`.
6. Nhập nhãn (Labels):
   * Mô hình tiền: `10000, 20000, 50000, 100000, 200000, 500000`
   * Mô hình ký tự: `0, 1, 2, 3, 4, 5, 6, 7, 8, 9, a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z`
7. Bấm **Convert**, tải gói zip về máy và giải nén tệp `.cvimodel` vào thư mục `Gay_Nguoi_Mu/firmware/maixcam_app/models/`.

---

## 6. Hướng Dẫn Nạp Chương Trình & Triển Khai

### 6.1. Nạp chương trình cho ESP32 ngoại vi (U3)
1. Mở Arduino IDE (phiên bản 2.x trở lên).
2. Thêm URL Board Manager ESP32: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`.
3. Cài đặt package **esp32** của Espressif (khuyên dùng phiên bản 3.0.x).
4. Mở tệp: `Gay_Nguoi_Mu/firmware/esp32_periph/esp32_periph.ino`.
5. Chọn Board **ESP32 Dev Module**, chọn đúng cổng COM và tiến hành nạp code.

### 6.2. Triển khai ứng dụng lên Sipeed MaixCAM Lite (U2)
Kết nối MaixCAM với PC qua cáp Type-C (giao diện mạng USB RNDIS) hoặc qua WiFi cục bộ:
```bash
python scripts/deploy_to_maixcam.py
```
Script sẽ tự động:
1. Sao chép toàn bộ mã nguồn `main.py`, thư mục âm thanh `audio/` và các mô hình trong `models/` lên thư mục `/root/maixcam_app/` trên thiết bị.
2. Cấu hình dịch vụ tự khởi động qua systemd:
   ```ini
   [Unit]
   Description=Smart Cane Firmware Service
   After=network.target

   [Service]
   Type=simple
   WorkingDirectory=/root/maixcam_app
   ExecStart=/usr/bin/python3 /root/maixcam_app/main.py
   Restart=always
   RestartSec=3

   [Install]
   WantedBy=multi-user.target
   ```
3. Khởi chạy dịch vụ nền `smartcane.service`.

---

## 7. Quy Chuẩn Vận Hành Thiết Bị

* **Bật nguồn thiết bị**: Nhấn nút nguồn BT1 trên mạch IP5306 một lần. Hệ thống khởi động trong ~8 giây, loa phát âm thông báo *"Hệ thống đã sẵn sàng"*.
* **Tắt nguồn thiết bị**: Nhấn giữ nút nguồn BT1 từ 3 đến 5 giây cho đến khi đèn LED tắt hẳn.
* **Chế độ nhận diện tiền tệ**: 
  * Hướng camera vào tờ tiền ở cự ly 15-30cm, nhấn nút quét tiền 1 lần (hoặc nhấn nút từ ESP32 gửi lệnh UART `CMD:MONEY`).
  * NPU thực thi nhận diện và loa phát trực tiếp giọng đọc: *"Mười nghìn đồng"*, *"Năm mươi nghìn đồng"*...
* **Chế độ đọc văn bản (OCR)**: 
  * Hướng camera vào trang sách, biển báo hoặc vé số, nhấn nút OCR (hoặc lệnh UART `CMD:OCR`).
  * Thiết bị ưu tiên nhận diện nhanh 36 ký tự cục bộ qua NPU. Nếu phát hiện đoạn văn bản dài, thiết bị tự động chuyển tiếp qua Cloud OCR và đọc nội dung tài liệu.
* **Cảnh báo va chạm siêu âm**: 
  * Cảm biến AJ-SR04M quét liên tục:
    * Khoảng cách **40cm - 80cm**: Loa phát tiếng bíp ngắt quãng nhắc nhở chú ý.
    * Khoảng cách **dưới 40cm**: Loa phát tiếng bíp dồn dập cảnh báo dừng bước ngay lập tức.
* **Kích hoạt cứu hộ khẩn cấp (SOS)**: 
  * Nhấn đúp nút SOS: Đèn LED cảnh báo chớp nháy liên tục, còi báo động kích hoạt.
  * ESP32 chốt tọa độ GPS mới nhất từ module NEO-6M, truyền qua module 4G A7680C gửi tin nhắn cảnh báo kèm đường dẫn vị trí Google Maps trực tiếp về Telegram người giám hộ.
