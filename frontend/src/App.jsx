import { useState, useMemo, useEffect } from "react";
import { api } from "./lib/api";

/* ============================================================================
   OURENSE É UD — App unificada (preview navegable, sen login aínda)
   ----------------------------------------------------------------------------
   Shell con menú lateral que reúne as catro seccións xa construídas:
     · Dashboard (clasificación + probabilidades)
     · Simulador (qué pasa se...)
     · Centro de Mando (UD Ourense)
     · Plantilla (cuadrícula + oRating)

   Identidade: neutros estruturados + vermello UDO como acento estrito.
   Elemento FIRMA: a banda de cor de zona (ascenso/playoff/descenso) percorre
   toda a app de forma coherente — na táboa, no simulador e na navegación.

   Datos MOCK con 8 xornadas simuladas para ver a estética (a temporada real
   arranca a cero o 30/08). Bilingüe gl/es.
   ============================================================================ */

const RED = "#C8102E";
const ZONE = {
  promo: { bar: "#1a8a4a", soft: "#e7f5ec" }, // ascenso directo — verde
  po:    { bar: "#e0a500", soft: "#fdf6e3" }, // playoff — amarillo
  rel:   { bar: "#c0392b", soft: "#fbecea" }, // descenso — rojo
};

/* ---------------------------------------------------------------- i18n ---- */
const I18N = {
  gl: {
    tagline: "a nosa vida",
    nav: { dashboard: "Clasificación", sim: "Simulador", hub: "UD Ourense", squad: "Plantilla" },
    season: "Tempada 2026-27 · 1ª RFEF · Grupo 1",
    team: "Equipo", pld: "PX", gd: "DG", pts: "Ptos", form: "Forma",
    oPts: "oPts", diff: "Δ", xg: "xG",
    champ: "Campión", playoff: "Playoff", releg: "Descenso",
    vTable: "Táboa", vProbs: "Probabilidades",
    probsTitle: "Probabilidades de tempada (Monte Carlo)", sims: "simulacións",
    legend: { promo: "Ascenso directo (1º)", po: "Playoff (2º-5º)", rel: "Descenso (16º-20º)" },
    simTitle: "Qué pasa se...", simSub: "Fixa resultados da xornada e mira como cambia todo.",
    jornada: "Xornada", reset: "Reiniciar", proj: "Clasificación proxectada",
    hubNext: "Próximo partido", hubForm: "Forma", win: "Vitoria", draw: "Empate", loss: "Derrota",
    likely: "Máis probable", h2h: "Cara a cara", pos: "Pos", elo: "Elo",
    perf: "Rendemento", perfSub: "oPts (merecidos) fronte a puntos reais.",
    deserves: "Merece", morePts: "puntos máis", lessPts: "puntos menos", onPar: "o esperado",
    squadTitle: "Plantilla", all: "Todos", gk: "Porteiros", df: "Defensas", mf: "Medios", fw: "Dianteiros",
    rating: "oRating", value: "Valor", years: "anos",
    ratingHelp: "oRating: nota propia de rendemento (media da tempada), con datos reais.",
    mockNote: "Datos simulados para ver a estética · a liga real arranca a cero o 30/08/2026",
  },
  es: {
    tagline: "a nosa vida",
    nav: { dashboard: "Clasificación", sim: "Simulador", hub: "UD Ourense", squad: "Plantilla" },
    season: "Temporada 2026-27 · 1ª RFEF · Grupo 1",
    team: "Equipo", pld: "PJ", gd: "DG", pts: "Pts", form: "Forma",
    oPts: "oPts", diff: "Δ", xg: "xG",
    champ: "Campeón", playoff: "Playoff", releg: "Descenso",
    vTable: "Tabla", vProbs: "Probabilidades",
    probsTitle: "Probabilidades de temporada (Monte Carlo)", sims: "simulaciones",
    legend: { promo: "Ascenso directo (1º)", po: "Playoff (2º-5º)", rel: "Descenso (16º-20º)" },
    simTitle: "Qué pasa si...", simSub: "Fija resultados de la jornada y mira cómo cambia todo.",
    jornada: "Jornada", reset: "Reiniciar", proj: "Clasificación proyectada",
    hubNext: "Próximo partido", hubForm: "Forma", win: "Victoria", draw: "Empate", loss: "Derrota",
    likely: "Más probable", h2h: "Cara a cara", pos: "Pos", elo: "Elo",
    perf: "Rendimiento", perfSub: "oPts (merecidos) frente a puntos reales.",
    deserves: "Merece", morePts: "puntos más", lessPts: "puntos menos", onPar: "lo esperado",
    squadTitle: "Plantilla", all: "Todos", gk: "Porteros", df: "Defensas", mf: "Medios", fw: "Delanteros",
    rating: "oRating", value: "Valor", years: "años",
    ratingHelp: "oRating: nota propia de rendimiento (media de temporada), con datos reales.",
    mockNote: "Datos simulados para ver la estética · la liga real arranca a cero el 30/08/2026",
  },
};

