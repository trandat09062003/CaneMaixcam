import asyncio
import os
import wave
import struct
import math
import subprocess
import edge_tts

AUDIO_DIR = r"c:\Users\Public\Documents\Altium\08052026\gay_nguoi_mu_maixcam\Gay_Nguoi_Mu\firmware\maixcam_app\audio"

async def gen_tts():
    texts = {
        "bat_nhan_dien_tien.mp3": "Bật nhận diện tiền.",
        "bat_doc_chu.mp3": "Bật đọc chữ.",
    }
    for fn, txt in texts.items():
        mp3_p = os.path.join(AUDIO_DIR, fn)
        comm = edge_tts.Communicate(txt, "vi-VN-HoaiMyNeural")
        await comm.save(mp3_p)
        print("Generated MP3:", mp3_p)
        
    # Upload to MaixCAM and convert to wav using /usr/bin/ffmpeg
    import paramiko
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect('10.225.139.1', username='root', password='root', timeout=4)
    sftp = c.open_sftp()
    
    for fn in texts.keys():
        mp3_p = os.path.join(AUDIO_DIR, fn)
        wav_p = os.path.join(AUDIO_DIR, fn.replace(".mp3", ".wav"))
        remote_mp3 = f"/root/maixcam_app/audio/{fn}"
        remote_wav = f"/root/maixcam_app/audio/{fn.replace('.mp3', '.wav')}"
        
        sftp.put(mp3_p, remote_mp3)
        c.exec_command(f'ffmpeg -y -i "{remote_mp3}" -acodec pcm_s16le -ac 2 -ar 44100 "{remote_wav}"')
        import time
        time.sleep(1.0)
        sftp.get(remote_wav, wav_p)
        print("Converted and downloaded WAV:", wav_p)
        
    sftp.close()
    c.close()

def gen_tut_tut():
    # Tao file am thanh 'tut_tut.wav' nhe nhang: 2 tieng bip cach nhau
    # Sample rate 44100Hz, stereo 16-bit
    wav_p = os.path.join(AUDIO_DIR, "tut_tut.wav")
    sr = 44100
    dur = 1.0 # 1 giay moi chu ky
    total_samples = int(sr * dur)
    
    with wave.open(wav_p, 'w') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        
        raw = bytearray()
        for i in range(total_samples):
            t = float(i) / sr
            sample = 0
            # Beep 1: 0.00s -> 0.08s (900Hz)
            if 0.0 <= t < 0.08:
                env = math.sin(math.pi * (t / 0.08))
                sample = int(18000 * env * math.sin(2 * math.pi * 900 * t))
            # Beep 2: 0.16s -> 0.24s (900Hz)
            elif 0.16 <= t < 0.24:
                t2 = t - 0.16
                env = math.sin(math.pi * (t2 / 0.08))
                sample = int(18000 * env * math.sin(2 * math.pi * 900 * t))
            # Silence: 0.24s -> 1.00s
            else:
                sample = 0
                
            packed = struct.pack('<hh', sample, sample)
            raw.extend(packed)
        wf.writeframes(raw)
    print("Generated tut_tut.wav:", wav_p)

if __name__ == "__main__":
    asyncio.run(gen_tts())
    gen_tut_tut()
