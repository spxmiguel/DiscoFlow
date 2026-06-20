def clamp_bpm(bpm):
    """Dead as Disco works best between 120–200 BPM. Double or halve if outside range."""
    if bpm <= 0:
        return None
    while bpm < 120:
        bpm *= 2
    while bpm > 200:
        bpm /= 2
    return round(bpm)


def format_duration(ms):
    s = ms // 1000
    return f"{s // 60}:{s % 60:02d}"
