import urllib.request
import urllib.parse
import json
import time
import sys

sys.stdout.reconfigure(line_buffering=True)

TOKEN = "8822877520:AAHP27Gh6rLVfnye6kGGhlYcW6lrGOvpHgg"

print(f"[BOT] Dang cho tin nhan toi @cane365bot (Token: {TOKEN[:10]}...)...", flush=True)

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
                msg = update.get("message") or update.get("channel_post") or update.get("my_chat_member", {}).get("chat")
                if msg:
                    chat = msg if "id" in msg and "type" in msg else msg.get("chat", {})
                    chat_id = chat.get("id")
                    chat_title = chat.get("title") or chat.get("username") or chat.get("first_name")
                    print(f"\n[DA NHAN TIN NHAN] Chat ID: {chat_id} | Ten: {chat_title}")
                    
                    # Test send message
                    test_text = urllib.parse.quote(f"KET NOI THANH CONG GAY THONG MINH VOI TELEGRAM!\nChat ID: {chat_id}")
                    send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&text={test_text}"
                    urllib.request.urlopen(send_url)
                    print("[THANH CONG] >>> DA GUI TIN NHAN TEST XAC NHAN TOI TELEGRAM! <<<")
                    
                    # Ghi vao config.h
                    cfg_path = r"c:\Users\Public\Documents\Altium\08052026\gay_nguoi_mu_maixcam\Gay_Nguoi_Mu\firmware\esp32_periph\config.h"
                    content = f"""#pragma once

// Cau hinh Telegram SOS cho Gay Thong Minh
#define TELEGRAM_BOT_TOKEN  "{TOKEN}"
#define TELEGRAM_CHAT_ID    "{chat_id}"

// APN SIM 4G: Viettel v-internet | Vinaphone m3-world | Mobifone m-wap
#define SIM_APN             "v-internet"
#define SIM_BOOT_MS         4000
"""
                    with open(cfg_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"[CONFIG] Da luu Chat ID {chat_id} vao {cfg_path} thanh cong!")
                    exit(0)
    except Exception as e:
        print(f"[DANG DOI] {e}")
        time.sleep(2)