/* ------------------------------------------------------- datos mock ------- */
const T = {
  ponferradina:{n:"SD Ponferradina",c:"#1f5fbf",s:"PFR"}, "racing-ferrol":{n:"Racing Ferrol",c:"#0a7a2f",s:"FER"},
  merida:{n:"AD Mérida",c:"#0b0b0b",s:"MER"}, zamora:{n:"Zamora CF",c:"#c8102e",s:"ZAM"},
  pontevedra:{n:"Pontevedra CF",c:"#1a3a7a",s:"PON"}, ourense:{n:"UD Ourense",c:RED,s:"OUR",udo:true},
  extremadura:{n:"CD Extremadura",c:"#0b6e3b",s:"EXT"}, "bilbao-ath":{n:"Bilbao Athletic",c:"#c10000",s:"ATH"},
  cacereno:{n:"CP Cacereño",c:"#0b6e3b",s:"CAC"}, mirandes:{n:"CD Mirandés",c:"#b1121b",s:"MIR"},
  barakaldo:{n:"Barakaldo CF",c:"#e0b000",s:"BAR"}, leonesa:{n:"CyD Leonesa",c:"#0a1b3d",s:"CUL"},
  aviles:{n:"Real Avilés",c:"#111",s:"AVI"}, "real-union":{n:"Real Unión",c:"#c8102e",s:"RUN"},
  fabril:{n:"RC Dep. Fabril",c:"#1874c4",s:"FAB"}, logrones:{n:"UD Logroñés",c:"#c8102e",s:"LOG"},
  unionistas:{n:"Unionistas",c:"#0a1b3d",s:"UNI"}, coria:{n:"CD Coria",c:"#123f8c",s:"COR"},
  lugo:{n:"CD Lugo",c:"#9b1b30",s:"LUG"}, arenas:{n:"Arenas Club",c:"#111",s:"ARE"},
};
const MOCK = [
  { k:"ponferradina", pld:8,w:6,d:1,l:1,gf:15,ga:6, opts:17.9,xg:12.9, F:["W","W","D","W","W"], pC:31,pP:79,pR:1 },
  { k:"racing-ferrol",pld:8,w:5,d:2,l:1,gf:13,ga:7, opts:16.2,xg:11.4, F:["W","D","W","W","L"], pC:20,pP:72,pR:1 },
  { k:"merida",       pld:8,w:5,d:1,l:2,gf:12,ga:8, opts:14.8,xg:12.0, F:["W","L","W","W","D"], pC:13,pP:59,pR:2 },
  { k:"zamora",       pld:8,w:4,d:3,l:1,gf:11,ga:7, opts:14.1,xg:10.1, F:["D","W","D","W","D"], pC:10,pP:55,pR:2 },
  { k:"pontevedra",   pld:8,w:3,d:4,l:1,gf:10,ga:8, opts:13.4,xg:9.7,  F:["D","D","W","D","W"], pC:6, pP:47,pR:3 },
  { k:"ourense",      pld:8,w:4,d:2,l:2,gf:12,ga:9, opts:12.6,xg:9.4,  F:["L","W","D","W","W"], pC:7, pP:44,pR:4, udo:true },
  { k:"extremadura",  pld:8,w:3,d:3,l:2,gf:9, ga:9, opts:11.8,xg:9.9,  F:["W","D","L","D","W"], pC:3, pP:33,pR:6 },
  { k:"bilbao-ath",   pld:8,w:3,d:3,l:2,gf:10,ga:10,opts:11.4,xg:10.6, F:["L","W","D","W","D"], pC:2, pP:30,pR:7 },
  { k:"cacereno",     pld:8,w:3,d:2,l:3,gf:9, ga:10,opts:10.6,xg:9.2,  F:["W","L","W","L","D"], pC:1, pP:24,pR:9 },
  { k:"mirandes",     pld:8,w:2,d:4,l:2,gf:8, ga:8, opts:10.4,xg:8.8,  F:["D","D","L","W","D"], pC:1, pP:22,pR:10 },
  { k:"barakaldo",    pld:8,w:2,d:4,l:2,gf:7, ga:8, opts:9.8, xg:7.5,  F:["D","L","D","D","W"], pC:0.5,pP:18,pR:12 },
  { k:"leonesa",      pld:8,w:2,d:3,l:3,gf:9, ga:11,opts:9.9, xg:10.2, F:["L","W","D","L","W"], pC:0.5,pP:17,pR:14 },
  { k:"aviles",       pld:8,w:2,d:3,l:3,gf:8, ga:10,opts:9.2, xg:8.4,  F:["D","L","L","W","D"], pC:0.3,pP:15,pR:16 },
  { k:"real-union",   pld:8,w:2,d:2,l:4,gf:7, ga:11,opts:8.4, xg:7.9,  F:["L","D","L","W","L"], pC:0.2,pP:12,pR:22 },
  { k:"fabril",       pld:8,w:1,d:4,l:3,gf:6, ga:9, opts:8.1, xg:7.1,  F:["D","L","D","D","L"], pC:0.1,pP:9, pR:28 },
  { k:"logrones",     pld:8,w:2,d:1,l:5,gf:8, ga:13,opts:6.9, xg:6.6,  F:["L","L","W","L","L"], pC:0.1,pP:8, pR:34 },
  { k:"unionistas",   pld:8,w:1,d:3,l:4,gf:6, ga:11,opts:6.4, xg:6.9,  F:["L","D","L","L","D"], pC:0, pP:6, pR:42 },
  { k:"coria",        pld:8,w:1,d:2,l:5,gf:5, ga:12,opts:5.8, xg:6.2,  F:["L","L","D","L","L"], pC:0, pP:4, pR:51 },
  { k:"lugo",         pld:8,w:1,d:2,l:5,gf:6, ga:14,opts:5.5, xg:5.5,  F:["L","L","L","D","L"], pC:0, pP:3, pR:58 },
  { k:"arenas",       pld:8,w:0,d:4,l:4,gf:5, ga:12,opts:5.2, xg:5.8,  F:["D","L","D","L","D"], pC:0, pP:3, pR:63 },
].map((r) => ({ ...r, pts:r.w*3+r.d, gd:r.gf-r.ga, ...T[r.k] }));

