import { useEffect, useState, useRef, useCallback } from "react";
import { api } from "./lib/api";

const RED = "#C8102E";

// cor do badge de oRating (igual que na plantilla)
// Código de cores do oRating (6 tramos), igual que na Plantilla.
function ratingColor(r) {
  if (r == null) return "#c4c4c4";
  if (r >= 9.0) return "#0ea5e9";   // Estelar (celeste)
  if (r >= 8.0) return "#1a8a4a";   // Excelente (verde escuro)
  if (r >= 7.0) return "#4ade80";   // Notable (verde claro)
  if (r >= 6.0) return "#c99700";   // Ben (ámbar)
  if (r >= 5.0) return "#e67e22";   // Suficiente (laranxa)
  return "#c0392b";                  // Insuficiente (vermello)
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
  const [editing, setEditing] = useState(false);   // modo edición (tamén en pasados)
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
    setEditing(day.kind !== "played");   // futuro: edición; pasado: lectura (pódese activar)
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
    })
    .sort((a, b) => {
      // ordenar por dorsal (os que non teñen, ao final)
      const da = a.dorsal ?? 999, db = b.dorsal ?? 999;
      return da - db;
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

  // ------- compartir aliñación (descargar imaxe / X) -------
  const [sharing, setSharing] = useState(false);

  // Debuxa o campo nun canvas (vista cenital limpa). Garante que o fondo SEMPRE aparece
  // (html2canvas non captura ben o gradiente inclinado 3D).
  const buildCanvas = async () => {
    const W = 800, H = 1100;
    const cv = document.createElement("canvas");
    cv.width = W; cv.height = H;
    const ctx = cv.getContext("2d");

    // franxas de céspede
    const bands = 10;
    for (let i = 0; i < bands; i++) {
      ctx.fillStyle = i % 2 === 0 ? "#81C784" : "#66BB6A";
      ctx.fillRect(0, (H / bands) * i, W, H / bands);
    }
    // liñas do campo
    ctx.strokeStyle = "rgba(255,255,255,0.55)"; ctx.lineWidth = 3;
    const m = 24;
    ctx.strokeRect(m, m, W - 2 * m, H - 2 * m);
    ctx.beginPath(); ctx.moveTo(m, H / 2); ctx.lineTo(W - m, H / 2); ctx.stroke();
    ctx.beginPath(); ctx.arc(W / 2, H / 2, 90, 0, Math.PI * 2); ctx.stroke();
    // áreas
    const aw = 360, ah = 150, ax = (W - aw) / 2;
    ctx.strokeRect(ax, m, aw, ah);
    ctx.strokeRect(ax, H - m - ah, aw, ah);

    // título
    ctx.fillStyle = "#C8102E"; ctx.font = "bold 34px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("Once · UD Ourense", W / 2, 60);
    ctx.fillStyle = "#333"; ctx.font = "600 22px system-ui, sans-serif";
    ctx.fillText(shareLabel().replace("Once da UD Ourense · ", ""), W / 2, 92);

    // carga a camiseta (png ou fallback)
    const loadImg = (src) => new Promise((res) => {
      const im = new Image(); im.crossOrigin = "anonymous";
      im.onload = () => res(im); im.onerror = () => res(null); im.src = src;
    });
    const shirt = await loadImg("/camiseta.png");
    const shirtGK = await loadImg("/camiseta_portero.png");

    // nodos (usa a mesma proxección invertida: y=0 abaixo)
    for (const p of onField) {
      if (!p.name) continue;
      const cx = (p.x / 100) * (W - 120) + 60;
      const cy = ((100 - p.y) / 100) * (H - 180) + 120;
      const s = 88;
      const img = p.role === "POR" ? (shirtGK || shirt) : shirt;
      if (img) {
        ctx.drawImage(img, cx - s / 2, cy - s / 2, s, s);
      } else {
        ctx.fillStyle = p.role === "POR" ? "#e0a500" : "#C8102E";
        ctx.beginPath(); ctx.arc(cx, cy, s / 3, 0, Math.PI * 2); ctx.fill();
      }
      // badge de nota (só pasados con oRating)
      if (showRatings && p.oRating != null) {
        const bx = cx + s / 2 - 8, by = cy - s / 2 + 8, br = 20;
        ctx.fillStyle = ratingColor(p.oRating);
        ctx.beginPath();
        if (ctx.roundRect) ctx.roundRect(bx - br, by - br, br * 2, br * 2, 6);
        else ctx.rect(bx - br, by - br, br * 2, br * 2);
        ctx.fill();
        ctx.fillStyle = "#fff"; ctx.font = "900 20px system-ui, sans-serif";
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.fillText(p.oRating.toFixed(1), bx, by);
        ctx.textBaseline = "alphabetic";
      }
      // nome
      const label = shortName(p.display, p.name);
      ctx.font = "800 22px system-ui, sans-serif";
      const tw = ctx.measureText(label).width;
      ctx.fillStyle = "rgba(0,0,0,0.6)";
      const pad = 8, lh = 30;
      ctx.fillRect(cx - tw / 2 - pad, cy + s / 2 + 2, tw + pad * 2, lh);
      ctx.fillStyle = "#fff"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText(label, cx, cy + s / 2 + 2 + lh / 2);
      ctx.textBaseline = "alphabetic";
    }
    return cv;
  };

  const shareLabel = () => {
    const rival = context?.rival || "";
    const jTxt = `${t.tpJ}${sel?.jornada ?? ""}`;
    return `Once da UD Ourense · ${jTxt}${rival ? " vs " + rival : ""}`;
  };

  const downloadImage = async () => {
    setSharing(true); setMsg("");
    try {
      const canvas = await buildCanvas();
      const a = document.createElement("a");
      a.href = canvas.toDataURL("image/png");
      a.download = `once-udo-${t.tpJ}${sel?.jornada ?? ""}.png`;
      a.click();
    } catch { setMsg("✗ Non se puido xerar a imaxe."); }
    finally { setSharing(false); }
  };

  const shareX = async () => {
    setSharing(true); setMsg("");
    try {
      const text = encodeURIComponent(shareLabel() + " #UDOurense");
      const canvas = await buildCanvas();
      canvas.toBlob(async (blob) => {
        const file = new File([blob], "once-udo.png", { type: "image/png" });
        if (navigator.canShare && navigator.canShare({ files: [file] })) {
          try { await navigator.share({ files: [file], text: shareLabel() }); }
          catch { /* cancelado */ }
        } else {
          const a = document.createElement("a");
          a.href = canvas.toDataURL("image/png");
          a.download = `once-udo-${t.tpJ}${sel?.jornada ?? ""}.png`;
          a.click();
          window.open(`https://twitter.com/intent/tweet?text=${text}`, "_blank");
        }
        setSharing(false);
      }, "image/png");
    } catch { setMsg("✗ Non se puido compartir."); setSharing(false); }
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
            Próxima · {t.tpJ}{days.next.jornada}
          </button>
        )}
        {days.played.slice().reverse().map((d) => (
          <button key={d.jornada} onClick={() => selectDay(d)}
            className={`tap shrink-0 rounded-lg border px-3 py-2 text-xs font-bold ${sel?.jornada === d.jornada ? "border-transparent text-white" : "border-neutral-200 bg-white text-neutral-600"}`}
            style={sel?.jornada === d.jornada ? { backgroundColor: RED } : undefined}>
            {t.tpJ}{d.jornada} {d.has_lineup ? "" : "·"}
          </button>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_300px]">
        {/* CAMPO 3D */}
        <div>
          <div className="rounded-xl bg-white p-2">
            <Pitch onField={onField} showRatings={isPast && !editing} editing={editing} onSlotClick={(i) => {
              if (!editing) return;
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

          {/* compartir aliñación */}
          <div className="mt-3 flex gap-2">
            <button onClick={downloadImage} disabled={sharing}
              className="tap flex-1 rounded-lg border border-neutral-300 py-2 text-sm font-semibold text-neutral-700 disabled:opacity-50">
              {sharing ? "…" : "↓ Descargar imaxe"}
            </button>
            <button onClick={shareX} disabled={sharing}
              className="tap flex-1 rounded-lg py-2 text-sm font-bold text-white disabled:opacity-50"
              style={{ backgroundColor: "#111" }}>
              Compartir en 𝕏
            </button>
          </div>
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

          {/* botón editar para partidos pasados (só admin) */}
          {isPast && !editing && token && (
            <button onClick={() => setEditing(true)}
              className="tap mb-4 w-full rounded-lg border border-neutral-300 py-2 text-sm font-semibold text-neutral-700">
              ✎ Editar aliñación a posteriori
            </button>
          )}

          {/* formación */}
          <label className="block text-[10px] font-bold uppercase text-neutral-400">Formación</label>
          <select value={formation} onChange={(e) => changeFormation(e.target.value)} disabled={!editing}
            className="mt-1 w-full rounded-lg border border-neutral-300 px-2 py-2 text-sm font-semibold disabled:opacity-60">
            {Object.keys(formations).map((f) => <option key={f} value={f}>{f}</option>)}
          </select>

          {/* banquillo / selector (só en edición) */}
          {editing && (
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

          {editing && token && (
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
function Pitch({ onField, showRatings, editing, onSlotClick, pickingIndex }) {
  const [isMobile, setIsMobile] = useState(
    typeof window !== "undefined" ? window.innerWidth < 640 : false);
  useEffect(() => {
    const onR = () => setIsMobile(window.innerWidth < 640);
    window.addEventListener("resize", onR);
    return () => window.removeEventListener("resize", onR);
  }, []);

  // En MÓBIL abrimos o rango (líñas máis separadas) e reducimos as camisetas. En
  // ESCRITORIO déixase EXACTAMENTE como estaba (perspectiva que gusta).
  const projectTop = (y) => {
    const top = 100 - y;
    const t = top / 100;
    const eased = t * t * 0.35 + t * 0.65;
    if (isMobile) return 20 + eased * 78;      // 20%..98%: líñas máis separadas
    return 24 + eased * 72;                    // 24%..96% (escritorio, igual que antes)
  };

  return (
    <div style={{ perspective: "760px", perspectiveOrigin: "center 30%" }}
      className="mx-auto w-full max-w-[560px]">
      <div style={{ position: "relative", aspectRatio: "3 / 3.5", transformStyle: "preserve-3d" }}>
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
        {/* CAPA 2: camisetas (plana e frontal á cámara) */}
        <div style={{ position: "absolute", inset: 0 }}>
          {onField.map((p, i) => (
            <PlayerNode key={i} p={p} showRatings={showRatings} editing={editing} picking={pickingIndex === i}
              mobile={isMobile} top={projectTop(p.y)} left={p.x} onClick={() => onSlotClick(i)} part="shirt" />
          ))}
        </div>
        {/* CAPA 3: nomes SEMPRE por riba das camisetas (cando colapsan, vese o nome) */}
        <div style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
          {onField.map((p, i) => (
            <PlayerNode key={i} p={p} mobile={isMobile}
              top={projectTop(p.y)} left={p.x} part="name" />
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

function PlayerNode({ p, showRatings, editing, picking, mobile, top, left, onClick, part = "shirt" }) {
  const empty = !p.name;
  const emptySize = mobile ? 40 : 56;
  const shirtSize = mobile ? 46 : 75;

  // CAPA DE NOME: só o nome, desprazado xusto debaixo da camiseta. Vai nunha capa
  // superior, así que cando dous nodos colapsan, o nome queda por diante da camiseta.
  if (part === "name") {
    if (empty) return null;
    return (
      <div style={{
        position: "absolute", left: `${left}%`, top: `${top}%`,
        transform: `translate(-50%, calc(-50% + ${shirtSize / 2 + (mobile ? 6 : 8)}px))`,
        pointerEvents: "none",
      }}>
        <span style={{
          display: "block",
          maxWidth: mobile ? 70 : 104, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
          fontSize: mobile ? 10 : 14, fontWeight: 800, lineHeight: 1.1, color: "#fff",
          padding: mobile ? "1px 4px" : "1px 6px", borderRadius: 4, background: "rgba(0,0,0,0.72)",
          transform: "translateZ(0)", textShadow: "0 1px 1px rgba(0,0,0,0.5)",
        }}>
          {shortName(p.display, p.name)}
        </span>
      </div>
    );
  }

  // CAPA DE CAMISETA (+ badge)
  return (
    <div onClick={onClick}
      style={{
        position: "absolute", left: `${left}%`, top: `${top}%`,
        transform: "translate(-50%, -50%)",
        cursor: editing ? "pointer" : "default",
        zIndex: Math.round(top),
        willChange: "transform",
      }}>
      <div className="flex flex-col items-center">
        {empty ? (
          <div className="grid place-items-center rounded-full border-2 border-dashed"
            style={{ width: emptySize, height: emptySize, borderColor: picking ? RED : "rgba(120,120,120,0.75)",
                     background: "rgba(255,255,255,0.12)", color: picking ? RED : "#777" }}>
            <span className="text-3xl leading-none">+</span>
          </div>
        ) : (
          <div className="relative">
            <Shirt gk={p.role === "POR"} mobile={mobile} />
            {showRatings && p.oRating != null && (
              <span className="absolute -right-2 -top-2 grid place-items-center rounded-lg font-black text-white"
                style={{ width: mobile ? 22 : 26, height: mobile ? 22 : 26, fontSize: mobile ? 10 : 12,
                         backgroundColor: ratingColor(p.oRating), boxShadow: "0 2px 5px rgba(0,0,0,0.3)" }}>
                {p.oRating.toFixed(1)}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* Camiseta: carga /camiseta.png (ou /camiseta_portero.png para o porteiro).
   Se non existe, cae a un SVG abstracto. */
function Shirt({ gk = false, mobile = false }) {
  const [ok, setOk] = useState(true);
  const size = mobile ? 46 : 75;
  const src = gk ? "/camiseta_portero.png" : "/camiseta.png";
  if (ok) {
    return <img src={src} alt="" onError={() => setOk(false)}
      style={{ width: size, height: size, objectFit: "contain",
               filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.32))" }} draggable={false} />;
  }
  const col = gk ? "#e0a500" : RED;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={col} aria-hidden
      style={{ filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.32))" }}>
      <path d="M9 2 L4 5 L6 9 L8 8 V21 H16 V8 L18 9 L20 5 L15 2 C14 3.5 10 3.5 9 2 Z" />
    </svg>
  );
}
