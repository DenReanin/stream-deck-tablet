r"""Cliente para Soundpad Remote Control API vía named pipe de Windows.

Protocolo: comandos de texto enviados al pipe `\\.\pipe\sp_remote_control`.
Documentación: https://www.leppsoft.com/soundpad/help/manual/tutorial/rc/
"""
from __future__ import annotations

import logging
import threading
import xml.etree.ElementTree as ET
from typing import Optional

import pywintypes
import win32file

log = logging.getLogger(__name__)

PIPE_PATH = r"\\.\pipe\sp_remote_control"
READ_BUFFER = 65536


class SoundpadError(RuntimeError):
    pass


class SoundpadClient:
    def __init__(self) -> None:
        self._handle = None
        self._lock = threading.Lock()

    def connect(self) -> bool:
        with self._lock:
            if self._handle is not None:
                return True
            try:
                self._handle = win32file.CreateFile(
                    PIPE_PATH,
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    0,
                    None,
                    win32file.OPEN_EXISTING,
                    0,
                    None,
                )
                log.info("Connected to Soundpad")
                return True
            except pywintypes.error as exc:
                log.warning("Cannot connect to Soundpad: %s", exc)
                self._handle = None
                return False

    def disconnect(self) -> None:
        with self._lock:
            if self._handle is not None:
                try:
                    win32file.CloseHandle(self._handle)
                except Exception:
                    pass
                self._handle = None

    @property
    def connected(self) -> bool:
        return self._handle is not None

    def _send_locked(self, command: str) -> str:
        if self._handle is None:
            raise SoundpadError("Not connected to Soundpad")
        try:
            win32file.WriteFile(self._handle, command.encode("utf-8"))
            _, data = win32file.ReadFile(self._handle, READ_BUFFER)
            return data.decode("utf-8", errors="ignore")
        except pywintypes.error as exc:
            log.warning("Pipe error, marking disconnected: %s", exc)
            try:
                win32file.CloseHandle(self._handle)
            except Exception:
                pass
            self._handle = None
            raise SoundpadError(f"Soundpad pipe error: {exc}") from exc

    def send(self, command: str) -> str:
        """Send a raw command; auto-connect once if not connected."""
        with self._lock:
            if self._handle is None:
                # Try a single reconnect
                pass
        if not self.connected and not self.connect():
            raise SoundpadError("Soundpad not running or remote control disabled")
        with self._lock:
            return self._send_locked(command)

    # --- High-level API -----------------------------------------------------

    def get_version(self) -> str:
        return _strip_status(self.send("GetVersion()"))

    def play_sound(self, index: int) -> str:
        if index < 1:
            raise ValueError("Soundpad sound indexes start at 1")
        return _strip_status(self.send(f"DoPlaySound({index})"))

    def stop_sound(self) -> str:
        return _strip_status(self.send("DoStopSound()"))

    def pause_sound(self) -> str:
        return _strip_status(self.send("DoTogglePause()"))

    def play_previous(self) -> str:
        return _strip_status(self.send("DoPlayPreviousSound()"))

    def play_next(self) -> str:
        return _strip_status(self.send("DoPlayNextSound()"))

    def get_sound_list(self) -> list[dict]:
        raw = self.send("GetSoundlist()")
        xml_start = raw.find("<?xml")
        if xml_start < 0:
            xml_start = raw.find("<Soundlist")
        if xml_start < 0:
            log.warning("Unexpected GetSoundlist response: %r", raw[:200])
            return []
        xml_text = raw[xml_start:]
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            log.error("Failed to parse soundlist XML: %s", exc)
            return []
        sounds: list[dict] = []
        for sound in root.findall(".//Sound"):
            try:
                idx = int(sound.get("index", "0"))
            except ValueError:
                continue
            if idx < 1:
                continue
            sounds.append(
                {
                    "index": idx,
                    "title": sound.get("title", f"Sonido {idx}"),
                    "url": sound.get("url", ""),
                    "duration": sound.get("duration", ""),
                    "artist": sound.get("artist", ""),
                }
            )
        return sounds


def _strip_status(response: str) -> str:
    """Soundpad responses sometimes prefix with 'R-200\\n' or similar status code."""
    if response.startswith("R-"):
        nl = response.find("\n")
        if nl >= 0:
            return response[nl + 1 :].strip()
    return response.strip()


_singleton: Optional[SoundpadClient] = None


def get_client() -> SoundpadClient:
    global _singleton
    if _singleton is None:
        _singleton = SoundpadClient()
    return _singleton
