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

pins = [r for r in records if r.get('RECORD') == '2']
labels = [r for r in records if r.get('RECORD') in ['25', '17']]
wires = [r for r in records if r.get('RECORD') == '27']

def get_labels_at(x, y):
    found = []
    for l in labels:
        lx = int(l.get('Location.X', '-9999'))
        ly = int(l.get('Location.Y', '-9999'))
        if abs(lx - x) <= 10 and abs(ly - y) <= 10:
            found.append(l.get('Text', ''))
    return found

# Trace wire connectivity
for comp_idx, name in [(645, 'SW1'), (671, 'BT1'), (299, 'U1'), (70, 'H2')]:
    print(f"\n================ {name} (Comp {comp_idx}) ================")
    comp_pins = [p for p in pins if p.get('OwnerIndex') == str(comp_idx)]
    for p in comp_pins:
        p_num = p.get('Designator', '')
        p_name = p.get('Name', '')
        px = int(p.get('Location.X', '-9999'))
        py = int(p.get('Location.Y', '-9999'))
        
        # DFS to find all connected points, wires, and labels
        frontier = [(px, py)]
        visited_wires = set()
        matched_labels = list(get_labels_at(px, py))
        connected_pins = []
        
        while frontier:
            cx, cy = frontier.pop()
            for w_idx, w in enumerate(wires):
                if w_idx in visited_wires: continue
                loc_cnt = int(w.get('LocationCount', '0'))
                pts = [(int(w.get(f'X{pi}', '-9999')), int(w.get(f'Y{pi}', '-9999'))) for pi in range(1, loc_cnt + 1)]
                if any(abs(pt[0] - cx) <= 5 and abs(pt[1] - cy) <= 5 for pt in pts):
                    visited_wires.add(w_idx)
                    for pt in pts:
                        frontier.append(pt)
                        for lbl in get_labels_at(pt[0], pt[1]):
                            if lbl not in matched_labels:
                                matched_labels.append(lbl)
                        # Check other pins
                        for op in pins:
                            if op == p: continue
                            opx = int(op.get('Location.X', '-9999'))
                            opy = int(op.get('Location.Y', '-9999'))
                            if abs(opx - pt[0]) <= 5 and abs(opy - pt[1]) <= 5:
                                op_owner = op.get('OwnerIndex', '')
                                op_pnum = op.get('Designator', '')
                                op_pname = op.get('Name', '')
                                connected_pins.append(f"Owner{op_owner}.Pin{op_pnum}({op_pname})")
                                
        print(f"Pin {p_num:>2} ({p_name:<8}) at ({px:>4}, {py:>4}) -> Labels: {matched_labels} | Connected Pins: {list(set(connected_pins))}")