const FIXTURES_J9 = [
  ["arenas","fabril"],["racing-ferrol","aviles"],["real-union","pontevedra"],["merida","ponferradina"],
  ["barakaldo","logrones"],["mirandes","ourense"],["cacereno","extremadura"],["leonesa","bilbao-ath"],
  ["unionistas","coria"],["zamora","lugo"],
];

const SQUAD = [
  { name:"Manu Vizoso",pos:"GK",dorsal:13,born:2003,nat:"ES",mv:100000,oR:6.7 },
  { name:"Bruno Rielo",pos:"GK",dorsal:4,born:2004,nat:"ES",mv:25000,oR:null },
  { name:"Javi Labrada",pos:"DF",dorsal:20,born:2003,nat:"ES",mv:100000,oR:6.9 },
  { name:"Igor Irazu",pos:"DF",dorsal:5,born:2002,nat:"ES",mv:50000,oR:6.5 },
  { name:"Lucas Puime",pos:"DF",dorsal:null,born:1993,nat:"ES",mv:25000,oR:6.4 },
  { name:"Julio Cabrera",pos:"LI",dorsal:15,born:2003,nat:"ES",mv:200000,oR:7.1 },
  { name:"Noel González",pos:"LD",dorsal:19,born:2005,nat:"ES",mv:100000,oR:6.8 },
  { name:"Samuel Pardo",pos:"LD",dorsal:2,born:2001,nat:"ES",mv:50000,oR:6.3 },
  { name:"Varo",pos:"LD",dorsal:null,born:1997,nat:"ES",mv:25000,oR:6.2 },
  { name:"Álvaro Bastida",pos:"MC",dorsal:null,born:2004,nat:"ES",mv:200000,oR:7.0 },
  { name:"Curro Rivelott",pos:"MC",dorsal:22,born:1999,nat:"ES",mv:150000,oR:7.2 },
  { name:"Diego Tejón",pos:"MC",dorsal:null,born:2002,nat:"ES",mv:150000,oR:6.6 },
  { name:"Viti Nieves",pos:"MC",dorsal:23,born:1994,nat:"VE",mv:25000,oR:6.1 },
  { name:"Roi Currás",pos:"MC",dorsal:null,born:2007,nat:"ES",mv:null,oR:null },
  { name:"Champi",pos:"MCO",dorsal:null,born:1996,nat:"ES",mv:50000,oR:6.7 },
  { name:"David Ferreiro",pos:"EI",dorsal:21,born:1988,nat:"ES",mv:50000,oR:6.9 },
  { name:"Valen Jaichenko",pos:"EI",dorsal:null,born:2002,nat:"AR",mv:25000,oR:6.0 },
  { name:"Mateo Gandarillas",pos:"ED",dorsal:null,born:2001,nat:"ES",mv:150000,oR:7.3 },
  { name:"Xabi Domínguez",pos:"ED",dorsal:null,born:2002,nat:"ES",mv:50000,oR:6.5 },
  { name:"Cristian Carro",pos:"ED",dorsal:15,born:2007,nat:"ES",mv:null,oR:null },
  { name:"Sergi Baldrich",pos:"DC",dorsal:9,born:2003,nat:"ES",mv:150000,oR:7.4 },
  { name:"Rufo Sánchez",pos:"DC",dorsal:null,born:1986,nat:"ES",mv:25000,oR:6.8 },
];

/* ---------------------------------------------------- helpers UI ---------- */
function BrandCrest({ size = 36 }) {
  // Escudo oficial da UD Ourense desde /public/escudos/ourense.png.
  // Mentres non exista o PNG, cae a un placeholder "é" en vermello.
  const [ok, setOk] = useState(true);
  if (ok) {
    return (
      <img src="/escudos/ourense.png" alt="UD Ourense" onError={() => setOk(false)}
        className="shrink-0" style={{ width: size, height: size, objectFit: "contain" }} />
    );
  }
  return (
    <span className="grid shrink-0 place-items-center rounded-md text-lg font-black text-white"
      style={{ width: size, height: size, backgroundColor: RED }}>é</span>
  );
}

function Crest({ team, size = 22 }) {
  // Escudo do club desde /public/escudos/{k}.png; placeholder monograma se falta.
  const [ok, setOk] = useState(true);
  if (ok && team.k) {
    return (
      <img src={`/escudos/${team.k}.png`} alt={team.n} onError={() => setOk(false)}
        className="shrink-0" style={{ width: size, height: size, objectFit: "contain" }} />
    );
  }
  const light = ["#e0b000","#ffffff"].includes(team.c);
  return (
    <span className="grid shrink-0 place-items-center rounded-full font-bold"
      style={{ width: size, height: size, backgroundColor: team.c, color: light ? "#111" : "#fff", fontSize: size * 0.36 }}>
      {team.s}
    </span>
  );
}
function FormDots({ form }) {
  const c = { W: "#1a8a4a", D: "#9a9a9a", L: "#c0392b" };
  return <span className="inline-flex gap-1">{form.map((r, i) => <span key={i} title={r} className="h-2 w-2 rounded-full" style={{ backgroundColor: c[r] }} />)}</span>;
}
function Bar({ value, color }) {
  return <div className="h-2.5 w-full overflow-hidden rounded bg-neutral-200"><div className="h-full rounded transition-all" style={{ width: `${Math.min(100, value)}%`, backgroundColor: color }} /></div>;
}

