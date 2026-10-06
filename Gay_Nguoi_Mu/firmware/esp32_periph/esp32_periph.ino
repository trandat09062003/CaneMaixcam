/*
 * Gay Nguoi Mu - ESP32 ngoai vi (U3)
 * SR04, GPS, SIM 4G, SOS, LED | UART <-> ESP32-S3
 */

#include "pins.h"
#include "gps_module.h"
#include "sim_module.h"

#define SERIAL_BAUD         115200
#define SR04_INTERVAL_MS    80     // Quet khoang cach nhanh 80ms
#define SR04_SEND_MIN_MS    100    // Gui nhanh toi thieu 100ms
#define SR04_SEND_FAR_MS    300    // Cap nhat dinh ky 300ms du vat can dung yen (muot ma)
#define SR04_SEND_DELTA_CM  2      // Thay doi chi 2cm la gui ngay sang MaixCAM
#define GPS_SEND_MS         60000
#define HEARTBEAT_MS        3000   // Heartbeat nhanh hon de link on dinh
#define SIM_REPORT_MS       300000
#define LINK_TIMEOUT_MS     45000  // Tang timeout: cho phep Telegram block 10-15s
#define BTN_DEBOUNCE_MS     40
#define BTN_SHORT_MAX_MS    500
#define BTN_DOUBLE_MS       360    // Chuyen che do nhanh, khong bi tre nua giay

static int warnThresholdCm = 150;
static String rxLine;
static String lastLiveSig;
static bool btnHeld = false;
static bool ocrBtnHeld = false;
static uint32_t ocrBtnPressMs = 0;
static uint32_t ocrLastTapMs = 0;
static int ocrTapCount = 0;
static bool ocrLongPressFired = false;
static bool sosLedLocal = false;
static bool sosActive = false;        // Trạng thái báo động SOS
static bool warnModeActive = false;  // Chế độ cảnh báo: LED nhấp nháy + loa kêu
static String currentAppMode = "IDLE"; // Chế độ ứng dụng: "IDLE", "MONEY", "OCR", "SOS", "WARN"
static uint32_t warnLedLastMs = 0;   // Thời điểm toggle LED cảnh báo gần nhất
static bool warnLedState = false;    // Trạng thái LED cảnh báo hiện tại
static bool linkUp = false;
static bool lastLinkUp = false;
static bool lastSimOk = false;
static int curLinkRxPin = PIN_LINK_RX; // 16 (D16)
static int curLinkTxPin = PIN_LINK_TX; // 17 (D17)
static bool linkLocked = true;          // DA CHOT CUNG RX=16, TX=17 KHONG THAY DOI
static uint32_t lastSwapMs = 0;
#define SWAP_INTERVAL_MS    5000

static uint32_t btnPressMs = 0;
static uint32_t lastTapMs = 0;
static int btnTapCount = 0;          // Đếm số lần tap BT2
static bool btnTapPending = false;   // Đang chờ xét tap BT2
static uint32_t lastSr04Ms = 0;
static uint32_t lastGpsSendMs = 0;
static uint32_t lastLiveLogMs = 0;
static uint32_t lastHeartbeatMs = 0;
static uint32_t lastSimReportMs = 0;
static uint32_t lastLinkRxMs = 0;
static int lastSr04Cm = -1;
static int lastSentSr04Cm = -1;
static uint32_t lastSr04SendMs = 0;
static uint32_t lastSr04LogMs = 0;
static uint32_t lastCompactLogMs = 0;
static String lastSpeak = "--";
static bool lastGpsFix = false;
static int lastGpsSats = -1;
static bool isReadingActive = false;
static uint32_t readingUntilMs = 0;

static int readSinglePingUs() {
    digitalWrite(PIN_SR04_TRIG, LOW);
    delayMicroseconds(4);
    digitalWrite(PIN_SR04_TRIG, HIGH);
    delayMicroseconds(15);
    digitalWrite(PIN_SR04_TRIG, LOW);
    long duration = pulseIn(PIN_SR04_ECHO, HIGH, 26000);
    return (int)duration;
}

