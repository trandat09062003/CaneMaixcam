# Gậy Thông Minh Hỗ Trợ Người Khiếm Thị (Smart Cane)

Hệ thống nhúng tích hợp trên gậy hỗ trợ người khiếm thị, sử dụng kết hợp **Sipeed MaixCAM Lite** (xử lý hình ảnh Edge AI, âm thanh trực tiếp) và **ESP32 DOIT DevKit V1** (quản lý cảm biến khoảng cách, GPS định vị và truyền thông 4G).

---

## 1. Kiến Trúc Phần Cứng & Phân Chia Nhiệm Vụ

Hệ thống chia làm 2 khối vi điều khiển giao tiếp nối tiếp qua UART1 (Baud 9600, 8N1):

### Khối xử lý trung tâm U2: Sipeed MaixCAM Lite (Linux / MaixPy v4)
* **Vi xử lý**: Sophgo SG2002 (Cortex-A53 1.0 GHz + RISC-V), tích hợp NPU 1 TOPS.
* **Camera**: Cảm biến MIPI CSI độ phân giải cao thu hình trực tiếp.
* **Nhận diện tiền VND**: Chạy mô hình YOLOv8 nano (`vnd_money_v2.cvimodel`) tăng tốc phần cứng trực tiếp trên NPU, tốc độ ~30 FPS ở độ phân giải 320x320. Nhận diện 6 mệnh giá tiền polymer: 10.000đ, 20.000đ, 50.000đ, 100.000đ, 200.000đ, 500.000đ.
* **Đọc văn bản (OCR)**: Chụp ảnh, tiền xử lý và gửi qua API Cloud để nhận dạng văn bản tiếng Việt.
* **Âm thanh**: Giải mã và phát âm thanh hướng dẫn trực tiếp qua bộ khuếch đại công suất onboard (chân VOP/VON nối loa 4Ω 3W).
* **Kết nối ngoại vi**: Cầu phân áp đo pin 18650 qua chân ADC, giao tiếp UART1 với ESP32 (`/dev/ttyS1`).

### Khối ngoại vi & cứu hộ U3: ESP32 DOIT DevKit V1 (Arduino C++)
* **Cảm biến siêu âm**: AJ-SR04M chống nước quét liên tục vật cản phía trước để cảnh báo va chạm.
* **Định vị GPS**: Module NEO-6M (hoặc ATGM336H) đọc tọa độ thời gian thực.
* **Module SIM 4G**: A7680C gửi tin nhắn cứu hộ, tọa độ vị trí qua Telegram Bot khi có sự cố.
* **Nút nhấn & Cảnh báo**: Nút bấm SOS, nút chuyển chế độ, đèn LED báo trạng thái.

---

## 2. Cấu Trúc Thư Mục

```text
gay_nguoi_mu_maixcam/
├── gaynguoimu/                     # File thiết kế phần cứng Altium Designer
│   ├── gaynguoimu.PrjPcb           # Project Altium
│   ├── Sheet2.SchDoc               # Sơ đồ nguyên lý (Schematic)
│   ├── PCB3.PcbDoc                 # Bản vẽ mạch in (PCB Layout)
│   └── gaynguoimu.BomDoc           # Danh mục linh kiện (BOM)
│
├── Gay_Nguoi_Mu/                   # Mã nguồn nhúng & tài nguyên hệ thống
│   ├── firmware/
│   │   ├── esp32_periph/           # Code Arduino C++ cho ESP32 ngoại vi
│   │   │   ├── esp32_periph.ino    # Chương trình chính
│   │   │   ├── gps_module.h        # Xử lý NMEA GPS
│   │   │   ├── sim_module.h        # Điều khiển tập lệnh AT module SIM 4G
│   │   │   └── pins.h              # Ánh xạ chân GPIO ESP32
│   │   │
│   │   └── maixcam_app/            # Ứng dụng Python chính chạy trên MaixCAM
│   │       ├── main.py             # Điều khiển camera, NPU, UART và loa
│   │       ├── audio/              # Các file âm thanh giọng nói tiếng Việt (.mp3/.wav)
│   │       └── models/             # Thư mục chứa mô hình NPU (.cvimodel, .mud)
│   │           ├── vnd_money_v2.cvimodel  # Model YOLOv8 nhận diện tiền (mới)
│   │           ├── vnd_money_v2.mud       # File cấu hình nhãn model v2
│   │           ├── vnd_currency.cvimodel  # Model dự phòng
│   │           └── vnd_currency.mud
│   │
│   ├── vnd_money_v2.onnx           # File ONNX mô hình tiền mới (opset 11, 320x320)
│   ├── best.onnx                   # Model ONNX gốc
│   └── calibration_images.zip      # Bộ ảnh hiệu chuẩn lượng tử hóa (Quantization)
│
├── dataset_money/                  # Dữ liệu ảnh thực tế phân theo 6 mệnh giá polymer
│   ├── 10000/                      # (front / back)
│   ├── 20000/
│   ├── 50000/
│   ├── 100000/
│   ├── 200000/
│   └── 500000/
│
├── scripts/                        # Tập lệnh huấn luyện, nạp code và kiểm thử
│   ├── prepare_money_dataset.py    # Lọc ảnh lỗi và tự động gán nhãn bounding box
│   ├── train_money_v2.py           # Huấn luyện YOLOv8 và xuất ONNX/MUD
│   ├── test_trained_model.py       # Kiểm thử độ chính xác mô hình trên tập val
│   └── deploy_to_maixcam.py        # Tự động nạp code & model lên MaixCAM qua SSH
│
├── summary.txt                     # Bảng nối chân phần cứng chi tiết (Pinout Mapping)
└── README.md                       # Tài liệu hướng dẫn sử dụng
```

