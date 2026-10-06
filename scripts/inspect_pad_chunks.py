import olefile, struct, re

ole = olefile.OleFileIO('gaynguoimu/PCB3.PcbDoc')
pad_data = ole.openstream('Pads6/Data').read()
net_data = ole.openstream('Nets6/Data').read()
net_names = [m.decode('latin1', errors='ignore') for m in re.findall(rb'\|NAME=([^\|]+)\|', net_data)]

# Let's see how pads are delimited:
chunks = pad_data.split(b'|&|')
print(f"Total pad chunks: {len(chunks)}")
for idx, ch in enumerate(chunks[:15]):
    # find any text or numbers
    text = re.sub(rb'[\x00-\x1f\x7f-\xff]', b' ', ch)
    print(f"Chunk {idx}: len={len(ch)} text={text[:60]}")
