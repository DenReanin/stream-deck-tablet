"""Carga y guarda la configuración del Stream Deck en disco.

Schema (v2):
{
  "grid": { "cols": 4, "rows": 4 },
  "pages": [
    { "id": "p1", "name": "Principal", "buttons": [ ... ] },
    { "id": "p2", "name": "Streaming", "buttons": [ ... ] }
  ]
}
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "grid": {"cols": 4, "rows": 4},
    "pages": [{"id": "p1", "name": "Principal", "buttons": []}],
    "obs": {"host": "localhost", "port": 4455, "password": ""},
}


def load() -> dict:
    if not CONFIG_PATH.exists():
        log.info("No config found at %s, using defaults", CONFIG_PATH)
        return _clone(DEFAULT_CONFIG)
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return _migrate(data)
    except (OSError, json.JSONDecodeError) as exc:
        log.error("Failed to load config: %s — using defaults", exc)
        return _clone(DEFAULT_CONFIG)


def save(config: dict) -> None:
    tmp = CONFIG_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    tmp.replace(CONFIG_PATH)


def autogen_from_sounds(sounds: list[dict], cols: int = 4, rows: int = 4) -> dict:
    """Genera una configuración con un botón por sonido de Soundpad.

    Si hay más sonidos que capacidad de una página, crea páginas adicionales.
    """
    palette = [
        "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
        "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16",
    ]
    capacity = cols * rows
    pages: list[dict] = []

    if not sounds:
        return _clone(DEFAULT_CONFIG)

    for page_idx, chunk_start in enumerate(range(0, len(sounds), capacity)):
        chunk = sounds[chunk_start : chunk_start + capacity]
        buttons = []
        for i, sound in enumerate(chunk):
            buttons.append(
                {
                    "id": f"b{i + 1}",
                    "label": sound["title"][:24],
                    "color": palette[(chunk_start + i) % len(palette)],
                    "action": {
                        "type": "soundpad_play",
                        "params": {"index": sound["index"]},
                    },
                }
            )
        name = "Principal" if page_idx == 0 else f"Sonidos {page_idx + 1}"
        pages.append({"id": f"p{page_idx + 1}", "name": name, "buttons": buttons})

    return {"grid": {"cols": cols, "rows": rows}, "pages": pages}


# --- Internal helpers ------------------------------------------------------

def _clone(d: dict) -> dict:
    return json.loads(json.dumps(d))


def _migrate(data: dict) -> dict:
    """Convierte schemas viejos al actual."""
    if "pages" in data and isinstance(data["pages"], list):
        return data  # ya es v2
    # v1: { grid, buttons } -> v2: { grid, pages: [{id, name, buttons}] }
    legacy_buttons = data.get("buttons") or []
    grid = data.get("grid") or {"cols": 4, "rows": 4}
    log.info("Migrating config from v1 (flat buttons) to v2 (pages)")
    return {
        "grid": grid,
        "pages": [
            {"id": "p1", "name": "Principal", "buttons": legacy_buttons}
        ],
    }


def find_page(config: dict, page_id: str | None) -> dict | None:
    pages = config.get("pages") or []
    if page_id:
        for p in pages:
            if p.get("id") == page_id:
                return p
    return pages[0] if pages else None


def next_page_id(config: dict) -> str:
    """Devuelve un id 'pN' único."""
    existing = {p.get("id") for p in config.get("pages") or []}
    i = 1
    while f"p{i}" in existing:
        i += 1
    return f"p{i}"
