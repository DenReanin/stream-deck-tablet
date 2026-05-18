"""Servidor del Stream Deck.

Arranca con:  py -m server.main
o desde la raíz del proyecto:  ./.venv/Scripts/python.exe -m server.main
"""
from __future__ import annotations

import json
import logging
import socket
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import actions, config
from .soundpad_client import SoundpadError, get_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("streamdeck")

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting Stream Deck server")
    client = get_client()
    if client.connect():
        try:
            ver = client.get_version()
            log.info("Soundpad version: %s", ver)
        except SoundpadError as exc:
            log.warning("Soundpad responded but version check failed: %s", exc)
    else:
        log.warning(
            "Soundpad not reachable. Open Soundpad and enable "
            "Preferences -> Remote Control."
        )
    log.info("Server URLs: %s", _local_urls(PORT))
    yield
    log.info("Shutting down")
    client.disconnect()


app = FastAPI(title="Stream Deck Tablet", lifespan=lifespan)


# --- HTTP routes -----------------------------------------------------------

@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "soundpad_connected": get_client().connected,
    }


@app.get("/api/sounds")
def list_sounds() -> dict:
    client = get_client()
    if not client.connected and not client.connect():
        raise HTTPException(503, "Soundpad not reachable")
    try:
        sounds = client.get_sound_list()
    except SoundpadError as exc:
        raise HTTPException(503, str(exc))
    return {"sounds": sounds}


@app.get("/api/config")
def get_config() -> dict:
    return config.load()


@app.post("/api/config")
async def update_config(payload: dict) -> dict:
    config.save(payload)
    await _broadcast({"type": "config_updated", "config": payload})
    return {"ok": True}


@app.post("/api/config/autogen")
def autogen_config() -> dict:
    """Genera una config inicial con un botón por sonido de Soundpad."""
    client = get_client()
    if not client.connected and not client.connect():
        raise HTTPException(503, "Soundpad not reachable")
    sounds = client.get_sound_list()
    current = config.load()
    grid = current.get("grid", {"cols": 4, "rows": 4})
    new = config.autogen_from_sounds(sounds, grid["cols"], grid["rows"])
    config.save(new)
    return new


# --- WebSocket -------------------------------------------------------------

_clients: set[WebSocket] = set()


async def _broadcast(message: dict) -> None:
    dead = []
    payload = json.dumps(message)
    for ws in _clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _clients.discard(ws)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    _clients.add(ws)
    log.info("Client connected (%d total)", len(_clients))
    try:
        await ws.send_json(
            {
                "type": "hello",
                "soundpad_connected": get_client().connected,
            }
        )
        while True:
            data = await ws.receive_json()
            await _handle_message(ws, data)
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("WebSocket error")
    finally:
        _clients.discard(ws)
        log.info("Client disconnected (%d remaining)", len(_clients))


async def _handle_message(ws: WebSocket, data: dict) -> None:
    msg_type = data.get("type")
    if msg_type == "ping":
        await ws.send_json({"type": "pong"})
        return
    if msg_type == "press":
        button_id = data.get("button_id")
        cfg = config.load()
        button = next(
            (b for b in cfg.get("buttons", []) if b.get("id") == button_id),
            None,
        )
        if button is None:
            await ws.send_json({"type": "press_result", "button_id": button_id,
                                "ok": False, "error": "button not found"})
            return
        result = actions.execute(button.get("action", {}))
        await ws.send_json({"type": "press_result", "button_id": button_id, **result})
        return
    if msg_type == "action":
        # Acción ad-hoc sin botón guardado (útil para tests).
        result = actions.execute(data.get("action", {}))
        await ws.send_json({"type": "action_result", **result})
        return
    await ws.send_json({"type": "error", "message": f"unknown message type: {msg_type}"})


# --- Static files (PWA) ----------------------------------------------------

# La PWA se sirve desde server/static/. index.html en la raíz.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/manifest.json")
def manifest():
    return FileResponse(STATIC_DIR / "manifest.json")


@app.get("/sw.js")
def service_worker():
    return FileResponse(STATIC_DIR / "sw.js", media_type="application/javascript")


@app.get("/")
def root():
    return FileResponse(STATIC_DIR / "index.html")


# --- Helpers ---------------------------------------------------------------

def _local_urls(port: int) -> list[str]:
    urls = [f"http://localhost:{port}"]
    try:
        hostname = socket.gethostname()
        for ip in {socket.gethostbyname_ex(hostname)[2][0], _primary_ip()}:
            if ip and ip not in ("127.0.0.1",):
                urls.append(f"http://{ip}:{port}")
    except Exception:
        pass
    return urls


def _primary_ip() -> str | None:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return None
    finally:
        s.close()


HOST = "0.0.0.0"
PORT = 8765


if __name__ == "__main__":
    uvicorn.run("server.main:app", host=HOST, port=PORT, log_level="info")
