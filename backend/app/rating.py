"""
rating.py — oRating: nota de rendemento por xogador (marca propia).

Por que unha nota propia e non "a de Sofascore":
  As notas tipo Sofascore/FlashScore saen dun feed comercial de eventos por
  xogador (pases completados, duelos gañados, tiros, xG individual, intercepcións...)
  que en 1ª RFEF ten cobertura moi pobre e non é scrapeable de forma fiable.
  oRating constrúese SÓ co que imos ter de verdade, e é transparente: calquera
  pode ver como se chega ao número.

Escala: 1.0 – 10.0, ancorada en 6.0 (partido "normal").

Entradas por partido e xogador:
  minutes      minutos xogados
  goals        goles
  assists      asistencias
  team_result  "W" | "D" | "L"  (resultado do equipo)
  pos          posición (GK/DF/LI/LD/MC/MCO/EI/ED/DC) → pondera accións
  conceded     goles encaixados (para porteiros/defensas)
  clean_sheet  bool (porteria a cero)
  motm         bool (mellor do partido, opcional, +bonus)

O modelo pondera segundo posición: a un dianteiro premian máis os goles; a un
porteiro/defensa, a portería a cero e poucos goles encaixados.

Cando (algún día) exista un feed de eventos mellor, engádese como termo extra sen
romper nada: oRating = base_actual * (1-w) + feed_rating * w.
"""

from __future__ import annotations

BASE = 6.0
ATTACK_POS = {"DC", "EI", "ED", "MCO"}
DEF_POS = {"GK", "DF", "LI", "LD"}


def match_rating(minutes: int, goals: int = 0, assists: int = 0,
                team_result: str = "D", pos: str = "MC",
                conceded: int = 0, clean_sheet: bool = False,
                motm: bool = False) -> float:
    """oRating dun xogador nun partido concreto (1.0–10.0)."""
    if minutes <= 0:
        return 0.0  # non xogou

    r = BASE

    # participación: quen xoga máis ten máis exposición ao resultado
    played_full = min(1.0, minutes / 90.0)

    # goles e asistencias, ponderados por posición
    goal_w = 1.3 if pos in ATTACK_POS else 1.0 if pos == "MC" else 0.8
    r += goals * goal_w
    r += assists * 0.75

    # resultado do equipo (compártese, atenuado)
    r += {"W": 0.6, "D": 0.0, "L": -0.5}.get(team_result, 0.0) * played_full

    # defensa: portería a cero e goles encaixados
    if pos in DEF_POS:
        if clean_sheet:
            r += 0.9 if pos == "GK" else 0.6
        r -= conceded * (0.35 if pos == "GK" else 0.2) * played_full

    if motm:
        r += 0.8

    return round(max(1.0, min(10.0, r)), 1)


def season_rating(match_ratings: list[float]) -> dict:
    """
    Media da tempada a partir das notas de partido (ignora partidos sen xogar).
    Devolve media, nº de partidos puntuados e forma (últimas 5 notas).
    """
    played = [x for x in match_ratings if x and x > 0]
    if not played:
        return {"avg": None, "games": 0, "form": []}
    return {
        "avg": round(sum(played) / len(played), 2),
        "games": len(played),
        "form": played[-5:],
    }
