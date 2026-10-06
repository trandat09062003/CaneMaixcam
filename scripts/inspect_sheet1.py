import zipfile, olefile, re, io

with zipfile.ZipFile('gaynguoimu/History/Sheet1.~(22).SchDoc.Zip') as z:
    b = z.read('Sheet1.~(22).SchDoc')

ole = olefile.OleFileIO(io.BytesIO(b))
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

# Record 34 is implementation / parameter (Designator, Comment)
for idx, r in enumerate(records):
    if r.get('RECORD') == '34':
        owner_idx = r.get('OwnerIndex', '')
        name = r.get('Name', '')
        text = r.get('Text', '')
        if name in ['Designator', 'Comment'] and owner_idx.isdigit():
            oid = int(owner_idx)
            if oid < len(records):
                records[oid][name] = text

print("=== COMPONENTS WITH DESIGNATORS ===")
for idx, r in enumerate(records):
    if r.get('RECORD') == '1':
        des = r.get('Designator', 'NO_DES')
        comm = r.get('Comment', '')
        lib = r.get('LibReference', '')
        print(f"[{idx:>3}] {des:>8}: {comm:<15} | Lib: {lib}")

# Let's inspect IP5306, BT1, SW1, H2, J1 connections
wires = [r for r in records if r.get('RECORD') == '27']
labels = [r for r in records if r.get('RECORD') in ['25', '17']] # net label / power port
pins = [r for r in records if r.get('RECORD') == '2']

print("\n=== PINS OF ALL INTERESTING COMPONENTS ===")
for p in pins:
    owner_idx = p.get('OwnerIndex', '')
    owner_des = '?'
    if owner_idx.isdigit() and int(owner_idx) < len(records):
        owner_des = records[int(owner_idx)].get('Designator', '?')
    if any(k in owner_des for k in ['BT', 'SW', 'U1', 'H2', 'J1', 'L1']):
        p_num = p.get('Designator', '')
        p_name = p.get('Name', '')
        px = int(p.get('Location.X', '0'))
        py = int(p.get('Location.Y', '0'))
        
        # Check label or power port at pin
        matched_lbl = []
        for l in labels:
            lx = int(l.get('Location.X', '0'))
            ly = int(l.get('Location.Y', '0'))
            if abs(lx - px) <= 15 and abs(ly - py) <= 15:
                matched_lbl.append(l.get('Text', ''))
                
        print(f"{owner_des:>6} Pin {p_num:>2} ({p_name:<8}) at ({px:>4},{py:>4}) -> Label: {matched_lbl}")
