import olefile, struct, re

ole = olefile.OleFileIO('gaynguoimu/PCB3.PcbDoc')
track_data = ole.openstream('Tracks6/Data').read()
via_data = ole.openstream('Vias6/Data').read()
net_data = ole.openstream('Nets6/Data').read()
net_names = [m.decode('latin1', errors='ignore') for m in re.findall(rb'\|NAME=([^\|]+)\|', net_data)]

print("Net 0:", net_names[0])
print("Net 9:", net_names[9])

# Let's inspect Tracks6/Data:
# In Altium binary, Track records are often:
# Record format in Altium Designer 6:
# Let's search for net index 0 and 9 in tracks.
# A track typically contains: NetID (int16/int32), Layer (uint8), X1, Y1, X2, Y2 (int32 coord), Width (int32)
# Let's verify by finding all tracks that have Net ID:
# Let's split by track record size or find patterns:
print("track_data length:", len(track_data))
# Let's search for NetSW1_3 or find the track lengths
# Let's inspect the first 200 bytes of track_data:
print("track_data first 100 bytes:", track_data[:100])
