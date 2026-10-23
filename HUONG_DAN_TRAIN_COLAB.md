# 🚀 HƯỚNG DẪN HUẤN LUYỆN MODEL AI MAIXCAM TRÊN GOOGLE COLAB

Tài liệu hướng dẫn chi tiết quy trình chuyển đổi từ **JupyterLab (CPU nội bộ)** sang **Google Colab (GPU T4 miễn phí)** để huấn luyện 2 mô hình:
1. **Nhận diện tiền Polymer VND** (10k, 20k, 50k, 100k, 200k, 500k)
2. **Nhận diện 36 Ký tự OCR** (0-9, A-Z)

---

## ⚡ Ưu điểm khi chuyển từ JupyterLab sang Google Colab
- **Tốc độ vượt trội**: Huấn luyện 25-30 epochs chỉ mất **~2 đến 3 phút** trên GPU T4 của Colab (thay vì 30 - 60 phút khi chạy CPU trên JupyterLab máy tính).
- **Không nóng máy / không tốn RAM** máy tính cá nhân.
- File Notebook đã cấu hình sẵn 100%, chỉ cần nhấn nút chạy theo từng ô.

---

## 📦 BƯỚC 1: ĐÓNG GÓI DỮ LIỆU TỪ MÁY TÍNH
Tại thư mục `gay_nguoi_mu_maixcam`, bạn có thể thực hiện 1 trong 2 cách:

- **Cách 1 (Khuyên dùng - 1 click):** Double click vào file:
  `CHUAN_BI_DATASET_CHO_COLAB.bat`
- **Cách 2 (Bằng dòng lệnh):**
  ```bash
  python scripts/pack_datasets_for_colab.py
  ```

Sau khi chạy xong, trong thư mục gốc sẽ có sẵn 2 file nén rất nhẹ:
- `dataset_money_yolo.zip` (~24 MB - 1,196 ảnh)
- `dataset_chars_yolo.zip` (~7 MB - 429 ảnh)

---

## 🌐 BƯỚC 2: MỞ NOTEBOOK TRÊN GOOGLE COLAB
1. Mở trình duyệt web và truy cập: **[https://colab.research.google.com/](https://colab.research.google.com/)**
2. Đăng nhập bằng tài khoản Google.
3. Khi hộp thoại hiện lên, chọn tab **Upload (Tải lên)** -> Bấm **Browse (Duyệt file)**.
4. Chọn file notebook trong thư mục dự án của bạn:
   `C:\Users\Public\Documents\Altium\08052026\gay_nguoi_mu_maixcam\Train_MaixCAM_GoogleColab.ipynb`

---

## ⚙️ BƯỚC 3: BẬT GPU MIỄN PHÍ TRÊN COLAB
1. Trên thanh menu trên cùng của Colab, chọn **Runtime (Thời gian chạy)** -> **Change runtime type (Thay đổi loại thời gian chạy)**.
2. Tại mục **Hardware accelerator (Bộ tăng tốc phần cứng)**: Chọn **T4 GPU**.
3. Bấm **Save (Lưu)**.

---

## 📤 BƯỚC 4: TẢI DATASET LÊN COLAB (CÓ TỰ ĐỘNG TẢI TỪ GOOGLE DRIVE)
Bạn có thể chọn 1 trong 2 cách:
- **Cách 1 (Tự động 100% - Khuyên dùng):** Ô Code Bước 2 trong Notebook đã được tích hợp sẵn link Google Drive của bạn (`dataset_money_yolo.zip` và `dataset_chars_yolo.zip`). Chỉ cần nhấn Play (▶) là Colab tự tải về trong 2-3 giây!
- **Cách 2 (Thủ công nếu muốn):** Bấm vào biểu tượng **Folder 📁** ở mép trái màn hình Colab, rồi kéo thả file zip từ máy tính vào.

---

## ▶️ BƯỚC 5: CHẠY TIẾN TRÌNH HUẤN LUYỆN
Bạn chỉ cần lần lượt bấm nút **Play (▶)** ở từng ô code:
- **Ô 1 (Setup)**: Cài đặt thư viện `ultralytics`, `onnx`, `onnxslim`, `gdown`.
- **Ô 2 (Download & Extract)**: Tự động tải dataset từ Google Drive và tạo cấu hình YAML chuẩn.
- **Ô 3A (Train Money)**: Huấn luyện YOLOv5nu Tiền VND (25 epochs, imgsz=320, GPU ~2 phút).
- **Ô 3B (Train Chars)**: Huấn luyện YOLOv5nu 36 Ký tự OCR (A-Z, 0-9).
- **Ô 4 (Export & Download)**: Tự động xuất file ONNX, sinh file `.mud` chuẩn (`model_type = yolov8`), đóng gói thành `maixcam_trained_models.zip` và tự động kích hoạt tải về máy tính của bạn!

---

## 🔄 BƯỚC 6: CHUYỂN ĐỔI SANG .CVIMODEL TRÊN MAIXHUB (CHO MAIXCAM SG2002)
1. Truy cập trang web chính thức: **[https://maixhub.com/model/convert](https://maixhub.com/model/convert)**
2. Chọn phần cứng: **MaixCAM** (Chip Sophgo SG2002 / CV181x).
3. Tải lên file ONNX (lấy từ file zip vừa tải về):
   - `vnd_money_v2.onnx` (Tiền VND)
   - hoặc `char_ocr_v2.onnx` (Ký tự OCR)
4. Chọn loại Model: **YOLOv8**  
   *(⚠️ LƯU Ý SỐNG CÒN: Phải chọn **YOLOv8** vì mô hình huấn luyện bằng `yolov5nu` có cấu trúc Detection Head dạng Anchor-Free của YOLOv8. Nếu chọn nhầm YOLOv5 thuần, MaixHub sẽ báo lỗi lệch tensor đầu ra!)*
5. Độ phân giải (Resolution): **320x320**.
6. Bấm **Convert**, hệ thống Cloud NPU của MaixHub sẽ biên dịch trong 1-2 phút.
7. Tải file ZIP từ MaixHub về, giải nén và đổi tên file `.cvimodel` bên trong thành:
   - `vnd_money_v2.cvimodel` (cho tiền)
   - `char_ocr_v2.cvimodel` (cho ký tự)

---

## 📲 BƯỚC 7: NẠP VÀO THIẾT BỊ MAIXCAM
1. Chép các file vừa tạo vào thư mục:
   `Gay_Nguoi_Mu/firmware/maixcam_app/models/`
   Gồm có:
   - `vnd_money_v2.cvimodel` + `vnd_money_v2.mud`
   - `char_ocr_v2.cvimodel` + `char_ocr_v2.mud`
2. Cắm cáp USB Type-C nối MaixCAM với máy tính.
3. Chạy lệnh đồng bộ tự động nạp lên phần cứng:
   ```bash
   python sync_and_test_maixcam.py
   ```
4. MaixCAM sẽ nạp mô hình mới vào NPU và chạy nhận diện siêu nhanh (~30ms/frame)!
