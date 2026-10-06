"""
Chia anh trong data/ thanh dataset2/<menh_gia>/ theo ten file.
Ten file: 010000_010000_001.jpg -> thu muc 010000/

Chay: python scripts/organize_dataset.py
"""
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data"
DST = ROOT / "dataset2"

PATTERN = re.compile(r"^(\d{6})_", re.IGNORECASE)
EXT = {".jpg", ".jpeg", ".png"}


def main() -> None:
    if not SRC.is_dir():
        raise SystemExit(f"Khong tim thay thu muc: {SRC}")

    DST.mkdir(parents=True, exist_ok=True)
    moved = 0
    unknown = []

    for f in sorted(SRC.iterdir()):
        if not f.is_file() or f.suffix.lower() not in EXT:
            continue
        m = PATTERN.match(f.name)
        if not m:
            unknown.append(f.name)
            continue
        label = m.group(1)
        out_dir = DST / label
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f.name
        if dest.exists():
            dest = out_dir / f"{f.stem}_dup{f.suffix}"
        shutil.move(str(f), str(dest))
        moved += 1

    print(f"Da chuyen {moved} anh vao {DST}")
    print("\nSo anh tung lop:")
    for d in sorted(DST.iterdir()):
        if d.is_dir():
            n = len(list(d.glob("*")))
            print(f"  {d.name}: {n}")

    if unknown:
        print(f"\nKhong nhan dien duoc ({len(unknown)} file):")
        for name in unknown[:10]:
            print(f"  {name}")


if __name__ == "__main__":
    main()
