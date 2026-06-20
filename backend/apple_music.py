"""
Apple Music via iTunes Search API — free, no auth required.
BPM is detected from the 30-second preview URLs using librosa.
"""

import json
import urllib.parse
import urllib.request


def _itunes_search(query, limit=20):
    url = (
        "https://itunes.apple.com/search?"
        + urllib.parse.urlencode({"term": query, "media": "music", "limit": limit})
    )
    with urllib.request.urlopen(url, timeout=8) as resp:
        return json.loads(resp.read()).get("results", [])


def search_tracks(query, limit=20):
    results = _itunes_search(query, limit)
    return [_format(t) for t in results if t.get("wrapperType") == "track"]


def _format(t):
    return {
        "id": str(t.get("trackId", "")),
        "name": t.get("trackName", ""),
        "artist": t.get("artistName", ""),
        "duration_ms": t.get("trackTimeMillis", 0),
        "preview_url": t.get("previewUrl", ""),
        "uri": t.get("trackViewUrl", ""),
        "bpm": None,
    }
