"""
report.py — Informe técnico previo ao próximo partido da UD Ourense en PDF.

Deseño MINIMALISTA EDITORIAL: paleta sobria (grises + un só acento vermello moi
puntual), tipografía limpa, tablas sen bordes (só finas liñas de separación onde
axudan), moito espazo negativo, métricas "ao espido", aliñación editorial.

Recibe un dict `data` (preparado por main.py cos datos reais) e devolve os bytes do PDF.
"""
from io import BytesIO
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                PageBreak,
                                Image, HRFlowable)
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY, TA_CENTER, TA_RIGHT

# --- paleta sobria ---
INK = colors.HexColor("#1a1a1a")       # case negro, para titulares
BODY = colors.HexColor("#3d3d3d")      # corpo de texto
MUTE = colors.HexColor("#8a8a8a")      # secundario / etiquetas
HAIR = colors.HexColor("#e4e4e4")      # liñas finísimas
ACCENT = colors.HexColor("#C8102E")    # vermello UDO, uso MOI puntual
C_WIN = colors.HexColor("#1a8a4a")     # verde vitoria
C_DRAW = colors.HexColor("#c99700")    # amarelo/ámbar empate
C_LOSS = colors.HexColor("#c0392b")    # vermello derrota
PAGE_W = A4[0]
CONTENT_W = PAGE_W - 36 * mm           # marxes de 18mm


def _styles():
    ss = getSampleStyleSheet()
    def add(name, **kw):
        ss.add(ParagraphStyle(name, parent=ss["Normal"], **kw))
    add("rKicker", fontName="Helvetica-Bold", fontSize=7, textColor=MUTE,
        leading=9, spaceAfter=1, tracking=1)
    add("rTitle", fontName="Helvetica-Bold", fontSize=16, textColor=INK, leading=18, spaceAfter=1)
    add("rSub", fontName="Helvetica", fontSize=8.5, textColor=MUTE, leading=11)
    add("rSec", fontName="Helvetica-Bold", fontSize=8, textColor=INK, leading=11,
        spaceBefore=9, spaceAfter=4, tracking=1.2)
    add("rBody", fontName="Helvetica", fontSize=9, textColor=BODY, leading=13.5, alignment=TA_JUSTIFY)
    add("rLead", fontName="Helvetica", fontSize=9.5, textColor=BODY, leading=14, alignment=TA_LEFT)
    add("rSmall", fontName="Helvetica", fontSize=7, textColor=MUTE, leading=9)
    add("rTip", fontName="Helvetica", fontSize=9, textColor=BODY, leading=13.5, leftIndent=10)
    add("rMetricN", fontName="Helvetica-Bold", fontSize=21, textColor=INK, leading=22)
    add("rMetricL", fontName="Helvetica", fontSize=5.8, textColor=MUTE, leading=7.5, tracking=0.5)
    add("rKVk", fontName="Helvetica", fontSize=8.5, textColor=MUTE, leading=12)
    add("rKVv", fontName="Helvetica-Bold", fontSize=8.5, textColor=INK, leading=12, alignment=TA_RIGHT)
    add("rScenL", fontName="Helvetica-Bold", fontSize=8, textColor=INK, leading=12)
    return ss


def _rule(color=HAIR, thick=0.5, sb=0, sa=0):
    return HRFlowable(width="100%", thickness=thick, color=color, spaceBefore=sb, spaceAfter=sa)


def _sec(title, ss):
    """Cabeceira de sección: texto en versalitas grises. title debe vir xa en
    maiúsculas (non se forza, para respectar tags HTML como <font>)."""
    p = Paragraph(title, ss["rSec"])
    return p


