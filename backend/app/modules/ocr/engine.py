"""Image -> MRZ text with Tesseract (installed in the API image). Pure CPU, no network."""

import io
import logging
import shutil
import subprocess

from PIL import Image, ImageOps

from app.modules.ocr.mrz import MrzResult, find_lines, parse_td3

log = logging.getLogger(__name__)
WHITELIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"
MAX_PIXELS = 40_000_000


class OcrUnavailable(RuntimeError):
    pass


def available() -> bool:
    return shutil.which("tesseract") is not None


def tesseract(img: Image.Image, psm: int = 6) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    try:
        out = subprocess.run(
            ["tesseract", "stdin", "stdout", "--psm", str(psm), "-l", "eng",
             "-c", f"tessedit_char_whitelist={WHITELIST}"],
            input=buf.getvalue(), capture_output=True, timeout=30, check=True,
        )
    except FileNotFoundError as exc:
        raise OcrUnavailable("tesseract is not installed") from exc
    return out.stdout.decode(errors="ignore")


def _prepare(img: Image.Image, crop_bottom: float | None) -> Image.Image:
    img = ImageOps.exif_transpose(img).convert("L")
    if crop_bottom:
        w, h = img.size
        img = img.crop((0, int(h * (1 - crop_bottom)), w, h))
    w, h = img.size
    if w < 1800:  # upscale small photos: MRZ glyphs need ~30 px height
        scale = 1800 / w
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    img = ImageOps.autocontrast(img, cutoff=1)
    return img.point(lambda p: 255 if p > 140 else 0)


def read_passport(data: bytes) -> MrzResult | None:
    """Best MRZ found in a passport photo/scan, or None if no MRZ could be read."""
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:  # noqa: BLE001 — any undecodable image
        raise ValueError("image could not be read") from exc

    best: MrzResult | None = None
    for crop in (0.35, 0.5, None):  # MRZ sits at the bottom of the data page
        for angle in (0, 180):
            candidate = _prepare(img.rotate(angle, expand=True) if angle else img, crop)
            lines = find_lines(tesseract(candidate))
            if not lines:
                continue
            try:
                result = parse_td3(*lines)
            except ValueError:
                continue
            if result.valid:
                return result
            score = sum(result.checks.values())
            if best is None or score > sum(best.checks.values()):
                best = result
    return best
