"""Generuje obrazy MSIX (Images\\*.png) na podstawie ikony aplikacji."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image

from src.icon_utils import ensure_app_icon

BACKGROUND = (26, 32, 44, 255)  # #1A202C, matches uap:VisualElements BackgroundColor
OUTPUT_DIR = PROJECT_ROOT / "installer" / "msix" / "Images"

SQUARE_SIZES = {
    "StoreLogo.png": 50,
    "Square44x44Logo.png": 44,
    "Square71x71Logo.png": 71,
    "Square150x150Logo.png": 150,
    "Square310x310Logo.png": 310,
}
WIDE_SIZE = ("Wide310x150Logo.png", 310, 150)


def _square_canvas(source: Image.Image, size: int) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), BACKGROUND)
    icon = source.resize((size, size), Image.Resampling.LANCZOS)
    canvas.paste(icon, (0, 0), icon)
    return canvas


def _wide_canvas(source: Image.Image, width: int, height: int) -> Image.Image:
    canvas = Image.new("RGBA", (width, height), BACKGROUND)
    icon_size = height - 20
    icon = source.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
    x = (width - icon_size) // 2
    y = (height - icon_size) // 2
    canvas.paste(icon, (x, y), icon)
    return canvas


def main() -> int:
    icon_path = ensure_app_icon()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with Image.open(icon_path) as icon_img:
        # Pillow's ICO plugin opens at the largest embedded size by default.
        source = icon_img.convert("RGBA")

        for filename, size in SQUARE_SIZES.items():
            out = _square_canvas(source, size)
            out.save(OUTPUT_DIR / filename, format="PNG")
            print(f"OK: {filename} ({size}x{size})")

        wide_name, wide_w, wide_h = WIDE_SIZE
        out = _wide_canvas(source, wide_w, wide_h)
        out.save(OUTPUT_DIR / wide_name, format="PNG")
        print(f"OK: {wide_name} ({wide_w}x{wide_h})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
