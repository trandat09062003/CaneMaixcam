import olefile, re

ole = olefile.OleFileIO('gaynguoimu/PCB3.PcbDoc')
net_data = ole.openstream('Nets6/Data').read()
net_names = [m.decode('latin1', errors='ignore') for m in re.findall(rb'\|NAME=([^\|]+)\|', net_data)]

pad_data = ole.openstream('Pads6/Data').read()

# Let's inspect the fields in pad_data
# In binary stream, let's look for text or tokens
for m in re.finditer(rb'BT1|SW1|U1', pad_data):
    s = max(0, m.start() - 100)
    e = min(len(pad_data), m.end() + 100)
    print("PAD MATCH:", pad_data[s:e])
