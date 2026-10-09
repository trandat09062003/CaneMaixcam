# Tài Liệu Kỹ Thuật Firmware & Triển Khai Gậy Thông Minh

Tài liệu hướng dẫn chi tiết dành cho phần mềm nhúng chạy trên **Sipeed MaixCAM Lite** và **ESP32 DOIT DevKit V1**.

---

## 1. Phân Bổ Kiến Trúc Firmware

```
[ Camera MIPI CSI ] ──> [ MaixCAM Lite (Sophgo SG2002) ] ──> [ Loa Onboard 4Ω 3W ]
                             │                      ▲
                    UART1 TX │ (9600 8N1)  UART1 RX │ (9600 8N1)
                    (/dev/ttyS1)           (/dev/ttyS1)
                             ▼                      │
                        [ ESP32 DOIT DevKit V1 ]
                             │         │         │
                             ▼         ▼         ▼
                        [AJ-SR04M] [NEO-6M] [A7680C 4G]
```

* **MaixCAM Lite (`maixcam_app/`)**: Đảm nhiệm tác vụ nặng về AI thị giác máy tính và phát âm thanh:
  * NPU Sophgo SG2002 tăng tốc mô hình `vnd_money_v2.cvimodel` (YOLOv5n nhận diện 6 mệnh giá polymer).
  * NPU tăng tốc mô hình `char_ocr_v2.cvimodel` (YOLOv5n nhận diện 36 ký tự số và chữ cái).
  * Xử lý giao tiếp UART1 với ESP32 qua chân A18 (RX), A19 (TX).
  * Phát trực tiếp file âm thanh `.mp3`/`.wav` tiếng Việt qua tầng công suất PA onboard (VOP/VON) ra loa.
* **ESP32 (`esp32_periph/`)**: Đảm nhiệm tác vụ I/O thời gian thực và cứu hộ:
  * Đọc khoảng cách cảm biến siêu âm chống nước AJ-SR04M (ngưỡng 40cm và 80cm).
  * Đọc tọa độ GPS thời gian thực từ module NEO-6M qua Serial2.
  * Điều khiển module SIMCom A7680C 4G LTE qua Serial1 bằng tập lệnh AT.
  * Gửi tọa độ GPS kèm liên kết Google Maps về Telegram khi kích hoạt nút SOS.

---

## 2. Danh Mục Tài Nguyên & File Mô Hình

Toàn bộ file mô hình nhị phân đã biên dịch cho NPU SG2002 được đặt tại thư mục:
`firmware/maixcam_app/models/`

| Tệp tin | Định dạng | Chức năng |
| :--- | :--- | :--- |
| `vnd_money_v2.cvimodel` | CVI INT8 Model | Mô hình nhận diện 6 mệnh giá tiền polymer VND |
| `vnd_money_v2.mud` | Cấu hình MaixPy | Khai báo nhãn, scale, mean và đường dẫn file cvimodel |
| `char_ocr_v2.cvimodel` | CVI INT8 Model | Mô hình nhận diện 36 ký tự (0-9, a-z) |
| `char_ocr_v2.mud` | Cấu hình MaixPy | Khai báo 36 nhãn ký tự cho mô hình OCR offline |

Thư mục âm thanh: `firmware/maixcam_app/audio/` chứa đầy đủ các file âm thanh giọng đọc tiếng Việt phục vụ thông báo trạng thái, đọc kết quả mệnh giá tiền và đọc ký tự/số.

---

## 3. Cấu Hình Dịch Vụ Nền Tự Động Khởi Động (Systemd)

Trên hệ điều hành Linux của MaixCAM, tạo file cấu hình dịch vụ tại `/etc/systemd/system/smartcane.service`:

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

Kích hoạt và chạy dịch vụ:
```bash
systemctl daemon-reload
systemctl enable smartcane.service
systemctl restart smartcane.service
```

Xem log hoạt động thời gian thực:
```bash
journalctl -u smartcane.service -f
```

---

## 4. Giao Thức Truyền Tin UART (MaixCAM <-> ESP32)

* Cấu hình cổng nối tiếp: **Baudrate: 9600**, **Data bits: 8**, **Parity: None**, **Stop bits: 1**.
* Cú pháp lệnh điều khiển:
  * `CMD:MONEY\n`: ESP32 yêu cầu MaixCAM kích hoạt camera quét mệnh giá tiền.
  * `CMD:OCR\n`: ESP32 yêu cầu MaixCAM kích hoạt camera quét đọc chữ/ký tự.
  * `DIST:<cm>\n`: ESP32 định kỳ gửi khoảng cách vật cản (đơn vị cm).
  * `STATUS:OK\n`: MaixCAM phản hồi trạng thái hoạt động bình thường.
