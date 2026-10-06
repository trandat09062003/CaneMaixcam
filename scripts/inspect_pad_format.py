import olefile, struct

ole = olefile.OleFileIO('gaynguoimu/PCB3.PcbDoc')
pad_data = ole.openstream('Pads6/Data').read()

# Let's inspect length and pattern
print("pad_data length:", len(pad_data))
# In Altium binary streams, each record starts with a size byte or word, or fixed size.
# Let's search for pin strings: b'1\x00', b'2\x00', etc. or component indices.
# Let's check if there are string properties in Pads6:
# Check if any ASCII text exists:
import re
ascii_strings = re.findall(rb'[\x20-\x7e]{3,}', pad_data)
print("Some strings in pad_data:", ascii_strings[:20])
