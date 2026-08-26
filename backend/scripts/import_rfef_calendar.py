import sys, json, re
sys.path.insert(0, "/home/claude/udo-tracker/backend")
from app.store import NAMES, save, load

# Texto del calendario oficial (pegado del PDF vía fetch)
CAL = open("/tmp/cal_text.txt", encoding="utf-8").read()

# Mapa nombres PDF (RFEF) → nuestros nombres canónicos en store.NAMES
MAP = {
    'Arenas Club': 'Arenas Club',
    'Athletic Club "B"': 'Bilbao Athletic',
    'Barakaldo CF': 'Barakaldo CF',
    'CD Coria': 'CD Coria',
    'CD Extremadura': 'CD Extremadura',
    'CD Lugo': 'CD Lugo',
    'CD Mirandés': 'CD Mirandés',
    'CyD Leonesa': 'CyD Leonesa',
    'AD Mérida': 'AD Mérida',
    'Pontevedra CF': 'Pontevedra CF',
    'Racing Club Ferrol': 'Racing Ferrol',
    'RC Deportivo Fabril': 'RC Deportivo Fabril',
    'Real Avilés Industrial': 'Real Avilés',
    'Real Unión Club': 'Real Unión',
    'SD Ponferradina': 'SD Ponferradina',
    'UD Logroñés': 'UD Logroñés',
    'UD Ourense': 'UD Ourense',
    'Unionistas de Salamanca CF': 'Unionistas',
    'CP Cacereño': 'CP Cacereño',
    'Zamora CF': 'Zamora CF',
}
# nombres del PDF ordenados por longitud desc para no romper al hacer split
pdf_names = sorted(MAP.keys(), key=len, reverse=True)

def split_teams(line):
    """Una línea del PDF tiene 'Local Visitante' pegados. Separa por nombres conocidos."""
    line = line.strip()
    for h in pdf_names:
        if line.startswith(h):
            rest = line[len(h):].strip()
            if rest in MAP:
                return h, rest
    return None

remaining = []
cur_j = None
date_re = re.compile(r'Jornada (\d+) \((\d{2})/(\d{2})/(\d{4})\)')
dates = {}
for raw in CAL.splitlines():
    line = raw.strip()
    m = date_re.search(line)
    if m:
        cur_j = int(m.group(1))
        dates[cur_j] = f"{m.group(4)}-{m.group(3)}-{m.group(2)}"
        continue
    if cur_j is None: continue
    # saltar cabeceras/pies
    if any(x in line for x in ["Primera Federación","GRUPO","Calendario","2026/2027","29/06/2026","Real Federación","/13"]):
        continue
    pair = split_teams(line)
    if pair:
        h, a = pair
        remaining.append({"jornada": cur_j, "home": MAP[h], "away": MAP[a], "date": dates.get(cur_j)})

# validación
from collections import Counter
c = Counter()
for m in remaining:
    c[m["home"]]+=1; c[m["away"]]+=1
print(f"Partidos totales: {len(remaining)} (esperado 380)")
print(f"Jornadas: {len(set(m['jornada'] for m in remaining))} (esperado 38)")
print(f"Partidos por equipo: {set(c.values())} (esperado {{38}})")
print(f"Equipos: {len(c)} (esperado 20)")
# verificar que todos los nombres son canónicos
unknown = set(c.keys()) - set(NAMES)
print(f"Nombres no reconocidos: {unknown if unknown else 'ninguno ✓'}")
# J1
j1 = [m for m in remaining if m["jornada"]==1]
print(f"\nJornada 1 ({dates[1]}):")
for m in j1: print(f"  {m['home']} - {m['away']}" + ("  ← UDO" if "Ourense" in (m['home'],m['away']) else ""))

# guardar temporada A CERO (played vacío, todo remaining)
data = load()
data["played"] = []
data["remaining"] = remaining
data["odds"] = {}
save(data)
print("\n✓ season_2026_27.json guardado A CERO con calendario oficial")
