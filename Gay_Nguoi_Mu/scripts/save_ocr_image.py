import os
import sys
import time
import base64
from datetime import datetime

# Yêu cầu thư viện: pip install pyserial
try:
    import serial
except ImportError:
    print("Vui long cai dat pyserial bang lenh: pip install pyserial")
    sys.exit(1)

def main():
    # Cấu hình cổng COM và baudrate (Thay đổi cổng COM cho đúng với máy của bạn)
    port = "COM9"  # Ví dụ: COM3, COM5, /dev/ttyUSB0...
    baudrate = 115200

    print("==================================================")
    print(" Chuong trinh tu dong luu anh tu ESP32-S3 sang PC")
    print("==================================================")
    print(f"Dang ket noi voi cong {port} o baudrate {baudrate}...")
    
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
    except Exception as e:
        print(f"Loi: Khong the mo cong {port}. Vui long kiem tra lai!")
        print(f"Chi tiet: {e}")
        return

    print(f"Da mo cong {port} thanh cong! Dang lang nghe du lieu...")
    print("--------------------------------------------------")

    # Tạo thư mục đầu ra nếu chưa có
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    is_collecting_img = False
    img_data_str = ""

    try:
        while True:
            if ser.in_waiting > 0:
                line_bytes = ser.readline()
                try:
                    line = line_bytes.decode('utf-8', errors='ignore').strip()
                except Exception:
                    continue

                if not line:
                    continue

                # Kích hoạt trạng thái nhận ảnh
                if line == "[IMG_START]":
                    is_collecting_img = True
                    img_data_str = ""
                    print("\n[PC] Dang nhan du lieu anh JPEG tu ESP32-S3...")
                    continue
                
                # Kết thúc nhận ảnh và lưu file
                elif line == "[IMG_END]":
                    is_collecting_img = False
                    if img_data_str:
                        try:
                            # Giải mã Base64 và lưu thành tệp hình ảnh
                            img_bytes = base64.b64decode(img_data_str)
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = os.path.join(output_dir, f"ocr_{timestamp}.jpg")
                            
                            with open(filename, "wb") as f:
                                f.write(img_bytes)
                                
                            print(f"[PC] -> DA LUU ANH THANH CONG: {filename} ({len(img_bytes)} bytes)\n")
                        except Exception as decode_err:
                            print(f"[PC] Loi khi giai ma/luu anh: {decode_err}\n")
                    else:
                        print("[PC] Du lieu anh rong, khong the luu.\n")
                    continue

                # Thu thập dữ liệu Base64
                if is_collecting_img:
                    # Nối dữ liệu dòng base64
                    img_data_str += line
                else:
                    # In nhật ký từ Serial Monitor ra màn hình
                    print(line)

            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\nDa dung chuong trinh.")
    finally:
        ser.close()

if __name__ == "__main__":
    main()
