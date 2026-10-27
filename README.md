# HỆ THỐNG GẬY THÔNG MINH HỖ TRỢ NGƯỜI KHIẾM THỊ (SMART CANE)
### Tích hợp Trí tuệ Nhân tạo Biên (Edge AI - Sipeed MaixCAM) & Vi điều khiển Ngoại vi (ESP32)

---

## 1. Kiến trúc Hệ thống Phần cứng

Dự án sử dụng mô hình điện toán phân tán 2 tầng (Dual-MCU Architecture) nhằm tách biệt tác vụ xử lý thị giác máy tính tải cao và các tác vụ thời gian thực (định vị, cảm biến, viễn thông 4G khẩn cấp):

```
                   ┌──────────────────────────────────────────────┐
                   │           Camera MIPI-CSI (OV5647)           │
                   └──────────────────────┬───────────────────────┘
                                          │ 2-lane MIPI
                                          ▼
                   ┌──────────────────────────────────────────────┐
                   │            SIPEED MAIXCAM (U2)               │
                   │    SoC: Sophgo SG2002 (ARM Cortex-A53)       │
                   │    NPU: 1.0 TOPS @ INT8 (TPU MLIR Runtime)   │
                   │    - Nhận diện 6 mệnh giá tiền Polymer VND   │──────► Loa 4Ω 3W (VOP/VON)
                   │    - Nhận diện 36 ký tự quang học (OCR)      │        (Giọng đọc tiếng Việt)
                   │    - Xử lý Morphological Text & Cloud OCR    │
                   └──────────────────────┬───────────────────────┘
                                          │
                                 UART1 (9600 bps, 8N1)
                              A19 (TX) ──► GPIO16 (RX2)
                              A18 (RX) ◄── GPIO17 (TX2)
                                          │
                                          ▼
                   ┌──────────────────────────────────────────────┐
                   │             ESP32 DEVKIT V1 (U3)             │
                   │      Bộ vi điều khiển ngoại vi & an toàn     │
                   └───────┬──────────────┬──────────────┬────────┘
                           │              │              │
                    GPIO32 │ GPIO33   GPIO13 │ GPIO14 GPIO25 │ GPIO26 (UART)
                           │ (Echo)          │ (RX)          │
                           ▼                 ▼               ▼
                   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
                   │   AJ-SR04M   │ │    NEO-6M    │ │ SIMCom A7680C│
                   │  (Siêu âm    │ │    (GPS      │ │   (4G LTE    │
                   │  chống nước) │ │  định vị)    │ │   Telegram)  │
                   └──────────────┘ └──────────────┘ └──────────────┘
                           ▲                 ▲               ▲
                           │                 │               │
                     Cảnh báo va chạm   Lấy tọa độ SOS   Gửi cảnh báo vị trí
```

### 1.1. Phân chia chức năng chi tiết
* **Sipeed MaixCAM (SoC Sophgo SG2002):**
  - Chạy hệ điều hành Linux nhúng (MaixPy v4 runtime).
  - Thu nhận khung hình từ cảm biến ảnh OV5647 qua giao tiếp MIPI-CSI 2-lane.
  - Tăng tốc phần cứng 2 mô hình Deep Learning trên NPU: Mô hình nhận diện tiền VND (`vnd_money_v2.cvimodel`) và mô hình OCR 36 ký tự (`char_ocr_v2.cvimodel`).
  - Tổng hợp âm thanh, giải mã file WAV/PCM 16-bit 16kHz trực tiếp ra mạch khuếch đại công suất onboard nối cọc loa 4Ω 3W.
* **ESP32 DOIT DevKit V1 (30 chân):**
  - Đọc cảm biến khoảng cách siêu âm AJ-SR04M chu kỳ 80ms, lọc trung vị khử nhiễu dội xung.
  - Phân tích chuỗi NMEA từ module GPS NEO-6M qua HardwareSerial.
  - Quản trị kết nối mạng di động LTE Cat-1 thông qua tập lệnh AT trên SIMCom A7680C; tự động gửi tin nhắn SOS kèm liên kết Google Maps về bot Telegram người thân khi bấm nút khẩn cấp.
  - Quản lý năng lượng và nút bấm cơ khí (chống rung phần mềm Debounce).

