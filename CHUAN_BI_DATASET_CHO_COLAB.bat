@echo off
chcp 65001 > nul
title CHUAN BI DATASET VA DONG GOI CHO GOOGLE COLAB
cls
echo ====================================================================
echo    DỰ ÁN: GẬY THÔNG MINH CHO NGƯỜI KHIẾM THỊ (MAIXCAM AI)
echo    TỰ ĐỘNG CHUẨN BỊ & ĐÓNG GÓI DATASET CHO GOOGLE COLAB
echo ====================================================================
echo.
echo [1/3] Đang cập nhật nhãn và phân chia tập dữ liệu Tiền VND...
python scripts\prepare_money_dataset.py
echo.
echo [2/3] Đang cập nhật nhãn và phân chia tập dữ liệu 36 Ký tự OCR...
python scripts\prepare_char_dataset_real.py
echo.
echo [3/3] Đang nén file ZIP và chuẩn hóa cấu hình cho Colab...
python scripts\pack_datasets_for_colab.py
echo.
echo ====================================================================
echo HOÀN TẤT! CÁC FILE ĐÃ SẴN SÀNG ĐỂ TẢI LÊN GOOGLE COLAB:
echo  - dataset_money_yolo.zip (Dataset tiền)
echo  - dataset_chars_yolo.zip (Dataset chữ cái / số)
echo  - Train_MaixCAM_GoogleColab.ipynb (File Notebook chạy trên Colab)
echo ====================================================================
echo.
pause