static int readSr04Cm(long* rawUs = nullptr) {
    int samples[3];
    int validCount = 0;
    for (int i = 0; i < 3; i++) {
        samples[i] = readSinglePingUs();
        if (samples[i] > 1000 && samples[i] < 26000) {
            validCount++;
        }
        if (i < 2) delayMicroseconds(2000);
    }

    if (validCount == 0) {
        if (rawUs) *rawUs = 0;
        return -1;
    }

    if (samples[0] > samples[1]) { int t = samples[0]; samples[0] = samples[1]; samples[1] = t; }
    if (samples[1] > samples[2]) { int t = samples[1]; samples[1] = samples[2]; samples[2] = t; }
    if (samples[0] > samples[1]) { int t = samples[0]; samples[0] = samples[1]; samples[1] = t; }

    int medianUs = samples[1] > 0 ? samples[1] : samples[2];
    if (rawUs) *rawUs = medianUs;

    int cm = (int)((medianUs + 29) / 58.2);
    if (cm >= 18 && cm <= 450) {
        return cm;
    }
    return -1;
}

static void setSosLed(bool on) {
    sosLedLocal = on;
    digitalWrite(PIN_LED_SOS, on ? HIGH : LOW);
}

// ============================================================
// NON-BLOCKING LED BLINK STATE MACHINE (khong dung delay())
// Pattern 1: Money  -> HIGH 250ms -> LOW (1 blink)
// Pattern 2: OCR    -> HIGH 180ms -> LOW 140ms -> HIGH 180ms -> LOW (2 blink)
// Pattern 3: Exit   -> HIGH 150ms -> LOW 100ms -> HIGH 150ms -> LOW 100ms -> HIGH 150ms -> LOW (3 blink)
// ============================================================
static uint8_t  ledBlinkPattern = 0;   // 0=off, 1=money, 2=ocr, 3=exit
static uint8_t  ledBlinkStep    = 0;
static uint32_t ledBlinkMs      = 0;

static void startBlinkMoney() {
    if (sosLedLocal || warnModeActive) return;  // SOS/WARN co uu tien cao hon
    ledBlinkPattern = 1;
    ledBlinkStep    = 0;
    ledBlinkMs      = millis();
    digitalWrite(PIN_LED_SOS, HIGH);
}

static void startBlinkOcr() {
    if (sosLedLocal || warnModeActive) return;
    ledBlinkPattern = 2;
    ledBlinkStep    = 0;
    ledBlinkMs      = millis();
    digitalWrite(PIN_LED_SOS, HIGH);
}

static void startBlinkExit() {
    if (sosLedLocal || warnModeActive) return;
    ledBlinkPattern = 3;
    ledBlinkStep    = 0;
    ledBlinkMs      = millis();
    digitalWrite(PIN_LED_SOS, HIGH);
}

// Goi moi vong loop() de cap nhat trang thai LED (non-blocking state machine)
// Pattern 1 (money) : step0=250ms HIGH -> step1=LOW (done)
// Pattern 2 (ocr)   : step0=180ms HIGH -> step1=140ms LOW -> step2=180ms HIGH -> step3=LOW (done)
// Pattern 3 (exit)  : step0=150ms HIGH -> step1=100ms LOW -> step2=150ms HIGH -> step3=100ms LOW -> step4=150ms HIGH -> step5=LOW (done)
static const uint32_t BLINK_MONEY_MS[] = {250};          // thoi gian giu tung step (bat dau tu HIGH)
static const uint32_t BLINK_OCR_MS[]   = {180, 140, 180}; // HIGH, LOW, HIGH (step3=LOW tuc thi)
static const uint32_t BLINK_EXIT_MS[]  = {150, 100, 150, 100, 150};

