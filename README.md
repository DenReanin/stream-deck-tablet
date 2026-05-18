# Stream Deck Tablet

Stream Deck DIY: usa una tablet vieja como controlador remoto para tu PC
(reproducir sonidos en Soundpad, lanzar atajos de teclado, abrir apps, etc.).

## Arquitectura

```
Tablet (Chrome PWA) ──WiFi/WebSocket──▶ Servidor Python ──▶ Soundpad / pynput / subprocess
```

- **Sin compilar APK.** La PWA se sirve desde el propio servidor.
- **Sin VB-Audio Cable.** Soundpad ya enruta al micrófono virtual.
- **Latencia <50ms** en LAN.

## Acciones disponibles

| Tipo | Descripción |
|---|---|
| `soundpad_play` | Reproducir un sonido por índice en Soundpad |
| `soundpad_stop` | Parar reproducción |
| `soundpad_next` / `soundpad_previous` | Pasar al sonido siguiente / anterior |
| `hotkey` | Pulsar un atajo de teclado (`ctrl+shift+f1`, etc.) |
| `launch_app` | Abrir una aplicación |
| `run_script` | Ejecutar un `.bat` / `.ps1` / `.cmd` |
| `open_url` | Abrir una URL en el navegador del PC |

## Inicio rápido

Ver [docs/INSTALACION.md](docs/INSTALACION.md) y [docs/USO.md](docs/USO.md).

```powershell
# Una vez:
py -m venv .venv
./.venv/Scripts/python.exe -m pip install -r server/requirements.txt

# Cada vez:
./.venv/Scripts/python.exe -m server.main
```

Luego abre `http://<IP-DE-TU-PC>:8765` en Chrome de la tablet.

## Estructura

```
stream-deck-tablet/
├── server/
│   ├── main.py                # FastAPI + WebSocket
│   ├── soundpad_client.py     # Cliente named-pipe de Soundpad
│   ├── actions/               # Tipos de acción (sound, hotkey, launch, url)
│   ├── config.py              # Carga/guarda config.json
│   ├── config.json            # Configuración del usuario (se crea al iniciar)
│   ├── requirements.txt
│   └── static/                # PWA (HTML/CSS/JS)
├── docs/
└── README.md
```
