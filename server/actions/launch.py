"""Lanzar aplicaciones o ejecutar scripts en el PC."""
from __future__ import annotations

import shlex
import subprocess


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
    shell = bool(params.get("shell", True))
    subprocess.Popen(path, shell=shell)
    return {"ran": path}