static void updateLedBlink(uint32_t now) {
    if (ledBlinkPattern == 0) return;

    uint32_t stepMs = 200;
    if (ledBlinkPattern == 1) {
        stepMs = (ledBlinkStep < 1) ? BLINK_MONEY_MS[ledBlinkStep] : 1;
    } else if (ledBlinkPattern == 2) {
        stepMs = (ledBlinkStep < 3) ? BLINK_OCR_MS[ledBlinkStep] : 1;
    } else if (ledBlinkPattern == 3) {
        stepMs = (ledBlinkStep < 5) ? BLINK_EXIT_MS[ledBlinkStep] : 1;
    }

    if (now - ledBlinkMs < stepMs) return;
    ledBlinkMs = now;

    if (ledBlinkPattern == 1) {
        // Money: step0 het -> tat LED, done
        digitalWrite(PIN_LED_SOS, LOW);
        ledBlinkPattern = 0;
        ledBlinkStep    = 0;
    } else if (ledBlinkPattern == 2) {
        ledBlinkStep++;
        switch (ledBlinkStep) {
            case 1: digitalWrite(PIN_LED_SOS, LOW);  break;  // sau 180ms: tat
            case 2: digitalWrite(PIN_LED_SOS, HIGH); break;  // sau 140ms: bat
            case 3: digitalWrite(PIN_LED_SOS, LOW);          // sau 180ms: tat, done
                    ledBlinkPattern = 0;
                    ledBlinkStep    = 0;
                    break;
        }
    } else if (ledBlinkPattern == 3) {
        ledBlinkStep++;
        switch (ledBlinkStep) {
            case 1: digitalWrite(PIN_LED_SOS, LOW);  break;  // sau 150ms: tat
            case 2: digitalWrite(PIN_LED_SOS, HIGH); break;  // sau 100ms: bat
            case 3: digitalWrite(PIN_LED_SOS, LOW);  break;  // sau 150ms: tat
            case 4: digitalWrite(PIN_LED_SOS, HIGH); break;  // sau 100ms: bat
            case 5: digitalWrite(PIN_LED_SOS, LOW);          // sau 150ms: tat, done
                    ledBlinkPattern = 0;
                    ledBlinkStep    = 0;
                    break;
        }
    }
}

static void initLinkSerial(int rxPin, int txPin) {
    curLinkRxPin = rxPin;
    curLinkTxPin = txPin;
    Serial1.end();
    delay(20);
    Serial1.begin(LINK_BAUD, SERIAL_8N1, rxPin, txPin);
    Serial.printf("[LINK] Kich hoat UART: RX=GPIO%d, TX=GPIO%d\n", rxPin, txPin);
}

static void trySwapLinkPinsIfNeeded(uint32_t now) {
    // Da chot cung RX=GPIO16, TX=GPIO17 theo yeu cau, khong tu dong swap nua
    return;
}

static void onLinkRx() {
    lastLinkRxMs = millis();
    if (!linkLocked) {
        linkLocked = true;
        Serial.printf("[LINK] >>> DA KHOA CHAN UART THANH CONG: RX=GPIO%d, TX=GPIO%d <<<\n", curLinkRxPin, curLinkTxPin);
    }
    linkUp = true;
}

static void handleTelegramViaSim(const String& raw) {
    String text = raw;
    text.replace("|", "\n");
    bool ok = Sim::sendTelegram(text);
    Serial1.printf("TG:%d\n", ok ? 1 : 0);
    Serial.printf("[TG] %s\n", ok ? "OK" : "FAIL");
}

static void handleLocationViaSim(const String& raw) {
    double lat = 0, lon = 0;
    if (sscanf(raw.c_str(), "%lf,%lf", &lat, &lon) != 2) {
        Serial1.println("TG:0");
        Serial.println("[TG] dinh dang sai");
        return;
    }
    bool ok = Sim::sendLocation(lat, lon);
    Serial1.printf("TG:%d\n", ok ? 1 : 0);
    Serial.printf("[TG] vi tri %s\n", ok ? "OK" : "FAIL");
}

static void handleTtsViaSim(const String& text) {
    static uint8_t buf[16384];
    size_t len = 0;
    String url = Sim::googleTtsUrl(text);
    if (!Sim::httpDownload(url, buf, sizeof(buf), &len)) {
        Serial.println("[TTS] FAIL");
        Serial1.println("W:0");
        Serial1.flush();
        return;
    }
    Serial1.printf("W:%u\n", (unsigned)len);
    Serial1.flush();
    delay(80);
    for (size_t i = 0; i < len; i += 120) {
        size_t n = len - i;
        if (n > 120) n = 120;
        Serial1.print("Y:");
        for (size_t j = 0; j < n; j++) {
            Serial1.printf("%02X", buf[i + j]);
        }
        Serial1.println();
        Serial1.flush();
        delay(12);
    }
    Serial1.println("Y:END");
    Serial1.flush();
}

