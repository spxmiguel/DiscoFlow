"""
Detect BPM from a 30-second audio preview URL.
Used by Apple Music, Tidal, and YouTube Music backends.
Falls back to iTunes search when the caller provides artist + title.
"""

import os
import json
import tempfile
import urllib.parse
import urllib.request


def _clamp(bpm):
    if not bpm or bpm <= 0:
        return None
    while bpm < 80:
        bpm *= 2
    while bpm > 200:
        bpm /= 2
    return round(bpm)


def bpm_from_url(url):
    """Download audio from url, detect BPM, return clamped value or None."""
    if not url:
        return None
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            audio_bytes = resp.read()

        suffix = ".m4a"
        for ext in (".mp3", ".ogg", ".wav", ".flac"):
            if ext in url:
                suffix = ext
                break

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_bytes)
            tmp = f.name

        try:
            import librosa
            y, sr = librosa.load(tmp, sr=None, mono=True)
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            return _clamp(float(tempo))
        finally:
            os.unlink(tmp)
    except Exception:
        return None


def find_preview_and_bpm(artist, title):
    """Search iTunes for a matching track, download preview, detect BPM."""
    try:
        query = f"{artist} {title}"
        url = (
            "https://itunes.apple.com/search?"
            + urllib.parse.urlencode({"term": query, "media": "music", "limit": 1})
        )
        with urllib.request.urlopen(url, timeout=8) as resp:
            results = json.loads(resp.read()).get("results", [])
        if results:
            preview = results[0].get("previewUrl", "")
            return bpm_from_url(preview)
    except Exception:
        pass
    return None
