"""RapidOCR ONNX wrapper (D3). English-only."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import structlog
from rapidocr_onnxruntime import RapidOCR

from ai_debugger.config import Settings
from ai_debugger.utils.text import clean_ocr_text

log = structlog.get_logger(__name__)


@dataclass
class OCRLine:
    text: str
    score: float
    box: list[list[float]] = field(default_factory=list)


@dataclass
class OCRResult:
    text: str
    lines: list[OCRLine]

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()


class OCREngine:
    """
    Singleton RapidOCR engine. Load once, reuse across requests.

    Note (D3): the shipped rapidocr-onnxruntime package uses bilingual
    (Chinese + English) recognition models. For strict English-only behaviour,
    supply EN-specific ONNX models via RapidOCR(params={"rec_model_path": ...}).
    At Phase 1 we rely on the shipped models and English being dominant in
    the target input (terminal logs / HTTP errors).
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._engine = RapidOCR()
        log.info("ocr.engine_loaded", lang=settings.ocr_lang)

    def extract(self, image: np.ndarray) -> OCRResult:
        """Run OCR on a numpy image. Returns cleaned text + per-line metadata."""
        raw, _elapse = self._engine(image)
        if not raw:
            log.info("ocr.empty")
            return OCRResult(text="", lines=[])

        lines: list[OCRLine] = []
        for box, text, score in raw:
            if score is None or float(score) < self._settings.ocr_min_confidence:
                continue
            lines.append(OCRLine(text=str(text), score=float(score), box=box))

        joined = "\n".join(line.text for line in lines)
        log.info(
            "OCR completed",
            elapsed_time_ms=np.round(_elapse, 3),
        )
        cleaned = clean_ocr_text(joined)

        log.info(
            "ocr.extracted",
            n_lines=len(lines),
            n_chars=len(cleaned),
            avg_score=round(sum(line.score for line in lines) / len(lines), 3) if lines else 0.0,
        )
        return OCRResult(text=cleaned, lines=lines)
