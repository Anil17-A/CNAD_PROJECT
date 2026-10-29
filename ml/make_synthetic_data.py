"""Creates data/hazard.csv (synthetic flood-sensor features) so train_early_warning.py runs without a real dataset."""
import os, numpy as np, pandas as pd
rng = np.random.default_rng(42)
n = 4000
event = rng.integers(0, 2, n)
df = pd.DataFrame({
    "water_level_m":   np.where(event, rng.normal(3.4, 0.7, n), rng.normal(2.0, 0.3, n)),
    "rate_of_change":  np.where(event, rng.normal(0.35, 0.15, n), rng.normal(0.0, 0.08, n)),
    "rainfall_mm_hr":  np.where(event, rng.gamma(6, 5, n), rng.gamma(2, 2, n)),
    "soil_moisture":   np.where(event, rng.beta(6, 2, n), rng.beta(2, 5, n)),
    "event": event})
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "hazard.csv")
df.to_csv(out, index=False); print(f"wrote {out}: {len(df)} rows, {event.mean():.0%} positive")
