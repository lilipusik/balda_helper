from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative_path: str) -> Path:
    base_path = getattr(sys, "_MEIPASS", None)

    if base_path is not None:
        return Path(base_path) / relative_path

    return Path(relative_path)