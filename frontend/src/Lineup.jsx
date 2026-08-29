import { useEffect, useState, useRef, useCallback } from "react";
import { api } from "./lib/api";

const RED = "#C8102E";

// cor do badge de oRating (igual que na plantilla)
function ratingColor(r) {
  if (r == null) return "#c4c4c4";
  if (r >= 7.0) return "#1a8a4a";
  if (r >= 6.3) return "#c99700";
  return "#b06a3b";
}

// escudo minimalista do rival
function RivalCrest({ slug, size = 28 }) {
  const [ok, setOk] = useState(true);
  if (ok && slug) {
    return <img src={`/escudos/${slug}.png`} alt="" onError={() => setOk(false)}
      style={{ width: size, height: size, objectFit: "contain" }} />;
  }
  return <span className="grid place-items-center rounded-full bg-neutral-200 text-[10px] font-bold text-neutral-500"
    style={{ width: size, height: size }}>?</span>;
}

// apelido curto para amosar debaixo do nodo
function shortName(display, name) {
  const n = (display || name || "").trim();
  if (!n) return "";
  const parts = n.split(/\s+/);
  return parts.length > 1 ? parts[parts.length - 1] : n;
}

export default function Lineup({ t, token: tokenProp }) {
  // token: do prop (admin) ou de sessionStorage (se xa fixo login nesta sesión)
  const token = tokenProp || (typeof window !== "undefined" ? sessionStorage.getItem("udo_token") : null);
  const [formations, setFormations] = useState({});
  const [days, setDays] = useState({ played: [], next: null });
  const [sel, setSel] = useState(null);        // jornada seleccionada
  const [formation, setFormation] = useState("4-2-3-1");
  const [onField, setOnField] = useState([]);   // [{name,display,x,y,role,oRating}]
  const [context, setContext] = useState(null);
  const [isPast, setIsPast] = useState(false);
  const [squad, setSquad] = useState([]);
  const [loading, setLoading] = useState(true);
  const [picking, setPicking] = useState(null); // índice do slot a asignar
  const [search, setSearch] = useState("");      // buscador do banco
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  // carga inicial
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [f, md, sq] = await Promise.all([
          api.lineupFormations(), api.lineupMatchdays(), api.squad(),
        ]);
        if (!alive) return;
        setFormations(f.formations || {});
        setDays(md);
        setSquad(Array.isArray(sq) ? sq : []);
        // selección por defecto: próxima jornada, ou a última xogada
        const def = md.next || (md.played.length ? md.played[md.played.length - 1] : null);
        if (def) selectDay(def);
      } catch { /* noop */ }
      finally { if (alive) setLoading(false); }
    })();
    return () => { alive = false; };
  }, []);

  const selectDay = useCallback(async (day) => {
    setSel(day); setIsPast(day.kind === "played"); setMsg(""); setPicking(null);
    try {
      const lu = await api.lineup(day.jornada);
      setFormation(lu.formation || "4-2-3-1");
      setContext(lu.context);
      setOnField((lu.players || []).map((p) => ({
        name: p.name || null, display: p.display || null,
        x: p.x, y: p.y, role: p.role, oRating: p.oRating ?? null,
      })));
    } catch { /* noop */ }
  }, []);

  // cambiar formación: recolocar os nodos nas novas coordenadas, mantendo os jugadores
  const changeFormation = (f) => {
    const coords = formations[f];
    if (!coords) return;
    setFormation(f);
    setOnField((prev) => coords.map((c, i) => ({
      name: prev[i]?.name || null, display: prev[i]?.display || null,
      oRating: prev[i]?.oRating ?? null,
      x: c.x, y: c.y, role: c.role,
    })));
  };

  // jugadores no campo (nomes ocupados)
  const usedNames = new Set(onField.map((p) => p.name).filter(Boolean));
  const bench = squad
    .filter((p) => !usedNames.has(p.name))
    .filter((p) => {
      if (!search.trim()) return true;
      const q = search.toLowerCase();
      return (p.display || p.name || "").toLowerCase().includes(q)
          || (p.name || "").toLowerCase().includes(q)
          || String(p.dorsal ?? "").includes(q);
    });

  const assign = (player) => {
    if (picking == null) return;
    setOnField((prev) => prev.map((p, i) => i === picking
      ? { ...p, name: player.name, display: player.display || player.name, oRating: null }
      : p));
    setPicking(null);
    setSearch("");
  };

  const clearSlot = (i) => setOnField((prev) => prev.map((p, j) =>
    j === i ? { ...p, name: null, display: null, oRating: null } : p));

  const save = async () => {
    if (!token) { setMsg("Só o admin pode gardar (entra en #admin)."); return; }
    setBusy(true); setMsg("");
    try {
      const players = onField.map((p) => ({ name: p.name, x: p.x, y: p.y, role: p.role }));
      await api.adminSaveLineup(token, sel.jornada, formation, players);
      setMsg("✓ Aliñación gardada.");
    } catch { setMsg("✗ Erro ao gardar."); }
    finally { setBusy(false); }
  };

  if (loading) return <div className="py-16 text-center text-sm text-neutral-400">Cargando…</div>;

  return (
    <div>
      <div className="mb-4">
        <h1 className="text-xl font-black tracking-tight" style={{ color: RED }}>Once inicial</h1>
        <p className="text-sm text-neutral-500">
          {isPast ? "Aliñación e notas do partido" : "Arma o teu once para o próximo partido"}
        </p>
      </div>

      {/* selector de jornada */}
      <div className="scroll-x mb-4 flex gap-2 pb-1">
        {days.next && (
          <button onClick={() => selectDay(days.next)}
            className={`tap shrink-0 rounded-lg border px-3 py-2 text-xs font-bold ${sel?.jornada === days.next.jornada ? "border-transparent text-white" : "border-neutral-200 bg-white text-neutral-600"}`}
            style={sel?.jornada === days.next.jornada ? { backgroundColor: RED } : undefined}>
            Próxima · J{days.next.jornada}
          </button>
        )}
        {days.played.slice().reverse().map((d) => (
          <button key={d.jornada} onClick={() => selectDay(d)}
            className={`tap shrink-0 rounded-lg border px-3 py-2 text-xs font-bold ${sel?.jornada === d.jornada ? "border-transparent text-white" : "border-neutral-200 bg-white text-neutral-600"}`}
            style={sel?.jornada === d.jornada ? { backgroundColor: RED } : undefined}>
            J{d.jornada} {d.has_lineup ? "" : "·"}
          </button>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_300px]">
        {/* CAMPO 3D */}
        <div>
          <Pitch onField={onField} isPast={isPast} onSlotClick={(i) => {
            if (isPast) return;
            if (onField[i].name) clearSlot(i); else setPicking(i);
          }} pickingIndex={picking} />
          {context && (
            <div className="mt-2 flex items-center justify-center gap-2 text-sm text-neutral-600">
              <span className="font-semibold">{context.is_home ? "UD Ourense" : context.rival}</span>
              {isPast && context.score && context.score[0] != null && (
                <span className="font-black">{context.is_home ? context.score[0] : context.score[1]}-{context.is_home ? context.score[1] : context.score[0]}</span>
              )}
              <RivalCrest slug={context.rival_slug} size={20} />
              <span className="text-neutral-400">{context.is_home ? context.rival : "UD Ourense"}</span>
            </div>
          )}
        </div>

        {/* PANEL LATERAL */}
        <aside className="rounded-xl border border-neutral-200 bg-white p-4">
          {/* rival */}
          {context && (
            <div className="mb-4 flex items-center gap-2 border-b border-neutral-100 pb-3">
              <RivalCrest slug={context.rival_slug} size={32} />
              <div>
                <div className="text-[10px] uppercase text-neutral-400">{context.is_home ? "Local vs" : "Visitante en"}</div>
                <div className="text-sm font-bold">{context.rival}</div>
              </div>
            </div>
          )}

          {/* formación */}
          <label className="block text-[10px] font-bold uppercase text-neutral-400">Formación</label>
          <select value={formation} onChange={(e) => changeFormation(e.target.value)} disabled={isPast}
            className="mt-1 w-full rounded-lg border border-neutral-300 px-2 py-2 text-sm font-semibold disabled:opacity-60">
            {Object.keys(formations).map((f) => <option key={f} value={f}>{f}</option>)}
          </select>

          {/* banquillo / selector */}
          {!isPast && (
            <div className="mt-4">
              <div className="mb-2 text-[10px] font-bold uppercase text-neutral-400">
                {picking != null ? "Elixe xogador para o oco" : "Banco"}
              </div>
              <input value={search} onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar xogador…"
                className="mb-2 w-full rounded-md border border-neutral-300 px-2 py-1.5 text-sm" />
              <div className="max-h-[320px] space-y-1 overflow-y-auto">
                {bench.map((p) => (
                  <button key={p.name} onClick={() => assign(p)} disabled={picking == null}
                    className={`tap flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-sm ${picking != null ? "bg-neutral-50 hover:bg-red-50" : "opacity-60"}`}>
                    <span className="truncate">
                      <span className="mr-1.5 inline-block w-5 text-center text-xs font-bold text-neutral-400">{p.dorsal ?? "–"}</span>
                      {p.display || p.name}
                    </span>
                    <span className="text-[10px] uppercase text-neutral-400">{p.pos}</span>
                  </button>
                ))}
                {bench.length === 0 && <p className="text-xs text-neutral-400">{search ? "Sen resultados." : "Todos no campo."}</p>}
              </div>
            </div>
          )}

          {msg && <p className="mt-3 text-sm font-medium" style={{ color: msg.startsWith("✓") ? "#1a8a4a" : "#c0392b" }}>{msg}</p>}

          {!isPast && token && (
            <button onClick={save} disabled={busy}
              className="tap mt-4 w-full rounded-lg py-2.5 text-sm font-bold text-white disabled:opacity-50"
              style={{ backgroundColor: RED }}>
              {busy ? "Gardando…" : "Gardar aliñación"}
            </button>
          )}
        </aside>
      </div>
    </div>
  );
}

/* ---------- Campo 3D: céspede inclinado + nodos nunha capa plana superposta ----------
   O céspede vai INCLINADO (perspectiva de cámara de TV). Os nodos van nunha capa á parte,
   plana e frontal á cámara, para non quedar "tumbados". O mapeo projectTop comprime o eixo
   Y para que os nodos caian sobre o punto correcto do campo inclinado. */
function Pitch({ onField, isPast, onSlotClick, pickingIndex }) {
  // O rotateX inclina o campo: a parte de arriba (rival) vai máis lonxe/comprimida e a de
  // abaixo (propia) máis preto/ancha. Reproducimos ese sesgo no posicionamento dos nodos:
  //  - top de arriba (rival) empeza máis abaixo do bordo (o campo "afúndese" ao lonxe)
  //  - o rango comprímese arriba e ábrese abaixo.
  const projectTop = (y) => {
    const top = 100 - y;           // 0 = área rival (arriba), 100 = área propia (abaixo)
    const t = top / 100;
    // curva suave: arriba xúntanse, abaixo sepáranse (imita a perspectiva).
    // rango 18%..96%: baixado para que ningún nodo se saia por arriba (o dianteiro
    // centro quedaba fóra do campo). O céspede inclinado ocupa esa franxa vertical.
    const eased = t * t * 0.40 + t * 0.60;   // 0..1
    return 22 + eased * 72;                    // 22%..94%
  };
  return (
    <div style={{ perspective: "760px", perspectiveOrigin: "center 30%" }}
      className="mx-auto w-full max-w-[560px]">
      <div style={{ position: "relative", aspectRatio: "3 / 4", transformStyle: "preserve-3d" }}>
        {/* CAPA 1: céspede INCLINADO (só fondo) */}
        <div style={{
          position: "absolute", inset: 0,
          transform: "rotateX(38deg)", transformOrigin: "center bottom",
          borderRadius: 10, overflow: "hidden",
          backgroundImage: "repeating-linear-gradient(0deg, #81C784 0, #81C784 10%, #66BB6A 10%, #66BB6A 20%)",
          boxShadow: "0 30px 50px -20px rgba(0,0,0,0.4)",
        }}>
          <PitchLines />
        </div>
        {/* CAPA 2: nodos, plana e frontal á cámara */}
        <div style={{ position: "absolute", inset: 0 }}>
          {onField.map((p, i) => (
            <PlayerNode key={i} p={p} isPast={isPast} picking={pickingIndex === i}
              top={projectTop(p.y)} left={p.x} onClick={() => onSlotClick(i)} />
          ))}
        </div>
      </div>
    </div>
  );
}

function PitchLines() {
  const line = "rgba(255,255,255,0.5)";
  return (
    <svg viewBox="0 0 100 133" preserveAspectRatio="none"
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}>
      <g fill="none" stroke={line} strokeWidth="0.4">
        <rect x="3" y="3" width="94" height="127" />
        <line x1="3" y1="66.5" x2="97" y2="66.5" />
        <circle cx="50" cy="66.5" r="11" />
        {/* área abaixo (propia) */}
        <rect x="26" y="3" width="48" height="18" />
        <rect x="39" y="3" width="22" height="7" />
        {/* área arriba (rival) */}
        <rect x="26" y="112" width="48" height="18" />
        <rect x="39" y="123" width="22" height="7" />
      </g>
    </svg>
  );
}

