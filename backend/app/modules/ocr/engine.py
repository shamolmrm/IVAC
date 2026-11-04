"""Image -> MRZ text with Tesseract (installed in the API image). Pure CPU, no network.

Two Tesseract models are used:
- ``mrz``: trained on the OCR-B MRZ font (BSD-3, DoubangoTelecom/tesseractMRZ), bundled in the
  API image. It reads the ``<`` fillers reliably, which the generic model turns into K/E/S.
- ``eng``: the generic model, used as a fallback when the MRZ model is missing.

Phone photos rarely show the page alone (hands, cloth, the opposite page), so the image is read
in overlapping horizontal bands with local (adaptive) thresholding instead of a global cut-off.
"""

import io
import logging
import os
import shutil
import subprocess
import time

from PIL import Image, ImageChops, ImageFilter, ImageOps

from app.modules.ocr.mrz import MrzResult, find_lines, parse_td3

log = logging.getLogger(__name__)
WHITELIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"
MAX_PIXELS = 40_000_000
MRZ_TESSDATA = os.environ.get("MRZ_TESSDATA_DIR", "/usr/local/share/tessdata-mrz")
TIME_BUDGET = 35.0  # seconds per image, across all attempts
BAND = 0.3  # band height as a fraction of the image; bands overlap by half


class OcrUnavailable(RuntimeError):
    pass


def available() -> bool:
    return shutil.which("tesseract") is not None


def has_mrz_model() -> bool:
    return os.path.isfile(os.path.join(MRZ_TESSDATA, "mrz.traineddata"))


def tesseract(img: Image.Image, psm: int = 6, lang: str = "eng") -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    cmd = ["tesseract", "stdin", "stdout", "--psm", str(psm), "-l", lang,
           "-c", f"tessedit_char_whitelist={WHITELIST}"]
    if lang == "mrz":
        cmd[3:3] = ["--tessdata-dir", MRZ_TESSDATA]
    try:
        out = subprocess.run(cmd, input=buf.getvalue(), capture_output=True, timeout=30,
                             check=True)
    except FileNotFoundError as exc:
        raise OcrUnavailable("tesseract is not installed") from exc
    return out.stdout.decode(errors="ignore")


def _scale(img: Image.Image, width: int) -> Image.Image:
    w, h = img.size
    return img.resize((width, max(1, int(h * width / w))), Image.Resampling.LANCZOS)


def _adaptive(img: Image.Image, width: int = 1400) -> Image.Image:
    """Dark text on any background -> black on white, using the local neighbourhood mean."""
    g = _scale(img, width)
    local = g.filter(ImageFilter.BoxBlur(25))
    return ImageChops.subtract(local, g, 1, 0).point(lambda p: 0 if p > 18 else 255)


def _global(img: Image.Image, crop_bottom: float | None) -> Image.Image:
    """Older pipeline: works well on flat scans with a clean background."""
    if crop_bottom:
        w, h = img.size
        img = img.crop((0, int(h * (1 - crop_bottom)), w, h))
    if img.size[0] < 1800:  # MRZ glyphs need ~30 px height
        img = _scale(img, 1800)
    img = ImageOps.autocontrast(img, cutoff=1)
    return img.point(lambda p: 255 if p > 140 else 0)


def _bands(img: Image.Image):
    """Overlapping horizontal bands, bottom first (the MRZ sits at the bottom of the page)."""
    w, h = img.size
    top = 1 - BAND
    while top > -BAND / 2:
        t = max(top, 0.0)
        yield img.crop((0, int(h * t), w, int(h * min(t + BAND, 1.0))))
        top -= BAND / 2


def _attempts(img: Image.Image):
    """Candidate images to OCR, most likely first: (image, lang)."""
    mrz = has_mrz_model()
    upright = (img, img.rotate(180, expand=True))
    if mrz:
        for page in upright:
            for band in _bands(page):
                yield _adaptive(band), "mrz"
    for page in upright:
        for crop in (0.35, 0.5, None):
            yield _global(page, crop), "eng"
    for angle in (90, 270):  # a portrait photo of a landscape page, or vice versa
        page = img.rotate(angle, expand=True)
        for band in _bands(page):
            yield _adaptive(band), "mrz" if mrz else "eng"


def read_passport(data: bytes) -> MrzResult | None:
    """Best MRZ found in a passport photo/scan, or None if no MRZ could be read."""
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:  # noqa: BLE001 — any undecodable image
        raise ValueError("image could not be read") from exc
    img = ImageOps.exif_transpose(img).convert("L")

    best: MrzResult | None = None
    deadline = time.monotonic() + TIME_BUDGET
    for candidate, lang in _attempts(img):
        if time.monotonic() > deadline:
            log.info("MRZ OCR stopped at the time budget")
            break
        lines = find_lines(tesseract(candidate, lang=lang))
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
