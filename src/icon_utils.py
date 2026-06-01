from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import DATA_DIR


def ensure_app_icon() -> Path:
    icon_path = DATA_DIR / "ocr_studio_icon.ico"
    if icon_path.exists():
        return icon_path

    img = Image.new("RGBA", (256, 256), (26, 32, 44, 255))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle((20, 20, 236, 236), radius=28, fill=(45, 55, 72, 255), outline=(99, 179, 237, 255), width=8)
    draw.ellipse((58, 58, 198, 198), outline=(99, 179, 237, 255), width=12)
    draw.line((156, 156, 220, 220), fill=(144, 205, 244, 255), width=14)

    try:
        font = ImageFont.truetype("arial.ttf", 44)
    except OSError:
        font = ImageFont.load_default()
    draw.text((88, 95), "OCR", font=font, fill=(226, 232, 240, 255))

    img.save(icon_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return icon_path
