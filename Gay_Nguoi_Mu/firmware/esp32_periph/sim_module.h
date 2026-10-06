#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include "pins.h"

#if __has_include("config.h")
#include "config.h"
#else
#define TELEGRAM_BOT_TOKEN  "YOUR_BOT_TOKEN"
#define TELEGRAM_CHAT_ID    "YOUR_CHAT_ID"
#define SIM_APN             "v-internet"
#define SIM_BOOT_MS         4000
#endif

#ifndef TELEGRAM_GROUP_ID
#define TELEGRAM_GROUP_ID TELEGRAM_CHAT_ID
#endif
#ifndef TELEGRAM_USER_ID
#define TELEGRAM_USER_ID ""
#endif

#ifndef SIM_BOOT_MS
#define SIM_BOOT_MS 4000
#endif

namespace Sim {

static bool ready = false;
static bool atOk = false;
static int signalCsq = -1;
static uint32_t simBaud = SIM_BAUD;
static uint32_t lastCheckMs = 0;
static bool uartOnSim = false;
static String atBuf;
static String lastStatus;

static const uint32_t PROBE_BAUDS[] = {115200, 9600, 57600, 38400};

static void setStatus(const char* msg) {
    lastStatus = msg;
}

static bool waitFor(const char* expect, uint32_t timeoutMs = 5000) {
    uint32_t start = millis();
    while (millis() - start < timeoutMs) {
        while (Serial2.available()) {
            char c = (char)Serial2.read();
            atBuf += c;
            if (atBuf.length() > 512) atBuf.remove(0, atBuf.length() - 256);
            if (atBuf.indexOf(expect) >= 0) return true;
            if (atBuf.indexOf("ERROR") >= 0 && atBuf.indexOf(expect) < 0) return false;
        }
        delay(3);
    }
    return false;
}

static bool sendCmd(const char* cmd, const char* expect, uint32_t timeoutMs = 5000) {
    atBuf = "";
    while (Serial2.available()) Serial2.read();
    Serial2.print(cmd);
    Serial2.print("\r\n");
    return waitFor(expect, timeoutMs);
}

static int actualSimRx = PIN_SIM_RX;
static int actualSimTx = PIN_SIM_TX;

static void switchToSim() {
    // Khong can thiep Serial2 de danh rieng 100% UART2 cho GPS
    return;
}

static void switchToGps() {
    uartOnSim = false;
    return;
}

static void powerOnSim() {
    Serial.println("[SIM] Thu kich hoat PWRKEY tren D18 de bat nguon SIM...");
    pinMode(PIN_SIM_RST, OUTPUT);
    digitalWrite(PIN_SIM_RST, LOW);
    delay(1200);
    digitalWrite(PIN_SIM_RST, HIGH);
    pinMode(PIN_SIM_RST, INPUT_PULLUP);
    delay(1500);
}

static void pulseReset() {
    // Khong ep chan D18 xuong muc thap de tranh lam tat module SIM khi vua sang den
    pinMode(PIN_SIM_RST, INPUT_PULLUP);
    delay(100);
}

static bool tryBaud(uint32_t baud) {
    simBaud = baud;
    Serial2.end();
    delay(20);
    Serial2.begin(baud, SERIAL_8N1, actualSimRx, actualSimTx);
    uartOnSim = true;
    atBuf = "";
    delay(50);
    for (int i = 0; i < 2; i++) {
        if (sendCmd("AT", "OK", 500)) return true;
        delay(80);
    }
    return false;
}

static bool autodetectBaud() {
    // 1. Thu cap chan mac dinh (D26 RX, D25 TX)
    for (uint32_t b : PROBE_BAUDS) {
        if (tryBaud(b)) {
            Serial.printf("[SIM] >> KET NOI THANH CONG tai RX=D%d, TX=D%d @%lu baud!\n", actualSimRx, actualSimTx, (unsigned long)b);
            return true;
        }
    }
    // 2. Neu khong duoc, thu DAO NGUOC CHIEU (D25 RX, D26 TX)
    int tmp = actualSimRx;
    actualSimRx = actualSimTx;
    actualSimTx = tmp;
    for (uint32_t b : PROBE_BAUDS) {
        if (tryBaud(b)) {
            Serial.printf("[SIM] >>> DAO CHIEU TX/RX THANH CONG! RX=D%d, TX=D%d @%lu baud! <<<\n", actualSimRx, actualSimTx, (unsigned long)b);
            return true;
        }
    }
    // Tra lai ve mac dinh neu ca 2 deu khong duoc
    tmp = actualSimRx; actualSimRx = actualSimTx; actualSimTx = tmp;
    return false;
}

static String urlEncode(const String& text) {
    String out;
    const char* hex = "0123456789ABCDEF";
    for (unsigned i = 0; i < text.length(); i++) {
        char c = text.charAt(i);
        if (isalnum(c) || c == '-' || c == '_' || c == '.' || c == '~') out += c;
        else if (c == ' ') out += '+';
        else {
            out += '%';
            out += hex[(c >> 4) & 0xF];
            out += hex[c & 0xF];
        }
    }
    return out;
}

static bool attachGprsSimcom() {
    if (!sendCmd("AT+CGATT=1", "OK", 10000)) return false;
    sendCmd("AT+SAPBR=3,1,\"CONTYPE\",\"GPRS\"", "OK", 4000);
    String apnCmd = String("AT+SAPBR=3,1,\"APN\",\"") + SIM_APN + "\"";
    if (!sendCmd(apnCmd.c_str(), "OK", 4000)) return false;
    return sendCmd("AT+SAPBR=1,1", "OK", 20000);
}

static bool attachGprsLte() {
    if (!sendCmd("AT+CGATT=1", "OK", 10000)) return false;
    String pdp = String("AT+CGDCONT=1,\"IP\",\"") + SIM_APN + "\"";
    sendCmd(pdp.c_str(), "OK", 4000);
    return sendCmd("AT+CGACT=1,1", "OK", 20000);
}

static bool attachGprs() {
    if (attachGprsSimcom()) return true;
    return attachGprsLte();
}

static bool httpGet(const String& url) {
    if (!sendCmd("AT+HTTPINIT", "OK", 4000)) return false;
    String para = String("AT+HTTPPARA=\"URL\",\"") + url + "\"";
    if (!sendCmd(para.c_str(), "OK", 6000)) {
        sendCmd("AT+HTTPTERM", "OK", 2000);
        return false;
    }
    if (!sendCmd("AT+HTTPACTION=0", "OK", 4000)) {
        sendCmd("AT+HTTPTERM", "OK", 2000);
        return false;
    }
    bool ok = waitFor("+HTTPACTION: 0,200", 60000) || waitFor("+HTTPACTION: 0,2", 60000);
    sendCmd("AT+HTTPTERM", "OK", 3000);
    return ok;
}

inline String googleTtsUrl(const String& text) {
    return String("http://translate.google.com.vn/translate_tts?ie=UTF-8&client=tw-ob&tl=vi&q=") +
           urlEncode(text);
}

static int parseHttpActionSize() {
    int idx = atBuf.indexOf("+HTTPACTION:");
    if (idx < 0) return -1;
    int method = 0, code = 0, size = 0;
    if (sscanf(atBuf.c_str() + idx, "+HTTPACTION: %d,%d,%d", &method, &code, &size) >= 2) {
        if (code == 200 && size > 0) return size;
    }
    return -1;
}

inline bool httpDownload(const String& url, uint8_t* buf, size_t maxLen, size_t* outLen) {
    *outLen = 0;
    if (!buf || maxLen < 256) return false;
    switchToSim();
    if (!attachGprs()) return false;

    if (!sendCmd("AT+HTTPINIT", "OK", 4000)) return false;
    String para = String("AT+HTTPPARA=\"URL\",\"") + url + "\"";
    if (!sendCmd(para.c_str(), "OK", 8000)) {
        sendCmd("AT+HTTPTERM", "OK", 2000);
        return false;
    }
    atBuf = "";
    if (!sendCmd("AT+HTTPACTION=0", "OK", 4000)) {
        sendCmd("AT+HTTPTERM", "OK", 2000);
        return false;
    }
    if (!waitFor("+HTTPACTION:", 90000)) {
        sendCmd("AT+HTTPTERM", "OK", 2000);
        return false;
    }
    int bodySize = parseHttpActionSize();
    if (bodySize <= 0 || (size_t)bodySize > maxLen) {
        sendCmd("AT+HTTPTERM", "OK", 2000);
        return false;
    }

    char readCmd[32];
    snprintf(readCmd, sizeof(readCmd), "AT+HTTPREAD=0,%d", bodySize);
    atBuf = "";
    while (Serial2.available()) Serial2.read();
    Serial2.print(readCmd);
    Serial2.print("\r\n");

    uint32_t start = millis();
    bool gotHeader = false;
    int dataRemaining = bodySize;
  size_t written = 0;
    String line;

    while (millis() - start < 90000UL && dataRemaining > 0) {
        while (Serial2.available()) {
            int ch = Serial2.read();
            if (!gotHeader) {
                if (ch == '\n') {
                    if (line.indexOf("+HTTPREAD:") >= 0) {
                        gotHeader = true;
                        line = "";
                    } else if (line.length() > 0) {
                        line = "";
                    }
                    continue;
                }
                if (ch != '\r') line += (char)ch;
            } else {
                buf[written++] = (uint8_t)ch;
                dataRemaining--;
                if (written >= maxLen) break;
            }
        }
        if (gotHeader && dataRemaining <= 0) break;
        delay(2);
    }

    sendCmd("AT+HTTPTERM", "OK", 3000);
    switchToGps();
    if (written < 128) return false;
    *outLen = written;
    return true;
}

static bool refreshCsq() {
    if (!ready || !atOk) return false;
    switchToSim();
    atBuf = "";
    if (sendCmd("AT+CSQ", "OK", 3000)) {
        int idx = atBuf.indexOf("+CSQ:");
        if (idx >= 0) signalCsq = atBuf.substring(idx + 6).toInt();
    }
    bool alive = sendCmd("AT", "OK", 1500);
    switchToGps();
    if (!alive) {
        ready = false;
        setStatus("mat ket noi AT — se thu lai");
    }
    return alive;
}

static bool probe() {
    switchToGps();
    switchToSim();
    pulseReset();

    atOk = autodetectBaud();
    if (!atOk) {
        powerOnSim();
        atOk = autodetectBaud();
    }
    if (!atOk) {
        ready = false;
        setStatus("khong phan hoi AT — kiem tra cap 5V, TX/RX D25/D26, anten");
        switchToGps();
        return false;
    }

    sendCmd("ATE0", "OK", 2000);
    sendCmd("AT+CMEE=1", "OK", 2000);

    bool cpinOk = sendCmd("AT+CPIN?", "READY", 5000);
    if (!cpinOk) {
        cpinOk = sendCmd("AT+CPIN?", "OK", 3000);
        if (!cpinOk) {
            ready = false;
            setStatus("AT OK nhung SIM chua READY — kiem tra SIM, PIN, anten");
            switchToGps();
            return false;
        }
    }

    signalCsq = -1;
    atBuf = "";
    if (sendCmd("AT+CSQ", "OK", 3000)) {
        int idx = atBuf.indexOf("+CSQ:");
        if (idx >= 0) {
            signalCsq = atBuf.substring(idx + 6).toInt();
        }
    }

    ready = true;
    char buf[80];
    snprintf(buf, sizeof(buf), "OK @%lu baud CSQ=%d APN=%s",
             (unsigned long)simBaud, signalCsq, SIM_APN);
    setStatus(buf);
    switchToGps();
    return true;
}

inline void begin() {
    pinMode(PIN_SIM_RST, INPUT_PULLUP);
    setStatus("Tam ngung quet SIM de uu tien danh rieng UART cho GPS");
}

inline void poll() {
    // Khong poll SIM de tranh chiem UART cua GPS
}

inline bool gpsUartActive() { return !uartOnSim; }

inline bool isReady() { return ready; }
inline const char* statusText() { return lastStatus.c_str(); }
inline int csq() { return signalCsq; }
inline uint32_t baud() { return simBaud; }

inline void formatStatus(char* buf, size_t len) {
    if (ready) {
        if (signalCsq >= 0) {
            snprintf(buf, len, "OK @%lu CSQ %d", (unsigned long)simBaud, signalCsq);
        } else {
            snprintf(buf, len, "OK @%lu baud", (unsigned long)simBaud);
        }
    } else {
        snprintf(buf, len, "LOI — %s", lastStatus.c_str());
    }
}

inline bool sendTelegram(const String& text) {
    const char* targets[] = { TELEGRAM_GROUP_ID, TELEGRAM_USER_ID };
    bool anyOk = false;

    for (const char* target : targets) {
        if (!target || strlen(target) == 0) continue;
        bool ok = false;
        if (WiFi.status() == WL_CONNECTED) {
            WiFiClientSecure client;
            client.setInsecure();
            if (client.connect("api.telegram.org", 443)) {
                String url = String("/bot") + TELEGRAM_BOT_TOKEN +
                             "/sendMessage?chat_id=" + target + "&text=" + urlEncode(text);
                client.print(String("GET ") + url + " HTTP/1.1\r\n" +
                             "Host: api.telegram.org\r\n" +
                             "Connection: close\r\n\r\n");
                uint32_t to = millis();
                while (client.connected() && millis() - to < 4000) {
                    if (client.available()) {
                        String line = client.readStringUntil('\n');
                        if (line.indexOf("200 OK") >= 0) { ok = true; break; }
                    }
                }
                if (!ok) ok = true; // Neu da gui GET thanh cong
            }
        }
        if (!ok && ready) {
            switchToSim();
            if (attachGprs()) {
                String url = String("https://api.telegram.org/bot") + TELEGRAM_BOT_TOKEN +
                             "/sendMessage?chat_id=" + target + "&text=" + urlEncode(text);
                ok = httpGet(url);
            }
            switchToGps();
        }
        Serial.printf("[TELEGRAM] Gui SOS toi ID %s: %s\n", target, ok ? "OK" : "FAIL");
        if (ok) anyOk = true;
    }
    return anyOk;
}

inline bool sendLocation(double lat, double lon) {
    const char* targets[] = { TELEGRAM_GROUP_ID, TELEGRAM_USER_ID };
    bool anyOk = false;

    for (const char* target : targets) {
        if (!target || strlen(target) == 0) continue;
        bool ok = false;
        if (WiFi.status() == WL_CONNECTED) {
            WiFiClientSecure client;
            client.setInsecure();
            if (client.connect("api.telegram.org", 443)) {
                String url = String("/bot") + TELEGRAM_BOT_TOKEN +
                             "/sendLocation?chat_id=" + target +
                             "&latitude=" + String(lat, 6) +
                             "&longitude=" + String(lon, 6);
                client.print(String("GET ") + url + " HTTP/1.1\r\n" +
                             "Host: api.telegram.org\r\n" +
                             "Connection: close\r\n\r\n");
                ok = true;
            }
        }
        if (!ok && ready) {
            switchToSim();
            if (attachGprs()) {
                String url = String("https://api.telegram.org/bot") + TELEGRAM_BOT_TOKEN +
                             "/sendLocation?chat_id=" + target +
                             "&latitude=" + String(lat, 6) +
                             "&longitude=" + String(lon, 6);
                ok = httpGet(url);
            }
            switchToGps();
        }
        Serial.printf("[TELEGRAM] Gui GPS toi ID %s: %s\n", target, ok ? "OK" : "FAIL");
        if (ok) anyOk = true;
    }
    return anyOk;
}

}  // namespace Sim
