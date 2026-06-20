"""
DiscoFlow installer.

Finds the Dead as Disco installation, drops the UE4SS mod in the right place,
and installs the Python backend as a startup shortcut.
"""

import os
import sys
import shutil
import subprocess
import winreg

MOD_NAME = "DiscoFlow"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
MOD_SRC = os.path.join(ROOT_DIR, "mod")
BACKEND_SRC = os.path.join(ROOT_DIR, "backend")


def find_game_path():
    # Try Steam registry
    steam_paths = []
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")
        steam_root, _ = winreg.QueryValueEx(key, "InstallPath")
        steam_paths.append(os.path.join(steam_root, "steamapps", "common", "Dead as Disco"))
    except Exception:
        pass

    for p in steam_paths:
        if os.path.exists(p):
            return p

    return None


def find_ue4ss(game_path):
    # UE4SS lives next to the game .exe under Binaries/Win64
    candidates = []
    for root, dirs, files in os.walk(game_path):
        for f in files:
            if f.lower() == "ue4ss.dll":
                candidates.append(root)
    return candidates[0] if candidates else None


def install_mod(ue4ss_dir):
    mods_dir = os.path.join(ue4ss_dir, "Mods", MOD_NAME)
    if os.path.exists(mods_dir):
        shutil.rmtree(mods_dir)
    shutil.copytree(MOD_SRC, mods_dir)
    print(f"  Mod installed → {mods_dir}")


def install_backend():
    dest = os.path.join(os.getenv("LOCALAPPDATA"), "DiscoFlow", "backend")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(BACKEND_SRC, dest)

    # install Python deps
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r",
                           os.path.join(dest, "requirements.txt"), "--quiet"])

    # create startup batch file
    bat = os.path.join(dest, "start.bat")
    with open(bat, "w") as f:
        f.write(f'@echo off\nstart /min "" "{sys.executable}" "{os.path.join(dest, "main.py")}"\n')

    # add to Windows startup (current user)
    startup = os.path.join(os.getenv("APPDATA"),
                           "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
    shutil.copy(bat, os.path.join(startup, "DiscoFlow.bat"))
    print(f"  Backend installed → {dest}")
    print(f"  Auto-start configured in Windows Startup folder")


def main():
    print("DiscoFlow Installer\n")

    game_path = find_game_path()
    if not game_path:
        game_path = input("Could not find Dead as Disco automatically.\nEnter the game folder path: ").strip()

    if not os.path.exists(game_path):
        print(f"Path not found: {game_path}")
        sys.exit(1)

    print(f"Game found: {game_path}")

    ue4ss_dir = find_ue4ss(game_path)
    if not ue4ss_dir:
        print(
            "\nUE4SS not found in the game folder.\n"
            "Download it from https://github.com/UE4SS-RE/RE-UE4SS/releases\n"
            "and install it in the game's Binaries/Win64 folder, then re-run this installer."
        )
        sys.exit(1)

    print(f"UE4SS found: {ue4ss_dir}")
    print()

    print("Installing mod...")
    install_mod(ue4ss_dir)

    print("Installing backend...")
    install_backend()

    print("\nDone! Launch Dead as Disco and press F6 in the Free Play menu.")


if __name__ == "__main__":
    main()
