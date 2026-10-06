import asyncio
import os
import sys
import edge_tts
import miniaudio
from scipy.io import wavfile
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

OUTPUT_DIR = r"Gay_Nguoi_Mu\firmware\maixcam_app\audio"
os.makedirs(OUTPUT_DIR, exist_ok=True)

VOICE = "vi-VN-HoaiMyNeural"

PHRASES = {
    "so_0": "Không",
    "so_1": "Một",
    "so_2": "Hai",
    "so_3": "Ba",
    "so_4": "Bốn",
    "so_5": "Năm",
    "so_6": "Sáu",
    "so_7": "Bảy",
    "so_8": "Tám",
    "so_9": "Chín",
    "ve_so": "Vé số",
    "dai_bac_lieu": "Đài Bạc Liêu",
    "dang_doc_ve_so": "Đang đọc vé số",
    "khong_thay_ve_so": "Không tìm thấy vé số, xin quét lại"
}

async def generate_phrase(name, text):
    mp3_path = os.path.join(OUTPUT_DIR, f"{name}.mp3")
    wav_path = os.path.join(OUTPUT_DIR, f"{name}.wav")
    
    comm = edge_tts.Communicate(text, VOICE)
    await comm.save(mp3_path)
    
    # Chuyển đổi MP3 sang chuẩn 16-bit 44.1kHz Stereo WAV tương thích 100% MaixCAM Player
    decoded = miniaudio.mp3_read_file_s16(mp3_path)
    sample_rate = decoded.sample_rate
    channels = decoded.nchannels
    
    samples = np.frombuffer(decoded.samples, dtype=np.int16)
    if channels == 1:
        samples = np.repeat(samples[:, np.newaxis], 2, axis=1)
    else:
        samples = samples.reshape(-1, channels)
        
    wavfile.write(wav_path, sample_rate, samples)
    print(f"-> Tao thanh cong: {wav_path} ('{text}')")
    
    try:
        os.remove(mp3_path)
    except Exception:
        pass

async def main():
    print(f"[AUDIO GEN] Dang tao toan bo file am thanh tieng Viet cho ve so vao {OUTPUT_DIR}...")
    for name, text in PHRASES.items():
        await generate_phrase(name, text)
    print("[AUDIO GEN] Hoan tat tao bo am thanh ve so!")

if __name__ == "__main__":
    asyncio.run(main())
