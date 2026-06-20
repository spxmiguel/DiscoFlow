"""
Tidal via tidalapi (unofficial but actively maintained).
OAuth login required on first run — opens a browser link for the user.
Token is saved to .tidal_session.json next to this file.
"""

import json
import os

SESSION_FILE = os.path.join(os.path.dirname(__file__), ".tidal_session.json")

_session = None


def _get_session():
    global _session
    if _session and _session.check_login():
        return _session

    try:
        import tidalapi
    except ImportError:
        raise RuntimeError("tidalapi not installed (pip install tidalapi)")

    session = tidalapi.Session()
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE) as f:
                data = json.load(f)
            session.load_oauth_session(
                data["token_type"], data["access_token"],
                data["refresh_token"], data.get("expiry_time")
            )
            if session.check_login():
                _session = session
                return session
        except Exception:
            pass

    # First-time OAuth login
    login, future = session.login_oauth()
    print(f"[Tidal] Visite: {login.verification_uri_complete}")

    # write a file so the backend IPC can surface it
    import ipc as _ipc
    _ipc.write_state({
        "status": "tidal_auth_needed",
        "tidal_login_url": login.verification_uri_complete,
    })

    future.result()
    token = session.token_type, session.access_token, session.refresh_token, session.expiry_time
    with open(SESSION_FILE, "w") as f:
        json.dump({
            "token_type":    session.token_type,
            "access_token":  session.access_token,
            "refresh_token": session.refresh_token,
            "expiry_time":   str(session.expiry_time),
        }, f)

    _session = session
    return session


def search_tracks(query, limit=20):
    session = _get_session()
    results = session.search(query, models=[session.parse_track], limit=limit)
    tracks = results.get("tracks", []) if isinstance(results, dict) else (results or [])
    return [_format(t) for t in tracks[:limit]]


def get_playlists(limit=30):
    session = _get_session()
    playlists = session.user.playlists()
    return [{"id": str(p.id), "name": p.name, "tracks": p.num_tracks}
            for p in (playlists or [])[:limit]]


def get_playlist_tracks(playlist_id, limit=50):
    session = _get_session()
    playlist = session.playlist(playlist_id)
    return [_format(t) for t in (playlist.tracks(limit=limit) or [])]


def _format(t):
    artist = ", ".join(a.name for a in (getattr(t, "artists", None) or []))
    preview = getattr(t, "audio_preview_url", "") or ""
    return {
        "id": str(t.id),
        "name": t.name or "",
        "artist": artist,
        "duration_ms": (t.duration or 0) * 1000,
        "preview_url": preview,
        "uri": f"tidal://track/{t.id}",
        "bpm": None,
    }
