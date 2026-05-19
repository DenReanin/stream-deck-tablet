"""Servidor del Stream Deck.

Arranca con:  py -m server.main
o desde la raíz del proyecto:  ./.venv/Scripts/python.exe -m server.main
"""
from __future__ import annotations

import asyncio
import json
import logging
import socket
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import actions, config, plantillas as tmpl_module
from .obs_client import OBSError, get_client as get_obs_client
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

    # Configurar OBS desde el config persistido (sin forzar conexión)
    cfg = config.load()
    obs_cfg = cfg.get("obs") or {}
    obs = get_obs_client()
    obs.configure(
        obs_cfg.get("host", "localhost"),
        obs_cfg.get("port", 4455),
        obs_cfg.get("password", ""),
    )

    # Registrar mDNS en un thread (Zeroconf tiene su propio event loop y
    # choca con el de FastAPI si se llama directamente).
    mdns = await asyncio.to_thread(_start_mdns, PORT)

    log.info("Server URLs: %s", _local_urls(PORT))
    log.info("También accesible desde tablet (si soporta mDNS): http://streamdeck.local:%d", PORT)
    yield
    log.info("Shutting down")
    if mdns is not None:
        try:
            await asyncio.to_thread(mdns.close)
        except Exception:
            pass
    obs.disconnect()
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


# --- OBS -------------------------------------------------------------------

@app.get("/api/obs/status")
def obs_status() -> dict:
    obs = get_obs_client()
    out = {"connected": obs.connected}
    if not obs.connected:
        obs.connect()
        out["connected"] = obs.connected
    if obs.connected:
        try:
            out["version"] = obs.get_version()
            out["streaming"] = obs.get_stream_status().get("active", False)
            out["recording"] = obs.get_record_status().get("active", False)
        except OBSError as exc:
            out["error"] = str(exc)
    return out


@app.get("/api/obs/scenes")
def obs_scenes() -> dict:
    obs = get_obs_client()
    if not obs.connected and not obs.connect():
        raise HTTPException(503, "OBS not reachable")
    try:
        return {"scenes": obs.get_scenes()}
    except OBSError as exc:
        raise HTTPException(503, str(exc))


@app.get("/api/obs/inputs")
def obs_inputs() -> dict:
    obs = get_obs_client()
    if not obs.connected and not obs.connect():
        raise HTTPException(503, "OBS not reachable")
    try:
        return {"inputs": obs.get_inputs_audio()}
    except OBSError as exc:
        raise HTTPException(503, str(exc))


@app.post("/api/obs/connect")
def obs_connect(payload: dict) -> dict:
    """Guarda credenciales OBS y reintenta la conexión."""
    host = payload.get("host", "localhost")
    port = int(payload.get("port", 4455))
    password = payload.get("password", "")
    obs = get_obs_client()
    obs.configure(host, port, password)

    # Persistir en config.json
    cfg = config.load()
    cfg["obs"] = {"host": host, "port": port, "password": password}
    config.save(cfg)

    ok = obs.connect()
    return {"ok": ok, "connected": obs.connected}


# --- Templates -------------------------------------------------------------

@app.get("/api/templates")
def list_templates() -> dict:
    return {
        "templates": [
            {
                "id": t["id"],
                "name": t["name"],
                "description": t["description"],
                "button_count": len(t["buttons"]),
            }
            for t in tmpl_module.TEMPLATES
        ]
    }


@app.post("/api/templates/{template_id}/apply")
def apply_template(template_id: str, mode: str = "new_page") -> dict:
    """Aplicar una plantilla.

    mode='new_page'      → crea una página nueva con los botones de la plantilla
    mode='current_page'  → añade los botones a los slots vacíos de la página actual
    """
    template = tmpl_module.get_by_id(template_id)
    if not template:
        raise HTTPException(404, f"Template not found: {template_id}")
    cfg = config.load()
    grid = cfg.get("grid", {"cols": 4, "rows": 4})
    capacity = grid["cols"] * grid["rows"]
    template_buttons = template["buttons"]

    if mode == "new_page":
        if len(template_buttons) > capacity:
            raise HTTPException(
                400,
                f"Template has {len(template_buttons)} buttons but grid only holds {capacity}",
            )
        new_page = {
            "id": config.next_page_id(cfg),
            "name": template["name"],
            "buttons": [
                {**btn, "id": f"b{i + 1}"}
                for i, btn in enumerate(template_buttons)
            ],
        }
        cfg.setdefault("pages", []).append(new_page)
    elif mode == "current_page":
        page_id = None  # primera por defecto si no se especifica
        page = config.find_page(cfg, page_id)
        if page is None:
            raise HTTPException(404, "No page available")
        used = {b["id"] for b in page.get("buttons", [])}
        free_slots = [f"b{i + 1}" for i in range(capacity) if f"b{i + 1}" not in used]
        if len(free_slots) < len(template_buttons):
            raise HTTPException(
                400,
                f"Not enough free slots ({len(free_slots)} free, {len(template_buttons)} needed)",
            )
        page.setdefault("buttons", []).extend(
            {**btn, "id": slot} for slot, btn in zip(free_slots, template_buttons)
        )
    else:
        raise HTTPException(400, f"Unknown mode: {mode}")

    config.save(cfg)
    return cfg


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
        page_id = data.get("page_id")
        cfg = config.load()
        page = config.find_page(cfg, page_id)
        if page is None:
            await ws.send_json({"type": "press_result", "button_id": button_id,
                                "ok": False, "error": "page not found"})
            return
        button = next(
            (b for b in page.get("buttons", []) if b.get("id") == button_id),
            None,
        )
        if button is None:
            await ws.send_json({"type": "press_result", "button_id": button_id,
                                "ok": False, "error": "button not found"})
            return
        result = await actions.execute_async(button.get("action", {}))
        await ws.send_json({"type": "press_result", "button_id": button_id,
                            "page_id": page.get("id"), **result})
        return
    if msg_type == "action":
        # Acción ad-hoc sin botón guardado (útil para tests).
        result = await actions.execute_async(data.get("action", {}))
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


def _start_mdns(port: int):
    """Registra un servicio mDNS para que la tablet pueda conectar como
    http://streamdeck.local:<port> sin escribir la IP."""
    try:
        from zeroconf import IPVersion, ServiceInfo, Zeroconf
    except ImportError:
        log.info("zeroconf no instalado, mDNS desactivado")
        return None
    ip = _primary_ip()
    if not ip:
        return None
    try:
        zc = Zeroconf(ip_version=IPVersion.V4Only)
        info = ServiceInfo(
            "_http._tcp.local.",
            "Stream Deck._http._tcp.local.",
            addresses=[socket.inet_aton(ip)],
            port=port,
            properties={"path": "/"},
            server="streamdeck.local.",
        )
        zc.register_service(info)
        log.info("mDNS registrado como streamdeck.local en %s:%d", ip, port)
        return zc
    except Exception as exc:
        log.warning("No se pudo registrar mDNS: %r", exc)
        return None


HOST = "0.0.0.0"
PORT = 8765


if __name__ == "__main__":
    uvicorn.run("server.main:app", host=HOST, port=PORT, log_level="info")
