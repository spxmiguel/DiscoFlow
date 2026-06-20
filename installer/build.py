"""
Build script — run from the repo root:

    python installer/build.py

Produces: dist/DiscoFlowInstaller.exe

Steps:
  1. Build backend/main.py → dist/discoflow-backend/discoflow-backend.exe
  2. Build installer/install.py → dist/DiscoFlowInstaller.exe
     (bundles backend.exe + mod/ as embedded assets)
"""

import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(*args):
    print(f"\n$ {' '.join(args)}\n")
    subprocess.run(args, check=True, cwd=ROOT)


def main():
    pip = [sys.executable, "-m", "pip"]
    pyinstaller = [sys.executable, "-m", "PyInstaller"]

    print("=== DiscoFlow build ===\n")

    print("Step 1 — Installing build dependencies...")
    run(*pip, "install", "--quiet", "pyinstaller", "psutil", "librosa")

    print("\nStep 2 — Building backend executable...")
    run(
        *pyinstaller,
        "--onefile",
        "--name", "discoflow-backend",
        "--distpath", "dist/discoflow-backend",
        "--workpath", "build/backend",
        "--specpath", "build",
        "--noconsole",
        "backend/main.py",
    )

    print("\nStep 3 — Building installer executable...")
    spec = os.path.join(ROOT, "installer", "DiscoFlow.spec")
    run(
        *pyinstaller,
        "--clean",
        "--distpath", "dist",
        "--workpath", "build/installer",
        spec,
    )

    out = os.path.join(ROOT, "dist", "DiscoFlowInstaller.exe")
    if os.path.exists(out):
        size_mb = os.path.getsize(out) / 1024 / 1024
        print(f"\nDone → {out}  ({size_mb:.1f} MB)")
    else:
        print("\nBuild may have failed — check output above.")


if __name__ == "__main__":
    main()
