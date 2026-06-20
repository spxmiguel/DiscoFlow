"""
DiscoFlow installer — bundled as a standalone .exe via PyInstaller.

Bundled assets (via spec datas):
  - assets/mod/          → UE4SS mod files
  - assets/backend.exe   → compiled backend (also PyInstaller)
"""

import os
import sys
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import winreg


# ── asset resolution ──────────────────────────────────────────────────────────

def _asset(rel):
    """Resolve bundled asset path (works both frozen and in dev)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "assets", rel)


# ── game detection ────────────────────────────────────────────────────────────

STEAM_REGISTRY_KEYS = [
    r"SOFTWARE\WOW6432Node\Valve\Steam",
    r"SOFTWARE\Valve\Steam",
]

def find_steam_root():
    for key_path in STEAM_REGISTRY_KEYS:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
            val, _ = winreg.QueryValueEx(key, "InstallPath")
            return val
        except Exception:
            pass
    return None

def find_game_path():
    steam_root = find_steam_root()
    if not steam_root:
        return None
    candidate = os.path.join(steam_root, "steamapps", "common", "Dead as Disco")
    return candidate if os.path.exists(candidate) else None

def find_ue4ss_dir(game_path):
    for root, _, files in os.walk(game_path):
        if "ue4ss.dll" in [f.lower() for f in files]:
            return root
    return None


# ── installation steps ────────────────────────────────────────────────────────

def install_mod(ue4ss_dir, log):
    dest = os.path.join(ue4ss_dir, "Mods", "DiscoFlow")
    log(f"Installing mod → {dest}")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(_asset("mod"), dest)

def install_backend(log):
    dest = os.path.join(os.getenv("LOCALAPPDATA"), "DiscoFlow")
    os.makedirs(dest, exist_ok=True)

    backend_src = _asset("backend.exe")
    backend_dst = os.path.join(dest, "discoflow-backend.exe")
    log(f"Installing backend → {backend_dst}")
    shutil.copy2(backend_src, backend_dst)

    # Windows Startup shortcut (.bat that launches the backend)
    startup = os.path.join(
        os.getenv("APPDATA"),
        "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
    )
    bat = os.path.join(startup, "DiscoFlow.bat")
    log("Adding to Windows Startup...")
    with open(bat, "w") as f:
        f.write(f'@echo off\nstart /min "" "{backend_dst}"\n')


# ── UI ────────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DiscoFlow Installer")
        self.resizable(False, False)
        self.configure(bg="#0f0f0f")
        self._center(500, 340)
        self._build()

    def _center(self, w, h):
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _build(self):
        PAD = {"padx": 28, "pady": 0}

        tk.Label(self, text="DiscoFlow", font=("Segoe UI", 22, "bold"),
                 fg="#e8d5ff", bg="#0f0f0f").pack(pady=(32, 4))
        tk.Label(self, text="Dead as Disco · Music Integration Mod",
                 font=("Segoe UI", 10), fg="#888", bg="#0f0f0f").pack()

        tk.Frame(self, height=1, bg="#2a2a2a").pack(fill="x", pady=20, **PAD)

        self.status = tk.Label(self, text="Ready to install.", font=("Segoe UI", 10),
                               fg="#ccc", bg="#0f0f0f", wraplength=440, justify="left")
        self.status.pack(anchor="w", **PAD)

        self.progress = ttk.Progressbar(self, length=444, mode="determinate")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TProgressbar", troughcolor="#1e1e1e",
                        background="#a855f7", bordercolor="#0f0f0f")
        self.progress.pack(pady=(10, 0), **PAD)

        self.log_box = tk.Text(self, height=5, bg="#1a1a1a", fg="#666",
                               font=("Consolas", 8), bd=0, state="disabled",
                               wrap="word", relief="flat")
        self.log_box.pack(fill="x", pady=(10, 0), **PAD)

        self.btn = tk.Button(self, text="Install", font=("Segoe UI", 11, "bold"),
                             bg="#7c3aed", fg="white", activebackground="#6d28d9",
                             activeforeground="white", bd=0, padx=20, pady=8,
                             cursor="hand2", command=self._start)
        self.btn.pack(pady=(20, 0))

    def _log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        self.status.configure(text=msg)
        self.update_idletasks()

    def _set_progress(self, val):
        self.progress["value"] = val
        self.update_idletasks()

    def _start(self):
        self.btn.configure(state="disabled")
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            self._log("Looking for Dead as Disco...")
            self._set_progress(10)

            game_path = find_game_path()
            if not game_path:
                raise RuntimeError(
                    "Dead as Disco not found via Steam.\n"
                    "Make sure the game is installed and Steam has run at least once."
                )

            self._log(f"Found: {game_path}")
            self._set_progress(25)

            self._log("Looking for UE4SS...")
            ue4ss_dir = find_ue4ss_dir(game_path)
            if not ue4ss_dir:
                raise RuntimeError(
                    "UE4SS not found in the game folder.\n\n"
                    "Download it from:\n"
                    "https://github.com/UE4SS-RE/RE-UE4SS/releases\n\n"
                    "Extract it into:\n"
                    "Dead as Disco/Binaries/Win64/\n\n"
                    "Then run this installer again."
                )

            self._set_progress(45)
            install_mod(ue4ss_dir, self._log)
            self._set_progress(70)
            install_backend(self._log)
            self._set_progress(100)

            self.status.configure(text="Installation complete!", fg="#a855f7")
            self._log("Done.")
            messagebox.showinfo(
                "DiscoFlow",
                "Installation complete!\n\nLaunch Dead as Disco and press F6 in Free Play."
            )
            self.btn.configure(state="normal", text="Close", command=self.destroy)

        except Exception as e:
            self.status.configure(text="Installation failed.", fg="#f87171")
            self._log(f"Error: {e}")
            messagebox.showerror("DiscoFlow", str(e))
            self.btn.configure(state="normal")


if __name__ == "__main__":
    App().mainloop()
