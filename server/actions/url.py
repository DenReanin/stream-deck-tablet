"""Abrir URLs en el navegador del PC."""
from __future__ import annotations

import webbrowser


def open_url(params: dict) -> dict:
    target = params.get("url")
    if not target:
        raise ValueError("open_url requires 'url'")
    webbrowser.open(target, new=2)
    return {"opened": target}
