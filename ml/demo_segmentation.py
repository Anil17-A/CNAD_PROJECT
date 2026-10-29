"""Runs the damage pipeline on a synthetic building mask (no GPU / torch needed):
mask -> damage % (damage/segmentation.py) -> Severity Index (damage/severity.py)."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "damage"))
from segmentation import damage_percent
from severity import compute_si, priority_label

rng = np.random.default_rng(7)
mask = np.zeros((256, 256), dtype=int)                    # 0 background, 1 intact, 2 damaged, 3 collapsed
for _ in range(40):                                       # drop 40 random "buildings"
    x, y = rng.integers(0, 240, 2); cls = rng.choice([1, 2, 3], p=[0.4, 0.4, 0.2])
    mask[y:y + 14, x:x + 14] = cls
dmg = damage_percent(mask)
si = compute_si(dmg, 0.81, 0.35)
print(f"buildings px={(mask > 0).sum()}  damaged/collapsed = {dmg}%")
print(f"Severity Index = {si} -> {priority_label(si)}")
