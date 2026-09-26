"""Colour parsing helpers. Accepts names, hex (#ff8800 / ff8800) or "r,g,b"."""

NAMED = {
    "red": (255, 0, 0), "green": (0, 255, 0), "blue": (0, 0, 255),
    "white": (255, 255, 255), "warm": (255, 147, 41), "orange": (255, 100, 0),
    "yellow": (255, 200, 0), "cyan": (0, 255, 255), "magenta": (255, 0, 255),
    "purple": (128, 0, 255), "pink": (255, 60, 140), "black": (0, 0, 0),
}


def parse_color(text: str) -> list[int]:
    """Return [r, g, b] (0-255 each) or raise ValueError."""
    t = text.strip().lower().lstrip("#")
    if t in NAMED:
        return list(NAMED[t])
    if "," in t:
        parts = [int(p) for p in t.split(",")]
        if len(parts) != 3 or any(not 0 <= p <= 255 for p in parts):
            raise ValueError(f"Bad RGB triplet: {text!r}")
        return parts
    if len(t) == 6:
        return [int(t[i:i + 2], 16) for i in (0, 2, 4)]
    raise ValueError(f"Unrecognised colour: {text!r} (try 'red', 'ff8800' or '255,136,0')")
