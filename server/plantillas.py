"""Plantillas predefinidas de botones para aplicar como nueva página.

Cada plantilla es un set de botones con etiquetas, colores y acciones
ya configurados. El usuario puede editarlos después.

NOTA: los atajos de OBS/Discord asumen los keybinds por defecto del
programa — el usuario debe configurar los hotkeys correspondientes
dentro de OBS/Discord para que coincidan.
"""
from __future__ import annotations

from typing import Any

TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "obs-classic",
        "name": "OBS Studio",
        "description": "Configura los hotkeys en OBS → Settings → Hotkeys para que coincidan",
        "buttons": [
            {"label": "Escena 1", "color": "#3b82f6",
             "action": {"type": "hotkey", "params": {"keys": ["ctrl", "shift", "f1"]}}},
            {"label": "Escena 2", "color": "#3b82f6",
             "action": {"type": "hotkey", "params": {"keys": ["ctrl", "shift", "f2"]}}},
            {"label": "Escena 3", "color": "#3b82f6",
             "action": {"type": "hotkey", "params": {"keys": ["ctrl", "shift", "f3"]}}},
            {"label": "Escena 4", "color": "#3b82f6",
             "action": {"type": "hotkey", "params": {"keys": ["ctrl", "shift", "f4"]}}},
            {"label": "▶ Stream", "color": "#ef4444",
             "action": {"type": "hotkey", "params": {"keys": ["ctrl", "shift", "s"]}}},
            {"label": "● REC", "color": "#10b981",
             "action": {"type": "hotkey", "params": {"keys": ["ctrl", "shift", "r"]}}},
            {"label": "🔇 Mute desktop", "color": "#f59e0b",
             "action": {"type": "hotkey", "params": {"keys": ["ctrl", "shift", "d"]}}},
            {"label": "🎙 Mute mic", "color": "#f59e0b",
             "action": {"type": "hotkey", "params": {"keys": ["ctrl", "shift", "m"]}}},
        ],
    },
    {
        "id": "discord",
        "name": "Discord",
        "description": "Configura los hotkeys en Discord → User Settings → Keybinds",
        "buttons": [
            {"label": "🔇 Mute mic", "color": "#5865f2",
             "action": {"type": "hotkey", "params": {"keys": ["ctrl", "shift", "m"]}}},
            {"label": "🔕 Deafen", "color": "#5865f2",
             "action": {"type": "hotkey", "params": {"keys": ["ctrl", "shift", "d"]}}},
            {"label": "🎙 PTT", "color": "#10b981",
             "action": {"type": "hotkey", "params": {"keys": ["ctrl", "shift", "p"]}}},
            {"label": "📞 Aceptar llamada", "color": "#10b981",
             "action": {"type": "hotkey", "params": {"keys": ["ctrl", "enter"]}}},
            {"label": "❌ Colgar", "color": "#ef4444",
             "action": {"type": "hotkey", "params": {"keys": ["ctrl", "shift", "h"]}}},
        ],
    },
    {
        "id": "media",
        "name": "Multimedia",
        "description": "Controla Spotify, YouTube y cualquier reproductor del sistema",
        "buttons": [
            {"label": "▶ Play/Pause", "color": "#10b981",
             "action": {"type": "hotkey", "params": {"keys": ["play_pause"]}}},
            {"label": "⏭ Siguiente", "color": "#3b82f6",
             "action": {"type": "hotkey", "params": {"keys": ["next_track"]}}},
            {"label": "⏮ Anterior", "color": "#3b82f6",
             "action": {"type": "hotkey", "params": {"keys": ["previous_track"]}}},
            {"label": "🔊 Vol +", "color": "#8b5cf6",
             "action": {"type": "hotkey", "params": {"keys": ["volume_up"]}}},
            {"label": "🔉 Vol -", "color": "#8b5cf6",
             "action": {"type": "hotkey", "params": {"keys": ["volume_down"]}}},
            {"label": "🔇 Mute", "color": "#f59e0b",
             "action": {"type": "hotkey", "params": {"keys": ["mute"]}}},
        ],
    },
    {
        "id": "system",
        "name": "Sistema",
        "description": "Atajos del sistema Windows",
        "buttons": [
            {"label": "🔒 Bloquear", "color": "#ef4444",
             "action": {"type": "hotkey", "params": {"keys": ["win", "l"]}}},
            {"label": "📷 Captura", "color": "#10b981",
             "action": {"type": "hotkey", "params": {"keys": ["win", "shift", "s"]}}},
            {"label": "📋 Portapapeles", "color": "#3b82f6",
             "action": {"type": "hotkey", "params": {"keys": ["win", "v"]}}},
            {"label": "🖥 Vista tareas", "color": "#3b82f6",
             "action": {"type": "hotkey", "params": {"keys": ["win", "tab"]}}},
            {"label": "🗂 Explorador", "color": "#f59e0b",
             "action": {"type": "launch_app", "params": {"path": "explorer.exe"}}},
            {"label": "🧮 Calculadora", "color": "#3b82f6",
             "action": {"type": "launch_app", "params": {"path": "calc.exe"}}},
            {"label": "🖋 Notepad", "color": "#8b5cf6",
             "action": {"type": "launch_app", "params": {"path": "notepad.exe"}}},
            {"label": "⚙ Ajustes", "color": "#94a3b8",
             "action": {"type": "launch_app", "params": {"path": "ms-settings:"}}},
        ],
    },
]


def get_by_id(template_id: str) -> dict | None:
    return next((t for t in TEMPLATES if t["id"] == template_id), None)
