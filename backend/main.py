import sys
from detect import detect_streaming_apps
from bpm import clamp_bpm, format_duration
import ipc

try:
    import spotify
    SPOTIFY_OK = True
except Exception:
    SPOTIFY_OK = False

try:
    import deezer
    DEEZER_OK = True
except Exception:
    DEEZER_OK = False

try:
    import local_files
    LOCAL_OK = True
except Exception:
    LOCAL_OK = False


def handle(req):
    action = req.get("action")

    if action == "detect":
        return {"services": detect_streaming_apps()}

    if action == "spotify_search":
        tracks = spotify.search_tracks(req["query"])
        for t in tracks:
            features = spotify.get_audio_features(t["id"])
            t["bpm"] = clamp_bpm(features["bpm"])
            t["duration"] = format_duration(t["duration_ms"])
        return {"tracks": tracks}

    if action == "spotify_playlists":
        return {"playlists": spotify.get_playlists()}

    if action == "spotify_playlist_tracks":
        tracks = spotify.get_playlist_tracks(req["playlist_id"])
        for t in tracks:
            features = spotify.get_audio_features(t["id"])
            t["bpm"] = clamp_bpm(features["bpm"])
            t["duration"] = format_duration(t["duration_ms"])
        return {"tracks": tracks}

    if action == "spotify_play":
        import subprocess
        subprocess.Popen(["explorer", req["uri"]])
        return {"ok": True}

    if action == "deezer_search":
        tracks = deezer.search_tracks(req["query"])
        for t in tracks:
            if not t.get("bpm"):
                t["bpm"] = None
            t["duration"] = format_duration(t["duration_ms"])
        return {"tracks": tracks}

    if action == "local_scan":
        tracks = local_files.scan_folder(req["folder"])
        return {"tracks": tracks}

    if action == "local_bpm":
        bpm = local_files.detect_bpm(req["path"])
        return {"bpm": clamp_bpm(bpm) if bpm else None}

    return {"error": f"unknown action: {action}"}


if __name__ == "__main__":
    print("DiscoFlow backend running...")
    print(f"IPC path: {ipc._BASE}")
    ipc.write_state({"status": "ready", "services": detect_streaming_apps()})
    ipc.poll(handle)
