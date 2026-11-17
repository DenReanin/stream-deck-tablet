#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

STREAMDECK_PORT="${STREAMDECK_PORT:-8765}"
export STREAMDECK_PORT

if [ ! -x ".venv/bin/python" ]; then
  echo "[Stream Deck] Creando entorno virtual .venv..."
  python3 -m venv --system-site-packages .venv
  echo "[Stream Deck] Instalando dependencias desde server/requirements.txt..."
  ./.venv/bin/pip install --upgrade pip >/dev/null || true
  ./.venv/bin/pip install -r server/requirements.txt httpx || (
    ./.venv/bin/pip install fastapi "uvicorn[standard]" zeroconf obsws-python httpx python-xlib six &&
    ./.venv/bin/pip install --no-deps pynput
  )
fi

if [ "${1:-}" = "--setup-only" ]; then
  echo "[Stream Deck] Entorno .venv listo."
  exit 0
fi

# Abrir el navegador automáticamente cuando FastAPI/Uvicorn empiece a escuchar
(
  for _ in $(seq 1 30); do
    if ./.venv/bin/python -c "import os, socket; s=socket.socket(); s.settimeout(0.2); s.connect(('127.0.0.1', int(os.environ.get('STREAMDECK_PORT', '8765')))); s.close()" 2>/dev/null; then
      if command -v xdg-open >/dev/null 2>&1 && [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
        xdg-open "http://127.0.0.1:${STREAMDECK_PORT}" >/dev/null 2>&1 || true
      fi
      break
    fi
    sleep 0.5
  done
) >/dev/null 2>&1 &

exec ./.venv/bin/python -u -m server.main
