# Gậy Thông Minh Hỗ Trợ Người Khiếm Thị (Smart Cane)
## Phiên bản nâng cấp: Sipeed MaixCAM Lite + ESP32 DOIT DevKit

Dự án thiết kế và phát triển hệ thống nhúng thông minh tích hợp trên gậy hỗ trợ người khiếm thị. Phiên bản nâng cấp này thay thế chip xử lý hình ảnh cũ bằng **Sipeed MaixCAM Lite** (xung nhịp 1GHz, tích hợp NPU 1 TOPS chuyên dụng cho Edge AI), giúp nâng cao tốc độ nhận diện tiền tệ và xử lý đọc chữ tiếng Việt (OCR) thời gian thực, đồng thời tối giản hóa mạch phần cứng bằng cách loại bỏ module DAC âm thanh rời.

---

## 1. Kiến Trúc Hệ Thống & Phân Chia Tác Vụ

Hệ thống hoạt động dựa trên sự phối hợp của 2 bộ xử lý giao tiếp qua UART nối tiếp (Baudrate: 9600, Khung truyền 8N1):

### Bộ xử lý chính U2: Sipeed MaixCAM Lite (Chạy Linux / MaixPy v3)
*   **Nhiệm vụ**:
    *   Thu nhận hình ảnh từ Camera MIPI CSI độ phân giải cao.
    *   Chạy mô hình AI cục bộ (YOLOv8-nano / MobileNet) trên NPU để nhận diện mệnh giá tiền polymer Việt Nam (VND) không cần Internet.
    *   Gửi ảnh nén qua kết nối mạng để nhận diện ký tự tiếng Việt (OCR) qua API OCR Space.
    *   Giải mã âm thanh và trực tiếp phát giọng nói hướng dẫn tiếng Việt ra loa thông qua mạch khuếch đại công suất (PA) tích hợp sẵn trên board (chân phát VOP/VON).
    *   Giao tiếp với chip ngoại vi U3 qua cổng UART1 (`/dev/ttyS1`).
*   **Ngoại vi kết nối**: Camera MIPI CSI, Loa mini (4Ω 3W hoặc 1W), Cầu phân áp đo dung lượng pin 18650 (300k/100k kết nối vào chân ADC).

### Vi điều khiển ngoại vi U3: ESP32 DOIT DevKit V1 (Chạy Arduino C++)
*   **Nhiệm vụ**:
    *   Quét cảm biến siêu âm liên tục để cảnh báo khoảng cách vật cản phía trước gậy.
    *   Đọc và cập nhật dữ liệu tọa độ định vị từ module GPS.
    *   Quản lý module SIM 4G LTE để thực hiện gửi dữ liệu cứu hộ (tọa độ GPS, tin nhắn khẩn cấp) lên Telegram khi mất kết nối WiFi.
    *   Giám sát nút nhấn khẩn cấp SOS, nút OCR độc lập và điều khiển LED cảnh báo.
*   **Ngoại vi kết nối**: Cảm biến siêu âm chống nước AJ-SR04M, Module GPS NEO-6M (hoặc ATGM336H), Module SIM 4G LTE A7680C, Nút nhấn SOS, Nút nhấn OCR, LED SOS.

---

## 2. Cấu Trúc Thư Mục Dự Án

Thư mục dự án được tổ chức đồng bộ và dọn dẹp sạch sẽ như sau:

```text
gay_nguoi_mu_maixcam/
├── gaynguoimu/                     # Thư mục thiết kế phần cứng Altium Designer
│   ├── gaynguoimu.PrjPcb           # File quản lý dự án mạch Altium
│   ├── Sheet2.SchDoc               # Sơ đồ nguyên lý (Schematic) mạch thiết kế mới
│   ├── PCB3.PcbDoc                 # Sơ đồ mạch in (PCB Layout) thiết kế mới
│   └── gaynguoimu.BomDoc           # Danh sách linh kiện của dự án (BOM)
│
├── Gay_Nguoi_Mu/                   # Thư mục mã nguồn nhúng của thiết bị
│   ├── firmware/
│   │   ├── esp32_periph/           # Mã nguồn C++ cho ESP32 ngoại vi (U3)
│   │   │   ├── esp32_periph.ino    # File chạy chính của Arduino
│   │   │   ├── gps_module.h        # Thư viện xử lý GPS
│   │   │   ├── sim_module.h        # Thư viện điều khiển module SIM qua lệnh AT
│   │   │   └── pins.h              # Chỉ định ánh xạ chân GPIO của U3
│   │   │
│   │   └── maixcam_app/            # Mã nguồn Python chạy trên Sipeed MaixCAM (U2)
│   │       └── main.py             # Script xử lý AI, UART, ADC và phát âm thanh
│   │
│   └── hardware/
│       └── pins_esp32.h            # File định nghĩa chân phần cứng cho ESP32
│
├── summary.txt                     # Sơ đồ nối chân phần cứng duy nhất (Source of Truth)
└── README.md                       # Hướng dẫn sử dụng và triển khai dự án này
```

---

## 3. Sơ Đồ Đấu Nối Chân Phần Cứng (Pin Mapping)

