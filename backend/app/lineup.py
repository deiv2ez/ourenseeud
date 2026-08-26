"""
lineup.py — Imaxe do once inicial (PNG 16:9) estilo día de partido.

Versión 2: máis minimalista e cos xogadores MÁIS GRANDES (inspiración: app do
Real Avilés). Cambios fronte á v1:
  - Fondo sólido (vermello UDO escuro) cun sutil degradado, sen campo detallado.
    Só unhas liñas finas de referencia. Menos ruído, máis foco nos xogadores.
  - Cada xogador é unha CAMISETA grande co dorsal dentro, non unha ficha pequena.
  - Nomes grandes e limpos debaixo.
  - Formacións elexibles. Xogadores como parámetro (o admin edítaos).

Uso:
    img = build_lineup(players=[...11...], formation="4-3-3",
                       title="UD OURENSE", subtitle="J1 · vs SD Ponferradina")
    img.save("once.png")
"""

from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

W, H = 1600, 900
RED = (200, 16, 46)
RED_DARK = (120, 12, 30)
RED_DEEP = (86, 8, 22)
WHITE = (248, 248, 248)
INK = (20, 20, 24)

FORMATIONS = {
    "4-3-3": [4, 3, 3],
    "4-4-2": [4, 4, 2],
    "3-5-2": [3, 5, 2],
    "5-3-2": [5, 3, 2],
    "4-2-3-1": [4, 2, 3, 1],
    "3-4-3": [3, 4, 3],
    "4-1-4-1": [4, 1, 4, 1],
}

FONT_DIR = Path("/usr/share/fonts")


def _font(size: int, bold: bool = False):
    cands = [
        "truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "truetype/dejavu/DejaVuSans.ttf",
        "truetype/liberation/LiberationSans-Bold.ttf" if bold else "truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for c in cands:
        p = FONT_DIR / c
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def _background(img: Image.Image):
    """Fondo sólido vermello con degradado vertical sutil (arriba máis escuro)."""
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(RED_DEEP[0] + (RED_DARK[0] - RED_DEEP[0]) * t)
        g = int(RED_DEEP[1] + (RED_DARK[1] - RED_DEEP[1]) * t)
        b = int(RED_DEEP[2] + (RED_DARK[2] - RED_DEEP[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    # liñas de referencia moi sutís (medio campo + círculo), en branco translúcido
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    od.line([70, H // 2, W - 70, H // 2], fill=(255, 255, 255, 22), width=2)
    od.ellipse([W // 2 - 90, H // 2 - 90, W // 2 + 90, H // 2 + 90], outline=(255, 255, 255, 22), width=2)
    img.alpha_composite(ov)


def _shirt(draw: ImageDraw.ImageDraw, cx: int, cy: int, name: str, number, scale: float = 1.0):
    """Debuxa unha camiseta co dorsal dentro e o nome debaixo."""
    w = int(84 * scale)   # ancho corpo
    h = int(78 * scale)   # alto corpo (máis baixo que antes para evitar solapes)
    sl = int(28 * scale)  # ombreiro/manga
    top = cy - h // 2

    body = WHITE
    # mangas
    draw.polygon([(cx - w // 2 - sl, top + sl // 2), (cx - w // 2, top),
                  (cx - w // 2, top + sl + 6), (cx - w // 2 - sl, top + sl + 3)], fill=body)
    draw.polygon([(cx + w // 2 + sl, top + sl // 2), (cx + w // 2, top),
                  (cx + w // 2, top + sl + 6), (cx + w // 2 + sl, top + sl + 3)], fill=body)
    # corpo
    draw.rounded_rectangle([cx - w // 2, top, cx + w // 2, top + h], radius=int(12 * scale), fill=body)
    # colo
    draw.rectangle([cx - int(14 * scale), top, cx + int(14 * scale), top + int(10 * scale)], fill=RED)
    # dorsal
    if number is not None:
        f = _font(int(42 * scale), bold=True)
        tw = draw.textlength(str(number), font=f)
        draw.text((cx - tw / 2, top + h // 2 - int(26 * scale)), str(number), font=f, fill=RED)
    # nome debaixo
    fn = _font(int(26 * scale), bold=True)
    tw = draw.textlength(name, font=fn)
    ny = top + h + int(8 * scale)
    draw.text((cx - tw / 2 + 1, ny + 1), name, font=fn, fill=(0, 0, 0))
    draw.text((cx - tw / 2, ny), name, font=fn, fill=WHITE)


def build_lineup(players: list[str], formation: str = "4-3-3",
                title: str = "UD OURENSE", subtitle: str = "",
                numbers: list[int] | None = None) -> Image.Image:
    if formation not in FORMATIONS:
        raise ValueError(f"Formación no soportada: {formation}. Opciones: {list(FORMATIONS)}")
    lines = FORMATIONS[formation]
    need = 1 + sum(lines)
    if len(players) != need:
        raise ValueError(f"{formation} requiere {need} jugadores, recibí {len(players)}")

    img = Image.new("RGBA", (W, H), RED_DEEP)
    _background(img)
    draw = ImageDraw.Draw(img, "RGBA")

    # cabeceira limpa
    draw.text((70, 46), title, font=_font(52, bold=True), fill=WHITE)
    if subtitle:
        draw.text((72, 108), subtitle, font=_font(26), fill=(255, 255, 255, 210))
    tf = _font(30, bold=True)
    tw = draw.textlength(formation, font=tf)
    # chip da formación
    draw.rounded_rectangle([W - tw - 96, 52, W - 56, 100], radius=24, fill=WHITE)
    draw.text((W - tw - 76, 60), formation, font=tf, fill=RED)

    # zona de xogo: repartimos en filas (porteiro + liñas) con celda propia
    scale = 1.05
    nums = numbers or list(range(1, need + 1))
    n_rows = 1 + len(lines)                 # porteiro + liñas de campo
    zone_top, zone_bottom = 200, H - 70
    cell_h = (zone_bottom - zone_top) / n_rows
    # centro vertical de cada fila (fila 0 = delanteira arriba ... última = porteiro)
    row_cy = [zone_top + cell_h * (i + 0.42) for i in range(n_rows)]

    idx = 0
    # players entra como [porteiro, liña1(defensa)..., liña2..., ...].
    # Visualmente pintamos de arriba (ataque) a abaixo, así que asignamos primeiro
    # os índices por liña e logo debuxamos cada liña na súa fila.
    line_players = []
    p = 1  # 0 é o porteiro
    for count in lines:
        line_players.append(list(range(p, p + count)))
        p += count

    # fila 0 (arriba) = última liña (ataque) ... fila n-1 = primeira liña (defensa)
    for row_from_top, line_idx in enumerate(reversed(range(len(lines)))):
        y = row_cy[row_from_top]
        ids = line_players[line_idx]
        count = len(ids)
        for pi, pidx in enumerate(ids):
            x = 150 + (pi + 1) * ((W - 300) / (count + 1))
            _shirt(draw, int(x), int(y), players[pidx], nums[pidx], scale=scale)

    # porteiro na última fila, centrado
    _shirt(draw, W // 2, int(row_cy[-1]), players[0], nums[0], scale=scale)

    # pé discreto
    draw.text((70, H - 46), "ourenseeud.vercel.app", font=_font(22, bold=True), fill=(255, 255, 255, 150))

    return img.convert("RGB")
