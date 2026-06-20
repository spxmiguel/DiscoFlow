"""
Build script — run from the repo root:

    python installer/build.py

Produces: dist/DiscoFlowInstaller.exe

Steps:
  1. Build backend/main.py  → dist/discoflow-backend/discoflow-backend.exe
  2. Build installer/install.py → dist/DiscoFlowInstaller.exe
     (bundles discoflow-backend.exe + mod/ folder as embedded assets)
"""

import os
import sys
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(*args):
    print(f"\n$ {' '.join(str(a) for a in args)}\n")
    subprocess.run(args, check=True, cwd=ROOT)


def sep(s):
    """os.pathsep-joined data tuple for PyInstaller --add-data / --add-binary."""
    return s


def main():
    pip = [sys.executable, "-m", "pip"]
    pyi = [sys.executable, "-m", "PyInstaller"]

    print("=== DiscoFlow build ===\n")

    print("Step 1 — Installing build dependencies...")
    run(*pip, "install", "--quiet", "pyinstaller", "psutil", "librosa")

    # ── Step 2: backend exe ────────────────────────────────────────────────────
    print("\nStep 2 — Building backend executable...")
    backend_dist = os.path.join(ROOT, "dist", "discoflow-backend")
    run(
        *pyi,
        "--onefile",
        "--name", "discoflow-backend",
        "--distpath", backend_dist,
        "--workpath", os.path.join(ROOT, "build", "backend"),
        "--specpath", os.path.join(ROOT, "build"),
        "--noconsole",
        os.path.join(ROOT, "backend", "main.py"),
    )

    backend_exe = os.path.join(backend_dist, "discoflow-backend.exe")
    if not os.path.exists(backend_exe):
        print(f"ERROR: backend exe not found at {backend_exe}")
        sys.exit(1)

    # ── Step 3: installer exe (bundles backend + mod) ─────────────────────────
    print("\nStep 3 — Building installer executable...")
    mod_src = os.path.join(ROOT, "mod")

    run(
        *pyi,
        "--onefile",
        "--name", "DiscoFlowInstaller",
        "--distpath", os.path.join(ROOT, "dist"),
        "--workpath", os.path.join(ROOT, "build", "installer"),
        "--specpath", os.path.join(ROOT, "build"),
        "--noconsole",
        "--windowed",
        # embed backend.exe → extracted to assets/ at runtime
        f"--add-binary={backend_exe}{os.pathsep}assets",
        # embed entire mod folder → extracted to assets/mod/ at runtime
        f"--add-data={mod_src}{os.pathsep}assets/mod",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=winreg",
        os.path.join(ROOT, "installer", "install.py"),
    )

    out = os.path.join(ROOT, "dist", "DiscoFlowInstaller.exe")
    if os.path.exists(out):
        size_mb = os.path.getsize(out) / 1024 / 1024
        print(f"\nDone → {out}  ({size_mb:.1f} MB)")
    else:
        print("\nBuild may have failed — check output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