static void pollLinkRx() {
    while (Serial1.available()) {
        char c = Serial1.read();
        if (c == '\n' || c == '\r') {
            if (rxLine.length() == 0) continue;
            onLinkRx(); // Bất kỳ gói tin nào từ MaixCAM đều xác nhận liên kết LINK OK
            if (rxLine.startsWith("T:")) {
                onLinkRx();
                int t = rxLine.substring(2).toInt();
                if (t != warnThresholdCm) {
                    warnThresholdCm = t;
                    Serial.printf("[CFG] nguong %dcm\n", warnThresholdCm);
                }
            } else if (rxLine.startsWith("L:")) {
                onLinkRx();
                setSosLed(rxLine.charAt(2) == '1');
            } else if (rxLine.startsWith("M:")) {
                onLinkRx();
                handleTelegramViaSim(rxLine.substring(2));
            } else if (rxLine.startsWith("P:")) {
                onLinkRx();
                handleLocationViaSim(rxLine.substring(2));
            } else if (rxLine.startsWith("SPK:1")) {
                onLinkRx();
                isReadingActive = true;
                readingUntilMs = millis() + 8000;
            } else if (rxLine.startsWith("SPK:0")) {
                onLinkRx();
                isReadingActive = false;
                lastCompactLogMs = millis();
            } else if (rxLine.startsWith("V:")) {
                onLinkRx();
                String ocrTxt = rxLine.substring(2);
                lastSpeak = ocrTxt;
                isReadingActive = true;
                readingUntilMs = millis() + 6000; // Tạm dừng log khi đang đọc vé số / văn bản
                Serial.printf("[OCR] >>> Nhận từ MaixCAM: \"%s\" <<<\n", ocrTxt.c_str());
                startBlinkOcr(); // Non-blocking 2 blink
            } else if (rxLine.startsWith("BTN:MONEY") || rxLine == "ACT") {
                onLinkRx();
                lastSpeak = "Doc tien";
                isReadingActive = true;
                readingUntilMs = millis() + 2500;
                Serial.println("[MaixCAM] Nhan dien tien -> LED 1 lan");
                setSosLed(false);
                startBlinkMoney(); // Non-blocking 1 blink
            } else if (rxLine.startsWith("BTN:SCAN") || rxLine.startsWith("BTN:OCR") || rxLine == "LOT") {
                onLinkRx();
                lastSpeak = "Doc chu";
                isReadingActive = true;
                readingUntilMs = millis() + 3500;
                Serial.println("[MaixCAM] Nhan dien chu -> LED 2 lan");
                setSosLed(false);
                startBlinkOcr(); // Non-blocking 2 blink
            } else if (rxLine.startsWith("BTN:IDLE") || rxLine.startsWith("BTN:EXIT") || rxLine.startsWith("MODE:IDLE") || rxLine == "STOP") {
                onLinkRx();
                lastSpeak = "Thoat quet";
                isReadingActive = false;
                currentAppMode = "IDLE";
                Serial.println("[MaixCAM] Thoat che do quet -> LED 3 lan");
                setSosLed(false);
                startBlinkExit(); // Non-blocking 3 blink
            } else if (rxLine.startsWith("MODE:")) {
                onLinkRx();
                String m = rxLine.substring(5);
                m.trim();
                m.toUpperCase();
                Serial.printf("[CHẾ ĐỘ] MaixCAM chuyển sang: %s\n", m.c_str());
                if (m == "MONEY") currentAppMode = "MONEY";
                else if (m == "OCR") currentAppMode = "OCR";
                else if (m == "IDLE") { currentAppMode = "IDLE"; isReadingActive = false; }
            } else if (rxLine.startsWith("A:")) {
                onLinkRx();
            } else if (rxLine.startsWith("I:")) {
                onLinkRx();
                String val = rxLine.substring(2);
                if (val == "FAIL") {
                    lastSpeak = "Khong ro";
                    Serial.println("[TIỀN] Nhận diện: Không rõ tờ tiền");
                } else if (val != "BUSY") {
                    int colonIdx = val.indexOf(':');
                    String denom = (colonIdx >= 0) ? val.substring(0, colonIdx) : val;
                    String conf = (colonIdx >= 0) ? val.substring(colonIdx + 1) : "";
                    if (conf.length() > 0) {
                        lastSpeak = denom + "d (" + conf + "%)";
                        Serial.printf("[TIEN] >>> %s VND (Do tin cay: %s%%) <<<\n", denom.c_str(), conf.c_str());
                    } else {
                        lastSpeak = denom + "d";
                        Serial.printf("[TIEN] >>> %s VND <<<\n", denom.c_str());
                    }
                    isReadingActive = true;
                    readingUntilMs = millis() + 3500; // Tạm dừng log khi đang đọc tiền
                    startBlinkMoney(); // Non-blocking 1 blink
                }
            }
            rxLine = "";
        } else {
            rxLine += c;
            if (rxLine.length() > 480) rxLine = "";
        }
    }
    if (linkUp && millis() - lastLinkRxMs > LINK_TIMEOUT_MS) {
        if (lastLinkUp) Serial.println("[LINK] mat S3");
        linkUp = false;
    }
    lastLinkUp = linkUp;
}

