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

# Record 34 is parameter
for idx, r in enumerate(records):
    if r.get('RECORD') == '34':
        owner_idx = r.get('OwnerIndex', '')
        name = r.get('Name', '')
        text = r.get('Text', '')
        if name in ['Designator', 'Comment'] and owner_idx.isdigit():
            oid = int(owner_idx)
            if oid < len(records):
                records[oid][name] = text

# Let's inspect pins of BT1, SW1, U1
pins = [r for r in records if r.get('RECORD') == '2']
wires = [r for r in records if r.get('RECORD') == '27']
labels = [r for r in records if r.get('RECORD') in ['25', '17']]

# For each pin, print its actual Location (X, Y)
for p in pins:
    owner_idx = p.get('OwnerIndex', '')
    owner_des = records[int(owner_idx)].get('Designator', '?') if owner_idx.isdigit() and int(owner_idx) < len(records) else '?'
    if any(k in owner_des for k in ['BT1', 'SW1', 'U1', 'H2']):
        p_num = p.get('Designator', '')
        p_name = p.get('Name', '')
        # In SchDoc, pin location is in Location.X, Location.Y
        # But wait, in Altium component, pin coordinates might be relative or absolute?
        # Let's check how coordinates are stored in p:
        print(f"Pin {owner_des}.{p_num} ({p_name}): {dict((k, v) for k, v in p.items() if 'Loc' in k or 'X' in k or 'Y' in k)}")
