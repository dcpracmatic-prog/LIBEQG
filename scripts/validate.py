#!/usr/bin/env python3
"""Bootstrap and run LIBEQG tests with one command: python scripts/validate.py.

Creates a project-local .venv, installs package/test/Aer dependencies, then attempts
CUDA-Q. It never installs D-Wave or connects to a remote service. A missing or
unsupported CUDA-Q install is reported as BLOCKED and makes the validation exit nonzero.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
MARKER = "LIBEQG_PROJECT_VENV"


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def run(command: list[str], *, cwd: Path = ROOT, check: bool = False) -> int:
    print("\n+", " ".join(str(part) for part in command), flush=True)
    result = subprocess.run(command, cwd=cwd)
    if check and result.returncode:
        raise SystemExit(result.returncode)
    return result.returncode


def main() -> int:
    if os.environ.get(MARKER) != "1":
        if not venv_python().exists():
            print(f"Creando entorno aislado: {VENV}")
            venv.EnvBuilder(with_pip=True).create(VENV)
        env = os.environ.copy()
        env[MARKER] = "1"
        return subprocess.run([str(venv_python()), str(Path(__file__).resolve())], cwd=ROOT, env=env).returncode

    python = str(venv_python())
    # First install package, test tools, and Aer. This must succeed for meaningful validation.
    run([python, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    run([python, "-m", "pip", "install", "-e", ".[test,phase-c-aer]"], check=True)

    # CUDA-Q is platform/Python-version dependent. Try it separately so its failure does
    # not prevent the ordinary suite and Aer tests from running; validation will report BLOCKED.
    cuda_install = run([python, "-m", "pip", "install", "cuda-quantum"])
    if cuda_install:
        print(
            "\nAVISO: no se pudo instalar CUDA-Q en este entorno. "
            "Se ejecutará la suite y el informe lo marcará BLOCKED; el resultado global no aprobará."
        )

    tests_rc = run([python, "-m", "pytest", "-v"])
    if tests_rc:
        print(f"Falló pytest con código {tests_rc}.")
        return tests_rc

    validation_rc = run([
        python, "-m", "libeqg", "validate", "--cpu",
        "--report", "reports/phase-c-cpu-validation.json",
    ])
    print("\nInforme esperado: reports/phase-c-cpu-validation.json")
    return validation_rc


if __name__ == "__main__":
    raise SystemExit(main())
