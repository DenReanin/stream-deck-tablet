"""Registro de tipos de acción que el servidor puede ejecutar.

Añadir un nuevo tipo: crear módulo en este paquete que exponga una función
sync `(params: dict) -> dict` (o async) y registrarla en ACTIONS.

`sequence` se maneja aparte porque necesita re-entrar al executor.
"""
from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Awaitable, Callable, Union

from . import delay as _delay
from . import hotkey, launch, obs, soundpad, text, url

log = logging.getLogger(__name__)

ActionResult = dict
ActionFn = Callable[[dict], Union[ActionResult, Awaitable[ActionResult]]]

ACTIONS: dict[str, ActionFn] = {
    "soundpad_play": soundpad.play,
    "soundpad_stop": soundpad.stop,
    "soundpad_next": soundpad.next_sound,
    "soundpad_previous": soundpad.previous_sound,
    "hotkey": hotkey.press,
    "launch_app": launch.launch_app,
    "run_script": launch.run_script,
    "open_url": url.open_url,
    "text_input": text.type_text,
    "delay": _delay.wait,
    "obs_scene": obs.set_scene,
    "obs_toggle_stream": obs.toggle_stream,
    "obs_toggle_record": obs.toggle_record,
    "obs_toggle_mute": obs.toggle_mute,
    "obs_transition": obs.transition,
}


async def execute_async(action: dict) -> dict:
    type_ = action.get("type")
    if not type_:
        return {"ok": False, "error": "missing action type"}
    if type_ == "sequence":
        return await _execute_sequence(action.get("params") or {})
    fn = ACTIONS.get(type_)
    if fn is None:
        return {"ok": False, "error": f"unknown action type: {type_}"}
    params = action.get("params") or {}
    try:
        if inspect.iscoroutinefunction(fn):
            result = await fn(params)
        else:
            result = await asyncio.to_thread(fn, params)
        return {"ok": True, **(result or {})}
    except Exception as exc:
        log.exception("Action %s failed", type_)
        return {"ok": False, "error": str(exc)}


async def _execute_sequence(params: dict) -> dict:
    steps = params.get("steps") or []
    if not isinstance(steps, list):
        return {"ok": False, "error": "sequence 'steps' must be a list"}
    for i, step in enumerate(steps):
        result = await execute_async(step)
        if result.get("ok") is False:
            return {
                "ok": False,
                "error": f"step {i + 1} failed: {result.get('error')}",
                "completed": i,
                "total": len(steps),
            }
    return {"ok": True, "steps_completed": len(steps)}


def execute(action: dict) -> dict:
    """Sync wrapper, útil para tests fuera del event loop."""
    return asyncio.run(execute_async(action))
