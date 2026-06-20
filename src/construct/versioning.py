"""Release + build version helpers."""

from __future__ import annotations

from construct._release import __version__ as RELEASE_VERSION

BUILD_STAMP_LEN = 14


def build_number() -> str:
    """Return the build stamp (YYYYMMDDHHMMSS) when stamped, else a zero placeholder."""
    try:
        from construct._build import __build__
    except ImportError:
        return "0" * BUILD_STAMP_LEN
    return __build__


def version_string() -> str:
    """Return the full CONSTRUCT version, e.g. ``0.3.20260620171439``."""
    return f"{RELEASE_VERSION}.{build_number()}"