---

## 2. Sơ đồ Đấu nối Chân (Pinout Map)

### 2.1. Kết nối Liên kết MaixCAM (U2) <--> ESP32 DevKit (U3)
| Chân MaixCAM | Tên cổng | Chân ESP32 | Tên cổng | Mức logic | Chức năng |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **A19** | UART1_TX | **GPIO16** | RX2 | 3.3V TTL | MaixCAM gửi trạng thái nhận diện, mode hoạt động sang ESP32 |
| **A18** | UART1_RX | **GPIO17** | TX2 | 3.3V TTL | ESP32 gửi lệnh chuyển mode, cảnh báo khoảng cách sang MaixCAM |
| **GND** | GND | **GND** | GND | 0V | Nối chung mass toàn hệ thống |
| **VSYS / VBUS**| 5V IN | **VIN** | 5V IN | 5.0V DC | Nhận nguồn từ mạch hạ áp/quản lý pin IP5306 |

### 2.2. Kết nối Ngoại vi trên ESP32 (U3)
| Ngoại vi | Chân ESP32 | Ký hiệu chân | Chế độ I/O | Lưu ý kỹ thuật |
| :--- | :--- | :--- | :--- | :--- |
| **AJ-SR04M (Trig)** | **GPIO32** | D32 | Output | Phát xung kích 10µs |
| **AJ-SR04M (Echo)** | **GPIO33** | D33 | Input | Cần cầu phân áp trở nếu module dùng nguồn 5V thuần |
| **SIM A7680C (TXD)** | **GPIO26** | D26 (RX) | Input | Kết nối chân TX của module SIM |
| **SIM A7680C (RXD)** | **GPIO25** | D25 (TX) | Output | Kết nối chân RX của module SIM |
| **SIM A7680C (RST)** | **GPIO18** | D18 | Output | Kéo mức thấp 100ms để reset phần cứng module SIM |
| **GPS NEO-6M (TX)** | **GPIO14** | D14 (RX) | Input | Tốc độ mặc định 9600 bps |
| **GPS NEO-6M (RX)** | **GPIO13** | D13 (TX) | Output | Gửi bản tin cấu hình NMEA (nếu cần) |
| **Nút bấm SOS (BT2)**| **GPIO27** | D27 | Input Pullup| Nhấn xuống kéo mass; giữ >1.2s kích hoạt báo động khẩn cấp |
| **Nút bấm OCR (BT3)**| **GPIO21** | D21 | Input Pullup| Nhấn nhả chuyển mode quét chữ hoặc chụp ảnh phân tích |
| **LED Báo động SOS** | **GPIO4**  | D4  | Output | Nối tiếp trở hạn dòng 330Ω, nhấp nháy khi SOS kích hoạt |

---

## 3. Kiến trúc Mô hình AI & Dữ liệu Huấn luyện

Hệ thống sử dụng mạng nơ-ron tích chập tối ưu hóa cho vi xử lý biên (Edge AI): **YOLOv5nu (YOLOv5 Nano với Anchor-Free Decoupled Head của YOLOv8)**.

### 3.1. Mô hình Nhận diện Tiền Polymer VND (`vnd_money_v2`)
* **Kiến trúc:** `yolov5nu.pt` (Anchor-Free Detection Head).
* **Độ phân giải đầu vào:** `320x320x3` (định dạng màu RGB, chuẩn hóa `mean=[0,0,0]`, `scale=[1/255, 1/255, 1/255]`).
* **Số lớp nhận diện:** 6 mệnh giá tiền polymer Việt Nam:
  - `0`: 10.000 VNĐ
  - `1`: 20.000 VNĐ
  - `2`: 50.000 VNĐ
  - `3`: 100.000 VNĐ
  - `4`: 200.000 VNĐ
  - `5`: 500.000 VNĐ
