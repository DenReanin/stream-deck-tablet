# Uso

## Funcionamiento básico

Al abrir la PWA en la tablet, el servidor:
1. Te muestra un grid 4×4 (16 botones)
2. La primera vez auto-rellena con los primeros 16 sonidos de Soundpad
3. Punto verde arriba = conectado, rojo = sin conexión

Toca un botón → sonido suena en Soundpad → sale por micrófono virtual.

## Editar botones desde la tablet

1. Toca el icono **✎** (arriba a la derecha)
2. Estás en **modo edición** (todos los botones tienen borde discontinuo)
3. Toca el botón que quieras editar
4. En el diálogo:
   - **Etiqueta**: texto del botón
   - **Color**: color de fondo
   - **Acción**: tipo y parámetros (ver abajo)
5. **Guardar** → la config se persiste en el PC
6. Toca **✓** para volver a modo normal

### Tipos de acción

| Tipo | Parámetros | Ejemplo |
|---|---|---|
| **Soundpad: reproducir sonido** | Selecciona uno de la lista | — |
| **Soundpad: parar/siguiente/anterior** | — | — |
| **Atajo de teclado** | Teclas separadas por `+` | `ctrl+shift+f1` |
| **Lanzar aplicación** | Ruta + args opcionales | `C:\Program Files\OBS\obs.exe` |
| **Ejecutar script** | Ruta al `.bat` / `.ps1` | `C:\scripts\setup.bat` |
| **Abrir URL** | URL completa | `https://twitch.tv/...` |

### Teclas válidas para `hotkey`

- Modificadores: `ctrl`, `shift`, `alt`, `win`
- Especiales: `enter`, `esc`, `tab`, `space`, `backspace`, `delete`,
  `up`/`down`/`left`/`right`, `home`/`end`, `pageup`/`pagedown`, `insert`
- Función: `f1`–`f20`
- Cualquier letra/número: `a`, `b`, `1`, `2`, etc.

## Editar `config.json` a mano

El archivo `server/config.json` se puede editar con cualquier editor.
Ejemplo:

```json
{
  "grid": { "cols": 4, "rows": 4 },
  "buttons": [
    {
      "id": "b1",
      "label": "Aplauso",
      "color": "#10b981",
      "action": { "type": "soundpad_play", "params": { "index": 1 } }
    },
    {
      "id": "b5",
      "label": "Mute mic",
      "color": "#ef4444",
      "action": { "type": "hotkey", "params": { "keys": ["ctrl", "shift", "m"] } }
    },
    {
      "id": "b9",
      "label": "OBS",
      "color": "#3b82f6",
      "action": {
        "type": "launch_app",
        "params": { "path": "C:\\Program Files\\obs-studio\\bin\\64bit\\obs64.exe" }
      }
    }
  ]
}
```

Los `id` deben ser `b1`, `b2`, … `bN` (posición en el grid de izquierda a
derecha, arriba a abajo). Después de editar a mano, recarga la PWA en la
tablet.

## Cambiar el tamaño del grid

Edita `server/config.json`:

```json
{ "grid": { "cols": 5, "rows": 3 } }
```

Reinicia el servidor (no hace falta, pero recarga la PWA).

## Auto-regenerar desde Soundpad

Si añades sonidos nuevos en Soundpad y quieres regenerar la config:

```powershell
curl -X POST http://localhost:8765/api/config/autogen
```

O simplemente borra `server/config.json` y recarga la PWA — la auto-genera.

## Apagar el servidor

`Ctrl+C` en la ventana de PowerShell donde lo arrancaste.
