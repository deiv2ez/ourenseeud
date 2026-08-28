"""
sofascore_parser.py — Extrae as estatísticas dun partido do volcado do Web Scraper
de Sofascore (formato: VALOR_LOCAL <tab> ETIQUETA <tab> VALOR_VISITANTE).

Usa a fila "Match overview" (a máis fiable). Devolve un dict de métricas normalizadas.
Ignora as filas desaliñadas (Shots, etc.) e o ruído (URLs, nomes de estilos).
"""
import re

# etiqueta de Sofascore → clave interna
LABELS = {
    "Ball possession": "possession",
    "Expected goals (xG)": "xg",
    "Total shots": "shots",
    "Shots on target": "shots_on_target",
    "Goalkeeper saves": "saves",
    "Corner kicks": "corners",
    "Fouls": "fouls",
    "Passes": "passes",
    "Tackles": "tackles",
    "Free kicks": "free_kicks",
    "Shots off target": "shots_off",
    "Blocked shots": "shots_blocked",
    "Shots inside box": "shots_inside",
    "Shots outside box": "shots_outside",
    "Big chances": "big_chances",
    "Crosses": "crosses",
    "Interceptions": "interceptions",
    "Offsides": "offsides",
}

_NUMERIC = re.compile(r'^[\d]+([.,]\d+)?%?$')       # 12, 1.61, 59%
_FRACTION = re.compile(r'^\d+/\d+$')                  # 41/115

def _val(x: str):
    """Converte un valor de cela a número aproveitable (float, int ou % → float)."""
    x = x.strip()
    if _NUMERIC.match(x):
        if x.endswith('%'):
            return float(x[:-1])
        return float(x.replace(',', '.'))
    if _FRACTION.match(x):
        num, den = x.split('/')
        return float(num)  # quedámonos co numerador (ex. acertos)
    return None

def parse_match(raw: str) -> dict:
    """
    Recibe o texto pegado (unha ou varias liñas) e devolve
    {'home': {metricas...}, 'away': {metricas...}} coas estatísticas fiables.
    """
    home, away = {}, {}
    for line in raw.split("\n"):
        cells = line.split("\t")
        i = 0
        while i < len(cells) - 2:
            loc, label, vis = cells[i].strip(), cells[i+1].strip(), cells[i+2].strip()
            key = LABELS.get(label)
            if key:
                vl, vv = _val(loc), _val(vis)
                if vl is not None and vv is not None and key not in home:
                    home[key] = vl
                    away[key] = vv
                    i += 3
                    continue
            i += 1
    return {"home": home, "away": away}
