"""Escribir texto en la aplicación enfocada."""
from __future__ import annotations

import shutil
import subprocess
import sys

_keyboard = None


def _get_keyboard():
    global _keyboard
    if _keyboard is None:
        from pynput.keyboard import Controller

        _keyboard = Controller()
    return _keyboard


def type_text(params: dict) -> dict:
    text = params.get("text")
    if not isinstance(text, str) or not text:
        raise ValueError("text_input requires non-empty 'text'")

    try:
        _get_keyboard().type(text)
        return {"typed_chars": len(text), "backend": "pynput"}
    except Exception as exc:
        if sys.platform.startswith("linux"):
            if shutil.which("wtype"):
                subprocess.run(["wtype", "--", text], check=True)
                return {"typed_chars": len(text), "backend": "wtype"}
            if shutil.which("xdotool"):
                subprocess.run(["xdotool", "type", "--clearmodifiers", "--", text], check=True)
                return {"typed_chars": len(text), "backend": "xdotool"}
        raise RuntimeError(f"Text input backend failed: {exc}") from exc
