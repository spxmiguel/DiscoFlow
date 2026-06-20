"""
YouTube Music via ytmusicapi.
Works unauthenticated for search (public tracks).
BPM is detected via iTunes preview lookup (find the same song there).
"""

import json
import urllib.parse
import urllib.request


def _ytm():
    try:
        from ytmusicapi import YTMusic
        return YTMusic()
    except ImportError:
        raise RuntimeError("ytmusicapi not installed (pip install ytmusicapi)")


def search_tracks(query, limit=20):
    yt = _ytm()
    try:
        results = yt.search(query, filter="songs", limit=limit)
    except Exception:
        results = []
    return [_format(r) for r in (results or [])[:limit]]


def _format(r):
    artists = r.get("artists") or []
    artist = ", ".join(a.get("name", "") for a in artists) if artists else ""
    duration_str = r.get("duration", "0:00")
    duration_ms = _parse_duration(duration_str)
    vid_id = r.get("videoId", "")
    return {
        "id": vid_id,
        "name": r.get("title", ""),
        "artist": artist,
        "duration_ms": duration_ms,
        "preview_url": "",        # no direct preview; BPM will use iTunes fallback
        "uri": f"https://music.youtube.com/watch?v={vid_id}" if vid_id else "",
        "bpm": None,
    }


def _parse_duration(s):
    try:
        parts = [int(x) for x in str(s).split(":")]
        if len(parts) == 2:
            return (parts[0] * 60 + parts[1]) * 1000
        if len(parts) == 3:
            return (parts[0] * 3600 + parts[1] * 60 + parts[2]) * 1000
    except Exception:
        pass
    return 0
