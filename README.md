# Stream Deck Tablet

Stream Deck casero. Una tablet vieja conectada por WiFi hace de mando para
el PC: lanzar sonidos de Soundpad, mandar atajos de teclado, abrir apps,
controlar OBS. La tablet no necesita app instalada — abre una URL en Chrome
y ya está.

Pensado para Windows + tablet Android con WiFi. Probado en Huawei
MediaPad M5 Lite (Android 8).

## Cómo funciona

```
Tablet (Chrome / PWA)  --WebSocket-->  Servidor Python (PC)
                                              |
                                              +-- Soundpad   (named pipe)
                                              +-- OBS Studio (WebSocket v5)
                                              +-- Teclado / apps / URLs
```

El servidor sirve la interfaz web y atiende los comandos. Soundpad ya se
encarga de mandar el audio al micrófono virtual; no hace falta VB-Cable
ni nada parecido.

## Requisitos

- Python 3.10 o superior (probado con 3.14)
- Windows 10/11
- Soundpad instalado (opcional, solo si quieres soundboard)
- OBS Studio 28+ (opcional, solo si quieres controlar OBS)
- Tablet en la misma red WiFi que el PC

## Arranque

Desde la carpeta del proyecto, en PowerShell:

```powershell
py -m venv .venv
./.venv/Scripts/python.exe -m pip install -r server/requirements.txt
./.venv/Scripts/python.exe -m server.main
```

O doble click a `start-server.bat`.

El servidor escucha en el puerto 8765. La primera vez Windows preguntará
por el firewall — acepta para redes privadas.

En la tablet, abre Chrome y entra a una de estas direcciones:

- `http://streamdeck.local:8765` (si la red soporta mDNS)
- `http://<IP-del-PC>:8765` (la IP aparece en el log al arrancar)

Desde el menú de Chrome, "Añadir a pantalla de inicio" deja la PWA como
si fuera una app.

## Soundpad

En Soundpad: Preferences (Ctrl+P) → Remote Control → marca *Enable remote
control*. Deja la contraseña en blanco. Mantén Soundpad abierto.

La primera vez, el servidor lee la lista de sonidos y la convierte en
botones automáticamente. Si añades sonidos nuevos, recarga la PWA.

## OBS Studio

En OBS: Tools → WebSocket Server Settings → Enable WebSocket server.
Anota puerto (4455 por defecto) y contraseña.

En la PWA, modo edición (icono lápiz) → botón "OBS" → introduce host,
puerto y contraseña. Al guardar se prueba la conexión y se cargan las
escenas y fuentes de audio.

Tipos de acción disponibles:

- `obs_scene` — cambiar a una escena por nombre
- `obs_toggle_stream` — start/stop streaming
- `obs_toggle_record` — start/stop grabación
- `obs_toggle_mute` — mute/unmute de una fuente de audio
- `obs_transition` — disparar transición en Studio Mode

## Acciones disponibles

| Tipo | Descripción |
|---|---|
| `soundpad_play` | Reproducir un sonido de Soundpad por índice |
| `soundpad_stop` | Parar el sonido actual |
| `soundpad_next` / `soundpad_previous` | Sonido siguiente / anterior |
| `hotkey` | Combinación de teclas (`ctrl+shift+f1`, etc.) |
| `launch_app` | Abrir un ejecutable |
| `run_script` | Ejecutar un `.bat`, `.ps1` o `.cmd` |
| `open_url` | Abrir una URL en el navegador del PC |
| `text_input` | Escribir texto en la app activa |
| `delay` | Pausa (útil dentro de `sequence`) |
| `sequence` | Encadenar varias acciones |
| `obs_scene` | OBS: cambiar de escena |
| `obs_toggle_stream` / `_record` | OBS: toggle stream / grabación |
| `obs_toggle_mute` | OBS: mute de una fuente |
| `obs_transition` | OBS: transición en Studio Mode |

Para `hotkey`, además de las teclas normales, valen estas:

- Modificadores: `ctrl`, `shift`, `alt`, `win`
- Función: `f1` a `f20`
- Navegación: `up`, `down`, `left`, `right`, `home`, `end`, `pageup`, `pagedown`
- Multimedia: `play_pause`, `next_track`, `previous_track`, `volume_up`,
  `volume_down`, `mute`

## Plantillas

En modo edición, el icono de plantillas (📋) abre un selector con sets
predefinidos: OBS Studio, Discord, Multimedia, Sistema. Cada uno se aplica
como página nueva con sus botones listos.

## Páginas

Las pestañas en la cabecera son páginas. Se cambian tocándolas o
deslizando horizontalmente sobre el grid en zonas vacías. En modo edición,
la pestaña activa se vuelve a tocar para renombrar o borrar. El "+" añade
una página.

## Edición

Icono del lápiz arriba a la derecha. Con el modo activo:

- Toque corto en un botón → editor del botón (etiqueta, color, icono,
  acción y sus parámetros).
- Pulsación larga (~250 ms) + arrastrar → mover botón a otro hueco.
- Toque en pestaña activa → editor de la página.

Los cambios se guardan en `server/config.json`, así que la configuración
vive en el PC y la tablet siempre lee el mismo estado.

## Estructura

```
stream-deck-tablet/
  server/
    main.py             FastAPI: WebSocket + HTTP + sirve la PWA
    soundpad_client.py  Cliente del named pipe de Soundpad
    obs_client.py       Cliente OBS WebSocket
    actions/            Un módulo por tipo de acción
    plantillas.py       Sets de botones predefinidos
    config.py           Carga / guarda config.json (con migración v1->v2)
    static/             PWA (HTML + CSS + JS vanilla)
  docs/
    INSTALACION.md
    USO.md
  start-server.bat
```

## Limitaciones conocidas

- El stack es Windows-only por usar pywin32 para el pipe de Soundpad y
  pynput para las teclas. En Linux/macOS habría que sustituir el cliente
  de Soundpad (no hay versión nativa).
- La configuración no tiene autenticación. Cualquiera en la misma WiFi
  que conozca la IP puede mandar comandos. Para uso doméstico está bien;
  para redes públicas, no.
- El service worker no cachea nada — los cambios en el servidor se ven
  inmediatamente pero la PWA no funciona offline (tampoco lo necesita).

## Licencia

Ver `LICENSE`.
