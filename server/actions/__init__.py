"""Registro de tipos de acción que el servidor puede ejecutar.

Añadir un nuevo tipo: crear módulo en este paquete que exponga una función
`execute(params: dict) -> dict` y registrarla en `ACTIONS`.
"""
from __future__ import annotations

import logging
from typing import Callable

from . import hotkey, launch, soundpad, url

log = logging.getLogger(__name__)

ActionFn = Callable[[dict], dict]

ACTIONS: dict[str, ActionFn] = {
    "soundpad_play": soundpad.play,
    "soundpad_stop": soundpad.stop,
    "soundpad_next": soundpad.next_sound,
    "soundpad_previous": soundpad.previous_sound,
    "hotkey": hotkey.press,
    "launch_app": launch.launch_app,
    "run_script": launch.run_script,
    "open_url": url.open_url,
}


def execute(action: dict) -> dict:
    type_ = action.get("type")
    if not type_:
        return {"ok": False, "error": "missing action type"}
    fn = ACTIONS.get(type_)
    if fn is None:
        return {"ok": False, "error": f"unknown action type: {type_}"}
    params = action.get("params", {}) or {}
    try:
        result = fn(params) or {}
        return {"ok": True, **result}
    except Exception as exc:
        log.exception("Action %s failed", type_)
        return {"ok": False, "error": str(exc)}
