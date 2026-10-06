import olefile, re

ole = olefile.OleFileIO('gaynguoimu/PCB3.PcbDoc')
for s in ole.listdir():
    stream_path = '/'.join(s)
    data = ole.openstream(s).read()
    for kw in [b'BT1', b'SW1', b'NetSW1_3', b'NetBT1_2']:
        for m in re.finditer(re.escape(kw), data):
            st = max(0, m.start() - 120)
            en = min(len(data), m.end() + 120)
            chunk = data[st:en]
            print(f"[{stream_path}] keyword={kw.decode()} at offset={m.start()}:")
            print("  RAW:", repr(chunk))
            print("  TEXT:", re.sub(r'[\x00-\x1f\x7f-\xff]', ' ', chunk.decode('latin1', errors='ignore')))
