"""
Single source of truth for runtime directory paths.

Distinguishes between running from source and running from a frozen
PyInstaller bundle (`getattr(sys, "frozen", False)`), so the rest of the
app never has to derive paths from `__file__` or `sys.executable` itself.
"""

from __future__ import annotations

import sys
from pathlib import Path


def get_base_dir() -> Path:
    """Directory the app should resolve external resources relative to.

    Frozen: the directory containing the executable.
    Source: the `streamlitapp/` project root (three levels above this file).
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[2]


def get_models_dir() -> Path:
    return get_base_dir() / "models"


def get_logs_dir() -> Path:
    return get_base_dir() / "logs"


def get_streamlit_config_dir() -> Path:
    return get_base_dir() / ".streamlit"
