import olefile, struct, re

ole = olefile.OleFileIO('gaynguoimu/PCB3.PcbDoc')
net_data = ole.openstream('Nets6/Data').read()
net_names = [m.decode('latin1', errors='ignore') for m in re.findall(rb'\|NAME=([^\|]+)\|', net_data)]

# Let's inspect Pads6/Data binary records:
# In Altium binary Pads6/Data:
# Each record has a header or size, or let's find component index.
# In Components6/Data:
comp_data = ole.openstream('Components6/Data').read()
# Let's find component positions/offsets for BT1, SW1, U1, H2
comps = {}
pos = 0
for m in re.finditer(rb'\|SOURCEDESIGNATOR=([^\|]+)\|', comp_data):
    des = m.group(1).decode('latin1', errors='ignore')
    comps[des] = m.start()

print("Found components:", list(comps.keys()))

# Let's inspect Tracks6/Data to trace nets:
track_data = ole.openstream('Tracks6/Data').read()
# Let's find tracks with Net index 0 (NetSW1_3), 9 (NetBT1_2), 16 (BAT_V), 30 (GND), 33 (VCC)
print("\nNet Names mapping:")
for i, n in enumerate(net_names):
    if any(k in n for k in ['SW1', 'BT1', 'BAT', 'VCC', 'GND', 'L1', 'J1']):
        print(f"  Net {i:2d}: {n}")