static void sendSimStatus(bool force) {
    bool ok = Sim::isReady();
    if (!force && ok == lastSimOk) return;
    if (ok != lastSimOk) {
        char st[64];
        Sim::formatStatus(st, sizeof(st));
        Serial.printf("[SIM] %s\n", st);
    }
    lastSimOk = ok;
    Serial1.printf("SIM:%d\n", ok ? 1 : 0);
    if (ok) Serial1.printf("Q:%d\n", Sim::csq());
}

static void sendSr04IfNeeded(int cm, uint32_t now, bool force) {
    if (cm <= 0) return;
    bool inWarn = (cm <= warnThresholdCm);
    uint32_t minGap = inWarn ? SR04_SEND_MIN_MS : SR04_SEND_FAR_MS;
    bool changed = (lastSentSr04Cm < 0 ||
                    abs(cm - lastSentSr04Cm) >= SR04_SEND_DELTA_CM);
    if (!force && !changed && (now - lastSr04SendMs) < minGap) return;
    lastSentSr04Cm = cm;
    lastSr04SendMs = now;
    Serial1.print("D:");
    Serial1.println(cm);
}

static void sendGpsIfNeeded(uint32_t now, bool force) {
    bool fix = Gps::fix();
    int sats = Gps::sats();
    bool changed = (fix != lastGpsFix || sats != lastGpsSats);
    if (!force && !changed && (now - lastGpsSendMs) < GPS_SEND_MS) return;
    lastGpsFix = fix;
    lastGpsSats = sats;
    lastGpsSendMs = now;
    if (fix) {
        Serial1.printf("G:%.6f,%.6f,%d\n", Gps::lat(), Gps::lon(), sats);
    } else if (Gps::nmeaAlive()) {
        Serial1.printf("G:0,0,%d\n", sats);
    }
}

static void logCompactLive(bool force = false) {
    uint32_t now = millis();
    // KHI ĐANG NHẬN DIỆN TIỀN, ĐỌC CHỮ HOẶC SOS / CẢNH BÁO: HOÀN TOÀN KHÔNG IN LOG!
    // Chỉ in log trạng thái khi ở chế độ chờ / bình thường (IDLE)
    if (currentAppMode == "MONEY" || currentAppMode == "OCR" || currentAppMode == "SOS" ||
        currentAppMode == "WARN" || sosActive || warnModeActive || isReadingActive) {
        return;
    }

    // Chỉ cập nhật log đều đặn 1 giây/lần khi ở chế độ chờ (IDLE)
    if (!force && (now - lastCompactLogMs < 1000)) return;
    lastCompactLogMs = now;

    char dStr[16];
    if (lastSr04Cm > 0) {
        snprintf(dStr, sizeof(dStr), "%dcm", lastSr04Cm);
    } else {
        snprintf(dStr, sizeof(dStr), "--");
    }

    char linkStr[32];
    if (linkUp) {
        snprintf(linkStr, sizeof(linkStr), "OK(RX:%d)", curLinkRxPin);
    } else {
        snprintf(linkStr, sizeof(linkStr), "--(RX:%d)", curLinkRxPin);
    }
    const char* simStr = Sim::isReady() ? "OK" : "--";
    const char* gpsStr = "--";
    if (Gps::fix()) {
        gpsStr = "FIX";
    } else if (Gps::nmeaAlive()) {
        gpsStr = "nmea";
    }

    int bt2Val = digitalRead(PIN_BTN_SOS);
    int bt3Val = digitalRead(PIN_BTN_OCR);
    Serial.printf("[TRẠNG THÁI] D:%s | Nhận diện:%s | Link:%s | GPS:%s | BT2:%d BT3:%d\n",
                  dStr, lastSpeak.c_str(), linkStr, gpsStr, bt2Val, bt3Val);
}

