import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "damage"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "prediction"))
from severity import compute_si, priority_label
from model import risk_from_window

def test_worked_example_from_deck():
    assert compute_si(62, 0.81, 0.35) == 62.3
    assert priority_label(62.3) == "HIGH"

def test_normal_readings_low_risk():
    assert risk_from_window([2.0, 2.01, 1.99, 2.0, 2.02, 1.98, 2.0, 2.01, 1.99, 2.0, 2.0])[0] < 0.3

def test_surge_high_risk():
    vals = [2.0]*20 + [2.5, 3.0, 3.6, 4.3, 5.0]
    assert risk_from_window(vals)[0] >= 0.6
