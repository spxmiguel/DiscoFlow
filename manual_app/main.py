"""
DiscoFlow — Biblioteca Manual
Standalone desktop app for managing a local music library for Dead as Disco.
Saves to %LOCALAPPDATA%\DiscoFlow\library.json, picked up automatically in-game.
"""

import os, sys, json, hashlib, threading, queue, time
from pathlib import Path
from tkinter import ttk, filedialog, messagebox
import tkinter as tk

# ── paths ─────────────────────────────────────────────────────────────────────
LOCALAPPDATA = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
BASE = Path(LOCALAPPDATA) / "DiscoFlow"
LIBRARY_FILE = BASE / "library.json"
SUPPORTED_EXT = {".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a"}

# ── colours (dark theme) ──────────────────────────────────────────────────────
BG       = "#121212"
BG2      = "#1e1e1e"
BG3      = "#2a2a2a"
ACCENT   = "#1db954"   # Spotify green — matches the vibe
FG       = "#e0e0e0"
FG2      = "#888888"
SEL_BG   = "#1db95440"

# ── BPM helpers ───────────────────────────────────────────────────────────────
def clamp_bpm(bpm):
    if not bpm or bpm <= 0:
        return None
    while bpm < 80:
        bpm *= 2
    while bpm > 200:
        bpm /= 2
    return round(bpm)


def format_duration(ms):
    if not ms:
        return ""
    s = int(ms) // 1000
    return f"{s // 60}:{s % 60:02d}"


def track_id(path):
    return hashlib.md5(str(path).encode()).hexdigest()[:12]


# ── metadata reading ──────────────────────────────────────────────────────────
def read_metadata(path):
    title = Path(path).stem
    artist = "Desconhecido"
    duration_ms = 0
    try:
        from mutagen import File as AudioFile
        audio = AudioFile(path, easy=True)
        if audio:
            title = str(audio.get("title", [title])[0])
            artist = str(audio.get("artist", [artist])[0])
            if hasattr(audio, "info") and audio.info:
                duration_ms = int(audio.info.length * 1000)
    except Exception:
        pass
    return {"title": title, "artist": artist, "duration_ms": duration_ms}


# ── BPM detection (background) ───────────────────────────────────────────────
def detect_bpm(path):
    try:
        import librosa
        y, sr = librosa.load(path, sr=None, mono=True, duration=60)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        return clamp_bpm(float(tempo))
    except Exception:
        return None


# ── library I/O ──────────────────────────────────────────────────────────────
def load_library():
    try:
        if LIBRARY_FILE.exists():
            return json.loads(LIBRARY_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"version": 1, "tracks": []}


def save_library(tracks):
    BASE.mkdir(parents=True, exist_ok=True)
    data = {"version": 1, "tracks": tracks}
    LIBRARY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── main app ──────────────────────────────────────────────────────────────────
class DiscoFlowApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DiscoFlow — Biblioteca Manual")
        self.geometry("760x520")
        self.minsize(640, 400)
        self.configure(bg=BG)

        # try to set an icon
        try:
            from PIL import Image, ImageTk, ImageDraw
            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.ellipse([4, 4, 60, 60], fill=ACCENT)
            d.text((20, 18), "DF", fill="white")
            self._icon_img = ImageTk.PhotoImage(img)
            self.iconphoto(True, self._icon_img)
        except Exception:
            pass

        self._tracks = []          # list of dicts (the library)
        self._bpm_queue = queue.Queue()   # (track_id, bpm) results
        self._bpm_pending = set()         # ids currently being detected

        self._build_ui()
        self._load()
        self._poll_bpm()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # ── toolbar ──
        toolbar = tk.Frame(self, bg=BG, pady=8, padx=12)
        toolbar.pack(fill="x")

        btn_kw = dict(bg=BG3, fg=FG, activebackground=ACCENT, activeforeground="white",
                      relief="flat", padx=10, pady=5, cursor="hand2", bd=0)

        tk.Button(toolbar, text="+ Arquivo", command=self._add_files, **btn_kw).pack(side="left", padx=4)
        tk.Button(toolbar, text="+ Pasta",   command=self._add_folder, **btn_kw).pack(side="left", padx=4)
        tk.Button(toolbar, text="✕ Remover", command=self._remove_selected, **btn_kw).pack(side="left", padx=4)
        tk.Button(toolbar, text="⟳ Detectar BPM de todos",
                  command=self._detect_all_bpm, **btn_kw).pack(side="left", padx=4)

        tk.Frame(toolbar, bg=BG).pack(side="left", expand=True)

        # ── table ──
        frame = tk.Frame(self, bg=BG, padx=12)
        frame.pack(fill="both", expand=True)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("DF.Treeview",
            background=BG2, foreground=FG,
            rowheight=26, fieldbackground=BG2,
            bordercolor=BG3, relief="flat")
        style.configure("DF.Treeview.Heading",
            background=BG3, foreground=FG2,
            relief="flat", borderwidth=0)
        style.map("DF.Treeview",
            background=[("selected", "#1db95450")],
            foreground=[("selected", "#ffffff")])

        cols = ("title", "artist", "bpm", "duration")
        self._tree = ttk.Treeview(frame, columns=cols, show="headings",
                                   style="DF.Treeview", selectmode="extended")

        self._tree.heading("title",    text="Título")
        self._tree.heading("artist",   text="Artista")
        self._tree.heading("bpm",      text="BPM")
        self._tree.heading("duration", text="Duração")

        self._tree.column("title",    width=300, stretch=True)
        self._tree.column("artist",   width=180, stretch=True)
        self._tree.column("bpm",      width=70,  stretch=False, anchor="center")
        self._tree.column("duration", width=70,  stretch=False, anchor="center")

        sb = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)

        sb.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True)

        # ── status bar ──
        self._status_var = tk.StringVar(value="Pronto")
        status_bar = tk.Frame(self, bg=BG3, pady=4, padx=12)
        status_bar.pack(fill="x", side="bottom")
        tk.Label(status_bar, textvariable=self._status_var,
                 bg=BG3, fg=FG2, anchor="w").pack(side="left")
        self._sync_var = tk.StringVar(value="")
        tk.Label(status_bar, textvariable=self._sync_var,
                 bg=BG3, fg=ACCENT, anchor="e").pack(side="right")

    # ── data operations ───────────────────────────────────────────────────────

    def _load(self):
        lib = load_library()
        self._tracks = lib.get("tracks", [])
        self._refresh_tree()
        self._set_status(f"{len(self._tracks)} faixa(s) na biblioteca")

    def _save(self):
        save_library(self._tracks)
        self._sync_var.set("✓ Sincronizado")

    def _refresh_tree(self):
        self._tree.delete(*self._tree.get_children())
        for t in self._tracks:
            bpm_str = str(t.get("bpm") or "…")
            dur_str = format_duration(t.get("duration_ms"))
            self._tree.insert("", "end", iid=t["id"],
                               values=(t.get("title","?"), t.get("artist","?"),
                                       bpm_str, dur_str))

    def _set_status(self, msg):
        self._status_var.set(msg)

    # ── file operations ───────────────────────────────────────────────────────

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Selecionar arquivos de áudio",
            filetypes=[("Áudio", "*.mp3 *.wav *.flac *.ogg *.aac *.m4a"), ("Todos", "*.*")])
        if paths:
            self._import_paths(list(paths))

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Selecionar pasta com músicas")
        if not folder:
            return
        paths = [str(p) for p in Path(folder).rglob("*")
                 if p.suffix.lower() in SUPPORTED_EXT]
        if not paths:
            messagebox.showinfo("Vazio", "Nenhum arquivo de áudio encontrado nesta pasta.")
            return
        self._import_paths(paths)

    def _import_paths(self, paths):
        existing_ids = {t["id"] for t in self._tracks}
        added = 0
        for path in paths:
            tid = track_id(path)
            if tid in existing_ids:
                continue
            meta = read_metadata(path)
            track = {
                "id": tid,
                "title": meta["title"],
                "artist": meta["artist"],
                "bpm": None,
                "duration_ms": meta["duration_ms"],
                "path": str(path),
            }
            self._tracks.append(track)
            existing_ids.add(tid)
            bpm_str = "…"
            self._tree.insert("", "end", iid=tid,
                               values=(track["title"], track["artist"],
                                       bpm_str, format_duration(track["duration_ms"])))
            self._queue_bpm(track)
            added += 1

        if added:
            self._save()
            self._set_status(f"{len(self._tracks)} faixa(s)  •  {added} adicionada(s)")
        self._sync_var.set("✓ Sincronizado")

    def _remove_selected(self):
        sel = self._tree.selection()
        if not sel:
            return
        ids = set(sel)
        self._tracks = [t for t in self._tracks if t["id"] not in ids]
        for iid in sel:
            self._tree.delete(iid)
        self._save()
        self._set_status(f"{len(self._tracks)} faixa(s) na biblioteca")

    # ── BPM detection ─────────────────────────────────────────────────────────

    def _queue_bpm(self, track):
        if track["id"] in self._bpm_pending:
            return
        self._bpm_pending.add(track["id"])
        threading.Thread(target=self._bpm_worker,
                         args=(track["id"], track["path"]),
                         daemon=True).start()

    def _detect_all_bpm(self):
        for t in self._tracks:
            if t.get("bpm") is None:
                self._queue_bpm(t)
        self._set_status("Detectando BPM em segundo plano…")

    def _bpm_worker(self, tid, path):
        bpm = detect_bpm(path)
        self._bpm_queue.put((tid, bpm))

    def _poll_bpm(self):
        updated = False
        try:
            while True:
                tid, bpm = self._bpm_queue.get_nowait()
                self._bpm_pending.discard(tid)
                for t in self._tracks:
                    if t["id"] == tid:
                        t["bpm"] = bpm
                        break
                if self._tree.exists(tid):
                    vals = self._tree.item(tid, "values")
                    self._tree.item(tid, values=(vals[0], vals[1],
                                                  str(bpm) if bpm else "?", vals[3]))
                updated = True
        except queue.Empty:
            pass
        if updated:
            self._save()
            pending = len(self._bpm_pending)
            if pending:
                self._set_status(f"Detectando BPM… {pending} restante(s)")
            else:
                self._set_status(f"{len(self._tracks)} faixa(s) — BPM completo")
        self.after(300, self._poll_bpm)

    # ── window lifecycle ──────────────────────────────────────────────────────

    def _on_close(self):
        if self._bpm_pending:
            if not messagebox.askyesno("Fechar",
                "BPM ainda sendo detectado. Fechar mesmo assim?"):
                return
        self.destroy()


def main():
    BASE.mkdir(parents=True, exist_ok=True)
    app = DiscoFlowApp()
    app.mainloop()


if __name__ == "__main__":
    main()
