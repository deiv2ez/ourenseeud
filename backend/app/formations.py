"""
formations.py — Coordenadas (X, Y en %) de cada formación para o once inicial.

X: 0 (banda esquerda) → 100 (banda dereita).
Y: 0 (liña de fondo propia, portería) → 100 (área rival, arriba no campo).
O portero vai abaixo (Y pequeno), os dianteiros arriba (Y grande).

Cada formación é unha LISTA de 11 slots con {x, y, role}. O role é só orientativo
(POR/DEF/MED/DEL): o sistema NON bloquea quen vai en cada slot, así que se pode poñer
un medio de central se se quere (versatilidade total, como pediu o usuario).
"""

FORMATIONS: dict[str, list[dict]] = {
    "4-3-3": [
        {"x": 50, "y": 8, "role": "POR"},
        {"x": 18, "y": 26, "role": "DEF"}, {"x": 39, "y": 22, "role": "DEF"},
        {"x": 61, "y": 22, "role": "DEF"}, {"x": 82, "y": 26, "role": "DEF"},
        {"x": 30, "y": 50, "role": "MED"}, {"x": 50, "y": 46, "role": "MED"},
        {"x": 70, "y": 50, "role": "MED"},
        {"x": 22, "y": 78, "role": "DEL"}, {"x": 50, "y": 84, "role": "DEL"},
        {"x": 78, "y": 78, "role": "DEL"},
    ],
    "4-2-3-1": [
        {"x": 50, "y": 8, "role": "POR"},
        {"x": 18, "y": 26, "role": "DEF"}, {"x": 39, "y": 22, "role": "DEF"},
        {"x": 61, "y": 22, "role": "DEF"}, {"x": 82, "y": 26, "role": "DEF"},
        {"x": 38, "y": 44, "role": "MED"}, {"x": 62, "y": 44, "role": "MED"},
        {"x": 22, "y": 66, "role": "MED"}, {"x": 50, "y": 64, "role": "MED"},
        {"x": 78, "y": 66, "role": "MED"},
        {"x": 50, "y": 86, "role": "DEL"},
    ],
    "4-4-2": [
        {"x": 50, "y": 8, "role": "POR"},
        {"x": 18, "y": 26, "role": "DEF"}, {"x": 39, "y": 22, "role": "DEF"},
        {"x": 61, "y": 22, "role": "DEF"}, {"x": 82, "y": 26, "role": "DEF"},
        {"x": 18, "y": 54, "role": "MED"}, {"x": 40, "y": 50, "role": "MED"},
        {"x": 60, "y": 50, "role": "MED"}, {"x": 82, "y": 54, "role": "MED"},
        {"x": 38, "y": 82, "role": "DEL"}, {"x": 62, "y": 82, "role": "DEL"},
    ],
    "3-5-2": [
        {"x": 50, "y": 8, "role": "POR"},
        {"x": 28, "y": 24, "role": "DEF"}, {"x": 50, "y": 20, "role": "DEF"},
        {"x": 72, "y": 24, "role": "DEF"},
        {"x": 14, "y": 52, "role": "MED"}, {"x": 35, "y": 48, "role": "MED"},
        {"x": 50, "y": 44, "role": "MED"}, {"x": 65, "y": 48, "role": "MED"},
        {"x": 86, "y": 52, "role": "MED"},
        {"x": 38, "y": 82, "role": "DEL"}, {"x": 62, "y": 82, "role": "DEL"},
    ],
    "3-4-3": [
        {"x": 50, "y": 8, "role": "POR"},
        {"x": 28, "y": 24, "role": "DEF"}, {"x": 50, "y": 20, "role": "DEF"},
        {"x": 72, "y": 24, "role": "DEF"},
        {"x": 18, "y": 52, "role": "MED"}, {"x": 40, "y": 48, "role": "MED"},
        {"x": 60, "y": 48, "role": "MED"}, {"x": 82, "y": 52, "role": "MED"},
        {"x": 22, "y": 80, "role": "DEL"}, {"x": 50, "y": 84, "role": "DEL"},
        {"x": 78, "y": 80, "role": "DEL"},
    ],
    "5-3-2": [
        {"x": 50, "y": 8, "role": "POR"},
        {"x": 12, "y": 30, "role": "DEF"}, {"x": 32, "y": 24, "role": "DEF"},
        {"x": 50, "y": 22, "role": "DEF"}, {"x": 68, "y": 24, "role": "DEF"},
        {"x": 88, "y": 30, "role": "DEF"},
        {"x": 30, "y": 54, "role": "MED"}, {"x": 50, "y": 50, "role": "MED"},
        {"x": 70, "y": 54, "role": "MED"},
        {"x": 38, "y": 82, "role": "DEL"}, {"x": 62, "y": 82, "role": "DEL"},
    ],
    "4-1-4-1": [
        {"x": 50, "y": 8, "role": "POR"},
        {"x": 18, "y": 26, "role": "DEF"}, {"x": 39, "y": 22, "role": "DEF"},
        {"x": 61, "y": 22, "role": "DEF"}, {"x": 82, "y": 26, "role": "DEF"},
        {"x": 50, "y": 42, "role": "MED"},
        {"x": 18, "y": 62, "role": "MED"}, {"x": 40, "y": 60, "role": "MED"},
        {"x": 60, "y": 60, "role": "MED"}, {"x": 82, "y": 62, "role": "MED"},
        {"x": 50, "y": 84, "role": "DEL"},
    ],
}


def formation_names() -> list[str]:
    return list(FORMATIONS.keys())
