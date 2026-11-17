"""Lanzar aplicaciones o ejecutar scripts en el PC."""
from __future__ import annotations

import shlex
import subprocess
import sys


def launch_app(params: dict) -> dict:
    path = params.get("path")
    if not path:
        raise ValueError("launch_app requires 'path'")
    args = params.get("args") or []
    if isinstance(args, str):
        args = shlex.split(args)
    cwd = params.get("cwd") or None
    subprocess.Popen([path, *args], cwd=cwd, shell=False)
    return {"launched": path}


def run_script(params: dict) -> dict:
    path = params.get("path")
    if not path:
        raise ValueError("run_script requires 'path'")
    args = params.get("args") or []
    if isinstance(args, str):
        args = shlex.split(args)
    cwd = params.get("cwd") or None

    lower = str(path).lower()
    if not sys.platform.startswith("win") and lower.endswith(".sh"):
        subprocess.Popen(["bash", path, *args], cwd=cwd, shell=False)
    elif lower.endswith(".py"):
        subprocess.Popen([sys.executable, path, *args], cwd=cwd, shell=False)
    elif args:
        subprocess.Popen([path, *args], cwd=cwd, shell=False)
    else:
        shell = bool(params.get("shell", True))
        subprocess.Popen(path, cwd=cwd, shell=shell)
    return {"ran": path}
