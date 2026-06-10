"""
make_icon.py
────────────────────────────────────────────────────────────────────────
Converts mugen_logo.png → mugen_logo.ico (multi-size Windows icon)
Run once before building with PyInstaller.
"""

from pathlib import Path
from PIL import Image

SRC = Path(__file__).parent / "mugen_logo.png"
DST = Path(__file__).parent / "mugen_logo.ico"

def make_ico():
    img = Image.open(SRC).convert("RGBA")

    # White background for small sizes to avoid transparency issues
    sizes = [16, 24, 32, 48, 64, 128, 256]
    icons = []
    for s in sizes:
        resized = img.resize((s, s), Image.LANCZOS)
        # Composite onto white bg for small sizes
        bg = Image.new("RGBA", (s, s), (255, 255, 255, 0))
        bg.paste(resized, (0, 0), resized)
        icons.append(bg.convert("RGBA"))

    icons[0].save(
        DST,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=icons[1:],
    )
    print(f"[OK] Icon saved to: {DST}")

if __name__ == "__main__":
    make_ico()
