# GẬY THÔNG MINH HỖ TRỢ NGƯỜI KHIẾM THỊ (SMART CANE)

Đề tài nghiên cứu và chế tạo thiết bị gậy thông minh tích hợp camera xử lý hình ảnh và cảm biến cảnh báo sớm, hỗ trợ người khiếm thị nhận biết môi trường xung quanh, nhận diện tiền giấy, đọc chữ và gửi tín hiệu định vị khẩn cấp.

---

## 1. Tổng quan hệ thống phần cứng

Hệ thống được xây dựng trên cấu trúc xử lý phân tán với 2 vi điều khiển chính:

- **Bộ xử lý hình ảnh (U2):** Module **Sipeed MaixCAM** (SoC Sophgo SG2002 - lõi ARM Cortex-A53 + NPU 1.0 TOPS @ INT8). Đảm nhiệm nhận diện mệnh giá tiền polymer Việt Nam, nhận diện ký tự quang học (OCR) và phát âm thanh giọng nói tiếng Việt qua loa.
- **Bộ điều khiển ngoại vi & cứu hộ (U3):** Vi điều khiển **ESP32 DOIT DevKit V1** (30 chân). Đảm nhiệm đo khoảng cách chướng ngại vật bằng cảm biến siêu âm chống nước AJ-SR04M, thu tọa độ từ module GPS NEO-6M, quản lý nút bấm SOS và gửi tin nhắn cảnh báo vị trí qua mạng di động 4G (SIMCom A7680C) về Telegram.
- **Khối nguồn:** Mạch tích hợp IC IP5306, sử dụng 1 cell pin Li-ion 18650, cấp nguồn 5V ổn định cho toàn bộ hệ thống qua các cổng chuyển đổi.

```
                  ┌───────────────────────────────┐
                  │    Camera MIPI CSI (OV5647)   │
                  └──────────────┬────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │    Sipeed MaixCAM (SG2002)    │──────► Loa 4 Ohm 3W
                  │  (Xử lý hình ảnh, Tiền & OCR) │
                  └──────────────┬────────────────┘
                                 │
                            UART1 (9600)
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │      ESP32 DevKit V1 (30P)    │
                  │ (Cảm biến, Định vị & Cứu hộ)  │
                  └──────┬───────┬────────┬───────┘
                         │       │        │
                         ▼       ▼        ▼
                      AJ-SR04M NEO-6M   A7680C
                     (Siêu âm)  (GPS)   (4G LTE)
```

---

## 2. Các chức năng chính

1. **Nhận diện tiền polymer Việt Nam:**
   - Hỗ trợ 6 mệnh giá: 10.000đ, 20.000đ, 50.000đ, 100.000đ, 200.000đ, 500.000đ.
   - Nhận diện trực tiếp trên phần cứng NPU (thời gian xử lý ~30ms/frame).
   - Cơ chế chốt giá trị thông minh: chỉ phát âm thanh đúng 1 lần khi đưa tiền vào vùng nhận diện, không lặp lại gây khó chịu.

2. **Đọc văn bản và ký tự (OCR):**
   - Chế độ offline: nhận diện 36 ký tự cơ bản (0-9, A-Z) phục vụ đọc số nhà, biển báo, vé số.
   - Chế độ online: chụp ảnh độ nét cao và gửi qua dịch vụ OCR tiếng Việt khi có kết nối WiFi để đọc toàn bộ đoạn văn bản dài.

3. **Cảnh báo vật cản bằng cảm biến siêu âm:**
   - Cảm biến AJ-SR04M chống nước quét liên tục góc nhìn phía trước.
   - Cảnh báo phân tầng: mức nhắc nhở (40 - 80cm) phát tiếng bíp ngắt quãng; mức nguy hiểm (< 40cm) phát tiếng bíp dồn dập.

4. **Định vị GPS và cảnh báo khẩn cấp (SOS):**
   - Khi người dùng nhấn nút SOS trên thân gậy, thiết bị nhấp nháy LED cảnh báo.
   - ESP32 trích xuất tọa độ kinh độ/vĩ độ từ GPS NEO-6M, kích hoạt module 4G A7680C gửi tin nhắn kèm liên kết Google Maps trực tiếp về ứng dụng Telegram của người thân.

---

## 3. Cấu trúc thư mục

