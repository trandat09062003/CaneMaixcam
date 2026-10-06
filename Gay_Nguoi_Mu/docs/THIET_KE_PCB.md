# Thiết kế PCB — Gậy hỗ trợ người khiếm thị

Tài liệu net label và layout Altium: `C:\Users\Public\Documents\Altium\2026\Gay_Nguoi_Mu`

## File pin mapping (dùng cho firmware)

| File | Nội dung |
|------|----------|
| `mo_ta_ket_noi_chan_PCB.txt` | Bảng nối chân đầy đủ U2 + U3 theo schematic |
| `hardware/pins_s3.h` | GPIO firmware ESP32-S3 (U2) |
| `hardware/pins_esp32.h` | GPIO firmware ESP32 DevKit (U3) |

## U2 — ESP32-S3-N16R8

| Net | GPIO | Chân IC | Chức năng |
|-----|------|---------|-----------|
| BAT_ADC | 3 | Pin 12 | Đo pin (ADC) |
| LINK_TX / LINK_RX | 39 / 38 | Pin 33 / 32 | UART nối U3 (ECO) |
| I2S_DIN / LRCLK / BCLK | 21 / 41 / 42 | Pin 24 / 35 / 36 | MAX98357A + loa |
| Camera DVP | 16 / 17 | Pin 8 / 9 | Freenove OV2640 (không nối LINK) |
| GPIO0 (BOOT) | 0 | Pin 28 | Nút MODE |
| U0TXD / U0RXD | 43 / 44 | Pin 40 / 39 | Nạp code + Serial Monitor |

Camera: `CAMERA_PROFILE=0` (Freenove) khi LINK dùng GPIO38/39.

## U3 — ESP32 DOIT DevKit (Sheet2.SchDoc — PCB đã hàn)

Quy ước: nhãn `Dn` = GPIO `n`. UART2: RX2 = D16 = GPIO16, TX2 = D17 = GPIO17.

| Net | GPIO | Nhãn DevKit |
|-----|------|-------------|
| SR04_TRIG / ECHO | 32 / 33 | D32 / D33 |
| TX_SIM / RX_SIM | 25 / 26 | D25 / D26 |
| RST_SIM | 18 | D18 |
| GPS_TX / GPS_RX | 13 / 14 | D13 / D14 |
| BTN_SOS / LED_SOS | 27 / 4 | D27 / D4 |
| LINK_TX / LINK_RX | 16 / 17 | RX2 (D16) / TX2 (D17) |

UART link (9600, chéo TX-RX):
- U2 GPIO39 (Pin33) → U3 GPIO16 (RX2)
- U2 GPIO38 (Pin32) ← U3 GPIO17 (TX2)

## Khối trên PCB

1. ESP32-S3 N16R8 (U2)
2. ESP32 DevKit (U3)
3. IP5306 + pin 18650
4. AJ-SR04M, GPS, SIM 4G
5. MAX98357A I2S + loa
6. Nút SOS + LED SOS

Chi tiết dây nguồn, trở, tụ: `mo_ta_ket_noi_chan_PCB.txt`.
