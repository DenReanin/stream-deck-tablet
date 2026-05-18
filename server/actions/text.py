"""Escribir texto en la aplicación enfocada."""
from __future__ import annotations

from pynput.keyboard import Controller

_keyboard = Controller()


def type_text(params: dict) -> dict:
    text = params.get("text")
    if not isinstance(text, str) or not text:
        raise ValueError("text_input requires non-empty 'text'")
    _keyboard.type(text)
    return {"typed_chars": len(text)}
