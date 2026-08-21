"""Stable audit serialization for cleaning decisions and row-removal evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_audit(path: Path, payload: dict[str, Any]) -> None:
    """Write canonical JSON so repeated cleaning runs have identical audit bytes."""
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
