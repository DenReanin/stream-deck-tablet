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
    "pages": [],  # Se rellenan en _migrate: p_sounds (auto) siempre primero
    "obs": {"host": "localhost", "port": 4455, "password": ""},
}

# Página automática que la PWA rellena con los primeros 16 sonidos de
# Soundpad. Tiene marker `auto: "soundpad"` para que la PWA la trate
# distinto (no editable, sin drag, refresh en cada cambio).
AUTO_PAGE_ID = "p_sounds"
AUTO_PAGE_NAME = "Soundpad"


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
    config = _migrate(config)
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


def autogen_from_categories(
    categories: list[dict],
    sounds: list[dict],
    cols: int = 4,
    rows: int = 4,
) -> dict:
    """Genera una página por categoría de Soundpad, con sus sonidos en orden.

    Si una categoría tiene más sonidos que la capacidad del grid, se
    parte en varias páginas con el mismo nombre y un sufijo numérico.
    Las categorías vacías se omiten. Si no hay categorías útiles, cae
    al modo flat.
    """
    palette = [
        "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
        "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16",
    ]
    sound_by_idx = {s["index"]: s for s in sounds}
    capacity = cols * rows
    pages: list[dict] = []
    page_counter = 1

    useful = [c for c in categories
              if (c.get("sound_indexes") or []) and c.get("name") and c["name"] != "Root"]

    if not useful:
        return autogen_from_sounds(sounds, cols, rows)

    for cat in useful:
        chunks_of_idxs = []
        cat_sounds = cat["sound_indexes"]
        for chunk_start in range(0, len(cat_sounds), capacity):
            chunks_of_idxs.append(cat_sounds[chunk_start : chunk_start + capacity])

        for n, chunk in enumerate(chunks_of_idxs):
            buttons = []
            for i, sound_idx in enumerate(chunk):
                s = sound_by_idx.get(sound_idx)
                if s is None:
                    continue
                buttons.append({
                    "id": f"b{i + 1}",
                    "label": s["title"][:24],
                    "color": palette[(page_counter + i) % len(palette)],
                    "action": {
                        "type": "soundpad_play",
                        "params": {"index": s["index"]},
                    },
                })
            name = cat["name"]
            if len(chunks_of_idxs) > 1:
                name = f"{name} {n + 1}"
            pages.append({
                "id": f"p{page_counter}",
                "name": name[:24],
                "buttons": buttons,
            })
            page_counter += 1

    if not pages:
        return autogen_from_sounds(sounds, cols, rows)
    return {"grid": {"cols": cols, "rows": rows}, "pages": pages}


# --- Internal helpers ------------------------------------------------------

def _clone(d: dict) -> dict:
    return json.loads(json.dumps(d))


def _migrate(data: dict) -> dict:
    """Convierte schemas viejos al actual y garantiza la página automática."""
    # v1 -> v2: pasar de 'buttons' plano a 'pages'
    if "pages" not in data or not isinstance(data.get("pages"), list):
        grid = data.get("grid") or {"cols": 4, "rows": 4}
        log.info("Migrating config from v1 (flat buttons) to v2 (pages)")
        data = {"grid": grid, "pages": []}

    # Rellenar cualquier clave nueva del schema por defecto.
    for key, value in DEFAULT_CONFIG.items():
        if key not in data:
            data[key] = _clone({key: value})[key]

    # Garantizar la página automática de Soundpad como primera. Si ya
    # existe, la dejamos donde esté pero la promovemos al inicio.
    pages = data.get("pages") or []
    auto = next((p for p in pages if p.get("id") == AUTO_PAGE_ID), None)
    if auto is None:
        auto = {
            "id": AUTO_PAGE_ID,
            "name": AUTO_PAGE_NAME,
            "auto": "soundpad",
            "buttons": [],
        }
        pages.insert(0, auto)
    else:
        auto["auto"] = "soundpad"
        auto["name"] = auto.get("name") or AUTO_PAGE_NAME
        pages.remove(auto)
        pages.insert(0, auto)
    data["pages"] = pages
    return data


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