---

## 3. Sơ Đồ Đấu Nối Phần Cứng

Chi tiết chân kết nối giữa MaixCAM, ESP32, IC quản lý nguồn IP5306, cảm biến siêu âm, GPS, module SIM và nút bấm được tổng hợp đầy đủ tại:

👉 **[summary.txt](file:///c:/Users/Public/Documents/Altium/08052026/gay_nguoi_mu_maixcam/summary.txt)**

*(Cần đối chiếu file này trước khi thi công hàn mạch hoặc cắm dây thử nghiệm).*

---

## 4. Huấn Luyện Lại Mô Hình Nhận Diện Tiền (Retrain)

Nếu bổ sung thêm ảnh mới vào `dataset_money/`, thực hiện quy trình sau để huấn luyện lại:

### Bước 1: Chuẩn bị dữ liệu và gắn nhãn tự động
```bash
python scripts/prepare_money_dataset.py
```
Script sẽ tự động quét thư mục `dataset_money/`, loại bỏ các file rỗng hoặc hỏng, gắn nhãn bounding box chuẩn YOLO và phân chia tập train/val tại `dataset_money_yolo/money.yaml`.

### Bước 2: Huấn luyện mô hình YOLOv8
```bash
python scripts/train_money_v2.py
```
* Huấn luyện YOLOv8 nano ở độ phân giải 320x320.
* Tự động lưu weights tại `Gay_Nguoi_Mu/firmware/maixcam_app/models/vnd_money_v2.pt`.
* Tự động xuất file ONNX tại `Gay_Nguoi_Mu/vnd_money_v2.onnx` (Opset 11).
* Tự động sinh file cấu hình `vnd_money_v2.mud`.

### Bước 3: Chuyển đổi sang .cvimodel trên MaixHub
1. Truy cập [https://maixhub.com/model/convert](https://maixhub.com/model/convert).
2. Chọn Hardware: **MaixCAM** (Sophgo SG2002).
3. Tải lên file: `Gay_Nguoi_Mu/vnd_money_v2.onnx`.
4. Chọn Model Type: **YOLOv8** (Resolution: 320x320).
5. File ảnh calibration: Chọn `Gay_Nguoi_Mu/calibration_images.zip`.
6. Bấm **Start**, sau khi chuyển đổi xong tải file zip về và giải nén.
7. Đổi tên file `.cvimodel` thành `vnd_money_v2.cvimodel`, chép vào thư mục `Gay_Nguoi_Mu/firmware/maixcam_app/models/`.

### Bước 4: Kiểm tra đánh giá
```bash
python scripts/test_trained_model.py
```

---

## 5. Hướng Dẫn Cài Đặt & Nạp Chương Trình

### 5.1. Nạp code cho ESP32 ngoại vi (U3)
1. Mở dự án trong **Arduino IDE** (phiên bản 2.x).
2. Cài đặt package board ESP32 (Espressif v3.0.x).
3. Mở file `Gay_Nguoi_Mu/firmware/esp32_periph/esp32_periph.ino`.
4. Chọn board **ESP32 Dev Module**, cắm cáp Type-C vào ESP32 và bấm **Upload**.

### 5.2. Nạp code & Triển khai lên Sipeed MaixCAM Lite (U2)
Cách nhanh nhất là sử dụng script tự động qua mạng WiFi/USB RNDIS:
```bash
python scripts/deploy_to_maixcam.py
```
Script sẽ tự động:
1. Đồng bộ toàn bộ mã nguồn `main.py`, file âm thanh và thư mục `models/` lên board.
2. Cấu hình file khởi động cùng hệ thống `smartcane.service`.
3. Khởi động lại service trên MaixCAM mà không cần can thiệp thủ công.

---

## 6. Hướng Dẫn Vận Hành

* **Bật / Tắt nguồn**: Nhấn nút nguồn trên mạch IP5306 một lần để bật. Nhấn giữ 3-5 giây để tắt nguồn. Nhấn đúp để xem mức pin hiển thị qua LED vạch.
* **Nhận diện tiền**: Hướng camera về phía tờ tiền và nhấn nút quét 1 lần. Thiết bị tự động chụp, nhận diện mệnh giá qua NPU và phát giọng nói tiếng Việt qua loa.
* **Đọc văn bản (OCR)**: Nhấn giữ nút quét hoặc bấm nút chuyển chế độ. Thiết bị chụp ảnh, xử lý và đọc to nội dung tài liệu.
* **Cảnh báo vật cản**: Cảm biến siêu âm tự động đo khoảng cách liên tục:
  * Từ 40cm đến 80cm: Loa phát tiếng bíp thưa.
  * Dưới 40cm: Loa phát tiếng bíp dồn dập cảnh báo dừng lại.
* **Cứu hộ SOS**: Nhấn đúp nút SOS. Thiết bị kích hoạt đèn nháy khẩn cấp, lấy tọa độ GPS mới nhất từ ESP32 và tự động gửi tin nhắn kèm vị trí Google Maps về Telegram người thân qua module SIM 4G.
