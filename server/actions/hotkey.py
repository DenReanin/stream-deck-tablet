"""Simular pulsaciones de teclas (atajos / macros)."""
from __future__ import annotations

from pynput.keyboard import Controller, Key

_keyboard = Controller()

# Mapeo de strings a teclas especiales de pynput.
SPECIAL_KEYS = {
    "ctrl": Key.ctrl,
    "control": Key.ctrl,
    "shift": Key.shift,
    "alt": Key.alt,
    "win": Key.cmd,
    "cmd": Key.cmd,
    "super": Key.cmd,
    "enter": Key.enter,
    "esc": Key.esc,
    "escape": Key.esc,
    "tab": Key.tab,
    "space": Key.space,
    "backspace": Key.backspace,
    "delete": Key.delete,
    "del": Key.delete,
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
    "home": Key.home,
    "end": Key.end,
    "pageup": Key.page_up,
    "pagedown": Key.page_down,
    "insert": Key.insert,
    "f1": Key.f1, "f2": Key.f2, "f3": Key.f3, "f4": Key.f4,
    "f5": Key.f5, "f6": Key.f6, "f7": Key.f7, "f8": Key.f8,
    "f9": Key.f9, "f10": Key.f10, "f11": Key.f11, "f12": Key.f12,
    "f13": Key.f13, "f14": Key.f14, "f15": Key.f15, "f16": Key.f16,
    "f17": Key.f17, "f18": Key.f18, "f19": Key.f19, "f20": Key.f20,
}


def _resolve(key_name: str):
    key = key_name.strip().lower()
    if key in SPECIAL_KEYS:
        return SPECIAL_KEYS[key]
    if len(key_name) == 1:
        return key_name
    raise ValueError(f"Unknown key: {key_name!r}")


def press(params: dict) -> dict:
    keys = params.get("keys")
    if not keys or not isinstance(keys, list):
        raise ValueError("hotkey requires 'keys' as a list of strings")
    resolved = [_resolve(k) for k in keys]
    for k in resolved:
        _keyboard.press(k)
    for k in reversed(resolved):
        _keyboard.release(k)
    return {"keys": keys}
