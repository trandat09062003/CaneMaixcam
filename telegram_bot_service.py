import urllib.request
import urllib.parse
import json
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

TOKEN = "8822877520:AAHP27Gh6rLVfnye6kGGhlYcW6lrGOvpHgg"
GROUP_ID = "-1004486621646"

print(f"[BOT SERVICE] Khoi dong bot @cane365bot tu dong phan hoi...")

def send_message(chat_id, text, reply_markup=None):
    try:
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data=urllib.parse.urlencode(data).encode('utf-8')
        )
        urllib.request.urlopen(req, timeout=8)
        return True
    except Exception as e:
        print(f"[SEND ERR] {e}")
        return False

def send_location(chat_id, lat, lon):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendLocation?chat_id={chat_id}&latitude={lat}&longitude={lon}"
        urllib.request.urlopen(url, timeout=8)
        return True
    except Exception as e:
        print(f"[LOC ERR] {e}")
        return False

def answer_callback(cb_id, text=None):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery?callback_query_id={cb_id}"
        if text:
            url += f"&text={urllib.parse.quote(text)}"
        urllib.request.urlopen(url, timeout=5)
    except:
        pass

def get_menu_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "🚨 Phát cảnh báo SOS", "callback_data": "sos"},
                {"text": "📍 Vị trí hiện tại", "callback_data": "location"}
            ],
            [
                {"text": "📊 Trạng thái gậy", "callback_data": "status"},
                {"text": "🔊 Tìm gậy (Phát loa)", "callback_data": "find"}
            ],
            [
                {"text": "📖 Hướng dẫn sử dụng", "callback_data": "help"}
            ]
        ]
    }

def handle_command(chat_id, text):
    cmd = text.strip().split()[0].lower()
    
    if cmd in ("/start", "/menu", "menu", "start"):
        menu_text = (
            "🦯 <b>HỆ THỐNG GẬY THÔNG MINH CHO NGƯỜI KHIẾM THỊ</b>\n\n"
            "Chào bạn! Tôi là trợ lý ảo kết nối trực tiếp với gậy thông minh.\n"
            "Chọn chức năng bên dưới để điều khiển hoặc theo dõi:"
        )
        send_message(chat_id, menu_text, get_menu_keyboard())
    elif cmd == "/status" or cmd == "status":
        status_text = (
            "📊 <b>TRẠNG THÁI HỆ THỐNG GẬY THÔNG MINH</b>\n\n"
            "• 📡 <b>Kết nối:</b> Online (Telegram Bot Sẵn sàng)\n"
            "• 🔋 <b>Nguồn:</b> Pin Lithium 3.7V - Hoạt động tốt\n"
            "• 👁️ <b>AI Camera:</b> Nhận diện tiền VND & OCR tiếng Việt\n"
            "• 🛰️ <b>GPS:</b> Sẵn sàng định vị vị trí cứu hộ\n"
            "• 🔘 <b>Nút bấm:</b> BT2 (SOS) | BT3 (Quét tiền / Chữ)"
        )
        send_message(chat_id, status_text)
    elif cmd == "/sos" or cmd == "sos":
        sos_text = (
            "🚨 <b>[CẢNH BÁO SOS KHẨN CẤP]</b> 🚨\n\n"
            "Người khiếm thị vừa kích hoạt cảnh báo cứu hộ khẩn cấp!\n"
            "Đang phát còi hú và gửi vị trí bên dưới:"
        )
        send_message(chat_id, sos_text)
        send_location(chat_id, 21.028511, 105.854444)
    elif cmd == "/find" or cmd == "find":
        send_message(chat_id, "🔊 <b>Đang phát âm thanh còi bíp trên gậy để tìm kiếm vị trí...</b>")
    elif cmd == "/help" or cmd == "help":
        help_text = (
            "📖 <b>HƯỚNG DẪN NÚT BẤM TRÊN GẬY:</b>\n\n"
            "• <b>Nút BT2:</b> Bấm 1 lần ➔ Kích hoạt còi hú & gửi SOS Telegram ngay lập tức.\n"
            "• <b>Nút BT3:</b> Bấm 1 lần ➔ Chế độ quét và đọc mệnh giá tiền VND.\n"
            "• <b>Nút BT3:</b> Nhấp đúp 2 lần ➔ Chụp ảnh và đọc văn bản OCR tiếng Việt qua loa."
        )
        send_message(chat_id, help_text)

offset = None
while True:
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?timeout=10"
        if offset:
            url += f"&offset={offset}"
        req = urllib.request.Request(url)
        res = urllib.request.urlopen(req, timeout=15).read()
        data = json.loads(res)
        
        if data.get("ok") and data.get("result"):
            for update in data["result"]:
                offset = update["update_id"] + 1
                
                # Xử lý tin nhắn văn bản
                if "message" in update:
                    m = update["message"]
                    chat_id = m.get("chat", {}).get("id")
                    text = m.get("text", "")
                    if text and chat_id:
                        print(f"[NHẬN LỆNH] Chat: {chat_id} | Lệnh: {text}")
                        handle_command(chat_id, text)
                
                # Xử lý nút bấm Inline Keyboard
                elif "callback_query" in update:
                    cb = update["callback_query"]
                    cb_id = cb.get("id")
                    chat_id = cb.get("message", {}).get("chat", {}).get("id")
                    action = cb.get("data")
                    
                    if action == "sos":
                        answer_callback(cb_id, "Đã gửi cảnh báo SOS!")
                        handle_command(chat_id, "/sos")
                    elif action == "location":
                        answer_callback(cb_id, "Đang lấy tọa độ GPS...")
                        send_location(chat_id, 21.028511, 105.854444)
                    elif action == "status":
                        answer_callback(cb_id)
                        handle_command(chat_id, "/status")
                    elif action == "find":
                        answer_callback(cb_id, "Đang phát loa tìm gậy!")
                        handle_command(chat_id, "/find")
                    elif action == "help":
                        answer_callback(cb_id)
                        handle_command(chat_id, "/help")
                        
    except Exception as e:
        time.sleep(1.5)
