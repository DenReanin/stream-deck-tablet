# Instalación

## 1. Requisitos en el PC

- **Windows 10/11**
- **Python 3.10+** (probado con 3.14)
- **Soundpad** instalado y configurado con sonidos
- Tablet y PC en la **misma red WiFi**

## 2. Activar la API remota de Soundpad

1. Abre **Soundpad**
2. **File → Preferences** (`Ctrl+P`)
3. Sección **Remote Control** (barra lateral)
4. ✅ **Enable remote control**
5. ⛔ Deja desactivado **Require password**
6. OK y deja Soundpad corriendo

> ⚠️ Si no haces este paso, el servidor arranca pero no podrá listar ni
> reproducir sonidos.

## 3. Preparar el entorno Python

Desde la carpeta del proyecto, en PowerShell:

```powershell
py -m venv .venv
./.venv/Scripts/python.exe -m pip install --upgrade pip
./.venv/Scripts/python.exe -m pip install -r server/requirements.txt
```

## 4. Permitir el puerto 8765 en el firewall

La primera vez que arranques el servidor, Windows te preguntará si quieres
permitir las conexiones entrantes. **Marca "Redes privadas" y acepta.**

Si te lo perdiste:

```powershell
New-NetFirewallRule -DisplayName "Stream Deck Tablet" `
  -Direction Inbound -Protocol TCP -LocalPort 8765 `
  -Action Allow -Profile Private
```

## 5. Arrancar el servidor

```powershell
./.venv/Scripts/python.exe -m server.main
```

Verás algo así:

```
23:24:27 [INFO] streamdeck: Starting Stream Deck server
23:24:27 [INFO] server.soundpad_client: Connected to Soundpad
23:24:27 [INFO] streamdeck: Soundpad version: 4.0.30
23:24:27 [INFO] streamdeck: Server URLs: ['http://localhost:8765',
                                          'http://192.168.18.226:8765']
INFO:     Uvicorn running on http://0.0.0.0:8765
```

Apunta la **IP de tu red local** (la que NO es `localhost` ni `172.x` —
suele ser `192.168.x.x`).

## 6. Conectar la tablet

1. En tu tablet Android (M5 Lite 10), abre **Chrome**
2. Ve a `http://<IP-de-tu-PC>:8765` (ej. `http://192.168.18.226:8765`)
3. Verás el grid de botones con tus sonidos auto-cargados
4. **Menú de Chrome (⋮) → "Añadir a pantalla de inicio"** → quedará como
   una app fullscreen

¡Listo! Toca un botón y debe sonar en tu micrófono virtual.

## Troubleshooting

| Problema | Solución |
|---|---|
| `python` no se reconoce | Usa `py` (Python launcher de Windows) |
| `Cannot connect to Soundpad` | Soundpad no está abierto o no tiene la API activada |
| La tablet no conecta | Revisa que ambos están en la misma WiFi y el firewall permite el puerto 8765 |
| Sonido suena en el PC pero no en OBS/Discord | Es config de Soundpad — selecciona el micrófono virtual como salida en Soundpad |
| Botones vacíos en la PWA | Soundpad no tiene sonidos cargados, o la sesión de Soundpad cambió. Recarga la PWA. |