static void fireCurrency() {
    currentAppMode = "MONEY";
    lastSpeak = "Bat nhan dien tien";
    isReadingActive = true;
    readingUntilMs = millis() + 60000;
    Serial.println("\n[NUT BT3] Nhấn 1 lần -> BẬT NHẬN DIỆN TIỀN (LED 1 lần, loa tút tút chờ...)");
    setSosLed(false);
    Serial1.println("ACT");   // Gui lenh truoc
    Serial1.flush();
    startBlinkMoney();         // Blink non-blocking
}

// ============================================================
// FREERTOS TASK: Gui Telegram nen (khong block loop())
// ============================================================
struct SosTaskParams {
    char msg[256];
    bool sendLoc;
    double lat, lon;
};

static void sosTelegramTask(void* param) {
    SosTaskParams* p = (SosTaskParams*)param;
    Sim::sendTelegram(String(p->msg));
    if (p->sendLoc) {
        Sim::sendLocation(p->lat, p->lon);
    }
    delete p;
    vTaskDelete(NULL);
}

static void fireSos() {
    sosActive = !sosActive;
    if (sosActive) {
        currentAppMode = "SOS";
        lastSpeak = "SOS";
        Serial.println("\n[NUT BT2] >>> BẬT KHẨN CẤP SOS! LOA KÊU LIÊN TỤC! <<<");
        warnModeActive   = false;
        ledBlinkPattern  = 0;    // Huy blink neu dang chay
        setSosLed(true);
        Serial1.println("SOS:ON");
        Serial1.flush();
        // Gui Telegram trong FreeRTOS task rieng - KHONG block loop()
        SosTaskParams* p = new SosTaskParams();
        strncpy(p->msg, "KHAN CAP SOS! Nguoi khiem thi can cuu giup!", sizeof(p->msg) - 1);
        p->sendLoc = Gps::fix();
        p->lat = p->sendLoc ? Gps::lat() : 0;
        p->lon = p->sendLoc ? Gps::lon() : 0;
        xTaskCreate(sosTelegramTask, "SosTask", 8192, p, 1, NULL);
    } else {
        currentAppMode = "IDLE";
        isReadingActive = false;
        Serial.println("\n[NUT BT2] >>> ĐÃ TẮT BÁO ĐỘNG SOS <<<");
        setSosLed(false);
        Serial1.println("SOS:OFF");
        Serial1.flush();
    }
}

// BT2 nhan 2 lan: Bat/tat che do canh bao (LED nhap nhay + loa keu lien tuc)
static void fireWarnToggle() {
    warnModeActive = !warnModeActive;
    ledBlinkPattern = 0; // Huy blink neu dang chay
    if (warnModeActive) {
        currentAppMode = "WARN";
        Serial.println("[NUT BT2] NHAN 2 LAN -> BAT CHE DO CANH BAO!");
        Serial1.println("WARN:ON");
        Serial1.flush();
        // LED blink 3 lan bao hieu - khong dung delay, dung warnLed state machine ngay
        warnLedState  = true;
        warnLedLastMs = millis();
        digitalWrite(PIN_LED_SOS, HIGH); // Bat truoc, blink se tiep tuc trong loop()
    } else {
        currentAppMode = "IDLE";
        isReadingActive = false;
        Serial.println("[NUT BT2] NHAN 2 LAN -> TAT CHE DO CANH BAO!");
        Serial1.println("WARN:OFF");
        Serial1.flush();
        setSosLed(false);
        warnLedState = false;
    }
}

