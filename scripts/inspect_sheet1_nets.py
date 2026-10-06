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

# Record 34: parameters
for idx, r in enumerate(records):
    if r.get('RECORD') == '34':
        owner_idx = r.get('OwnerIndex', '')
        name = r.get('Name', '')
        text = r.get('Text', '')
        if name in ['Designator', 'Comment'] and owner_idx.isdigit():
            oid = int(owner_idx)
            if oid < len(records):
                records[oid][name] = text

power_ports = [r for r in records if r.get('RECORD') == '17']
net_labels = [r for r in records if r.get('RECORD') == '25']

print("Power Ports:")
for p in power_ports:
    print(f"  {str(p.get('Text')):<15} at ({str(p.get('Location.X')):>4}, {str(p.get('Location.Y')):>4})")

print("\nNet Labels:")
for l in net_labels:
    print(f"  {str(l.get('Text')):<15} at ({str(l.get('Location.X')):>4}, {str(l.get('Location.Y')):>4})")