* **Tập dữ liệu huấn luyện:** Tập dữ liệu cân bằng hoàn hảo gồm **23.967 ảnh** (~4.000 ảnh/mệnh giá, bao gồm cả mặt trước và mặt sau trong nhiều điều kiện góc nghiêng, khoảng cách và ánh sáng).
* **Hiệu năng kiểm thử:** Độ tin cậy nhận diện trên mẫu kiểm thử thực tế đạt **99% confidence (0.99)** trên cả 6 mệnh giá; thời gian suy luận (Inference Latency) trên NPU Sophgo SG2002 đạt **~30ms/frame (~33 FPS)**.

### 3.2. Mô hình Nhận diện Ký tự OCR 36 Lớp (`char_ocr_v2`)
* **Kiến trúc:** `yolov5nu.pt` (320x320, 70 epochs huấn luyện trên GPU).
* **Tham số quan trọng:** Tắt hoàn toàn lật ngang (`fliplr=0.0`) trong quá trình data augmentation để chống nhầm lẫn cấu trúc giữa các ký tự đối xứng gương (như `b` với `d`, `p` với `q`).
* **Số lớp nhận diện:** 36 ký tự: `0-9` (10 số) và `a-z` (26 chữ cái không dấu).
* **Hiệu năng kiểm thử:** Đạt `Precision = 65.5%`, `mAP50 = 56.4%` trên tập validation kiểm thử quang học.

### 3.3. Quy tắc Đọc Âm thanh Chống Lặp (Audio Latching Logic)
Để tránh hiện tượng đọc liên tục gây khó chịu khi người khiếm thị giữ tờ tiền trước camera:
1. Khi phát hiện tờ tiền mới đạt ngưỡng tin cậy (`conf >= 0.70`), phát âm thanh đúng **1 lần duy nhất**.
2. Khóa trạng thái nhận diện (Latching). Dù camera tiếp tục thấy tờ tiền trong các frame tiếp theo, hệ thống giữ im lặng.
3. Khi người dùng hạ tờ tiền xuống (không có detection trong 1.8 giây liên tiếp), hệ thống tự động reset cờ nhận diện, sẵn sàng cho tờ tiền kế tiếp.

---

## 4. Cấu trúc Cây Thư mục Dự án

```
gay_nguoi_mu_maixcam/
├── gaynguoimu/                               # Thiết kế phần cứng PCB trên Altium Designer
│   ├── gaynguoimu.PrjPcb                     # File dự án mạch Altium
│   ├── Sheet2.SchDoc                         # Sơ đồ nguyên lý mạch điều khiển (Schematic)
│   └── PCB3.PcbDoc                           # Thiết kế bố trí linh kiện & đi dây mạch in (PCB)
│
├── Gay_Nguoi_Mu/
│   ├── firmware/
│   │   ├── esp32_periph/                     # Firmware nạp cho vi điều khiển ESP32 (Arduino C++)
│   │   │   ├── esp32_periph.ino              # Vòng lặp chính xử lý cảm biến, SOS và giao thức UART
│   │   │   ├── gps_module.h                  # Module giải mã NMEA GPS NEO-6M
│   │   │   ├── sim_module.h                  # Quản lý module 4G A7680C & gửi tin nhắn Telegram
│   │   │   └── pins.h                        # Liên kết định nghĩa chân GPIO
│   │   │
│   │   └── maixcam_app/                      # Ứng dụng trung tâm trên MaixCAM (Python 3 / MaixPy v4)
│   │       ├── main.py                       # Điều khiển camera, NPU inference, phát âm thanh WAV
│   │       ├── audio/                        # Thư mục chứa các file âm thanh giọng đọc tiếng Việt
│   │       └── models/                       # Thư mục nạp trên phần cứng MaixCAM
│   │           ├── vnd_money_v2.cvimodel     # Model nhị phân NPU cho tiền polymer VND
│   │           ├── vnd_money_v2.mud          # Descriptor metadata nhãn tiền
│   │           ├── vnd_money_v2.onnx         # Model ONNX chuẩn opset 11 (320x320)
│   │           ├── vnd_money_v2.pt           # Trọng số PyTorch gốc
│   │           ├── char_ocr_v2.cvimodel      # Model nhị phân NPU cho ký tự OCR
│   │           ├── char_ocr_v2.mud           # Descriptor metadata nhãn ký tự
│   │           ├── char_ocr_v2.onnx          # Model ONNX ký tự chuẩn opset 11
│   │           └── char_ocr_v2.pt            # Trọng số PyTorch ký tự
│   │
│   ├── hardware/
│   │   └── pins_esp32.h                      # Khai báo cấu hình chân GPIO trên bo mạch
│   ├── vnd_money_v2.onnx                     # Bản sao mô hình ONNX tiền VND
│   └── char_ocr_v2.onnx                      # Bản sao mô hình ONNX ký tự OCR
│
├── maixcam_trained_models.zip                # Gói nén trọn bộ mô hình mới (.pt, .onnx, .mud)
├── dataset_money_yolo.zip                    # Dataset mẫu tiền VND định dạng chuẩn YOLO
├── dataset_chars_yolo.zip                    # Dataset mẫu ký tự OCR định dạng chuẩn YOLO
├── Train_MaixCAM_GoogleColab.ipynb           # Notebook huấn luyện tự động trên Google Colab GPU T4
├── HUONG_DAN_TRAIN_COLAB.md                  # Hướng dẫn chi tiết quy trình huấn luyện & export
├── sync_and_test_maixcam.py                  # Script đồng bộ tự động mã nguồn & model qua USB RNDIS
├── live_log_maixcam.py                       # Script giám sát luồng log trực tiếp từ thiết bị
├── telegram_bot_service.py                   # Script kiểm tra tích hợp cổng thông báo Telegram
├── summary.txt                               # Bảng tóm tắt kết nối chân và lệnh AT phần cứng
└── README.md                                 # Tài liệu kỹ thuật dự án
```

