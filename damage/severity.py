ALPHA, BETA, GAMMA = 0.5, 0.3, 0.2

def compute_si(structural_damage_pct: float, population_exposure: float, access_difficulty: float) -> float:
    """SI = a*Damage% + b*Exposure + g*Access, with exposure/access given on 0..1 and scaled to 0..100."""
    return round(ALPHA * structural_damage_pct + BETA * population_exposure * 100
                 + GAMMA * access_difficulty * 100, 1)

def priority_label(si: float) -> str:
    return "HIGH" if si >= 60 else "MEDIUM" if si >= 35 else "LOW"
