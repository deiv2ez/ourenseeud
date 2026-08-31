"""
gemini.py — Xera análise textual dun equipo con Gemini a partir dos datos DUROS
(xG, goles, tiros...). Só se activa se hai GEMINI_API_KEY en Render.

FALLBACK: sen clave, devolve None e o sistema usa as etiquetas por umbrais
(xg_analysis.fallback_insights). Así non depende de Gemini.

Seguridade: a clave vai SÓ no backend (variable de entorno), nunca no frontend.
Antialucinación: o prompt prohíbe inventar; só pode usar os números dados.
"""
import os
import httpx

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"


def enabled() -> bool:
    return bool(GEMINI_API_KEY)


def analyze_team(team_name: str, s: dict, lang: str = "gl") -> str | None:
    """
    Pide a Gemini 2-3 frases de análise cos datos xG do equipo. Devolve o texto,
    ou None se non hai clave ou falla (o chamador usará o fallback por umbrais).
    """
    if not enabled():
        return None
    idioma = "galego" if lang == "gl" else "castelán"
    prompt = (
        f"Es un analista de fútbol experto na Primeira Federación española (1ª RFEF), "
        f"unha categoría moi igualada e defensiva. Escribe unha análise BREVE (2-3 frases, "
        f"máximo 55 palabras) en {idioma} sobre o rendemento do equipo '{team_name}', "
        f"baseándote SÓ nestes datos reais. NON inventes nada nin engadas datos que non estean aquí. "
        f"Datos ({s['matches']} partidos con estatísticas):\n"
        f"- Goles a favor: {s['gf']} | xG xerado: {s['xgf']} (diferenza {s['off_diff']:+})\n"
        f"- Goles en contra: {s['ga']} | xG concedido: {s['xga']} (diferenza {s['def_diff']:+})\n"
        f"- Tiros por partido: {s['shots_pg']} | Posesión media: {s['possession_avg']}%\n"
        f"Interpreta: diferenza ofensiva negativa = desperdicia ocasións (pouca puntería); "
        f"positiva = moi eficaz. Diferenza defensiva positiva = bloque sólido/afortunado. "
        f"Ton informativo e claro, sen floreos. Non uses markdown."
    )
    try:
        with httpx.Client(timeout=20) as client:
            r = client.post(
                URL,
                headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            r.raise_for_status()
            data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return text or None
    except Exception:
        return None   # calquera fallo → fallback por umbrais


def report_matchup(home: str, away: str, is_home: bool,
                   rival: dict, udo: dict, pw: int, pd: int, pl: int,
                   lang: str = "gl") -> dict | None:
    """
    Xera texto para o INFORME a partir dos DATOS REAIS (sen inventar): unha clave
    ofensiva e unha análise casa/fóra, coherentes co estilo dominador da UD Ourense.
    Devolve {"key_for": ..., "venue_analysis": ...} ou None se non hai clave / falla.
    O chamador usará o repertorio (report_copy) como fallback.
    """
    if not enabled():
        return None
    idioma = "galego" if lang == "gl" else "castelán"
    rival_name = away if is_home else home
    lugar = "na casa (O Couto)" if is_home else "a domicilio"
    prompt = (
        f"Es o analista da UD Ourense (adestrador Juan Carballo). O estilo do equipo é: "
        f"VALENTE, dominador do balón, presión alta tras perda, transicións verticais polas "
        f"bandas, bloque defensivo sólido. Xoga ASÍ tanto en casa como fóra (NON xoga á contra). "
        f"Próximo partido: UD Ourense {'vs ' + rival_name if is_home else 'a domicilio contra ' + rival_name} ({lugar}). "
        f"Escribe en {idioma}, ton informativo e sobrio, SEN markdown, SEN inventar datos. "
        f"Usa SÓ estes datos reais:\n"
        f"- Probabilidades do modelo: vitoria {pw}%, empate {pd}%, derrota {pl}%.\n"
        f"- Rival '{rival_name}': goles a favor {rival.get('gf','—')}, en contra {rival.get('ga','—')}, "
        f"xG xerado {rival.get('xgf','—')}, xG concedido {rival.get('xga','—')}, forma {rival.get('form_label','—')}.\n"
        f"- UD Ourense: goles a favor {udo.get('gf','—')}, en contra {udo.get('ga','—')}, xG xerado {udo.get('xgf','—')}.\n"
        f"Devolve EXACTAMENTE dúas liñas, sen etiquetas:\n"
        f"Liña 1 (máx 30 palabras): unha clave ofensiva concreta para facerlle dano ao rival, "
        f"coherente co estilo dominador (nada de 'xogar á contra').\n"
        f"Liña 2 (máx 45 palabras): breve análise de como afrontar o partido {lugar}, "
        f"mantendo a identidade dominadora."
    )
    try:
        with httpx.Client(timeout=20) as client:
            r = client.post(
                URL,
                headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            r.raise_for_status()
            data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if len(lines) >= 2:
            return {"key_for": lines[0], "venue_analysis": lines[1]}
        return None
    except Exception:
        return None


def context_from_news(rival_name: str, is_home: bool, lang: str = "gl") -> str | None:
    """
    Usa Gemini con BUSCA WEB (Google Search grounding) para dar contexto de DINÁMICA
    recente da UD Ourense e do rival, a partir de noticias das últimas ~2 semanas.

    GARDARRAÍLES (importante):
    - SÓ dinámica de xogo, sensacións, rendemento e resultados recentes.
    - PROHIBIDO: rumores de fichaxes, lesións, altas/baixas, mercado, especulación.
    - Se non atopa información fiable, devolve None (o informe non inclúe este bloque).
    Devolve 1-2 frases sobrias, ou None se non hai clave / falla / non hai info.
    """
    if not enabled():
        return None
    idioma = "galego" if lang == "gl" else "castelán"
    lugar = "na casa" if is_home else "a domicilio"
    prompt = (
        f"Busca noticias FIABLES das últimas 2 semanas sobre a UD Ourense (fútbol, Primeira "
        f"Federación 2026-27) e o seu vindeiro rival, o {rival_name}. "
        f"Escribe en {idioma} un contexto BREVE (1-2 frases, máx 45 palabras) sobre a DINÁMICA "
        f"recente: como veñen xogando, sensacións, rendemento e resultados. "
        f"REGRAS ESTRITAS:\n"
        f"- SÓ dinámica de xogo e resultados. Ton informativo e sobrio.\n"
        f"- PROHIBIDO mencionar rumores de fichaxes, lesións, altas, baixas ou mercado.\n"
        f"- NON inventes. Se non atopas información fiable e recente, responde exactamente 'SEN_INFO'.\n"
        f"- Non uses markdown nin cites fontes; só a frase de contexto."
    )
    try:
        with httpx.Client(timeout=25) as client:
            r = client.post(
                URL,
                headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "tools": [{"google_search": {}}],   # grounding con busca web
                },
            )
            r.raise_for_status()
            data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        if not text or "SEN_INFO" in text.upper() or "SIN_INFO" in text.upper():
            return None
        # filtro de seguridade: se aparece vocabulario de rumores, descartar
        low = text.lower()
        for banned in ["fichaj", "fichax", "lesion", "lesión", "baixa", "baja",
                       "mercado", "renov", "traspaso", "cedid", "rumor"]:
            if banned in low:
                return None
        return text
    except Exception:
        return None
