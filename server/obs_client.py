"""Cliente OBS WebSocket (v5 protocol) — envuelve obsws-python.

Conexión perezosa: solo intenta conectar al primer uso o cuando se
configura. La instancia es global (singleton) por proceso.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

import obsws_python as obs

log = logging.getLogger(__name__)


class OBSError(RuntimeError):
    pass


class OBSClient:
    def __init__(self) -> None:
        self._client: obs.ReqClient | None = None
        self._lock = threading.Lock()
        self._host = "localhost"
        self._port = 4455
        self._password = ""

    # --- Connection management --------------------------------------------

    def configure(self, host: str, port: int, password: str) -> None:
        with self._lock:
            self._host = host or "localhost"
            self._port = int(port) if port else 4455
            self._password = password or ""
            self._close_locked()

    def connect(self) -> bool:
        with self._lock:
            if self._client is not None:
                return True
            try:
                self._client = obs.ReqClient(
                    host=self._host,
                    port=self._port,
                    password=self._password,
                    timeout=3,
                )
                log.info("Connected to OBS at %s:%s", self._host, self._port)
                return True
            except Exception as exc:
                log.warning("Cannot connect to OBS (%s:%s): %s",
                            self._host, self._port, exc)
                self._client = None
                return False

    def disconnect(self) -> None:
        with self._lock:
            self._close_locked()

    def _close_locked(self) -> None:
        if self._client is not None:
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._client = None

    @property
    def connected(self) -> bool:
        return self._client is not None

    # --- Internal call wrapper --------------------------------------------

    def _call(self, method_name: str, *args, **kwargs) -> Any:
        if not self.connected and not self.connect():
            raise OBSError("OBS WebSocket not reachable (check OBS → Tools → WebSocket Server)")
        with self._lock:
            try:
                fn = getattr(self._client, method_name)
                return fn(*args, **kwargs)
            except Exception as exc:
                # Una pipe rota requiere reconectar
                log.warning("OBS call %s failed: %s", method_name, exc)
                self._close_locked()
                raise OBSError(str(exc)) from exc

    # --- Public API --------------------------------------------------------

    def get_version(self) -> dict:
        r = self._call("get_version")
        return {
            "obs_version": getattr(r, "obs_version", "?"),
            "ws_version": getattr(r, "obs_web_socket_version", "?"),
        }

    def get_scenes(self) -> list[dict]:
        r = self._call("get_scene_list")
        current = getattr(r, "current_program_scene_name", None)
        scenes = []
        for s in reversed(getattr(r, "scenes", []) or []):
            # OBS devuelve nombres como "sceneName"
            name = s.get("sceneName") if isinstance(s, dict) else s
            scenes.append({"name": name, "active": name == current})
        return scenes

    def set_scene(self, name: str) -> None:
        self._call("set_current_program_scene", name)

    def get_inputs_audio(self) -> list[dict]:
        """Lista de inputs de audio (con propiedad mute)."""
        r = self._call("get_input_list")
        inputs = []
        for inp in getattr(r, "inputs", []) or []:
            if not isinstance(inp, dict):
                continue
            kind = inp.get("inputKind", "")
            # Heurística: kinds que típicamente son audio
            if any(k in kind for k in ("wasapi", "coreaudio", "pulse", "alsa", "audio")):
                inputs.append({"name": inp.get("inputName"), "kind": kind})
        return inputs

    def toggle_input_mute(self, name: str) -> bool:
        r = self._call("toggle_input_mute", name)
        return bool(getattr(r, "input_muted", False))

    def set_input_mute(self, name: str, muted: bool) -> None:
        self._call("set_input_mute", name, muted)

    def get_stream_status(self) -> dict:
        r = self._call("get_stream_status")
        return {"active": bool(getattr(r, "output_active", False))}

    def toggle_stream(self) -> bool:
        r = self._call("toggle_stream")
        return bool(getattr(r, "output_active", False))

    def get_record_status(self) -> dict:
        r = self._call("get_record_status")
        return {"active": bool(getattr(r, "output_active", False))}

    def toggle_record(self) -> bool:
        r = self._call("toggle_record")
        return bool(getattr(r, "output_active", False))

    def trigger_studio_transition(self) -> None:
        self._call("trigger_studio_mode_transition")


_singleton: OBSClient | None = None


def get_client() -> OBSClient:
    global _singleton
    if _singleton is None:
        _singleton = OBSClient()
    return _singleton
