"""Request / response schemas for the HTTP API."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class Envelope(BaseModel):
    """Uniform success envelope: {data, success}."""

    data: Any
    success: bool = True


class ErrorInfo(BaseModel):
    code: str
    message: str


class ErrorEnvelope(BaseModel):
    data: None = None
    success: bool = False
    error: ErrorInfo


class FeedbackRequest(BaseModel):
    message_id: str
    value: Literal["like"]   # C5 + Q6


class HealthData(BaseModel):
    status: str = "ok"
    version: str
    message: str = "Welcome to AI Debugging Assistant"