static void fireLottery() {
    currentAppMode = "OCR";
    lastSpeak = "Bat quet chu";
    isReadingActive = true;
    readingUntilMs = millis() + 60000;
    Serial.println("\n[NUT BT3] Nhấn 2 lần -> BẬT QUÉT CHỮ LIÊN TỤC (LED 2 lần, quét & đọc liên tục...)");
    setSosLed(false);
    Serial1.println("LOT");   // Gui lenh sang MaixCAM bat doc chu lien tuc
    Serial1.flush();
    startBlinkOcr();           // Blink non-blocking (2 lan)
}

static void fireExit() {
    currentAppMode = "IDLE";
    lastSpeak = "Thoat quet";
    isReadingActive = false;
    Serial.println("\n[NUT BT3] Nhấn 3 lần liên tục -> THOÁT CHẾ ĐỘ QUÉT (LED 3 lần, về chế độ chờ)");
    setSosLed(false);
    Serial1.println("STOP");   // Gui lenh sang MaixCAM thoat ve IDLE
    Serial1.flush();
    startBlinkExit();          // Blink non-blocking (3 lan)
}

static void pollUserButton() {
    bool pressed = (digitalRead(PIN_BTN_SOS) == LOW);
    uint32_t now = millis();

    // Phát hiện nhấn xuống
    if (pressed && !btnHeld) {
        btnHeld = true;
        btnPressMs = now;
    }

    // Phát hiện nhả ra
    if (!pressed && btnHeld) {
        uint32_t held = now - btnPressMs;
        btnHeld = false;
        if (held >= BTN_DEBOUNCE_MS) {
            if (held < BTN_SHORT_MAX_MS) {
                // Short tap -> đếm
                btnTapCount++;
                lastTapMs = now;
                btnTapPending = true;
            }
            // Long press (>= BTN_SHORT_MAX_MS) -> SOS ngay
            else {
                btnTapCount = 0;
                btnTapPending = false;
                Serial.println("[NUT BT2] GIU DAI -> KHAN CAP SOS!");
                fireSos();
            }
        }
    }

    // Đang giữ lâu -> SOS ngay khi đủ 1.2s (không cần nhả)
    if (btnHeld && (now - btnPressMs) >= 1200) {
        btnHeld = false;       // Reset để không fire liên tục
        btnTapCount = 0;
        btnTapPending = false;
        Serial.println("[NUT BT2] GIU > 1.2s -> KHAN CAP SOS!");
        fireSos();
    }

    // Xét kết quả tap sau khoảng chờ double-tap
    if (btnTapPending && !btnHeld && (now - lastTapMs) > BTN_DOUBLE_MS) {
        btnTapPending = false;
        if (btnTapCount == 1) {
            // 1 lần nhấn ngắn -> WARN toggle
            fireWarnToggle();
        } else if (btnTapCount >= 2) {
            // 2+ lần -> WARN toggle (giữ nguyên ý nghĩa)
            fireWarnToggle();
        }
        btnTapCount = 0;
    }
}

