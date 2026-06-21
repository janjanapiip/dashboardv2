"""Convert a logo image to a navbar-ready PNG with a transparent background.

Usage:
    python tools/make_logo.py                          # uses default source
    python tools/make_logo.py path/to/logo.jpg         # custom source

Default source : data/uploads/_logo_source.png
Default output : static/img/stip-logo.png (max 192 px tall, transparent BG)

The script flood-fills near-white pixels (RGB >= 240) starting from the
four borders. Interior light areas (e.g. white paper on the eagle) are
preserved — only the background gets transparent.
"""
import sys
from collections import deque
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SRC = ROOT / "data" / "uploads" / "_logo_source.png"
DEFAULT_DST = ROOT / "static" / "img" / "stip-logo.png"

WHITE_THRESHOLD = 240   # any channel >= this is considered "white-ish"
MAX_HEIGHT      = 192   # navbar fits ~40 px, 192 gives crisp retina display


def is_whitish(px) -> bool:
    return px[0] >= WHITE_THRESHOLD and px[1] >= WHITE_THRESHOLD and px[2] >= WHITE_THRESHOLD


def flood_fill_background(img: Image.Image) -> Image.Image:
    """4-direction BFS from every border pixel; clear the alpha of any white-ish pixel reached."""
    rgba = img.convert("RGBA")
    px = rgba.load()
    w, h = rgba.size
    seen = bytearray(w * h)  # 0 = unvisited, 1 = visited
    q: deque = deque()

    def push(x: int, y: int):
        if 0 <= x < w and 0 <= y < h and not seen[y * w + x]:
            r, g, b, _ = px[x, y]
            if is_whitish((r, g, b)):
                seen[y * w + x] = 1
                q.append((x, y))

    for x in range(w):
        push(x, 0); push(x, h - 1)
    for y in range(h):
        push(0, y); push(w - 1, y)

    while q:
        x, y = q.popleft()
        r, g, b, _ = px[x, y]
        px[x, y] = (r, g, b, 0)  # make transparent
        push(x + 1, y); push(x - 1, y); push(x, y + 1); push(x, y - 1)

    return rgba


def resize(img: Image.Image, max_h: int) -> Image.Image:
    w, h = img.size
    if h <= max_h:
        return img
    ratio = max_h / h
    return img.resize((int(w * ratio), max_h), Image.LANCZOS)


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    dst = DEFAULT_DST

    if not src.exists():
        print(f"  ERROR: sumber logo tidak ditemukan: {src}")
        print(f"  Simpan file logo di: {DEFAULT_SRC}")
        print(f"  Atau jalankan: python tools/make_logo.py <path-ke-logo>")
        sys.exit(1)

    print(f"  Membaca       : {src}")
    img = Image.open(src)
    print(f"  Ukuran asal   : {img.size}, mode {img.mode}")

    print(f"  Menghapus background putih ...")
    img = flood_fill_background(img)

    print(f"  Mengubah ukuran ke tinggi maks {MAX_HEIGHT}px ...")
    img = resize(img, MAX_HEIGHT)

    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, "PNG", optimize=True)
    print(f"  Tersimpan     : {dst}")
    print(f"  Ukuran akhir  : {img.size}, {dst.stat().st_size // 1024} KB")
    print()
    print("  Logo siap dipakai. Restart server jika sedang berjalan agar perubahan terlihat.")


if __name__ == "__main__":
    main()