def _header(data, ss, logo_path):
    """Cabeceira editorial: logo pequeno (firma) + kicker + título + subtítulo."""
    left = []
    left.append(Paragraph("INFORME PREVIO", ss["rKicker"]))
    # colorear "UD Ourense" en vermello; o rival queda en tinta
    def color_udo(txt):
        return txt.replace("UD Ourense", "<font color='#C8102E'>UD Ourense</font>")
    title_txt = color_udo(f"{data['home']} · {data['away']}")
    left.append(Paragraph(title_txt, ss["rTitle"]))
    left.append(Paragraph(f"Xornada {data['jornada']} · {data['venue_context']} · a nosa vida", ss["rSub"]))
    left_tbl = Table([[x] for x in left], colWidths=[CONTENT_W - 20 * mm])
    left_tbl.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0),
                                  ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                  ("TOPPADDING", (0, 0), (-1, -1), 0),
                                  ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    if logo_path and Path(logo_path).exists():
        logo = Image(str(logo_path), width=14 * mm, height=14 * mm)
        row = Table([[left_tbl, logo]], colWidths=[CONTENT_W - 20 * mm, 20 * mm])
        row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                 ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                                 ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                 ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
        return row
    return left_tbl


def _metrics_row(items, ss):
    """Fila de métricas 'ao espido': número grande, etiqueta pequena debaixo. Sen bordes.
    Cada item pode ser (valor, etiqueta) ou (valor, etiqueta, cor_do_número)."""
    minis = []
    n = len(items)
    for it in items:
        val, lab = it[0], it[1]
        col = it[2] if len(it) > 2 else INK
        num_style = ParagraphStyle("rn", parent=ss["rMetricN"], textColor=col)
        num = Paragraph(str(val), num_style)
        label = Paragraph(lab.upper(), ss["rMetricL"])
        t = Table([[num], [label]], colWidths=[CONTENT_W / n])
        t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                               ("TOPPADDING", (0, 0), (0, 0), 0),
                               ("BOTTOMPADDING", (0, 0), (0, 0), 2),
                               ("TOPPADDING", (0, 1), (0, 1), 0)]))
        minis.append(t)
    row = Table([minis], colWidths=[CONTENT_W / n] * n)
    row.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                             ("TOPPADDING", (0, 0), (-1, -1), 2),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                             ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return row


def _kv_block(title, rows, ss):
    """Bloque de datos: título de sección + pares clave→valor con liñas finísimas."""
    els = [_sec(title, ss)]
    body = [[Paragraph(str(k), ss["rKVk"]), Paragraph(str(v), ss["rKVv"])] for k, v in rows]
    t = Table(body, colWidths=[(CONTENT_W / 2 - 6 * mm) * 0.60, (CONTENT_W / 2 - 6 * mm) * 0.40])
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, HAIR),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    els.append(t)
    return els


