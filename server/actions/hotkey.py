"""Simular pulsaciones de teclas (atajos / macros)."""
from __future__ import annotations

import shutil
import subprocess
import sys

_keyboard = None

_XDOTOOL_KEYS = {
    "ctrl": "ctrl",
    "control": "ctrl",
    "shift": "shift",
    "alt": "alt",
    "win": "super",
    "cmd": "super",
    "super": "super",
    "enter": "Return",
    "esc": "Escape",
    "escape": "Escape",
    "tab": "Tab",
    "space": "space",
    "backspace": "BackSpace",
    "delete": "Delete",
    "del": "Delete",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "home": "Home",
    "end": "End",
    "pageup": "Prior",
    "pagedown": "Next",
    "insert": "Insert",
    "play_pause": "XF86AudioPlay",
    "media_play": "XF86AudioPlay",
    "media_play_pause": "XF86AudioPlay",
    "next_track": "XF86AudioNext",
    "media_next": "XF86AudioNext",
    "previous_track": "XF86AudioPrev",
    "media_previous": "XF86AudioPrev",
    "volume_up": "XF86AudioRaiseVolume",
    "volume_down": "XF86AudioLowerVolume",
    "volume_mute": "XF86AudioMute",
    "mute": "XF86AudioMute",
}


def _get_keyboard():
    global _keyboard
    if _keyboard is None:
        from pynput.keyboard import Controller

        _keyboard = Controller()
    return _keyboard


def _resolve_pynput(key_name: str):
    from pynput.keyboard import Key

    special = {
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
        "play_pause": Key.media_play_pause,
        "media_play": Key.media_play_pause,
        "media_play_pause": Key.media_play_pause,
        "next_track": Key.media_next,
        "media_next": Key.media_next,
        "previous_track": Key.media_previous,
        "media_previous": Key.media_previous,
        "volume_up": Key.media_volume_up,
        "volume_down": Key.media_volume_down,
        "volume_mute": Key.media_volume_mute,
        "mute": Key.media_volume_mute,
    }
    key = key_name.strip().lower()
    if key in special:
        return special[key]
    if len(key_name) == 1:
        return key_name
    raise ValueError(f"Unknown key: {key_name!r}")


def _resolve_xdotool(key_name: str) -> str:
    key = key_name.strip().lower()
    if key in _XDOTOOL_KEYS:
        return _XDOTOOL_KEYS[key]
    if key.startswith("f") and key[1:].isdigit():
        return key.upper()
    if len(key_name) == 1:
        return key_name
    raise ValueError(f"Unknown key: {key_name!r}")


def press(params: dict) -> dict:
    keys = params.get("keys")
    if not keys or not isinstance(keys, list):
        raise ValueError("hotkey requires 'keys' as a list of strings")

    try:
        kb = _get_keyboard()
        resolved = [_resolve_pynput(k) for k in keys]
        for k in resolved:
            kb.press(k)
        for k in reversed(resolved):
            kb.release(k)
        return {"keys": keys, "backend": "pynput"}
    except ValueError:
        raise
    except Exception as exc:
        if sys.platform.startswith("linux") and shutil.which("xdotool"):
            combo = "+".join(_resolve_xdotool(k) for k in keys)
            subprocess.run(["xdotool", "key", combo], check=True)
            return {"keys": keys, "backend": "xdotool"}
        raise RuntimeError(f"Keyboard backend failed: {exc}") from exc
