import json
import urllib.parse
import urllib.request


BASE = "https://api.deezer.com"


def _get(path):
    with urllib.request.urlopen(f"{BASE}{path}") as resp:
        return json.loads(resp.read())


def search_tracks(query, limit=20):
    encoded = urllib.parse.quote(query)
    data = _get(f"/search?q={encoded}&limit={limit}")
    return [_format_track(t) for t in data.get("data", [])]


def get_track(track_id):
    data = _get(f"/track/{track_id}")
    return _format_track(data)


def _format_track(t):
    return {
        "id": str(t["id"]),
        "name": t["title"],
        "artist": t.get("artist", {}).get("name", ""),
        "duration_ms": t.get("duration", 0) * 1000,
        "bpm": round(t.get("bpm", 0)) or None,
    }
