from __future__ import annotations

import sys
from pathlib import Path


class ScannerUnavailableError(RuntimeError):
    pass


class ScannerService:
    """
    Lightweight Windows WIA wrapper.
    Requires pywin32 and a WIA-compatible scanner.
    """

    def __init__(self) -> None:
        if not sys.platform.startswith("win"):
            raise ScannerUnavailableError("Skanowanie WIA jest dostepne tylko na Windows.")

    @staticmethod
    def _prepare_output_path(path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.unlink()
        return path

    def scan_to_file(self, target_path: Path, fmt: str = "png") -> Path:
        try:
            import win32com.client  # type: ignore
        except ImportError as exc:
            raise ScannerUnavailableError(
                "Brak pywin32. Zainstaluj: pip install pywin32"
            ) from exc

        if fmt.lower() not in {"png", "jpeg", "jpg", "pdf"}:
            raise ScannerUnavailableError("Obslugiwane formaty skanu: png, jpeg, pdf.")

        wia = win32com.client.Dispatch("WIA.CommonDialog")
        device = wia.ShowSelectDevice()
        if device is None:
            raise ScannerUnavailableError("Nie wybrano urzadzenia skanujacego.")

        item = device.Items[1]
        image = wia.ShowTransfer(item)
        if image is None:
            raise ScannerUnavailableError("Skanowanie anulowane.")

        if fmt.lower() == "pdf":
            final_path = self._prepare_output_path(target_path.with_suffix(".pdf"))
            tmp_jpeg = self._prepare_output_path(final_path.with_suffix(".jpg"))
            image.SaveFile(str(tmp_jpeg))
            from PIL import Image

            with Image.open(tmp_jpeg).convert("RGB") as img:
                img.save(final_path, "PDF")
            tmp_jpeg.unlink(missing_ok=True)
            return final_path

        ext = ".jpg" if fmt.lower() in {"jpg", "jpeg"} else ".png"
        final_path = self._prepare_output_path(target_path.with_suffix(ext))
        image.SaveFile(str(final_path))
        return final_path
