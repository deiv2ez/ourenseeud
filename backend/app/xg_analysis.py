"""
xg_analysis.py — Calcula insights de rendemento a partir das estatísticas xG
gardadas (Sofascore). NON toca o motor de predición: é unha capa descriptiva.

Para cada equipo agrega, sobre os partidos con estatísticas dispoñibles:
  · xG a favor / en contra acumulado
  · goles a favor / en contra reais
  · diferenza (puntería ofensiva e solidez defensiva)
  · tiros, posesión medias (se hai)
E xera unhas etiquetas/insights por umbrais (fallback se non hai Gemini).
"""

def team_xg_stats(team_name: str, stats_rows: list[dict], played: list[dict]) -> dict | None:
    """
    Agrega as estatísticas xG dun equipo. `stats_rows` = load_stats() (de Supabase).
    `played` = partidos xogados (para os goles reais). Devolve None se non hai datos.
    """
    xgf = xga = 0.0
    gf = ga = 0
    shots_f = shots_a = 0.0
    poss_sum = 0.0
    n = 0
    # índice de resultados reais por (home,away)
    result_idx = {(m["home"], m["away"]): (m["hg"], m["ag"]) for m in played}

    for s in stats_rows:
        h, a = s["home"], s["away"]
        if team_name not in (h, a):
            continue
        sh, sa = s.get("stats_home", {}), s.get("stats_away", {})
        is_home = (h == team_name)
        mine = sh if is_home else sa
        theirs = sa if is_home else sh
        if "xg" not in mine or "xg" not in theirs:
            continue
        xgf += mine["xg"]; xga += theirs["xg"]
        shots_f += mine.get("shots", 0); shots_a += theirs.get("shots", 0)
        poss_sum += mine.get("possession", 50)
        # goles reais dese partido
        real = result_idx.get((h, a))
        if real:
            gf += real[0] if is_home else real[1]
            ga += real[1] if is_home else real[0]
        n += 1

    if n == 0:
        return None
    return {
        "matches": n,
        "xgf": round(xgf, 1), "xga": round(xga, 1),
        "gf": gf, "ga": ga,
        "off_diff": round(gf - xgf, 1),   # + sobrerrende / − desperdicia
        "def_diff": round(xga - ga, 1),   # + concede menos do esperado (sorte/portería)
        "shots_pg": round(shots_f / n, 1),
        "shots_against_pg": round(shots_a / n, 1),
        "possession_avg": round(poss_sum / n),
    }


def fallback_insights(team_name: str, s: dict, lang: str = "gl") -> list[str]:
    """
    Xera etiquetas de análise por umbrais (fallback sen Gemini). Devolve frases curtas.
    """
    out = []
    off, dfd = s["off_diff"], s["def_diff"]
    # ofensiva
    if off <= -2.0:
        out.append("Xera moitas ocasións pero fáltalle puntería: marca bastante menos do esperado."
                   if lang == "gl" else
                   "Genera muchas ocasiones pero le falta puntería: marca bastante menos de lo esperado.")
    elif off >= 2.0:
        out.append("Moi eficaz de cara a portería: marca máis do que xera (pode ser insostible)."
                   if lang == "gl" else
                   "Muy eficaz de cara a portería: marca más de lo que genera (puede ser insostenible).")
    else:
        out.append("Puntería axustada ás ocasións que xera." if lang == "gl" else
                   "Puntería ajustada a las ocasiones que genera.")
    # defensiva
    if dfd >= 2.0:
        out.append("Bloque defensivo sólido: concede menos goles do que suxiren as ocasións rivais."
                   if lang == "gl" else
                   "Bloque defensivo sólido: concede menos goles de lo que sugieren las ocasiones rivales.")
    elif dfd <= -2.0:
        out.append("Defensa permisiva: encaixa máis do esperado polas ocasións concedidas."
                   if lang == "gl" else
                   "Defensa permisiva: encaja más de lo esperado por las ocasiones concedidas.")
    return out
