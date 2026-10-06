import olefile, re

ole = olefile.OleFileIO('gaynguoimu/gaynguoimu.BomDoc')
for s in ole.listdir():
    stream_name = '/'.join(s)
    data = ole.openstream(s).read()
    print("Stream:", stream_name, len(data))
    for m in re.finditer(rb'SW1|BT1|U1|IP5306', data):
        st = max(0, m.start() - 100)
        en = min(len(data), m.end() + 100)
        print("  MATCH:", data[st:en])
