#pragma once

// U3 ESP32 DOIT DEVKIT — SR04, GPS, SIM 4G, SOS, LED
// PCB ECO 15/06/2026 + link UART qua RX2/TX2
// Quy uoc: Dn = GPIO n | RX2/D16 = GPIO16 | TX2/D17 = GPIO17

#define PIN_SR04_TRIG         32   // D32
#define PIN_SR04_ECHO         33   // D33

// SIM 4G (H3): D26 nhận (RX) | D25 truyền (TX)
#define PIN_SIM_RX            26   // D26 <- SIM TX
#define PIN_SIM_TX            25   // D25 -> SIM RX
#define PIN_SIM_RST           18   // D18 -> RST_SIM
#define SIM_BAUD              115200

// GPS (H4): D13 truyen (TX) | D14 nhan (RX)
#define PIN_GPS_TX            13   // D13 (ESP32 TX) -> GPS RX
#define PIN_GPS_RX            14   // D14 (ESP32 RX) <- GPS TX
#define GPS_BAUD              9600

#define PIN_BTN_SOS           27   // D27 (Net BTN_SOS -> Nut BT2)
#define PIN_BTN_OCR           21   // D21 (Nut BT3)
#define PIN_BTN_3             2    // D2 (Net BTN_3 tren PCB)
#define PIN_LED_SOS           4    // D4

#define PIN_LINK_RX           16   // D16 (RX2 pin on silk) <- MaixCAM TX (A19 / Lỗ 9)
#define PIN_LINK_TX           17   // D17 (TX2 pin on silk) -> MaixCAM RX (A18 / Lỗ 8)
#define LINK_BAUD             9600


inline void logPinMap(Print& out) {
    out.println("[PINS] ========== U3 ESP32 DevKit ==========");
    out.printf("[PINS] SR04:  TRIG=GPIO%d (D32)  ECHO=GPIO%d (D33)  [cap 5V]\n",
               PIN_SR04_TRIG, PIN_SR04_ECHO);
    out.printf("[PINS] SIM:   RX=GPIO%d (D26<-SIM TX)  TX=GPIO%d (D25->SIM RX)  RST=GPIO%d (D18)\n",
               PIN_SIM_RX, PIN_SIM_TX, PIN_SIM_RST);
    out.printf("[PINS] GPS:   TX=GPIO%d (D13->GPS RX)  RX=GPIO%d (D14<-GPS TX)  @%d\n",
               PIN_GPS_TX, PIN_GPS_RX, GPS_BAUD);
    out.printf("[PINS] SOS:   BTN=GPIO%d (D27)  LED=GPIO%d (D4)\n",
               PIN_BTN_SOS, PIN_LED_SOS);
    out.printf("[PINS] LINK:  RX=GPIO%d (D16<-MaixCAM TX A19)  TX=GPIO%d (D17->MaixCAM RX A18) @%d\n",
               PIN_LINK_RX, PIN_LINK_TX, LINK_BAUD);
    out.println("[PINS] =====================================");
}

