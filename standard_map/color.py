import colorsys
import numpy as np


def make_color_table(n: int, mode: str = "hsv_cycle") -> np.ndarray:
    """
    Returns shape (n, 3) uint8 array of (R, G, B) values.

    hsv_cycle:  hue cycles 0→1 over all trajectories — works well for any N
    legacy_rgb: exact Processing behavior — R=j*256/n, G=100, B=200
    """
    if mode == "legacy_rgb":
        R = (np.arange(n) * 256 // max(n, 1)).astype(np.uint8)
        G = np.full(n, 100, dtype=np.uint8)
        B = np.full(n, 200, dtype=np.uint8)
        return np.stack([R, G, B], axis=1)

    hues = np.linspace(0.0, 1.0, n, endpoint=False)
    rows = []
    for h in hues:
        r, g, b = colorsys.hsv_to_rgb(h, 0.75, 0.92)
        rows.append([int(r * 255), int(g * 255), int(b * 255)])
    return np.array(rows, dtype=np.uint8)
