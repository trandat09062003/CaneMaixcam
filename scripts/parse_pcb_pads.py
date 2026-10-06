import olefile, struct, re

ole = olefile.OleFileIO('gaynguoimu/PCB3.PcbDoc')
track_data = ole.openstream('Tracks6/Data').read()
via_data = ole.openstream('Vias6/Data').read()
pad_data = ole.openstream('Pads6/Data').read()

# Let's inspect the first pad record in Pads6/Data:
# Pad chunks were split by b'|&|'
chunks = pad_data.split(b'|&|')
print("Chunk 0 length:", len(chunks[0]))
print("Chunk 1 length:", len(chunks[1]))

# In Altium PCB binary format, let's find the pad designator string:
for idx, ch in enumerate(chunks[1:], 1):
    # Search for designator text (e.g. '1', '2', '3', 'VIN', etc.)
    # In Altium, string is usually pascal string or null-terminated or fixed offset
    # Let's find any readable ASCII in the chunk:
    words = re.findall(rb'[A-Za-z0-9_]{1,10}', ch)
    # Also find coordinates (integers in mils/nm)
    if any(w in [b'SW1', b'BT1', b'U1', b'H2', b'L1'] for w in words):
        print(f"Pad {idx}: words={words}")
