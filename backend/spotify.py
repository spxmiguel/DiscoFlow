import os
import json
import time
import webbrowser
import threading
import urllib.parse
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
REDIRECT_URI = "http://localhost:8765/callback"
SCOPES = "user-read-currently-playing user-read-playback-state"
TOKEN_FILE = os.path.join(os.path.dirname(__file__), ".spotify_token.json")

_auth_code = None
_auth_event = threading.Event()


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            _auth_code = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h2>DiscoFlow: autorizado! Pode fechar esta aba.</h2>")
            _auth_event.set()
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, *args):
        pass


def _run_callback_server():
    server = HTTPServer(("localhost", 8765), _CallbackHandler)
    server.handle_request()


def authorize():
    if not CLIENT_ID:
        raise RuntimeError("SPOTIFY_CLIENT_ID not set")

    _auth_event.clear()
    t = threading.Thread(target=_run_callback_server, daemon=True)
    t.start()

    params = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
    })
    webbrowser.open(f"https://accounts.spotify.com/authorize?{params}")
    _auth_event.wait(timeout=120)

    if not _auth_code:
        raise RuntimeError("Spotify authorization timed out")

    return _exchange_code(_auth_code)


def _exchange_code(code):
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": os.getenv("SPOTIFY_CLIENT_SECRET", ""),
    }).encode()

    req = urllib.request.Request("https://accounts.spotify.com/api/token", data=data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req) as resp:
        token = json.loads(resp.read())
        token["expires_at"] = time.time() + token["expires_in"]
        _save_token(token)
        return token


def _refresh_token(token):
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": token["refresh_token"],
        "client_id": CLIENT_ID,
        "client_secret": os.getenv("SPOTIFY_CLIENT_SECRET", ""),
    }).encode()

    req = urllib.request.Request("https://accounts.spotify.com/api/token", data=data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req) as resp:
        new_token = json.loads(resp.read())
        token.update(new_token)
        token["expires_at"] = time.time() + new_token["expires_in"]
        _save_token(token)
        return token


def _save_token(token):
    with open(TOKEN_FILE, "w") as f:
        json.dump(token, f)


def load_token():
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE) as f:
        return json.load(f)


def get_valid_token():
    token = load_token()
    if not token:
        return authorize()
    if time.time() >= token.get("expires_at", 0) - 60:
        return _refresh_token(token)
    return token


def _api_get(path, token):
    req = urllib.request.Request(f"https://api.spotify.com/v1{path}")
    req.add_header("Authorization", f"Bearer {token['access_token']}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def search_tracks(query, limit=20):
    token = get_valid_token()
    encoded = urllib.parse.quote(query)
    data = _api_get(f"/search?q={encoded}&type=track&limit={limit}", token)
    tracks = data.get("tracks", {}).get("items", [])
    return [_format_track(t) for t in tracks]


def get_audio_features(track_id):
    token = get_valid_token()
    data = _api_get(f"/audio-features/{track_id}", token)
    return {
        "bpm": round(data.get("tempo", 0)),
        "time_signature": data.get("time_signature", 4),
        "energy": data.get("energy", 0),
        "danceability": data.get("danceability", 0),
    }


def get_current_track():
    token = get_valid_token()
    try:
        data = _api_get("/me/player/currently-playing", token)
        if not data or not data.get("item"):
            return None
        return _format_track(data["item"])
    except Exception:
        return None


def get_playlists(limit=50):
    token = get_valid_token()
    data = _api_get(f"/me/playlists?limit={limit}", token)
    return [
        {"id": p["id"], "name": p["name"], "tracks": p["tracks"]["total"]}
        for p in data.get("items", [])
    ]


def get_playlist_tracks(playlist_id, limit=50):
    token = get_valid_token()
    data = _api_get(f"/playlists/{playlist_id}/tracks?limit={limit}", token)
    return [_format_track(item["track"]) for item in data.get("items", []) if item.get("track")]


def _format_track(t):
    return {
        "id": t["id"],
        "name": t["name"],
        "artist": ", ".join(a["name"] for a in t["artists"]),
        "duration_ms": t["duration_ms"],
        "uri": t["uri"],
    }