def build_report(data: dict, logo_path: str | None = None) -> bytes:
    ss = _styles()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=14 * mm, bottomMargin=12 * mm,
                            title=f"Informe {data['home']} vs {data['away']}")
    S = []
    S.append(_header(data, ss, logo_path))
    S.append(Spacer(1, 5))
    S.append(_rule(INK, 1.0, sa=7))

    # ---- Métricas ao espido: predición + marcador esperado ----
    S.append(_metrics_row([
        (f"{data['p_win']}%", "Vitoria", C_WIN),
        (f"{data['p_draw']}%", "Empate", C_DRAW),
        (f"{data['p_loss']}%", "Derrota", C_LOSS),
        (f"{data['expected_score'][0]}–{data['expected_score'][1]}", "Marcador esperado"),
        (f"{data['og_home']}", data.get("og_home_label", "oGoals")),
        (f"{data['og_away']}", data.get("og_away_label", "oGoals")),
    ], ss))
    S.append(Spacer(1, 6))

    lead = (f"{data['favor_text']} O contexto do encontro {data['venue_place']} "
            f"{data['venue_text']}")
    if data.get("intro_value"):
        lead += f" {data['intro_value']}"
    S.append(Paragraph(lead, ss["rLead"]))
    S.append(Spacer(1, 5))
    S.append(_rule(HAIR, 0.5, sa=6))

    # ---- Dous bloques enfrontados: rival / nós ----
    rival_name = data['away'] if data['is_home'] else data['home']
    left = _kv_block(f"Como chega · {rival_name}", [
        ("Goles a favor", data["rival"]["gf"]),
        ("Goles en contra", data["rival"]["ga"]),
        ("xG xerado", data["rival"]["xgf"]),
        ("xG concedido", data["rival"]["xga"]),
        ("Forma", data["rival"]["form_label"]),
    ], ss)
    right = _kv_block("Como chegamos · <font color='#C8102E'>UD Ourense</font>", [
        ("Goles a favor", data["udo"]["gf"]),
        ("Goles en contra", data["udo"]["ga"]),
        ("xG xerado", data["udo"]["xgf"]),
        ("Puntería", data["udo"]["finish_label"]),
        ("Solidez", data["udo"]["defense_label"]),
    ], ss)
    cols = Table([[left, right]], colWidths=[CONTENT_W / 2, CONTENT_W / 2])
    cols.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("LEFTPADDING", (0, 0), (0, 0), 0),
                              ("RIGHTPADDING", (0, 0), (0, 0), 12),
                              ("LEFTPADDING", (1, 0), (1, 0), 12),
                              ("RIGHTPADDING", (1, 0), (1, 0), 0),
                              ("LINEBEFORE", (1, 0), (1, 0), 0.5, HAIR)]))
    S.append(cols)
    S.append(Spacer(1, 7))

    # ---- Estado dos xogadores: táboa SEN bordes, só cabeceira con liña ----
    S.append(_sec("Estado dos nosos xogadores", ss))
    if data["players"]:
        head = [Paragraph("XOGADOR", ss["rMetricL"]), Paragraph("POS", ss["rMetricL"]),
                Paragraph("ORATING", ss["rMetricL"]), Paragraph("FORMA", ss["rMetricL"])]
        rows = [head]
        for p in data["players"][:6]:
            rows.append([
                Paragraph(p["name"], ss["rKVk"]),
                Paragraph(p["pos"], ss["rKVk"]),
                Paragraph(f"<b>{p['oRating']}</b>", ParagraphStyle("r", parent=ss["rKVk"], textColor=INK)),
                Paragraph(p.get("form_txt", "—"), ss["rSmall"]),
            ])
        pt = Table(rows, colWidths=[CONTENT_W * 0.42, CONTENT_W * 0.13, CONTENT_W * 0.18, CONTENT_W * 0.27])
        pt.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK),
            ("LINEBELOW", (0, 1), (-1, -2), 0.4, HAIR),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("ALIGN", (1, 0), (2, -1), "LEFT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        S.append(pt)
    else:
        S.append(Paragraph("Aínda sen datos de rendemento dos xogadores nesta tempada.", ss["rSmall"]))
    S.append(Spacer(1, 8))

    # ================= claves e plan =================
    # Que funciona / que evitar, en dúas columnas editoriais
    def bullets(title, items):
        els = [_sec(title, ss)]
        for it in items:
            els.append(Paragraph(f"—&nbsp;&nbsp;{it}", ss["rTip"]))
            els.append(Spacer(1, 3))
        return els

    colA = bullets("Que funciona", data["keys_for"])
    colB = bullets("Que evitar", data["keys_against"])
    kk = Table([[colA, colB]], colWidths=[CONTENT_W / 2, CONTENT_W / 2])
    kk.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (0, 0), 0),
                            ("RIGHTPADDING", (0, 0), (0, 0), 12),
                            ("LEFTPADDING", (1, 0), (1, 0), 12),
                            ("RIGHTPADDING", (1, 0), (1, 0), 0)]))
    S.append(kk)
    S.append(Spacer(1, 6))
    S.append(_rule(HAIR, 0.5, sa=6))

    # ---- Contexto de dinámica recente (noticias, só se hai) ----
    if data.get("context_news"):
        S.append(_sec("Dinámica recente", ss))
        S.append(Paragraph(data["context_news"], ss["rBody"]))
        S.append(_rule(HAIR, 0.5, sa=6))

    # ---- Escenarios ----
    S.append(_sec("Como cambia segundo o escenario", ss))
    S.append(Paragraph(data["venue_analysis"], ss["rBody"]))
    S.append(Spacer(1, 5))
    scen = Table([
        [Paragraph("SE MARCAMOS PRIMEIRO", ss["rMetricL"]), Paragraph(data["scenario_lead"], ss["rBody"])],
        [Paragraph("SE ENCAIXAMOS PRIMEIRO", ss["rMetricL"]), Paragraph(data["scenario_behind"], ss["rBody"])],
    ], colWidths=[CONTENT_W * 0.24, CONTENT_W * 0.76])
    scen.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 0.4, HAIR),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (0, 0), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    S.append(scen)
    S.append(Spacer(1, 6))

    # ---- Consellos ----
    S.append(_sec("Consellos", ss))
    for i, tip in enumerate(data["advice"], 1):
        S.append(Paragraph(f"<font color='#C8102E'><b>{i:02d}</b></font>&nbsp;&nbsp;{tip}", ss["rTip"]))
        S.append(Spacer(1, 4))

    S.append(Spacer(1, 7))
    S.append(_rule(HAIR, 0.5, sa=4))
    S.append(Paragraph("Xerado automaticamente a partir de datos reais de rendemento, xG e "
                       "probabilidades · Ourense é UD", ss["rSmall"]))

    # ============ SEGUNDA PÁXINA: análise táctico (se hai) ============
    ap = data.get("analysis_page")
    if ap:
        S.append(PageBreak())
        S += _analysis_page(ap, data, ss)

    doc.build(S)
    return buf.getvalue()