---

## 5. Hướng dẫn Triển khai & Vận hành

### 5.1. Nạp Firmware cho ESP32
1. Mở mã nguồn trong thư mục:
   `Gay_Nguoi_Mu/firmware/esp32_periph/esp32_periph.ino` bằng **Arduino IDE** (hoặc VS Code với extension PlatformIO).
2. Trong **Board Manager**, cài đặt gói `esp32 by Espressif Systems`. Chọn board: `DOIT ESP32 DEVKIT V1`.
3. Cài đặt các thư viện phụ thuộc:
   - `TinyGPSPlus` (bởi Mikal Hart).
   - `HardwareSerial` (tích hợp sẵn trong core ESP32).
4. Kiểm tra cấu hình Telegram Bot Token và Chat ID trong file `sim_module.h`:
   ```cpp
   const char TELEGRAM_TOKEN[] = "YOUR_BOT_TOKEN";
   const char TELEGRAM_CHAT_ID[] = "YOUR_CHAT_ID";
   ```
5. Cắm cáp micro-USB vào bo ESP32, chọn đúng cổng COM và tiến hành nạp code (**Upload**).

### 5.2. Nạp Ứng dụng & Mô hình vào Sipeed MaixCAM
1. Kết nối MaixCAM với máy tính qua cáp USB Type-C. Thiết bị sẽ nhận diện giao diện mạng ảo USB RNDIS (IP mặc định: `192.168.0.1` hoặc nhận IP qua DHCP).
2. Đảm bảo máy tính đã cài đặt Python 3. Cài đặt các thư viện hỗ trợ truyền file nếu cần:
   ```bash
   pip install paramiko scp
   ```
3. Chạy script đồng bộ một chạm:
   ```bash
   python sync_and_test_maixcam.py
   ```
   Script sẽ tự động:
   - Kiểm tra kết nối mạng với MaixCAM.
   - Đồng bộ toàn bộ mã nguồn `main.py`, thư mục âm thanh `audio/` và các mô hình trong `models/` vào đường dẫn `/root/maixcam_app/` trên hệ thống Linux nhúng.
   - Tự động khởi chạy ứng dụng và hiển thị thông tin log kiểm tra camera & NPU.

---

## 6. Quy trình Huấn luyện lại Mô hình AI (Retraining Pipeline)

Khi cần cập nhật thêm ảnh hoặc huấn luyện lại với dữ liệu mới:

