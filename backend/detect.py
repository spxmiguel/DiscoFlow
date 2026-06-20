import os
import psutil

STREAMING_APPS = {
    "Spotify": {
        "exe": "Spotify.exe",
        "paths": [r"%APPDATA%\Spotify", r"%LOCALAPPDATA%\Spotify"],
    },
    "Apple Music": {
        "exe": "AppleMusic.exe",
        "paths": [r"%ProgramFiles%\iTunes", r"%LOCALAPPDATA%\Apple\Apple Music"],
    },
    "Tidal": {
        "exe": "TIDAL.exe",
        "paths": [r"%LOCALAPPDATA%\TIDAL"],
    },
    "Deezer": {
        "exe": "Deezer.exe",
        "paths": [r"%LOCALAPPDATA%\Deezer"],
    },
    "Amazon Music": {
        "exe": "Amazon Music.exe",
        "paths": [r"%LOCALAPPDATA%\Amazon Music"],
    },
}


def get_running_processes():
    try:
        return {p.name() for p in psutil.process_iter(["name"])}
    except Exception:
        return set()


def detect_streaming_apps():
    running = get_running_processes()
    found = []

    for name, info in STREAMING_APPS.items():
        exe_running = info["exe"] in running
        path_exists = any(
            os.path.exists(os.path.expandvars(p)) for p in info["paths"]
        )
        if exe_running or path_exists:
            found.append({"name": name, "running": exe_running})

    # YouTube Music works unauthenticated via ytmusicapi — always available
    found.append({"name": "YouTube Music", "running": True})
    found.append({"name": "Local Files", "running": True})
    return found