```
gay_nguoi_mu_maixcam/
├── gaynguoimu/                               # Bản vẽ thiết kế phần cứng Altium Designer
│   ├── gaynguoimu.PrjPcb                     # Dự án Altium
│   ├── Sheet2.SchDoc                         # Sơ đồ nguyên lý
│   └── PCB3.PcbDoc                           # Thiết kế mạch in PCB
│
├── Gay_Nguoi_Mu/
│   ├── firmware/
│   │   ├── esp32_periph/                     # Mã nguồn nạp cho ESP32 (Arduino C++)
│   │   │   ├── esp32_periph.ino              # Chương trình chính
│   │   │   ├── gps_module.h                  # Thư viện xử lý GPS NMEA
│   │   │   ├── sim_module.h                  # Thư viện lệnh AT cho SIM A7680C & Telegram
│   │   │   └── pins.h                        # Định nghĩa sơ đồ chân GPIO
│   │   │
│   │   └── maixcam_app/                      # Ứng dụng chạy trên MaixCAM (Python 3)
│   │       ├── main.py                       # Chương trình điều khiển camera, NPU và âm thanh
│   │       ├── audio/                        # Tập hợp file âm thanh giọng đọc tiếng Việt
│   │       └── models/                       # File mô hình (.cvimodel, .mud)
│   │           ├── vnd_money_v2.cvimodel     # Model nhận diện tiền polymer (v2)
│   │           ├── vnd_money_v2.mud          # Cấu hình nhãn tiền
│   │           ├── char_ocr_v2.cvimodel      # Model nhận diện ký tự OCR (v2)
│   │           └── char_ocr_v2.mud           # Cấu hình nhãn ký tự
│   │
│   ├── vnd_money_v2.onnx                     # File mô hình ONNX tiền (320x320)
│   └── char_ocr_v2.onnx                      # File mô hình ONNX ký tự (320x320)
│
├── dataset_money_yolo.zip                    # Bộ dữ liệu tiền VND chuẩn format YOLO
├── dataset_chars_yolo.zip                    # Bộ dữ liệu ký tự chuẩn format YOLO
├── Train_MaixCAM_GoogleColab.ipynb           # Notebook huấn luyện mô hình trên Google Colab
├── HUONG_DAN_TRAIN_COLAB.md                  # Hướng dẫn chi tiết cách train lại model
├── sync_and_test_maixcam.py                  # Script tự động đồng bộ code & model vào MaixCAM
├── summary.txt                               # Bảng tra cứu đấu nối chân phần cứng
└── README.md
```

---

## 4. Sơ đồ kết nối phần cứng

### 4.1. Kết nối giữa MaixCAM và ESP32
| Chân trên MaixCAM | Chân trên ESP32 | Mô tả chức năng |
| :--- | :--- | :--- |
| **A19 (UART1_TX)** | **GPIO16 (RX2)** | MaixCAM truyền trạng thái sang ESP32 |
| **A18 (UART1_RX)** | **GPIO17 (TX2)** | ESP32 truyền lệnh nút bấm & khoảng cách sang MaixCAM |
| **GND** | **GND** | Nối chung mass hệ thống |
| **VBUS / VSYS** | **VIN (5V)** | Nguồn nuôi 5V từ IC IP5306 |

### 4.2. Kết nối ngoại vi trên ESP32
- **Cảm biến siêu âm AJ-SR04M:** Chân TRIG nối GPIO32, chân ECHO nối GPIO33.
- **Module GPS NEO-6M:** Chân TX nối GPIO13, chân RX nối GPIO14.
- **Module 4G LTE A7680C:** Chân TXD nối GPIO26, chân RXD nối GPIO25.
- **Nút bấm SOS:** Nối GPIO27 (kéo trở nội).
- **LED cảnh báo SOS:** Nối GPIO4 (qua điện trở hạn dòng 330 Ohm).

---

## 5. Hướng dẫn nạp phần mềm & Vận hành

### 5.1. Nạp code cho ESP32
1. Mở phần mềm **Arduino IDE** (khuyến nghị phiên bản 2.x).
2. Cài đặt board package **ESP32 by Espressif**.
3. Cài đặt các thư viện cần thiết: `TinyGPSPlus`, `HardwareSerial`.
4. Mở file `Gay_Nguoi_Mu/firmware/esp32_periph/esp32_periph.ino`.
5. Chọn đúng cổng COM và nạp chương trình.

### 5.2. Đồng bộ chương trình vào MaixCAM
1. Kết nối MaixCAM với máy tính qua cáp USB Type-C.
2. Đảm bảo máy tính đã nhận giao diện mạng USB RNDIS của MaixCAM.
3. Chạy lệnh đồng bộ tự động:
   ```bash
   python sync_and_test_maixcam.py
   ```
   Script sẽ tự động truyền source code, các file âm thanh và mô hình vào thư mục `/root/maixcam_app/` trên thiết bị và khởi động ứng dụng.

---

## 6. Huấn luyện và Cập nhật Model AI

Khi cần bổ sung dữ liệu huấn luyện hoặc cập nhật mô hình mới:

1. Mở file [Train_MaixCAM_GoogleColab.ipynb](Train_MaixCAM_GoogleColab.ipynb) trên Google Colab.
2. Bật môi trường **GPU T4** (`Runtime` -> `Change runtime type` -> `T4 GPU`).
3. Chạy tuần tự các ô lệnh để tải dữ liệu, huấn luyện mạng YOLOv5n (320x320) và xuất file ONNX.
4. Truy cập trang chuyển đổi của nhà sản xuất [MaixHub Model Convert](https://maixhub.com/model/convert), upload file ONNX, chọn phần cứng **MaixCAM**, loại mô hình **YOLOv8** và độ phân giải **320x320** để biên dịch thành file `.cvimodel`.
5. Chép file `.cvimodel` mới vào thư mục `Gay_Nguoi_Mu/firmware/maixcam_app/models/` và chạy script đồng bộ lên thiết bị.

Chi tiết xem tại tài liệu: [HUONG_DAN_TRAIN_COLAB.md](HUONG_DAN_TRAIN_COLAB.md).
