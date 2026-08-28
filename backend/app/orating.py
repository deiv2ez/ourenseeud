"""
orating.py — Parsea as estatísticas de xogador de Sofascore e calcula o oRating,
un rating REALISTA (escala 0-10 de verdade, non o 6-8 tibio de Sofascore).

Fórmula (calibrada con partidos reais da categoría):
  oRating = clip(0, 10, BASE + ataque + posesión + físico)
    BASE = 4.5
    ataque   = goles*2.0 + asistencias*1.2
    posesión = pases_ok*0.05 − pases_fallados*0.15   (castiga o pase fallado)
    físico   = duelos_gañados*0.12 − duelos_perdidos*NEG + tackles_gañados*0.25
               (terrestres e aéreos por separado; tope ±2.0)
               NEG = 0.05 para dianteiros (F), 0.10 para o resto
               → un dianteiro non se ve tan penalizado por perder duelos.

Formato de entrada (volcado do Web Scraper, unha liña por xogador):
  NOME  goles  [asist]  PASES(ok/tot %)  duelos(tot(gañ))  aéreos(tot(gañ))
        [tackles(tot(gañ))]  minutos  [.]  POSICIÓN(D/M/F/G)
As columnas varían (ás veces falta asistencia). Áncoras fiables: os pases teñen
formato "N/M", a posición é a última cela D/M/F/G, os minutos rematan en "'".
"""
import re

BASE = 4.5
DUEL_WIN = 0.12          # valor de cada duelo gañado
TACKLE_WIN = 0.25        # valor de cada tackle gañado
PHYS_CAP = 2.0           # tope (+/-) do bloque físico

_PASS = re.compile(r'^(\d+)/(\d+)')
_VW = re.compile(r'^(\d+)\s*\((\d+)\)$')   # "19 (6)" → total 19, gañados 6
_MIN = re.compile(r"^\d+'$")
_INT = re.compile(r'^\d+$')


def parse_player(cells: list[str]) -> dict | None:
    """Parsea unha fila de xogador. Devolve None se non hai datos de pases fiables."""
    cells = [c.strip() for c in cells]
    if not cells or not cells[0]:
        return None
    name = cells[0]
    pos = next((c for c in reversed(cells) if c in ("D", "M", "F", "G")), "M")
    min_cell = next((c for c in cells if _MIN.match(c)), "90'")
    mins = int(min_cell.rstrip("'"))
    # índice dos pases (áncora)
    pi = next((i for i, c in enumerate(cells) if _PASS.match(c)), None)
    if pi is None:
        return None
    pm = _PASS.match(cells[pi])
    pass_ok, pass_tot = int(pm.group(1)), int(pm.group(2))
    # goles/asistencias: enteiros simples antes dos pases
    pre = [c for c in cells[1:pi] if _INT.match(c)]
    goals = int(pre[0]) if len(pre) >= 1 else 0
    assists = int(pre[1]) if len(pre) >= 2 else 0
    # duelos/aéreos/tackles: celas "N (M)" despois dos pases
    post = [c for c in cells[pi + 1:] if _VW.match(c)]

    def vw(s):
        m = _VW.match(s)
        return int(m.group(1)), int(m.group(2))

    dt = dw = at = aw = tk_w = 0
    if len(post) >= 1:
        dt, dw = vw(post[0])        # duelos terrestres: total, gañados
    if len(post) >= 2:
        at, aw = vw(post[1])        # aéreos
    if len(post) >= 3:
        _, tk_w = vw(post[2])       # tackles: só nos interesan os gañados
    return {
        "name": name, "pos": pos, "mins": mins,
        "goals": goals, "assists": assists,
        "pass_ok": pass_ok, "pass_tot": pass_tot,
        "duels_tot": dt, "duels_won": dw,
        "aerial_tot": at, "aerial_won": aw,
        "tackles_won": tk_w,
    }


def orating(p: dict) -> float:
    """Calcula o oRating dun xogador xa parseado."""
    att = p["goals"] * 2.0 + p["assists"] * 1.2
    poss = p["pass_ok"] * 0.05 - (p["pass_tot"] - p["pass_ok"]) * 0.15
    neg = 0.05 if p["pos"] == "F" else 0.10
    terr = p["duels_won"] * DUEL_WIN - (p["duels_tot"] - p["duels_won"]) * neg
    aer = p["aerial_won"] * DUEL_WIN - (p["aerial_tot"] - p["aerial_won"]) * neg
    phys = terr + aer + p["tackles_won"] * TACKLE_WIN
    phys = max(-PHYS_CAP, min(PHYS_CAP, phys))
    return round(max(0.0, min(10.0, BASE + att + poss + phys)), 1)


def parse_lineup(raw: str) -> list[dict]:
    """
    Parsea o volcado completo dun equipo (varias liñas) e devolve a lista de
    xogadores co seu oRating. Ignora liñas de cabeceira e as que non teñen pases.
    """
    out = []
    for line in raw.split("\n"):
        if not line.strip() or line.startswith("textStyle"):
            continue
        p = parse_player(line.split("\t"))
        if p is None:
            continue
        p["oRating"] = orating(p)
        out.append(p)
    return out
