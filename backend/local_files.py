import os

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac"}


def scan_folder(folder_path):
    tracks = []
    for root, _, files in os.walk(folder_path):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                full_path = os.path.join(root, f)
                tracks.append({"name": os.path.splitext(f)[0], "path": full_path})
    return tracks


def detect_bpm(file_path):
    try:
        import librosa
        y, sr = librosa.load(file_path, duration=60)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        return round(float(tempo))
    except ImportError:
        return None
    except Exception:
        return None
