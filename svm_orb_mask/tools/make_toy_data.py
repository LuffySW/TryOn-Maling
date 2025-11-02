"""
Generate a tiny synthetic dataset and a simple t-shirt PNG for smoke testing.

Creates:
- svm_orb_tshirt/data/torso/: positive crops
- svm_orb_tshirt/data/non_torso/: negative crops
- svm_orb_tshirt/assets/tshirt.png: simple transparent shirt-like overlay
"""
import os
from pathlib import Path
import numpy as np
import cv2


ROOT = Path(__file__).resolve().parents[1]
DATA_TORSO = ROOT / "data" / "torso"
DATA_NEG = ROOT / "data" / "non_torso"
ASSETS = ROOT / "assets"


def ensure_dirs():
    DATA_TORSO.mkdir(parents=True, exist_ok=True)
    DATA_NEG.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)


def rand_color(rng):
    return tuple(int(x) for x in rng.integers(40, 220, size=3))


def make_positive(rng, idx: int):
    H, W = 256, 192
    img = np.full((H, W, 3), 230, dtype=np.uint8)
    # Torso-like shape: rectangle with a neck notch and slight shoulders
    torso_color = rand_color(rng)
    # Main body
    x0, y0, x1, y1 = 32, 40, W - 32, H - 20
    cv2.rectangle(img, (x0, y0), (x1, y1), torso_color, thickness=-1)
    # Neck notch
    cv2.rectangle(img, (W // 2 - 12, y0 - 8), (W // 2 + 12, y0 + 6), (230, 230, 230), thickness=-1)
    # Shoulder accents
    cv2.ellipse(img, (x0, y0 + 12), (18, 10), 0, 0, 180, torso_color, -1)
    cv2.ellipse(img, (x1, y0 + 12), (18, 10), 0, 0, 180, torso_color, -1)
    # Add some texture lines to generate ORB keypoints
    for _ in range(12):
        x = int(rng.integers(x0 + 4, x1 - 4))
        y = int(rng.integers(y0 + 8, y1 - 8))
        lcolor = tuple(int(c * 0.7) for c in torso_color)
        cv2.circle(img, (x, y), int(rng.integers(2, 4)), lcolor, -1)
    out = DATA_TORSO / f"pos_{idx:04d}.png"
    cv2.imwrite(str(out), img)


def make_negative(rng, idx: int):
    H, W = 256, 192
    img = np.full((H, W, 3), 200, dtype=np.uint8)
    # Random shapes and lines (no centered torso-like shape)
    for _ in range(25):
        color = rand_color(rng)
        if rng.random() < 0.5:
            p1 = (int(rng.integers(0, W)), int(rng.integers(0, H)))
            p2 = (int(rng.integers(0, W)), int(rng.integers(0, H)))
            cv2.line(img, p1, p2, color, int(rng.integers(1, 3)))
        else:
            c = (int(rng.integers(0, W)), int(rng.integers(0, H)))
            r = int(rng.integers(3, 20))
            cv2.circle(img, c, r, color, -1)
    out = DATA_NEG / f"neg_{idx:04d}.png"
    cv2.imwrite(str(out), img)


def make_tshirt_png():
    # Simple T-shirt-like shape with alpha
    H, W = 300, 260
    rgba = np.zeros((H, W, 4), dtype=np.uint8)
    shirt_color = (50, 160, 255, 230)  # BGRA
    # Body
    cv2.rectangle(rgba, (40, 80), (W - 40, H - 20), shirt_color, -1)
    # Sleeves
    cv2.ellipse(rgba, (40, 100), (40, 20), 0, 90, 270, shirt_color, -1)
    cv2.ellipse(rgba, (W - 40, 100), (40, 20), 0, -90, 90, shirt_color, -1)
    # Neck opening (alpha = 0)
    cv2.circle(rgba, (W // 2, 80), 20, (0, 0, 0, 0), -1)
    out = ASSETS / "tshirt.png"
    cv2.imwrite(str(out), rgba)


def main():
    ensure_dirs()
    rng = np.random.default_rng(42)
    n_pos = 140
    n_neg = 140
    for i in range(n_pos):
        make_positive(rng, i)
    for i in range(n_neg):
        make_negative(rng, i)
    make_tshirt_png()
    print(f"Generated {n_pos} positives and {n_neg} negatives.")


if __name__ == "__main__":
    main()
