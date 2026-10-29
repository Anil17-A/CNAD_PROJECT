"""Placeholder for CV damage segmentation.
Replace `damage_percent` with inference from the U-Net trained in ml/train_unet.py.
Mask classes: 0=background, 1=intact, 2=damaged, 3=collapsed."""
import numpy as np

def damage_percent(mask: np.ndarray) -> float:
    buildings = (mask > 0).sum()
    if buildings == 0:
        return 0.0
    return round(float(((mask == 2) | (mask == 3)).sum() / buildings * 100), 1)