function PlayerNode({ p, isPast, picking, top, left, onClick }) {
  const empty = !p.name;
  return (
    <div onClick={onClick}
      style={{
        position: "absolute", left: `${left}%`, top: `${top}%`,
        // capa plana: só centramos. Sen rotateX → totalmente frontal á cámara.
        transform: "translate(-50%, -50%)",
        cursor: isPast ? "default" : "pointer",
        zIndex: Math.round(top),
        // nitidez do texto: forzar renderizado en capa propia sen suavizado raro
        willChange: "transform",
      }}>
      <div className="flex flex-col items-center gap-1">
        {empty ? (
          <div className="grid place-items-center rounded-full border-2 border-dashed"
            style={{ width: 56, height: 56, borderColor: picking ? RED : "rgba(120,120,120,0.75)",
                     background: "rgba(255,255,255,0.12)", color: picking ? RED : "#777" }}>
            <span className="text-3xl leading-none">+</span>
          </div>
        ) : (
          <div className="relative">
            {/* camiseta: PNG personalizado (camiseta.png). Fallback a SVG abstracto. */}
            <Shirt />
            {/* badge de oRating (só pasados) — estética da sección Plantilla:
                cadrado redondeado, font-black, cor de fondo segundo a nota. */}
            {isPast && p.oRating != null && (
              <span className="absolute -right-2 -top-2 grid place-items-center rounded-lg font-black text-white"
                style={{ width: 26, height: 26, fontSize: 12, backgroundColor: ratingColor(p.oRating),
                         boxShadow: "0 2px 5px rgba(0,0,0,0.3)" }}>
                {p.oRating.toFixed(1)}
              </span>
            )}
          </div>
        )}
        {!empty && (
          <span style={{
            maxWidth: 104, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
            fontSize: 14, fontWeight: 800, lineHeight: 1.1, color: "#fff",
            padding: "1px 6px", borderRadius: 4, background: "rgba(0,0,0,0.6)",
            // nitidez: evitar subpíxel borroso ao centrar
            transform: "translateZ(0)",
            textShadow: "0 1px 1px rgba(0,0,0,0.4)",
          }}>
            {shortName(p.display, p.name)}
          </span>
        )}
      </div>
    </div>
  );
}

/* Camiseta: intenta cargar /camiseta.png; se non existe, cae a un SVG abstracto.
   Tamaño ~+35% respecto á versión anterior (de 34 a 46px). */
function Shirt() {
  const [ok, setOk] = useState(true);
  const size = 75;
  if (ok) {
    return <img src="/camiseta.png" alt="" onError={() => setOk(false)}
      style={{ width: size, height: size, objectFit: "contain",
               filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.32))" }} draggable={false} />;
  }
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={RED} aria-hidden
      style={{ filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.32))" }}>
      <path d="M9 2 L4 5 L6 9 L8 8 V21 H16 V8 L18 9 L20 5 L15 2 C14 3.5 10 3.5 9 2 Z" />
    </svg>
  );
}
