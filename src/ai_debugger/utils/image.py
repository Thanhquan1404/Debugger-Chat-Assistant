"""
In-memory image handling. HARD CONSTRAINT C1:
No disk writes. No tempfile. No .save(). Ever.
"""
from __future__ import annotations

import io

import numpy as np
import structlog
from PIL import Image, UnidentifiedImageError

log = structlog.get_logger(__name__)

# downscale very large screenshots before OCR - optimize computing resource when loading on RAM
MAX_DIMENSION = 4096


class ImageDecodeError(ValueError):
    """Raised when image bytes cannot be decoded."""


def load_image_in_memory(data: bytes) -> np.ndarray:
    """
    Decode image bytes into a numpy array (RGB).

    Everything stays in RAM. No file handles opened. No disk paths touched.
    """
    if not data:
        raise ImageDecodeError("empty image data")

    try:
        # BytesIO is in-memory; nothing is written to disk.
        with Image.open(io.BytesIO(data)) as img:
            img.load()  # force decode while BytesIO is still alive
            if img.mode != "RGB":
                img = img.convert("RGB")
            if max(img.size) > MAX_DIMENSION:
                img = _downscale(img, MAX_DIMENSION)
            arr = np.asarray(img)
    except UnidentifiedImageError as exc:
        raise ImageDecodeError(f"unsupported image format: {exc}") from exc

    log.info("image.decoded", shape=arr.shape, dtype=str(arr.dtype))
    return arr


def _downscale(img: Image.Image, max_dim: int) -> Image.Image:
    w, h = img.size
    scale = max_dim / max(w, h)
    new_size = (int(w * scale), int(h * scale))
    log.info("image.downscaled", from_=f"{w}x{h}", to=f"{new_size[0]}x{new_size[1]}")
    return img.resize(new_size, Image.LANCZOS)
