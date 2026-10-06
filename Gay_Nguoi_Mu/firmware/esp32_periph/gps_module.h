#pragma once

#include <Arduino.h>
#include "tinygps_plus.h"
#include "pins.h"

namespace Gps {

static TinyGPSPlus gps;
static uint32_t totalBytesReceived = 0;
static uint32_t lastPrintMs = 0;
static uint32_t lastSwapMs = 0;

static int actualTx = PIN_GPS_TX; // D13
static int actualRx = PIN_GPS_RX; // D14
static bool locked = false;

inline void begin() {
    actualTx = PIN_GPS_TX;
    actualRx = PIN_GPS_RX;
    totalBytesReceived = 0;
    locked = false;
    lastSwapMs = millis();
    lastPrintMs = millis();

    Serial2.begin(GPS_BAUD, SERIAL_8N1, actualRx, actualTx);
    Serial.printf("[GPS] Khoi tao Serial2: TX=D%d, RX=D%d @%d baud (Che do loc: KHONG ghi raw NMEA)\n",
                  actualTx, actualRx, GPS_BAUD);
}

inline void poll() {
    while (Serial2.available() > 0) {
        char c = (char)Serial2.read();
        totalBytesReceived++;
        gps.encode(c);
        if (!locked && (c == '$' || totalBytesReceived > 10)) {
            locked = true;
        }
    }

    uint32_t now = millis();

    // Auto-swap cap chan neu chua nhan duoc byte nao sau 4s
    if (!locked && totalBytesReceived == 0 && (now - lastSwapMs >= 4000)) {
        lastSwapMs = now;
        if (actualTx == PIN_GPS_TX) {
            actualTx = PIN_GPS_RX; // 14
            actualRx = PIN_GPS_TX; // 13
        } else {
            actualTx = PIN_GPS_TX; // 13
            actualRx = PIN_GPS_RX; // 14
        }
        Serial.printf("[GPS] Khong co luong NMEA, tu dong doi cap chan -> TX=D%d, RX=D%d...\n",
                      actualTx, actualRx);
        Serial2.end();
        delay(30);
        Serial2.begin(GPS_BAUD, SERIAL_8N1, actualRx, actualTx);
    }

    // Chi in log khi GPS bat duoc toa do FIX thuc su (khong spam dinh ky)
    if (gps.location.isUpdated() && gps.location.isValid()) {
        if (now - lastPrintMs >= 10000) {
            lastPrintMs = now;
            int sats = gps.satellites.isValid() ? gps.satellites.value() : 0;
            Serial.printf("[GPS FIX] Toa do: %.6f, %.6f | Ve tinh: %d\n",
                          gps.location.lat(), gps.location.lng(), sats);
        }
    }
}

inline bool nmeaAlive() { return totalBytesReceived > 0; }
inline bool fix() { return gps.location.isValid(); }
inline double lat() { return gps.location.lat(); }
inline double lon() { return gps.location.lng(); }
inline int sats() { return gps.satellites.isValid() ? gps.satellites.value() : 0; }
inline uint32_t bytesReceived() { return totalBytesReceived; }

} // namespace Gps