Để đảm bảo thông tin nhất quán và tránh sai lệch thiết kế, toàn bộ cấu hình kết nối chân của cả 2 vi điều khiển (MaixCAM Lite & ESP32), mạch nguồn IP5306, các kết nối UART và cách nối dây module ngoại vi được tổng hợp chi tiết tại file:

👉 **[summary.txt](file:///C:/Users/Public/Documents/Altium/2026/gay_nguoi_mu_maixcam/summary.txt)**

*Vui lòng tham khảo tệp tin trên khi thực hiện hàn nối linh kiện trên PCB hoặc khi kiểm tra đường mạch.*

---

## 4. Hướng Dẫn Nạp Chương Trình & Cấu Hình Phần Mềm

### 4.1. Cấu hình và nạp code cho ESP32 ngoại vi (U3)
1.  Cài đặt phần mềm **Arduino IDE** (khuyên dùng bản 2.x).
2.  Thêm URL quản lý board ESP32 trong `Preferences`:
    `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
3.  Vào `Board Manager` tìm kiếm và cài đặt gói cấu hình **esp32** bởi **Espressif** (phiên bản ổn định khuyên dùng: **3.0.x**).
4.  Mở thư mục `Gay_Nguoi_Mu/firmware/esp32_periph/esp32_periph.ino`.
5.  Chọn đúng Board là **"ESP32 Dev Module"**, kết nối cáp nạp USB-UART vào mạch, chọn cổng COM tương ứng và bấm **Upload**.

### 4.2. Triển khai code trên Sipeed MaixCAM Lite (U2)
1.  Kết nối MaixCAM Lite với máy tính qua cổng USB Type-C hoặc kết nối mạng WiFi chung.
2.  Truy cập vào thiết bị qua SSH (sử dụng MobaXterm hoặc Command Prompt):
    *   Địa chỉ IP: Kiểm tra IP cấp phát trên Router hoặc qua màn hình hiển thị.
    *   User: `root` | Password: `root` (hoặc mật khẩu mặc định của NSX).
3.  Tải thư mục `Gay_Nguoi_Mu/firmware/maixcam_app/` lên thư mục `/root/` của MaixCAM.
4.  Cài đặt các thư viện Python bổ sung nếu chưa có (ví dụ: `pyserial`, `requests`):
    `pip install pyserial requests`
5.  **Cấu hình API Key**:
    *   Mở file `/root/maixcam_app/main.py` trên thiết bị và điền API Key đăng ký miễn phí từ ocr.space vào biến `OCR_API_KEY`.
6.  **Cài đặt tự động khởi chạy khi bật nguồn**:
    *   Tạo file dịch vụ systemd: `/etc/systemd/system/smartcane.service`
        ```ini
        [Unit]
        Description=Smart Cane Main Python Application
        After=multi-user.target

        [Service]
        Type=simple
        WorkingDirectory=/root/maixcam_app
        ExecStart=/usr/bin/python3 /root/maixcam_app/main.py
        Restart=always
        RestartSec=5

        [Install]
        WantedBy=multi-user.target
        ```
    *   Kích hoạt dịch vụ:
        ```bash
        systemctl daemon-reload
        systemctl enable smartcane.service
        systemctl start smartcane.service
        ```

---

## 5. Hướng Dẫn Vận Hành Thiết Bị

*   **Bật/Tắt nguồn**: Nhấn nút nguồn **BT1** (nối IP5306) một lần để khởi động thiết bị. Để tắt, nhấn giữ nút nguồn 3-5 giây. Nhấn 2 lần nhanh để kiểm tra vạch pin hiển thị qua LED1-LED4 trên mạch.
*   **Nhận diện mệnh giá tiền**: Nhấn **Nút SOS (BT2)** 1 lần. Camera MaixCAM sẽ chụp ảnh, chạy mô hình học máy cục bộ trên NPU để phân tích và phát âm thanh mệnh giá tiền tìm được ra loa ngay lập tức (Ví dụ: *"Mười nghìn đồng"*, *"Năm mươi nghìn đồng"*...).
*   **Gửi tín hiệu cứu hộ SOS**: Nhấn **Nút SOS (BT2)** 2 lần nhanh. Thiết bị sẽ kích hoạt đèn LED nhấp nháy liên tục, lấy dữ liệu tọa độ GPS mới nhất từ U3, sau đó gửi tin nhắn khẩn cấp kèm link liên kết Google Maps vị trí của gậy về Telegram của người thân.
*   **Đọc chữ tài liệu/sách báo**: Nhấn **Nút OCR (BTN_OCR)** 1 lần. Thiết bị sẽ phát âm thanh thông báo bắt đầu chụp, gửi ảnh lên hệ thống đám mây để nhận dạng chữ tiếng Việt, sau đó phát văn bản đọc được ra loa.
*   **Cảnh báo khoảng cách va chạm**: Cảm biến siêu âm tự động hoạt động liên tục.
    *   Khoảng cách vật cản **40cm - 80cm**: Loa phát tiếng bíp thưa.
    *   Khoảng cách vật cản **dưới 40cm**: Loa phát tiếng bíp dồn dập báo hiệu nguy hiểm cần dừng lại ngay.
