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
    import apple_music
    APPLE_OK = True
except Exception:
    APPLE_OK = False

try:
    import tidal
    TIDAL_OK = True
except Exception:
    TIDAL_OK = False

try:
    import youtube_music
    YT_OK = True
except Exception:
    YT_OK = False

try:
    import local_files
    LOCAL_OK = True
except Exception:
    LOCAL_OK = False

import bpm_preview


def _enrich_bpm(tracks, artist_key="artist", name_key="name"):
    """Add BPM to tracks that have a preview_url; fall back to iTunes lookup."""
    for t in tracks:
        if t.get("bpm"):
            t["bpm"] = clamp_bpm(t["bpm"])
            continue
        preview = t.get("preview_url", "")
        if preview:
            bpm = bpm_preview.bpm_from_url(preview)
        else:
            bpm = bpm_preview.find_preview_and_bpm(t.get(artist_key, ""), t.get(name_key, ""))
        t["bpm"] = clamp_bpm(bpm) if bpm else None
        if t.get("duration_ms"):
            t["duration"] = format_duration(t["duration_ms"])
    return tracks


def handle(req):
    action = req.get("action")

    # ── detect ────────────────────────────────────────────────────────────────
    if action == "detect":
        return {"services": detect_streaming_apps()}

    # ── Spotify ───────────────────────────────────────────────────────────────
    if action == "spotify_search":
        tracks = spotify.search_tracks(req["query"])
        for t in tracks:
            feat = spotify.get_audio_features(t["id"])
            t["bpm"] = clamp_bpm(feat["bpm"])
            t["duration"] = format_duration(t["duration_ms"])
        return {"tracks": tracks}

    if action == "spotify_playlists":
        return {"playlists": spotify.get_playlists()}

    if action == "spotify_playlist_tracks":
        tracks = spotify.get_playlist_tracks(req["playlist_id"])
        for t in tracks:
            feat = spotify.get_audio_features(t["id"])
            t["bpm"] = clamp_bpm(feat["bpm"])
            t["duration"] = format_duration(t["duration_ms"])
        return {"tracks": tracks}

    if action == "spotify_play":
        import subprocess
        subprocess.Popen(["explorer", req["uri"]])
        return {"ok": True}

    # ── Deezer ────────────────────────────────────────────────────────────────
    if action == "deezer_search":
        tracks = deezer.search_tracks(req["query"])
        for t in tracks:
            if not t.get("bpm"):
                t["bpm"] = None
            t["duration"] = format_duration(t["duration_ms"])
        return {"tracks": tracks}

    # ── Apple Music ───────────────────────────────────────────────────────────
    if action == "apple_music_search":
        if not APPLE_OK:
            return {"error": "apple_music module unavailable"}
        tracks = apple_music.search_tracks(req["query"])
        for t in tracks:
            t["duration"] = format_duration(t.get("duration_ms", 0))
            # BPM via preview URL (fast for iTunes — preview is already in the response)
            if t.get("preview_url"):
                t["bpm"] = clamp_bpm(bpm_preview.bpm_from_url(t["preview_url"]))
            else:
                t["bpm"] = None
        return {"tracks": tracks}

    # ── Tidal ─────────────────────────────────────────────────────────────────
    if action == "tidal_search":
        if not TIDAL_OK:
            return {"error": "tidalapi not installed"}
        tracks = tidal.search_tracks(req["query"])
        for t in tracks:
            t["duration"] = format_duration(t.get("duration_ms", 0))
            bpm = None
            if t.get("preview_url"):
                bpm = bpm_preview.bpm_from_url(t["preview_url"])
            if not bpm:
                bpm = bpm_preview.find_preview_and_bpm(t.get("artist", ""), t.get("name", ""))
            t["bpm"] = clamp_bpm(bpm) if bpm else None
        return {"tracks": tracks}

    if action == "tidal_playlists":
        if not TIDAL_OK:
            return {"error": "tidalapi not installed"}
        return {"playlists": tidal.get_playlists()}

    if action == "tidal_playlist_tracks":
        if not TIDAL_OK:
            return {"error": "tidalapi not installed"}
        tracks = tidal.get_playlist_tracks(req["playlist_id"])
        for t in tracks:
            t["duration"] = format_duration(t.get("duration_ms", 0))
            bpm = bpm_preview.find_preview_and_bpm(t.get("artist", ""), t.get("name", ""))
            t["bpm"] = clamp_bpm(bpm) if bpm else None
        return {"tracks": tracks}

    # ── YouTube Music ─────────────────────────────────────────────────────────
    if action == "youtube_music_search":
        if not YT_OK:
            return {"error": "ytmusicapi not installed"}
        tracks = youtube_music.search_tracks(req["query"])
        for t in tracks:
            t["duration"] = format_duration(t.get("duration_ms", 0))
            bpm = bpm_preview.find_preview_and_bpm(t.get("artist", ""), t.get("name", ""))
            t["bpm"] = clamp_bpm(bpm) if bpm else None
        return {"tracks": tracks}

    # ── Amazon Music ──────────────────────────────────────────────────────────
    if action == "amazon_music_search":
        return {
            "error": "Amazon Music nao tem API publica. Use a Biblioteca Manual para adicionar suas musicas.",
            "tracks": [],
        }

    # ── Local files ───────────────────────────────────────────────────────────
    if action == "local_scan":
        tracks = local_files.scan_folder(req["folder"])
        return {"tracks": tracks}

    if action == "local_bpm":
        bpm = local_files.detect_bpm(req["path"])
        return {"bpm": clamp_bpm(bpm) if bpm else None}

    # ── BPM from preview URL (on-demand, e.g. Deezer/YTM) ────────────────────
    if action == "bpm_from_preview":
        url = req.get("url", "")
        artist = req.get("artist", "")
        name = req.get("name", "")
        bpm = bpm_preview.bpm_from_url(url) if url else None
        if not bpm and (artist or name):
            bpm = bpm_preview.find_preview_and_bpm(artist, name)
        return {"bpm": clamp_bpm(bpm) if bpm else None}

    return {"error": f"unknown action: {action}"}


if __name__ == "__main__":
    print("DiscoFlow backend running...")
    print(f"IPC path: {ipc._BASE}")
    ipc.write_state({"status": "ready", "services": detect_streaming_apps()})
    ipc.poll(handle)
