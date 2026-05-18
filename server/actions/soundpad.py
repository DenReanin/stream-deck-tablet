"""Acciones que controlan Soundpad."""
from __future__ import annotations

from ..soundpad_client import get_client


def play(params: dict) -> dict:
    index = params.get("index")
    if index is None:
        raise ValueError("soundpad_play requires 'index' (1-based)")
    get_client().play_sound(int(index))
    return {"played": index}


def stop(params: dict) -> dict:
    get_client().stop_sound()
    return {}


def next_sound(params: dict) -> dict:
    get_client().play_next()
    return {}


def previous_sound(params: dict) -> dict:
    get_client().play_previous()
    return {}
