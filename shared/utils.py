"""
Pure utility functions with zero internal dependencies.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone


def new_id() -> uuid.UUID:
    """Generate a new random UUID."""
    return uuid.uuid4()


def utc_now() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(tz=timezone.utc)


def slugify(text: str) -> str:
    """Convert arbitrary text to a URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return re.sub(r"^-+|-+$", "", text)


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp *value* to the closed interval [minimum, maximum]."""
    return max(minimum, min(maximum, value))