static void pollOcrButton() {
    bool ocrPressed = (digitalRead(PIN_BTN_OCR) == LOW);
    uint32_t now = millis();

    // Bắt đầu nhấn xuống
    if (ocrPressed && !ocrBtnHeld) {
        ocrBtnHeld = true;
        ocrBtnPressMs = now;
        ocrLongPressFired = false;
    }

    // Đang GIỮ NÚT: Nếu giữ nút >= 1.2s -> TẮT NGAY CHẾ ĐỘ NHẬN DIỆN TIỀN / QUÉT
    if (ocrPressed && ocrBtnHeld && !ocrLongPressFired) {
        if ((now - ocrBtnPressMs) >= 1200) {
            ocrLongPressFired = true;
            ocrTapCount = 0;
            Serial.println("\n[NUT BT3] GIỮ NÚT >= 1.2s -> TẮT CHẾ ĐỘ NHẬN DIỆN (THOÁT QUÉT)");
            fireExit();
        }
    }

    // Xử lý tap nhấn nhả (1 tap = Quét tiền, 2 tap = Quét chữ, >=3 tap = Thoát)
    if (ocrTapCount > 0 && (now - ocrLastTapMs) > BTN_DOUBLE_MS) {
        if (ocrTapCount == 1) {
            fireCurrency();
        } else if (ocrTapCount == 2) {
            fireLottery();
        } else if (ocrTapCount >= 3) {
            fireExit();
        }
        ocrTapCount = 0;
    }

    // Nhả nút
    if (!ocrPressed && ocrBtnHeld) {
        uint32_t held = now - ocrBtnPressMs;
        ocrBtnHeld = false;
        if (!ocrLongPressFired && held >= BTN_DEBOUNCE_MS && held < BTN_SHORT_MAX_MS) {
            ocrTapCount++;
            ocrLastTapMs = now;
        }
    }
}

void setup() {
    Serial.begin(SERIAL_BAUD);
    delay(500);

    pinMode(PIN_SR04_TRIG, OUTPUT);
    pinMode(PIN_SR04_ECHO, INPUT);
    pinMode(PIN_LED_SOS, OUTPUT);
    pinMode(PIN_BTN_SOS, INPUT_PULLUP);
    pinMode(PIN_BTN_OCR, INPUT_PULLUP);
    pinMode(PIN_BTN_3, INPUT_PULLUP);
    digitalWrite(PIN_SR04_TRIG, LOW);
    digitalWrite(PIN_LED_SOS, LOW); // Mặc định tắt, chỉ sáng khi có sự kiện hoặc SOS
    setSosLed(false);

    // Kết nối WiFi "Nha Tro 5" hỗ trợ gửi Telegram & Internet
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.printf("[WIFI] Dang ket noi mang '%s'...\n", WIFI_SSID);

    initLinkSerial(PIN_LINK_RX, PIN_LINK_TX);
    Sim::begin();
    Gps::begin();

    Serial.println("\n=== U3 ready ===");
    Serial1.println("R:READY");
    sendSimStatus(true);
    delay(300);
    int cm = readSr04Cm();
    if (cm > 0) lastSr04Cm = cm;
    logCompactLive(true);
    sendSr04IfNeeded(lastSr04Cm, millis(), true);
    sendGpsIfNeeded(millis(), true);
}

void loop() {
    uint32_t now = millis();
    trySwapLinkPinsIfNeeded(now);
    pollLinkRx();
    pollUserButton();
    pollOcrButton();
    Sim::poll();
    if (Sim::gpsUartActive()) Gps::poll();

    if (now - lastHeartbeatMs >= HEARTBEAT_MS) {
        lastHeartbeatMs = now;
        Serial1.println("H:1");
    }

    if (now - lastSimReportMs >= SIM_REPORT_MS) {
        lastSimReportMs = now;
        sendSimStatus(false);
    }

    if (now - lastSr04Ms >= SR04_INTERVAL_MS) {
        lastSr04Ms = now;
        long echoUs = 0;
        int cm = readSr04Cm(&echoUs);
        if (cm > 0) {
            lastSr04Cm = cm;
            sendSr04IfNeeded(cm, now, false);
        } else {
            lastSr04Cm = -1;
        }
    }

    sendGpsIfNeeded(now, false);

    // Luật điều khiển LED:
    // - Khi SOS: Sáng đỏ hoàn toàn
    // - Khi WARN mode: Nhấp nháy 300ms
    // - Bình thường: Tắt
    if (sosLedLocal) {
        digitalWrite(PIN_LED_SOS, HIGH);
    } else if (warnModeActive) {
        if (now - warnLedLastMs >= 300) {
            warnLedLastMs = now;
            warnLedState = !warnLedState;
            digitalWrite(PIN_LED_SOS, warnLedState ? HIGH : LOW);
        }
    } else {
        if (warnLedState) {
            warnLedState = false;
            digitalWrite(PIN_LED_SOS, LOW);
        }
    }

    // Cap nhat LED blink state machine (KHONG delay)
    updateLedBlink(now);

    logCompactLive(false);
    delay(2);
}
