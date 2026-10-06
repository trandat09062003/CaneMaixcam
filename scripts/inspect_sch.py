import olefile, re

ole = olefile.OleFileIO('gaynguoimu/Sheet2.SchDoc')
data = ole.openstream('FileHeader').read()
pairs = re.findall(rb'\|([A-Za-z0-9_]+)=([^\|]+)', data)
records = []
cur = {}
for k, v in pairs:
    ks = k.decode('ascii', errors='ignore')
    vs = v.decode('latin1', errors='ignore').split('\x00')[0]
    if ks == 'RECORD':
        if cur: records.append(cur)
        cur = {'RECORD': vs}
    else: cur[ks] = vs
if cur: records.append(cur)

# Match pins and net labels by coordinate or connection
esp_pins = [r for r in records if r.get('RECORD') == '2' and r.get('OwnerIndex') == '692']
labels = [r for r in records if r.get('RECORD') in ['25', '17']]

print("=== ESP32 PINS AND CONNECTED LABELS ===")
for p in esp_pins:
    px = int(p.get('Location.X', '0'))
    py = int(p.get('Location.Y', '0'))
    p_num = p.get('Designator', '')
    p_name = p.get('Name', '')
    # Check if a label or power port is at or very close to this pin
    matched = []
    for l in labels:
        lx = int(l.get('Location.X', '0'))
        ly = int(l.get('Location.Y', '0'))
        if abs(lx - px) <= 10 and abs(ly - py) <= 10:
            matched.append(l.get('Text', ''))
    print(f"ESP32 Pin {p_num:>2} ({p_name:<6}) at ({px:>4}, {py:>4}) -> {matched}")

print("\n=== H4 CONNECTOR PINS (GPS) ===")
# Find component H4
h4_pins = [r for r in records if r.get('RECORD') == '2' and r.get('OwnerIndex') == '210']
for p in h4_pins:
    px = int(p.get('Location.X', '0'))
    py = int(p.get('Location.Y', '0'))
    p_num = p.get('Designator', '')
    p_name = p.get('Name', '')
    matched = []
    for l in labels:
        lx = int(l.get('Location.X', '0'))
        ly = int(l.get('Location.Y', '0'))
        if abs(lx - px) <= 10 and abs(ly - py) <= 10:
            matched.append(l.get('Text', ''))
    print(f"H4 Pin {p_num:>2} ({p_name:<6}) at ({px:>4}, {py:>4}) -> {matched}")
