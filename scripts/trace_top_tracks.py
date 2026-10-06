import olefile, struct

ole = olefile.OleFileIO('gaynguoimu/PCB3.PcbDoc')
track_data = ole.openstream('Tracks6/Data').read()
net_data = ole.openstream('Nets6/Data').read()
import re
net_names = [m.decode('latin1', errors='ignore') for m in re.findall(rb'\|NAME=([^\|]+)\|', net_data)]

rec_len = 49
num_tracks = len(track_data) // rec_len
print(f"Total tracks: {num_tracks}")

# In each track record:
# Let's inspect where net_id is stored
for i in range(num_tracks):
    rec = track_data[i*rec_len : (i+1)*rec_len]
    # Let's unpack coordinates:
    x1, y1, x2, y2 = struct.unpack('<iiii', rec[18:34])
    width = struct.unpack('<i', rec[34:38])[0]
    # Net ID is typically at offset 12 or 16 or 42
    # Let's check which byte corresponds to Net ID by checking values < len(net_names):
    net_cand = struct.unpack('<h', rec[12:14])[0]
    
    # Let's convert coordinates to mm: 1 mil = 10000 nm (or 254000 altium internal units = 10 mil)
    # Altium internal unit = 1/10000 mil = 0.0001 mil = 2.54 nm
    x1_mm = x1 * 0.0000254
    y1_mm = y1 * 0.0000254
    x2_mm = x2 * 0.0000254
    y2_mm = y2 * 0.0000254

    # Let's check if this track belongs to Net 0 (NetSW1_3) or Net 9 (NetBT1_2):
    # Let's print rec bytes to find net index:
    # Let's check all shorts in rec:
    shorts = struct.unpack('<24h', rec[1:49])
    for s_idx, val in enumerate(shorts):
        if val in [0, 9] and shorts[1] == -1: # check
            pass

# Let's search specifically for coordinates near BT1 and SW1:
# In the PCB image:
# BT1 is next to SW1 at the top of the board.
# Let's find all tracks at the top of the board (large Y coordinates):
top_tracks = []
for i in range(num_tracks):
    rec = track_data[i*rec_len : (i+1)*rec_len]
    x1, y1, x2, y2 = struct.unpack('<iiii', rec[18:34])
    x1_mm = x1 * 0.0000254
    y1_mm = y1 * 0.0000254
    x2_mm = x2 * 0.0000254
    y2_mm = y2 * 0.0000254
    layer = rec[12]
    # Check net index in rec:
    # Let's print tracks with y > 60mm (top of board):
    if y1_mm > 55 or y2_mm > 55:
        # find which byte has net index
        top_tracks.append((i, layer, x1_mm, y1_mm, x2_mm, y2_mm, rec.hex()))

print(f"Top tracks count: {len(top_tracks)}")
for t in top_tracks[:20]:
    print(f"Track {t[0]}: Layer {t[1]} from ({t[2]:.2f}, {t[3]:.2f}) to ({t[4]:.2f}, {t[5]:.2f})")
