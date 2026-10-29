"""Early-warning scoring. Replace/extend with a trained XGBoost classifier and autoencoder (see ml/)."""
import statistics

def risk_from_window(values):
    """values: recent readings, oldest -> newest. Returns (risk 0..1, minutes_to_impact, ci)."""
    if len(values) < 10:
        return 0.0, None, (0.0, 0.0)
    hist, last = values[:-1], values[-1]
    mu = statistics.mean(hist)
    sd = statistics.pstdev(hist) or 0.05
    z = abs(last - mu) / sd                      # anomaly score
    rate = values[-1] - values[-4] if len(values) >= 4 else 0   # rate of change
    risk = min(1.0, z / 8 + max(rate, 0) / 3)
    minutes = None if risk < 0.3 else max(5, int(120 * (1 - risk)))
    ci = (round(max(0, risk - 0.1), 2), round(min(1, risk + 0.1), 2))
    return round(risk, 3), minutes, ci
