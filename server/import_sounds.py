"""Importa sonidos de una carpeta a Soundpad.

Uso CLI:
    py -m server.import_sounds                # usa carpeta de config.json
    py -m server.import_sounds C:\\carpeta\\sonidos    # override

También expone import_folder() que el endpoint HTTP llama.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from . import config
from .soundpad_client import SoundpadError, get_client

log = logging.getLogger(__name__)

AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma"}


def list_audio_files(folder: Path) -> list[Path]:
    if not folder.exists() or not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir()
                  if p.is_file() and p.suffix.lower() in AUDIO_EXTS)


def import_folder(folder: str | Path | None = None) -> dict:
    """Lee la carpeta dada (o la de config.json) y añade los archivos
    de audio que aún no estén en Soundpad."""
    if folder is None:
        cfg = config.load()
        folder = cfg.get("sounds_folder") or ""
    folder = Path(folder)

    client = get_client()
    if not client.connected and not client.connect():
        return {"ok": False, "error": "Soundpad no está accesible"}

    files = list_audio_files(folder)
    if not files:
        return {
            "ok": True, "folder": str(folder),
            "added": [], "skipped": [], "errors": [],
            "message": "Carpeta vacía o no existe",
        }

    existing = client.get_sound_list()
    existing_names = {s["title"].lower() for s in existing}

    added, skipped, errors = [], [], []
    for f in files:
        name = f.stem.lower()
        if name in existing_names:
            skipped.append(f.name)
            continue
        try:
            client.add_sound(str(f.resolve()))
            added.append(f.name)
        except SoundpadError as exc:
            errors.append({"file": f.name, "error": str(exc)})

    log.info("Import: %d añadidos, %d ya existían, %d errores",
             len(added), len(skipped), len(errors))
    return {
        "ok": True,
        "folder": str(folder),
        "added": added,
        "skipped": skipped,
        "errors": errors,
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s: %(message)s")
    folder = sys.argv[1] if len(sys.argv) > 1 else None
    result = import_folder(folder)
    if not result["ok"]:
        print(f"Error: {result.get('error')}")
        return 1
    print(f"Carpeta: {result['folder']}")
    print(f"Añadidos ({len(result['added'])}):")
    for a in result["added"]:
        print(f"  + {a}")
    print(f"Ya estaban ({len(result['skipped'])}):")
    for s in result["skipped"]:
        print(f"  = {s}")
    if result["errors"]:
        print(f"Errores ({len(result['errors'])}):")
        for e in result["errors"]:
            print(f"  ! {e['file']}: {e['error']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
