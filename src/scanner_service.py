from __future__ import annotations

import sys
from pathlib import Path


class ScannerUnavailableError(RuntimeError):
    """Raised when scanning cannot proceed. `key` names an i18n message key."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(key)


class ScannerService:
    """
    Lightweight Windows WIA wrapper.
    Requires pywin32 and a WIA-compatible scanner.
    """

    def __init__(self) -> None:
        if not sys.platform.startswith("win"):
            raise ScannerUnavailableError("win_only")

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
            raise ScannerUnavailableError("no_pywin32") from exc

        if fmt.lower() not in {"png", "jpeg", "jpg", "pdf"}:
            raise ScannerUnavailableError("bad_format")

        wia = win32com.client.Dispatch("WIA.CommonDialog")
        device = wia.ShowSelectDevice()
        if device is None:
            raise ScannerUnavailableError("no_device")

        item = device.Items[1]
        image = wia.ShowTransfer(item)
        if image is None:
            raise ScannerUnavailableError("cancelled")

        # WIA.ShowTransfer() without an explicit FormatID keeps whatever raw
        # format the device returned (usually BMP), so SaveFile() ignores the
        # target extension entirely — a scan requested as .png/.jpg would be
        # written with BMP bytes under the wrong extension. Dump to a
        # temp file first and let Pillow re-encode into the real format.
        from PIL import Image

        tmp_raw = self._prepare_output_path(target_path.with_suffix(".wiatmp"))
        image.SaveFile(str(tmp_raw))
        try:
            with Image.open(tmp_raw) as raw_image:
                if fmt.lower() == "pdf":
                    final_path = self._prepare_output_path(target_path.with_suffix(".pdf"))
                    raw_image.convert("RGB").save(final_path, "PDF")
                    return final_path

                ext = ".jpg" if fmt.lower() in {"jpg", "jpeg"} else ".png"
                final_path = self._prepare_output_path(target_path.with_suffix(ext))
                if ext == ".jpg":
                    raw_image.convert("RGB").save(final_path, "JPEG", quality=95)
                else:
                    raw_image.save(final_path, "PNG")
                return final_path
        finally:
            tmp_raw.unlink(missing_ok=True)
