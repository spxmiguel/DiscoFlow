"""
DiscoFlow — plug-and-play installer.

Steps (all automatic):
  1. Find Dead as Disco via Steam registry
  2. Download latest UE4SS from GitHub releases
  3. Extract UE4SS into game's Binaries/Win64
  4. Install DiscoFlow mod into UE4SS Mods folder
  5. Install backend to %LOCALAPPDATA%\DiscoFlow
  6. Add backend to Windows Startup
"""

import os
import sys
import io
import json
import shutil
import zipfile
import threading
import urllib.request
import winreg
import tkinter as tk
from tkinter import ttk, messagebox


# ── asset resolution ──────────────────────────────────────────────────────────

def _asset(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "assets", rel)


# ── Steam / game detection ────────────────────────────────────────────────────

def find_steam_root():
    for hive, key_path in [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"),
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Valve\Steam"),
    ]:
        try:
            key = winreg.OpenKey(hive, key_path)
            val, _ = winreg.QueryValueEx(key, "InstallPath")
            return val
        except Exception:
            pass
    return None


def find_all_steam_libraries(steam_root):
    """Return all Steam library paths, including secondary ones."""
    libraries = [os.path.join(steam_root, "steamapps")]
    vdf = os.path.join(steam_root, "steamapps", "libraryfolders.vdf")
    if not os.path.exists(vdf):
        return libraries
    with open(vdf, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if '"path"' in line.lower():
                parts = line.split('"')
                if len(parts) >= 4:
                    p = parts[3].replace("\\\\", "\\")
                    lib = os.path.join(p, "steamapps")
                    if os.path.exists(lib):
                        libraries.append(lib)
    return libraries


def find_game_path():
    steam_root = find_steam_root()
    if not steam_root:
        return None
    for lib in find_all_steam_libraries(steam_root):
        candidate = os.path.join(lib, "common", "Dead as Disco")
        if os.path.exists(candidate):
            return candidate
    return None


def find_game_exe(game_path):
    for root, _, files in os.walk(game_path):
        for f in files:
            if f.lower().endswith(".exe") and "uninstall" not in f.lower():
                return root
    return None


# ── UE4SS download ────────────────────────────────────────────────────────────

UE4SS_API = "https://api.github.com/repos/UE4SS-RE/RE-UE4SS/releases/latest"


def fetch_ue4ss_download_url():
    req = urllib.request.Request(UE4SS_API,
                                 headers={"User-Agent": "DiscoFlow-Installer"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())

    assets = data.get("assets", [])
    # prefer the main zip (not debug symbols, not source)
    for asset in assets:
        name = asset["name"].lower()
        if name.endswith(".zip") and "debug" not in name and "source" not in name:
            return asset["browser_download_url"], data["tag_name"]

    raise RuntimeError("Could not find a UE4SS zip in the latest release assets.")


def download_bytes(url, progress_cb=None):
    req = urllib.request.Request(url, headers={"User-Agent": "DiscoFlow-Installer"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        buf = io.BytesIO()
        downloaded = 0
        chunk = 65536
        while True:
            data = resp.read(chunk)
            if not data:
                break
            buf.write(data)
            downloaded += len(data)
            if progress_cb and total:
                progress_cb(downloaded / total)
    buf.seek(0)
    return buf


def install_ue4ss(binaries_dir, progress_cb=None):
    url, tag = fetch_ue4ss_download_url()
    buf = download_bytes(url, progress_cb)
    with zipfile.ZipFile(buf) as zf:
        zf.extractall(binaries_dir)
    return tag


# ── DiscoFlow mod + backend ───────────────────────────────────────────────────

def install_mod(binaries_dir):
    dest = os.path.join(binaries_dir, "Mods", "DiscoFlow")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(_asset("mod"), dest)


def install_backend():
    dest = os.path.join(os.getenv("LOCALAPPDATA"), "DiscoFlow")
    os.makedirs(dest, exist_ok=True)

    backend_src = _asset("backend.exe")
    backend_dst = os.path.join(dest, "discoflow-backend.exe")
    shutil.copy2(backend_src, backend_dst)

    startup = os.path.join(
        os.getenv("APPDATA"),
        "Microsoft", "Windows", "Start Menu", "Programs", "Startup",
    )
    with open(os.path.join(startup, "DiscoFlow.bat"), "w") as f:
        f.write(f'@echo off\nstart /min "" "{backend_dst}"\n')

    # start the backend right now so the user doesn't need to reboot
    import subprocess
    subprocess.Popen([backend_dst], creationflags=subprocess.CREATE_NO_WINDOW)


# ── UI ────────────────────────────────────────────────────────────────────────

STEPS = [
    "Locating Dead as Disco...",
    "Downloading UE4SS...",
    "Installing UE4SS...",
    "Installing DiscoFlow mod...",
    "Installing backend...",
    "Done!",
]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DiscoFlow")
        self.resizable(False, False)
        self.configure(bg="#0f0f0f")
        self._center(480, 320)
        self._build()

    def _center(self, w, h):
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build(self):
        PAD = {"padx": 28, "pady": 0}

        tk.Label(self, text="DiscoFlow", font=("Segoe UI", 22, "bold"),
                 fg="#e8d5ff", bg="#0f0f0f").pack(pady=(28, 4))
        tk.Label(self, text="Dead as Disco · Music Integration Mod",
                 font=("Segoe UI", 10), fg="#666", bg="#0f0f0f").pack()

        tk.Frame(self, height=1, bg="#2a2a2a").pack(fill="x", pady=18, **PAD)

        self.status_var = tk.StringVar(value="Ready.")
        self.status = tk.Label(self, textvariable=self.status_var,
                               font=("Segoe UI", 10), fg="#ccc", bg="#0f0f0f",
                               wraplength=420, justify="left")
        self.status.pack(anchor="w", **PAD)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TProgressbar", troughcolor="#1e1e1e",
                        background="#a855f7", bordercolor="#0f0f0f",
                        lightcolor="#a855f7", darkcolor="#a855f7")

        self.progress = ttk.Progressbar(self, length=424, maximum=100,
                                        mode="determinate")
        self.progress.pack(pady=(10, 0), **PAD)

        self.sub_progress = ttk.Progressbar(self, length=424, maximum=100,
                                            mode="determinate")
        self.sub_progress.pack(pady=(4, 0), **PAD)
        self.sub_progress.pack_forget()  # hidden until UE4SS download

        self.btn = tk.Button(
            self, text="Install", font=("Segoe UI", 11, "bold"),
            bg="#7c3aed", fg="white", activebackground="#6d28d9",
            activeforeground="white", bd=0, padx=20, pady=8,
            cursor="hand2", command=self._start,
        )
        self.btn.pack(pady=(24, 0))

    def _set(self, msg, pct):
        self.status_var.set(msg)
        self.progress["value"] = pct
        self.update_idletasks()

    def _start(self):
        self.btn.configure(state="disabled")
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            # Step 1 — find game
            self._set(STEPS[0], 5)
            game_path = find_game_path()
            if not game_path:
                raise RuntimeError(
                    "Dead as Disco was not found.\n\n"
                    "Make sure the game is installed on Steam and that Steam "
                    "has launched at least once."
                )

            binaries_dir = find_game_exe(game_path)
            if not binaries_dir:
                raise RuntimeError(
                    f"Could not locate the game executable inside:\n{game_path}"
                )

            # Step 2 — download UE4SS
            self._set(STEPS[1], 20)
            self.sub_progress.pack(pady=(4, 0), padx=28)

            def dl_progress(fraction):
                self.sub_progress["value"] = fraction * 100
                self.update_idletasks()

            tag = install_ue4ss(binaries_dir, dl_progress)

            self.sub_progress.pack_forget()

            # Step 3 (extract happened inside install_ue4ss)
            self._set(f"UE4SS {tag} installed.", 55)

            # Step 4 — DiscoFlow mod
            self._set(STEPS[3], 70)
            install_mod(binaries_dir)

            # Step 5 — backend
            self._set(STEPS[4], 85)
            install_backend()

            # Done
            self._set(STEPS[5], 100)
            self.status.configure(fg="#a855f7")
            self.btn.configure(
                state="normal", text="Close", bg="#1e1e1e",
                activebackground="#2a2a2a", command=self.destroy,
            )
            messagebox.showinfo(
                "DiscoFlow",
                "All done!\n\nLaunch Dead as Disco and press F6 in Free Play.",
            )

        except Exception as e:
            self.status_var.set(f"Error: {e}")
            self.status.configure(fg="#f87171")
            self.sub_progress.pack_forget()
            messagebox.showerror("DiscoFlow — Installation failed", str(e))
            self.btn.configure(state="normal")


if __name__ == "__main__":
    App().mainloop()
