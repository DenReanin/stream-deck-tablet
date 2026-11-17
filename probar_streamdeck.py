#!/usr/bin/env python3
"""Suite de pruebas automatizadas de Stream Deck Tablet."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from server import actions, config, plantillas
from server.main import app

fallos: list[str] = []


def comprobar(nombre: str, condicion: bool, detalle: str = "") -> None:
    if condicion:
        print(f"  [OK]    {nombre}")
    else:
        print(f"  [FALLO] {nombre}" + (f" — {detalle}" if detalle else ""))
        fallos.append(nombre)


def caso_config_y_plantillas(tmp_cfg: Path) -> None:
    print("\n1. Configuración y plantillas")
    config.CONFIG_PATH = tmp_cfg

    cfg = config.load()
    comprobar("carga configuración por defecto con página p_sounds",
              any(p.get("id") == config.AUTO_PAGE_ID for p in cfg.get("pages", [])))

    cfg["pages"].append({"id": config.next_page_id(cfg), "name": "Extra", "buttons": []})
    config.save(cfg)
    reloaded = config.load()
    comprobar("guarda y recarga config.json correctamente",
              len(reloaded["pages"]) == 2 and reloaded["pages"][0]["id"] == config.AUTO_PAGE_ID)
    comprobar("find_page localiza página por id",
              config.find_page(reloaded, "p1") is not None)
    comprobar("plantillas predefinidas disponibles",
              len(plantillas.TEMPLATES) >= 4 and plantillas.get_by_id("obs-classic") is not None)


def caso_acciones() -> None:
    print("\n2. Motor de acciones")
    r_delay = actions.execute({"type": "delay", "params": {"ms": 10}})
    comprobar("acción delay ejecuta OK", r_delay.get("ok") is True, str(r_delay))

    r_seq = actions.execute({
        "type": "sequence",
        "params": {"steps": [{"type": "delay", "params": {"ms": 5}}]},
    })
    comprobar("acción sequence ejecuta OK", r_seq.get("ok") is True and r_seq.get("steps_completed") == 1, str(r_seq))

    r_sp = actions.execute({"type": "soundpad_play", "params": {"index": 1}})
    comprobar("soundpad sin conexión falla controladamente", r_sp.get("ok") is False, str(r_sp))

    r_hk = actions.execute({"type": "hotkey", "params": {"keys": ["tecla_inexistente_xyz"]}})
    comprobar("hotkey con tecla inválida devuelve error", r_hk.get("ok") is False, str(r_hk))


def caso_api_y_websocket(tmp_cfg: Path) -> None:
    print("\n3. API REST y WebSocket (/ws)")
    config.CONFIG_PATH = tmp_cfg

    with TestClient(app) as client:
        r_root = client.get("/")
        comprobar("GET / devuelve la PWA", r_root.status_code == 200 and "text/html" in r_root.headers.get("content-type", ""))

        r_health = client.get("/api/health")
        h = r_health.json()
        comprobar("GET /api/health responde ok=True con urls y platform",
                  r_health.status_code == 200 and h.get("ok") is True and "urls" in h and "platform" in h, str(h))

        r_cfg = client.get("/api/config")
        comprobar("GET /api/config responde 200", r_cfg.status_code == 200 and "pages" in r_cfg.json())

        r_tmpl = client.get("/api/templates")
        comprobar("GET /api/templates lista plantillas",
                  r_tmpl.status_code == 200 and len(r_tmpl.json().get("templates", [])) >= 4)

        r_apply = client.post("/api/templates/obs-classic/apply?mode=new_page")
        comprobar("POST /api/templates/obs-classic/apply crea página",
                  r_apply.status_code == 200 and any(p.get("name") == "OBS Studio" for p in r_apply.json().get("pages", [])))

        r_obs = client.get("/api/obs/status")
        comprobar("GET /api/obs/status responde sin excepciones", r_obs.status_code == 200 and "connected" in r_obs.json())

        with client.websocket_connect("/ws") as ws:
            hello = ws.receive_json()
            comprobar("WS /ws envía saludo hello", hello.get("type") == "hello", str(hello))

            ws.send_json({"type": "ping"})
            pong = ws.receive_json()
            comprobar("WS /ws responde pong", pong.get("type") == "pong", str(pong))

            ws.send_json({"type": "action", "action": {"type": "delay", "params": {"ms": 10}}})
            act = ws.receive_json()
            comprobar("WS /ws ejecuta acción ad-hoc", act.get("type") == "action_result" and act.get("ok") is True, str(act))


def main() -> int:
    orig_cfg = config.CONFIG_PATH
    tmp_dir = Path(tempfile.mkdtemp(prefix="streamdeck_test_"))
    try:
        tmp_cfg = tmp_dir / "config.json"
        caso_config_y_plantillas(tmp_cfg)
        caso_acciones()
        caso_api_y_websocket(tmp_cfg)
    finally:
        config.CONFIG_PATH = orig_cfg
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print()
    if fallos:
        print(f"RESULTADO: {len(fallos)} comprobación(es) fallida(s):")
        for f in fallos:
            print(f"  · {f}")
        return 1
    print("RESULTADO: todas las comprobaciones pasan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
