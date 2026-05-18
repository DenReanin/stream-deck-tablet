"""Carga y guarda la configuración del Stream Deck en disco."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "grid": {"cols": 4, "rows": 4},
    "buttons": [],
}


def load() -> dict:
    if not CONFIG_PATH.exists():
        log.info("No config found at %s, using defaults", CONFIG_PATH)
        return json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except (OSError, json.JSONDecodeError) as exc:
        log.error("Failed to load config: %s — using defaults", exc)
        return json.loads(json.dumps(DEFAULT_CONFIG))


def save(config: dict) -> None:
    tmp = CONFIG_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    tmp.replace(CONFIG_PATH)


def autogen_from_sounds(sounds: list[dict], cols: int = 4, rows: int = 4) -> dict:
    """Genera una configuración inicial con un botón por sonido de Soundpad."""
    palette = [
        "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
        "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16",
    ]
    buttons = []
    capacity = cols * rows
    for i, sound in enumerate(sounds[:capacity]):
        buttons.append(
            {
                "id": f"b{i + 1}",
                "label": sound["title"][:24],
                "color": palette[i % len(palette)],
                "action": {
                    "type": "soundpad_play",
                    "params": {"index": sound["index"]},
                },
            }
        )
    return {
        "grid": {"cols": cols, "rows": rows},
        "buttons": buttons,
    }
