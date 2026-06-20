# DiscoFlow

Stream any music directly into Dead as Disco — no manual BPM entry, no file copying, no sync headaches.

DiscoFlow is a mod + backend that connects your streaming services (Spotify, Deezer, Tidal, Apple Music) and local library to Dead as Disco's Free Play mode. Pick a song, and the BPM is set automatically.

## How It Works

Dead as Disco requires a BPM value and a Beat Offset for every custom song. Getting these right is tedious — you have to look up the BPM, type it manually, calibrate the offset, and only then start playing.

DiscoFlow eliminates that. A lightweight Python backend talks to each streaming service's API, fetches the BPM for whichever track you choose, and passes it to an in-game overlay built with UE4SS. You pick the song from inside the game and everything is ready.

The overlay opens with **F6** in the Free Play screen.

## Features

- In-game overlay with search, playlist browsing, and song selection.
- Automatic BPM detection from Spotify and Deezer APIs.
- BPM auto-correction: doubles or halves values outside the 120–200 range Dead as Disco recommends.
- Local file scanner with BPM detection via librosa.
- Detects which streaming apps are installed and shows only those.
- One-time Beat Offset calibration per machine — works across all songs.
- BPM copied to clipboard as fallback if game injection fails.

## Supported Services

| Service | BPM source | Auth required |
|---|---|---|
| Spotify | `audio-features` API — exact BPM | OAuth (one-time browser login) |
| Deezer | Track API — BPM field | None |
| Tidal | Process detection + manual input | None |
| Apple Music | Process detection + manual input | None |
| Local Files | librosa audio analysis | None |

## Requirements

- Dead as Disco (Steam, Early Access)
- Windows 10 or later

No Python, no UE4SS, no manual steps — everything is bundled in the installer.

## Installation

Download `DiscoFlowInstaller.exe` from the [Releases](../../releases/latest) page and run it.

The installer automatically:
1. Locates Dead as Disco via the Steam registry (including secondary Steam libraries)
2. Downloads the latest UE4SS from GitHub and extracts it into the game folder
3. Installs the DiscoFlow mod into the UE4SS Mods folder
4. Installs the backend to `%LOCALAPPDATA%\DiscoFlow` and starts it immediately
5. Adds the backend to Windows Startup

**3. Spotify setup (optional)**

Create a free app at [developer.spotify.com](https://developer.spotify.com/dashboard) and set the redirect URI to `http://localhost:8765/callback`. Then set:

```
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
```

You can add these to your system environment variables or to a `.env` file next to `main.py`. On first use, a browser window will open for one-time authorization.

**4. Launch the game**

Open Dead as Disco, go to Free Play, and press **F6**. The DiscoFlow overlay appears.

## Usage

1. Press **F6** to open the overlay.
2. Select your streaming service from the list.
3. Search for a song or browse your playlists (Spotify).
4. Click a track — BPM is set and the song opens in your streaming app.
5. Start playing.

## Beat Offset

Beat Offset compensates for your hardware's audio latency and stays the same across songs. Calibrate it once using the game's Advanced Editor, save it, and DiscoFlow handles the rest.

If you need guidance: [Dead as Disco Beat Offset guide](https://gamerant.com/dead-as-disco-bpm-beat-offset-sync-fix/).

## Manual Backend Start

The backend starts automatically with Windows. To start it manually:

```
%LOCALAPPDATA%\DiscoFlow\backend\start.bat
```

Or in a terminal:

```
python %LOCALAPPDATA%\DiscoFlow\backend\main.py
```

## Building from Source

```bash
git clone https://github.com/spxmiguel/DiscoFlow
cd DiscoFlow
python installer/build.py
```

Output: `dist/DiscoFlowInstaller.exe`

To run the backend directly during development:

```bash
pip install -r backend/requirements.txt
python backend/main.py
```

The IPC files are written to `%LOCALAPPDATA%\DiscoFlow\`. The Lua mod reads `state.json` and `response.json` from the same folder.

## Project Structure

```
DiscoFlow/
├── backend/
│   ├── main.py          entry point, request router
│   ├── ipc.py           file-based IPC with the Lua mod
│   ├── detect.py        streaming app detection
│   ├── spotify.py       Spotify OAuth + Web API
│   ├── deezer.py        Deezer public API
│   ├── local_files.py   local file scanner + librosa BPM detection
│   ├── bpm.py           BPM clamping and formatting utilities
│   └── requirements.txt
├── mod/
│   └── Scripts/
│       ├── main.lua     UE4SS entry point, key bindings, BP hooks
│       ├── ui.lua       ImGui overlay — all screens and interactions
│       └── ipc.lua      file-based IPC client + minimal JSON codec
├── installer/
│   ├── install.py       tkinter GUI installer (bundled by PyInstaller)
│   ├── DiscoFlow.spec   PyInstaller spec — bundles mod + backend.exe
│   └── build.py         build script → dist/DiscoFlowInstaller.exe
└── README.md
```

## Tech Stack

- Python 3.11 (bundled — no install required)
- PyInstaller (single .exe packaging)
- UE4SS (Lua scripting + ImGui for Unreal Engine games)
- Spotify Web API
- Deezer Public API
- librosa (local BPM detection)
- psutil (process detection)
- GitHub Actions (automated .exe builds on release)

## Roadmap

- Tidal and Apple Music full API integration.
- In-game Beat Offset calibration assistant.
- Playlist sync: import a Spotify playlist as a Dead as Disco Free Play queue.
- Community song configs: share BPM + offset presets for popular songs.
- Auto-detect BPM from Spotify's real-time audio stream (experimental).

## Contributing

PRs are welcome. If you reverse-engineer a better hook point for the Free Play menu or find the exact UObject path for the BPM field in the current game version, open an issue or PR — that's the part most likely to break on game updates.

## License

MIT
