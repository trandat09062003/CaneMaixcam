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

wires = [r for r in records if r.get('RECORD') == '27']
labels = [r for r in records if r.get('RECORD') in ['25', '17']]

print("=== WIRES NEAR SW1 (X: 1040-1120, Y: 820-860) ===")
for w in wires:
    loc_cnt = int(w.get('LocationCount', '0'))
    pts = [(int(w.get(f'X{pi}', '-9999')), int(w.get(f'Y{pi}', '-9999'))) for pi in range(1, loc_cnt + 1)]
    if any(1040 <= pt[0] <= 1120 and 800 <= pt[1] <= 880 for pt in pts):
        print(f"Wire near SW1: {pts}")

print("\n=== LABELS NEAR SW1 ===")
for l in labels:
    lx = int(l.get('Location.X', '-9999'))
    ly = int(l.get('Location.Y', '-9999'))
    if 1040 <= lx <= 1120 and 800 <= ly <= 880:
        print(f"Label near SW1: {l.get('Text')} at ({lx}, {ly})")

print("\n=== WIRES NEAR BT1 (X: 870-930, Y: 690-760) ===")
for w in wires:
    loc_cnt = int(w.get('LocationCount', '0'))
    pts = [(int(w.get(f'X{pi}', '-9999')), int(w.get(f'Y{pi}', '-9999'))) for pi in range(1, loc_cnt + 1)]
    if any(870 <= pt[0] <= 930 and 690 <= pt[1] <= 760 for pt in pts):
        print(f"Wire near BT1: {pts}")

print("\n=== LABELS NEAR BT1 ===")
for l in labels:
    lx = int(l.get('Location.X', '-9999'))
    ly = int(l.get('Location.Y', '-9999'))
    if 870 <= lx <= 930 and 690 <= ly <= 760:
        print(f"Label near BT1: {l.get('Text')} at ({lx}, {ly})")
