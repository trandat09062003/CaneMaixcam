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

check_points = [(980, 850), (1140, 780), (990, 720), (1010, 860), (900, 690)]

for idx, r in enumerate(records):
    for k, v in r.items():
        if k in ['Location.X', 'X', 'X1', 'X2'] and v.lstrip('-').isdigit():
            x = int(v)
            yk = k.replace('X', 'Y')
            y = int(r.get(yk, '-9999'))
            for cp in check_points:
                if abs(x - cp[0]) <= 20 and abs(y - cp[1]) <= 20:
                    owner_idx = r.get('OwnerIndex', '')
                    owner_des = ''
                    if owner_idx.isdigit() and int(owner_idx) < len(records):
                        owner_des = records[int(owner_idx)].get('Designator', records[int(owner_idx)].get('Text', ''))
                    info = r.get('Name') or r.get('Text') or r.get('Comment') or r.get('LibReference') or r.get('Designator')
                    rec_type = r.get('RECORD')
                    print(f"Near {cp}: Rec {idx} (type {rec_type}) owner={owner_des} -> {info}")