def _analysis_page(ap: dict, data: dict, ss) -> list:
    """Renderiza a 2ª páxina: análise táctico do rival (datos reais), estilo do informe."""
    rival_name = data['away'] if data['is_home'] else data['home']
    S = []
    # cabeceira da páxina
    S.append(Paragraph("Análise táctico", ss["rTitle"]))
    S.append(Paragraph(f"Radiografía do rival · <b>{rival_name}</b>", ss["rSub"]))
    S.append(Spacer(1, 4))
    S.append(_rule(INK, 1.0, sa=7))

    # debilidade estrutural
    if ap.get("key_weakness"):
        S.append(_sec("A herida do rival", ss))
        S.append(Paragraph(ap["key_weakness"], ss["rBody"]))
        S.append(Spacer(1, 4))

    # 3 directrices innegociables
    if ap.get("directives"):
        S.append(_sec("Directrices innegociables", ss))
        for i, d in enumerate(ap["directives"][:3], 1):
            S.append(Paragraph(f"<font color='#C8102E'><b>{i:02d}</b></font>&nbsp;&nbsp;{d}", ss["rTip"]))
            S.append(Spacer(1, 3))
        S.append(Spacer(1, 3))

    # matchups: VANTAXE / RISCO / DESVANTAXE
    if ap.get("matchups"):
        S.append(_sec("Cruces de datos", ss))
        tag_color = {"VANTAXE": "#1a8a4a", "RISCO": "#c99700", "DESVANTAXE": "#c0392b"}
        rows = []
        for mu in ap["matchups"]:
            tag = (mu.get("tag") or "").upper()
            col = tag_color.get(tag, "#555555")
            rows.append([
                Paragraph(f"<font color='{col}'><b>{tag}</b></font>", ss["rScenL"]),
                Paragraph(mu.get("text", ""), ss["rBody"]),
            ])
        t = Table(rows, colWidths=[CONTENT_W * 0.22, CONTENT_W * 0.78])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW", (0, 0), (-1, -2), 0.4, HAIR),
        ]))
        S.append(t)
        S.append(Spacer(1, 6))

    # game plan (con / sen balón)
    if ap.get("gameplan_with") or ap.get("gameplan_without"):
        S.append(_sec("Plan de partido", ss))
        gp = Table([
            [Paragraph("CON BALÓN", ss["rMetricL"]), Paragraph(ap.get("gameplan_with", ""), ss["rBody"])],
            [Paragraph("SEN BALÓN", ss["rMetricL"]), Paragraph(ap.get("gameplan_without", ""), ss["rBody"])],
        ], colWidths=[CONTENT_W * 0.20, CONTENT_W * 0.80])
        gp.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW", (0, 0), (-1, 0), 0.4, HAIR),
        ]))
        S.append(gp)
        S.append(Spacer(1, 6))

    # momentum por minutos
    if ap.get("momentum"):
        S.append(_sec("Momentum e alertas", ss))
        for tr in ap["momentum"]:
            label = tr.get("label", "")
            txt = tr.get("text", "")
            S.append(Paragraph(f"<b>{label}</b> — {txt}", ss["rBody"]))
            S.append(Spacer(1, 3))

    S.append(Spacer(1, 6))
    S.append(_rule(HAIR, 0.5, sa=4))
    S.append(Paragraph("Análise táctico a partir de datos reais de eventos · Ourense é UD", ss["rSmall"]))
    return S