### Bước 1: Chuẩn bị dữ liệu
- Chạy file batch nén dataset tự động:
  ```bash
  CHUAN_BI_DATASET_CHO_COLAB.bat
  ```
  hoặc thực thi script: `python scripts/pack_datasets_for_colab.py`.

### Bước 2: Huấn luyện trên Google Colab
1. Truy cập [Google Colab](https://colab.research.google.com/) và tải lên file notebook [Train_MaixCAM_GoogleColab.ipynb](Train_MaixCAM_GoogleColab.ipynb).
2. Chuyển môi trường sang GPU T4 (`Runtime` -> `Change runtime type` -> `T4 GPU`).
3. Chạy lần lượt các cell lệnh. Quá trình huấn luyện với mạng `yolov5nu`:
   - Mô hình tiền: 25 - 50 epochs (mất ~2 phút trên GPU T4).
   - Mô hình ký tự OCR: 70 epochs (`fliplr=0.0`, mất ~3 phút trên GPU T4).
4. Cell cuối sẽ tự động xuất file ONNX chuẩn hóa (`opset=11`, `simplify=True`), tạo file descriptor `.mud` và đóng gói thành `maixcam_trained_models.zip` tải về máy.

### Bước 3: Biên dịch NPU trên MaixHub
1. Truy cập công cụ biên dịch NPU trực tuyến: [https://maixhub.com/model/convert](https://maixhub.com/model/convert).
2. Thiết lập cấu hình biên dịch:
   - **Hardware platform:** `MaixCAM` (Chip Sophgo SG2002 / CV181x).
   - **Input file:** Upload file `vnd_money_v2.onnx` hoặc `char_ocr_v2.onnx`.
   - **Model type:** Chọn **YOLOv8** *(Lưu ý bắt buộc: Kiến trúc `yolov5nu` sử dụng đầu ra Anchor-Free tương đồng với YOLOv8, không chọn YOLOv5 truyền thống)*.
   - **Resolution:** `320x320`.
3. Bấm **Convert** để máy chủ Cloud sinh file nhị phân `.cvimodel`.
4. Giải nén file kết quả từ MaixHub, đổi tên thành `vnd_money_v2.cvimodel` (hoặc `char_ocr_v2.cvimodel`) và đặt vào thư mục `Gay_Nguoi_Mu/firmware/maixcam_app/models/`.

---

## 7. Xử lý Sự cố Kỹ thuật Thường gặp (Troubleshooting)

1. **MaixCAM không mở được Camera (MIPI CSI Error):**
   - Kiểm tra chốt khóa cáp ribbon MIPI 2-lane. Tiếp điểm mạ vàng phải hướng đúng về phía board mạch theo ký hiệu trên connector.
   - Kiểm tra log bằng lệnh `dmesg | grep -i csi` hoặc chạy `python live_log_maixcam.py`.

2. **Lỗi không nhận diện được mô hình trên NPU (`cvimodel load fail`):**
   - Đảm bảo file `.mud` và file `.cvimodel` nằm cùng thư mục và có tên trùng khớp với khai báo `model = <ten_file>.cvimodel` trong file `.mud`.
   - Kiểm tra cờ `model_type = yolov8` trong file `.mud`.

3. **ESP32 không nhận được dữ liệu từ MaixCAM qua UART:**
   - Kiểm tra đấu chéo chân: Chân **A19 (TX)** của MaixCAM phải nối vào **GPIO16 (RX2)** của ESP32; chân **A18 (RX)** phải nối vào **GPIO17 (TX2)**.
   - Đảm bảo chung mass (`GND`).
   - Kiểm tra baudrate hai bên đều đặt ở mức `9600 bps`.

4. **Module 4G A7680C bị sụt nguồn / không đăng ký được mạng di động:**
   - Module phát sóng RF LTE Cat-1 có thể tiêu thụ dòng đỉnh tức thời lên tới 2A khi phát tín hiệu.
   - Bắt buộc phải cấp nguồn 5V ổn định từ IC IP5306 và đặt thêm tụ hóa lọc nguồn tối thiểu 470µF - 1000µF đặt gần chân nguồn VCC của module SIM.
   - Đảm bảo anten 4G đã được gắn chắc chắn và SIM đã kích hoạt gói cước dữ liệu Data.
