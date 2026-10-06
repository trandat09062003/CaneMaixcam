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

# Function to trace full net of a wire starting from a point
def trace_network(start_pt):
    frontier = [start_pt]
    visited_wires = set()
    all_pts = set([start_pt])
    
    while frontier:
        cx, cy = frontier.pop()
        for w_idx, w in enumerate(wires):
            if w_idx in visited_wires: continue
            loc_cnt = int(w.get('LocationCount', '0'))
            pts = [(int(w.get(f'X{pi}', '-9999')), int(w.get(f'Y{pi}', '-9999'))) for pi in range(1, loc_cnt + 1)]
            
            # Check if wire touches any segment or point
            # For simplicity: check if (cx, cy) is on any segment of wire
            touch = False
            for i in range(len(pts) - 1):
                x1, y1 = pts[i]
                x2, y2 = pts[i+1]
                # Check point on segment:
                if min(x1, x2) <= cx <= max(x1, x2) and min(y1, y2) <= cy <= max(y1, y2):
                    if (x2 - x1) * (cy - y1) == (y2 - y1) * (cx - x1):
                        touch = True
                        break
            if not touch:
                for pt in pts:
                    if abs(pt[0] - cx) <= 2 and abs(pt[1] - cy) <= 2:
                        touch = True
                        break
            if touch:
                visited_wires.add(w_idx)
                for pt in pts:
                    if pt not in all_pts:
                        all_pts.add(pt)
                        frontier.append(pt)
                        
    # Find all labels and power ports on this network
    found_labels = []
    for l in labels:
        lx = int(l.get('Location.X', '-9999'))
        ly = int(l.get('Location.Y', '-9999'))
        for cx, cy in all_pts:
            if abs(lx - cx) <= 2 and abs(ly - cy) <= 2:
                found_labels.append(l.get('Text'))
                
    # Also find all component records near points
    found_comps = []
    for r in records:
        if r.get('RECORD') == '1': # Component
            continue
        # Check text or designators near points
        for cx, cy in all_pts:
            rx = int(r.get('Location.X', r.get('X', r.get('X1', '-9999'))))
            ry = int(r.get('Location.Y', r.get('Y', r.get('Y1', '-9999'))))
            if abs(rx - cx) <= 2 and abs(ry - cy) <= 2:
                t = r.get('Text', r.get('Name', r.get('Comment', '')))
                if t: found_comps.append(f"Rec{records.index(r)}:{t}")
                
    return all_pts, found_labels, found_comps

print("=== TRACING SW1 PIN 1 (1060, 840) ===")
pts, lbls, cmps = trace_network((1060, 840))
print(f"Points: {pts}\nLabels: {lbls}\nOther items: {cmps[:10]}")

print("\n=== TRACING SW1 PIN 2 / PIN 3 (1100, 840) ===")
pts, lbls, cmps = trace_network((1100, 840))
print(f"Points: {pts}\nLabels: {lbls}\nOther items: {cmps[:10]}")

print("\n=== TRACING BT1 PIN (900, 690) ===")
pts, lbls, cmps = trace_network((900, 690))
print(f"Points: {pts}\nLabels: {lbls}\nOther items: {cmps[:10]}")
