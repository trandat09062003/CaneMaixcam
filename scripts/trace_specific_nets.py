import olefile, re

ole = olefile.OleFileIO('gaynguoimu/PCB3.PcbDoc')
pad_data = ole.openstream('Pads6/Data').read()
net_data = ole.openstream('Nets6/Data').read()
net_names = [m.decode('latin1', errors='ignore') for m in re.findall(rb'\|NAME=([^\|]+)\|', net_data)]

# Let's inspect where NetSW1_3 and NetBT1_2 connect
# In PCB3.PcbDoc, let's search for NetSW1_3 and NetBT1_2 in all streams
for stream_name in ole.listdir():
    s = '/'.join(stream_name)
    data = ole.openstream(stream_name).read()
    if b'NetSW1_3' in data:
        print(f"NetSW1_3 found in {s}")
    if b'NetBT1_2' in data:
        print(f"NetBT1_2 found in {s}")