/* ================================================================ APP ===== */
export default function App() {
  const [lang, setLang] = useState("gl");
  const [section, setSection] = useState("dashboard");
  const t = I18N[lang];

  const nav = [
    ["dashboard", t.nav.dashboard, "▦"],
    ["sim", t.nav.sim, "⇄"],
    ["hub", t.nav.hub, "◆"],
    ["squad", t.nav.squad, "◫"],
  ];

  return (
    <div className="flex min-h-screen bg-neutral-50 font-sans text-neutral-900">
      {/* ---------- menú lateral ---------- */}
      <aside className="sticky top-0 flex h-screen w-16 flex-col justify-between border-r border-neutral-200 bg-white sm:w-56">
        <div>
          {/* marca */}
          <div className="flex items-center gap-2.5 border-b border-neutral-100 px-3 py-4 sm:px-4">
            <BrandCrest size={36} />
            <div className="hidden leading-tight sm:block">
              <div className="text-sm font-black tracking-tight">Ourense é <span style={{ color: RED }}>UD</span></div>
              <div className="text-[11px] italic text-neutral-400">{t.tagline}</div>
            </div>
          </div>
          {/* navegación */}
          <nav className="mt-2 px-2">
            {nav.map(([k, label, icon]) => (
              <button key={k} onClick={() => setSection(k)}
                className={`mb-1 flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                  section === k ? "text-white" : "text-neutral-600 hover:bg-neutral-100"
                }`}
                style={section === k ? { backgroundColor: RED } : undefined}>
                <span className="text-base">{icon}</span>
                <span className="hidden sm:inline">{label}</span>
              </button>
            ))}
          </nav>
        </div>
        {/* idioma */}
        <div className="border-t border-neutral-100 p-2">
          <div className="flex gap-1">
            {["gl", "es"].map((l) => (
              <button key={l} onClick={() => setLang(l)}
                className={`flex-1 rounded px-2 py-1.5 text-xs font-semibold transition ${lang === l ? "bg-neutral-900 text-white" : "bg-neutral-100 text-neutral-500 hover:bg-neutral-200"}`}>
                {l.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </aside>

      {/* ---------- contido ---------- */}
      <main className="min-w-0 flex-1">
        <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6">
          {section === "dashboard" && <Dashboard t={t} />}
          {section === "sim" && <Simulator t={t} />}
          {section === "hub" && <CommandCenter t={t} />}
          {section === "squad" && <Squad t={t} />}
          <p className="mt-6 text-center text-xs text-neutral-400">{t.mockNote}</p>
        </div>
      </main>
    </div>
  );
}

/* --- mapa nome do backend → slug/cor do noso catálogo T --------------------
   O backend devolve nomes canónicos; buscamos o slug para pintar escudos/cor. */
const NAME_TO_KEY = Object.fromEntries(Object.entries(T).map(([k, v]) => [v.n, k]));

function adaptStandings(apiRows) {
  // Converte a resposta de /api/standings ao formato que usa a táboa.
  return apiRows.map((r) => {
    const k = NAME_TO_KEY[r.team] || r.slug;
    const meta = T[k] || { n: r.team, c: "#888", s: (r.team || "?").slice(0, 3).toUpperCase() };
    return {
      k, ...meta,
      pld: r.pld, w: r.w, d: r.d, l: r.l, gf: r.gf, ga: r.ga, gd: r.gd, pts: r.pts,
      opts: r.oPts ?? 0, xg: r.oPts ?? 0,
      F: (r.form || []).slice(-5),
      udo: r.team === "UD Ourense",
      // probabilidades énchense despois desde /api/probs
      pC: 0, pP: 0, pR: 0,
    };
  });
}

/* =========================================================== DASHBOARD ==== */
function Dashboard({ t }) {
  const [view, setView] = useState("table");
  const [rows, setRows] = useState(() => [...MOCK].sort((a, b) => b.pts - a.pts || b.gd - a.gd || b.gf - a.gf));
  const [live, setLive] = useState(false); // true se cargaron datos reais

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        // clasificación real; as probabilidades veñen aparte e fusiónanse
        const [st, pr] = await Promise.all([
          api.standings(),
          api.probs().catch(() => []),
        ]);
        if (!alive) return;
        const probByTeam = Object.fromEntries((pr || []).map((p) => [p.team, p]));
        const adapted = adaptStandings(st).map((r) => {
          const p = probByTeam[r.n] || {};
          return { ...r, pC: p.pChamp ?? 0, pP: p.pPO ?? 0, pR: p.pRel ?? 0 };
        });
        adapted.sort((a, b) => b.pts - a.pts || b.gd - a.gd || b.gf - a.gf);
        setRows(adapted);
        setLive(true);
      } catch {
        // se o backend está durmido ou falla, quedamos co mock (xa cargado)
      }
    })();
    return () => { alive = false; };
  }, []);

  const zoneOf = (i) => (i === 0 ? "promo" : i <= 4 ? "po" : i >= 15 ? "rel" : null);

  return (
    <div>
      <SectionHead title={t.nav.dashboard} sub={t.season} />
      <div className="mb-4 inline-flex rounded-lg border border-neutral-200 bg-white p-1">
        {[["table", t.vTable], ["probs", t.vProbs]].map(([k, label]) => (
          <button key={k} onClick={() => setView(k)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${view === k ? "bg-neutral-900 text-white" : "text-neutral-600 hover:text-neutral-900"}`}>
            {label}
          </button>
        ))}
      </div>

      {view === "table" ? (
        <div className="overflow-x-auto rounded-lg border border-neutral-200 bg-white">
          <table className="w-full min-w-[640px] border-collapse text-sm">
            <thead className="bg-neutral-100 text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th className="px-2 py-2.5 text-center font-semibold">#</th>
                <th className="px-3 py-2.5 text-left font-semibold">{t.team}</th>
                <th className="px-2 py-2.5 text-center font-semibold">{t.pld}</th>
                <th className="px-2 py-2.5 text-center font-semibold">{t.gd}</th>
                <th className="px-2 py-2.5 text-center font-bold text-neutral-700">{t.pts}</th>
                <th className="px-2 py-2.5 text-center font-semibold">{t.oPts}</th>
                <th className="px-2 py-2.5 text-center font-semibold" title="oPts - Pts">{t.diff}</th>
                <th className="px-3 py-2.5 text-center font-semibold">{t.form}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => {
                const z = zoneOf(i), delta = +(r.opts - r.pts).toFixed(1);
                return (
                  <tr key={r.k} className={`border-t border-neutral-100 ${r.udo ? "" : "hover:bg-neutral-50"}`} style={r.udo ? { backgroundColor: "#fdecec" } : undefined}>
                    <td className="relative px-2 py-2 text-center tabular-nums text-neutral-500">
                      {z && <span className="absolute left-0 top-0 h-full w-1.5" style={{ backgroundColor: ZONE[z].bar }} />}
                      {i + 1}
                    </td>
                    <td className="px-3 py-2"><div className="flex items-center gap-2.5"><Crest team={r} /><span className={r.udo ? "font-bold" : "font-medium"} style={r.udo ? { color: RED } : undefined}>{r.n}</span></div></td>
                    <td className="px-2 py-2 text-center tabular-nums text-neutral-600">{r.pld}</td>
                    <td className="px-2 py-2 text-center tabular-nums text-neutral-600">{r.gd > 0 ? `+${r.gd}` : r.gd}</td>
                    <td className="px-2 py-2 text-center font-bold tabular-nums">{r.pts}</td>
                    <td className="px-2 py-2 text-center tabular-nums text-neutral-500">{r.opts.toFixed(1)}</td>
                    <td className="px-2 py-2 text-center font-medium tabular-nums" style={{ color: delta > 0.5 ? "#1a8a4a" : delta < -0.5 ? "#c0392b" : "#9a9a9a" }}>{delta > 0 ? `+${delta}` : delta}</td>
                    <td className="px-3 py-2 text-center"><FormDots form={r.F} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="rounded-lg border border-neutral-200 bg-white p-4">
          <div className="mb-3 flex items-baseline justify-between">
            <h3 className="text-sm font-bold">{t.probsTitle}</h3>
            <span className="text-xs text-neutral-400">10.000 {t.sims}</span>
          </div>
          <div className="space-y-2">
            {rows.map((r) => (
              <div key={r.k} className="grid grid-cols-[130px_1fr] items-center gap-3 rounded px-2 py-1" style={r.udo ? { backgroundColor: "#fdecec" } : undefined}>
                <div className="flex items-center gap-2"><Crest team={r} size={18} /><span className={`truncate text-xs ${r.udo ? "font-bold" : "text-neutral-700"}`} style={r.udo ? { color: RED } : undefined}>{r.n}</span></div>
                <div className="grid grid-cols-3 gap-2">
                  <ProbMini label={t.champ} v={r.pC} color={ZONE.promo.bar} />
                  <ProbMini label={t.playoff} v={r.pP} color={ZONE.po.bar} />
                  <ProbMini label={t.releg} v={r.pR} color={ZONE.rel.bar} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <Legend t={t} />
    </div>
  );
}

function ProbMini({ label, v, color }) {
  return (
    <div>
      <div className="mb-0.5 flex justify-between text-[10px] text-neutral-500"><span>{label}</span><span className="tabular-nums font-medium">{v}%</span></div>
      <Bar value={v} color={color} />
    </div>
  );
}

/* =========================================================== SIMULADOR ==== */
function Simulator({ t }) {
  const [results, setResults] = useState({});
  const base = useMemo(() => Object.fromEntries(MOCK.map((r) => [r.k, { ...r }])), []);
  const baseOrder = useMemo(() => [...MOCK].sort((a, b) => b.pts - a.pts || b.gd - a.gd).map((r) => r.k), []);

  const projected = useMemo(() => {
    const map = Object.fromEntries(Object.entries(base).map(([k, v]) => [k, { ...v }]));
    FIXTURES_J9.forEach(([h, a], i) => {
      const res = results[i];
      if (!res) return;
      if (res === "1") { map[h].pts += 3; map[h].gd += 1; map[a].gd -= 1; }
      else if (res === "2") { map[a].pts += 3; map[a].gd -= 1; map[h].gd += 1; }
      else { map[h].pts += 1; map[a].pts += 1; }
    });
    return Object.values(map).sort((x, y) => y.pts - x.pts || y.gd - x.gd);
  }, [results, base]);

  const zoneOf = (i) => (i === 0 ? "promo" : i <= 4 ? "po" : i >= 15 ? "rel" : null);
  const fixedCount = Object.keys(results).length;

  return (
    <div>
      <SectionHead title={t.simTitle} sub={t.simSub} action={fixedCount > 0 && (
        <button onClick={() => setResults({})} className="rounded px-3 py-1 text-xs font-semibold text-neutral-500 hover:bg-neutral-200">↺ {t.reset}</button>
      )} />

      <section className="mb-5 rounded-lg border border-neutral-200 bg-white p-4">
        <h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-neutral-500">{t.jornada} 9</h3>
        <div className="grid gap-2 sm:grid-cols-2">
          {FIXTURES_J9.map(([h, a], i) => (
            <div key={i} className="flex items-center justify-between gap-2 rounded-md border border-neutral-100 px-3 py-2">
              <div className="flex min-w-0 flex-1 items-center justify-end gap-1.5">
                <span className={`truncate text-xs ${T[h].udo ? "font-bold" : "text-neutral-700"}`} style={T[h].udo ? { color: RED } : undefined}>{T[h].n}</span>
                <Crest team={T[h]} size={18} />
              </div>
              <div className="flex shrink-0 gap-1">
                {["1", "X", "2"].map((v) => (
                  <button key={v} onClick={() => setResults((p) => ({ ...p, [i]: p[i] === v ? undefined : v }))}
                    className={`h-7 w-8 rounded text-xs font-bold transition ${results[i] === v ? "text-white" : "bg-neutral-100 text-neutral-500 hover:bg-neutral-200"}`}
                    style={results[i] === v ? { backgroundColor: RED } : undefined}>{v}</button>
                ))}
              </div>
              <div className="flex min-w-0 flex-1 items-center gap-1.5">
                <Crest team={T[a]} size={18} />
                <span className={`truncate text-xs ${T[a].udo ? "font-bold" : "text-neutral-700"}`} style={T[a].udo ? { color: RED } : undefined}>{T[a].n}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-neutral-200 bg-white">
        <h3 className="border-b border-neutral-100 px-4 py-3 text-sm font-bold">{t.proj}</h3>
        <div className="p-2">
          {projected.map((r, i) => {
            const z = zoneOf(i), prevIdx = baseOrder.indexOf(r.k), moved = prevIdx - i;
            return (
              <div key={r.k} className="flex items-center gap-2 rounded px-2 py-1.5 text-sm" style={r.udo ? { backgroundColor: "#fdecec" } : undefined}>
                <span className="relative w-6 text-center tabular-nums text-neutral-400">
                  {z && <span className="absolute left-0 top-0 h-full w-1 rounded" style={{ backgroundColor: ZONE[z].bar }} />}{i + 1}
                </span>
                <Crest team={r} size={20} />
                <span className={`flex-1 truncate ${r.udo ? "font-bold" : "font-medium"}`} style={r.udo ? { color: RED } : undefined}>{r.n}</span>
                {moved !== 0 && <span className="text-[10px] font-bold tabular-nums" style={{ color: moved > 0 ? "#1a8a4a" : "#c0392b" }}>{moved > 0 ? `▲${moved}` : `▼${-moved}`}</span>}
                <span className="w-8 text-right font-bold tabular-nums">{r.pts}</span>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

/* ======================================================= CENTRO DE MANDO == */
function CommandCenter({ t }) {
  const us = MOCK.find((r) => r.k === "ourense");
  const them = MOCK.find((r) => r.k === "mirandes");
  const usPos = [...MOCK].sort((a,b)=>b.pts-a.pts||b.gd-a.gd).findIndex(r=>r.k==="ourense")+1;
  const themPos = [...MOCK].sort((a,b)=>b.pts-a.pts||b.gd-a.gd).findIndex(r=>r.k==="mirandes")+1;
  // Próximo partido: Mirandés (local) vs UD Ourense (visitante).
  // oGoals respectando a orde: primeiro o local, segundo o visitante.
  const udoIsHome = false; // neste mock a UDO xoga fóra
  const ogHome = udoIsHome ? 1.94 : 2.81; // local
  const ogAway = udoIsHome ? 2.81 : 1.94; // visitante
  const next = { win: 28, draw: 23, loss: 49, likely: [1, 2] };
  const evo = [[1,0,1.2],[2,1,2.4],[3,1,3.6],[4,2,4.9],[5,5,6.3],[6,5,8.6],[7,5,9.1],[8,6,10.5]];
  const gap = evo[evo.length-1][2] - evo[evo.length-1][1];

  return (
    <div>
      <SectionHead title="UD Ourense" sub={t.nav.hub} accent />
      <div className="grid gap-4 md:grid-cols-2">
        {/* próximo partido */}
        <section className="rounded-lg border border-neutral-200 bg-white p-4">
          <h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-neutral-500">{t.hubNext}</h3>
          <div className="mb-3 flex items-center justify-center gap-3">
            <div className="flex flex-col items-center gap-1"><Crest team={them} size={40} /><span className="text-xs text-neutral-600">{them.n}</span></div>
            <span className="text-neutral-300">vs</span>
            <div className="flex flex-col items-center gap-1"><Crest team={us} size={40} /><span className="text-xs font-bold" style={{ color: RED }}>{us.n}</span></div>
          </div>
          <div className="mb-1 flex h-7 overflow-hidden rounded">
            <div className="grid place-items-center text-[10px] font-bold text-white" style={{ width: `${next.win}%`, backgroundColor: "#1a8a4a" }}>{next.win}%</div>
            <div className="grid place-items-center text-[10px] font-bold text-white" style={{ width: `${next.draw}%`, backgroundColor: "#9a9a9a" }}>{next.draw}%</div>
            <div className="grid place-items-center text-[10px] font-bold text-white" style={{ width: `${next.loss}%`, backgroundColor: "#c0392b" }}>{next.loss}%</div>
          </div>
          <div className="mb-3 flex justify-between text-[10px] text-neutral-500"><span>{t.win}</span><span>{t.draw}</span><span>{t.loss}</span></div>
          <div className="grid grid-cols-2 gap-2 text-center">
            <div className="rounded bg-neutral-50 p-2"><div className="text-[10px] text-neutral-500">{t.likely}</div><div className="text-xl font-black tabular-nums">{next.likely[0]}-{next.likely[1]}</div></div>
            <div className="rounded bg-neutral-50 p-2"><div className="text-[10px] text-neutral-500">oGoals</div><div className="text-xl font-black tabular-nums">
              <span style={udoIsHome ? { color: RED } : { color: "#9a9a9a" }}>{ogHome}</span>
              <span className="text-neutral-300">·</span>
              <span style={udoIsHome ? { color: "#9a9a9a" } : { color: RED }}>{ogAway}</span>
            </div></div>
          </div>
        </section>

        {/* cara a cara */}
        <section className="rounded-lg border border-neutral-200 bg-white p-4">
          <h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-neutral-500">{t.h2h}</h3>
          <div className="mb-2 grid grid-cols-3 items-center"><div className="flex justify-start"><Crest team={us} size={28} /></div><span /><div className="flex justify-end"><Crest team={them} size={28} /></div></div>
          {[[t.pos, `${usPos}º`, `${themPos}º`, usPos < themPos],[t.pts, us.pts, them.pts, us.pts > them.pts],["GF", us.gf, them.gf, us.gf > them.gf],["GC", us.ga, them.ga, us.ga < them.ga]].map(([label, a, b, better]) => (
            <div key={label} className="grid grid-cols-3 items-center py-1 text-sm">
              <span className="text-left font-bold tabular-nums" style={better ? { color: RED } : { color: "#bbb" }}>{a}</span>
              <span className="text-center text-[10px] uppercase text-neutral-400">{label}</span>
              <span className={`text-right font-bold tabular-nums ${!better ? "" : "text-neutral-400"}`}>{b}</span>
            </div>
          ))}
          <div className="grid grid-cols-3 items-center pt-1"><div className="flex justify-start"><FormDots form={us.F} /></div><span className="text-center text-[10px] uppercase text-neutral-400">{t.hubForm}</span><div className="flex justify-end"><FormDots form={them.F} /></div></div>
        </section>
      </div>

      {/* rendimiento */}
      <section className="mt-4 rounded-lg border border-neutral-200 bg-white p-4">
        <h3 className="mb-1 text-xs font-bold uppercase tracking-wide text-neutral-500">{t.perf}</h3>
        <p className="mb-3 text-xs text-neutral-500">{t.perfSub}</p>
        <div className="mb-3 inline-flex items-center gap-1.5 rounded-md px-3 py-1 text-sm font-bold" style={{ backgroundColor: gap > 0.5 ? "#fbecea" : "#e7f5ec", color: gap > 0.5 ? "#c0392b" : "#1a8a4a" }}>
          {gap > 0.5 ? "▼" : "▲"} {t.deserves} {Math.abs(gap).toFixed(1)} {gap > 0 ? t.morePts : t.lessPts}
        </div>
        <EvoChart evo={evo} t={t} />
      </section>
    </div>
  );
}

function EvoChart({ evo }) {
  const W = 600, H = 180, pad = { l: 28, r: 12, t: 12, b: 20 };
  const maxY = Math.ceil(Math.max(...evo.map((e) => Math.max(e[1], e[2]))) + 1);
  const x = (j) => pad.l + ((j - 1) / (evo.length - 1)) * (W - pad.l - pad.r);
  const y = (v) => H - pad.b - (v / maxY) * (H - pad.t - pad.b);
  const path = (idx) => evo.map((e, i) => `${i ? "L" : "M"}${x(e[0]).toFixed(1)},${y(e[idx]).toFixed(1)}`).join(" ");
  const area = evo.map((e, i) => `${i ? "L" : "M"}${x(e[0]).toFixed(1)},${y(e[2]).toFixed(1)}`).join(" ") + " " + [...evo].reverse().map((e) => `L${x(e[0]).toFixed(1)},${y(e[1]).toFixed(1)}`).join(" ") + " Z";
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 220 }}>
      {Array.from({ length: maxY + 1 }).map((_, i) => i % 3 === 0 ? <line key={i} x1={pad.l} x2={W - pad.r} y1={y(i)} y2={y(i)} stroke="#eee" /> : null)}
      {evo.map((e) => <text key={e[0]} x={x(e[0])} y={H - 6} textAnchor="middle" fontSize="8" fill="#aaa">{e[0]}</text>)}
      <path d={area} fill="#c0392b12" />
      <path d={path(2)} fill="none" stroke="#9a9a9a" strokeWidth="2" strokeDasharray="4 3" />
      <path d={path(1)} fill="none" stroke={RED} strokeWidth="2.5" />
      {evo.map((e) => <circle key={e[0]} cx={x(e[0])} cy={y(e[1])} r="2.5" fill={RED} />)}
    </svg>
  );
}

/* ============================================================== PLANTILLA == */
function Squad({ t }) {
  const [filter, setFilter] = useState("all");
  const [players, setPlayers] = useState(SQUAD);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const sq = await api.squad();
        if (!alive || !Array.isArray(sq) || !sq.length) return;
        // o backend dá born como data "YYYY-MM-DD"; a tarxeta usa o ano
        setPlayers(sq.map((p) => ({
          ...p,
          born: typeof p.born === "string" ? parseInt(p.born.slice(0, 4)) : p.born,
          oR: p.oRating ?? null,
        })));
      } catch { /* fallback ao SQUAD mock xa cargado */ }
    })();
    return () => { alive = false; };
  }, []);

  const GROUP = { GK: "gk", DF: "df", LI: "df", LD: "df", MC: "mf", MCO: "mf", EI: "fw", ED: "fw", DC: "fw" };
  const POS = { GK: "POR", DF: "DFC", LI: "LI", LD: "LD", MC: "MC", MCO: "MCO", EI: "EI", ED: "ED", DC: "DC" };
  const rc = (r) => (r == null ? "#c4c4c4" : r >= 7.0 ? "#1a8a4a" : r >= 6.3 ? "#c99700" : "#b06a3b");
  const fmtMV = (v) => (v == null ? "—" : `${Math.round(v / 1000)} mil €`);
  const list = filter === "all" ? players : players.filter((p) => GROUP[p.pos] === filter);
  const tabs = [["all", t.all], ["gk", t.gk], ["df", t.df], ["mf", t.mf], ["fw", t.fw]];

  return (
    <div>
      <SectionHead title={t.squadTitle} sub="UD Ourense · 2026-27" accent />
      <div className="mb-4 inline-flex flex-wrap gap-1 rounded-lg border border-neutral-200 bg-white p-1">
        {tabs.map(([k, label]) => (
          <button key={k} onClick={() => setFilter(k)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${filter === k ? "text-white" : "text-neutral-600 hover:text-neutral-900"}`}
            style={filter === k ? { backgroundColor: RED } : undefined}>{label}</button>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {list.map((p) => (
          <div key={p.name} className="relative overflow-hidden rounded-xl border border-neutral-200 bg-white p-3 transition hover:shadow-md">
            <div className="absolute inset-x-0 top-0 h-1" style={{ backgroundColor: RED }} />
            <div className="mb-2 flex items-start justify-between">
              <div className="flex items-baseline gap-1.5">
                <span className="text-2xl font-black tabular-nums">{p.dorsal ?? "–"}</span>
                <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-[9px] font-bold uppercase text-neutral-500">{POS[p.pos]}</span>
              </div>
              <span className="grid h-9 w-9 place-items-center rounded-lg text-sm font-black text-white" style={{ backgroundColor: rc(p.oR) }}>{p.oR != null ? p.oR.toFixed(1) : "–"}</span>
            </div>
            <h4 className="truncate text-sm font-bold leading-tight">{p.name}</h4>
            <div className="mt-0.5 text-xs text-neutral-500">{2026 - p.born} {t.years} · {p.nat}</div>
            <div className="mt-2 border-t border-neutral-100 pt-1.5 text-xs"><span className="text-neutral-400">{t.value}: </span><span className="font-semibold text-neutral-700">{fmtMV(p.mv)}</span></div>
          </div>
        ))}
      </div>
      <p className="mt-4 text-xs text-neutral-400">{t.ratingHelp}</p>
    </div>
  );
}

/* --------------------------------------------------------- compartidos ---- */
function SectionHead({ title, sub, action, accent }) {
  return (
    <div className="mb-4 flex items-end justify-between">
      <div>
        <h1 className="text-xl font-black tracking-tight sm:text-2xl" style={accent ? { color: RED } : undefined}>{title}</h1>
        {sub && <p className="mt-0.5 text-sm text-neutral-500">{sub}</p>}
      </div>
      {action}
    </div>
  );
}

function Legend({ t }) {
  return (
    <div className="mt-4 flex flex-wrap gap-4 rounded-lg border border-neutral-200 bg-white px-4 py-3 text-xs">
      {[[ZONE.promo.bar, t.legend.promo], [ZONE.po.bar, t.legend.po], [ZONE.rel.bar, t.legend.rel]].map(([c, label]) => (
        <span key={label} className="flex items-center gap-1.5"><span className="h-3 w-3 rounded" style={{ backgroundColor: c }} />{label}</span>
      ))}
    </div>
  );
}
