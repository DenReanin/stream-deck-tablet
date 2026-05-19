"""Acciones que controlan OBS Studio vía OBS WebSocket."""
from __future__ import annotations

from ..obs_client import get_client


def set_scene(params: dict) -> dict:
    name = params.get("scene")
    if not name:
        raise ValueError("obs_scene requires 'scene'")
    get_client().set_scene(name)
    return {"scene": name}


def toggle_stream(params: dict) -> dict:
    active = get_client().toggle_stream()
    return {"streaming": active}


def toggle_record(params: dict) -> dict:
    active = get_client().toggle_record()
    return {"recording": active}


def toggle_mute(params: dict) -> dict:
    name = params.get("input")
    if not name:
        raise ValueError("obs_toggle_mute requires 'input' (audio source name)")
    muted = get_client().toggle_input_mute(name)
    return {"input": name, "muted": muted}


def transition(params: dict) -> dict:
    get_client().trigger_studio_transition()
    return {}
