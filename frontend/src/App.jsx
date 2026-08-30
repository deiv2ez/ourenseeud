import { useState, useMemo, useEffect } from "react";
import { api } from "./lib/api";
import Lineup from "./Lineup";

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
    nav: { dashboard: "Clasificación", sim: "Simulador", matchday: "Xornada", analysis: "Análise", hub: "UD Ourense", squad: "Plantilla", once: "Once" },
    season: "Tempada 2026-27 · 1ª RFEF · Grupo 1",
    team: "Equipo", pld: "PX", gf: "GF", ga: "GC", gd: "DG", pts: "Ptos", form: "Forma",
    oPts: "oPts", diff: "Δ", xg: "xG",
    champ: "Campión", playoff: "Playoff", releg: "Descenso",
    vTable: "Táboa", vProbs: "Probabilidades",
    vResume: "Currículum",
    resumeTitle: "Currículum — valor real dos puntos",
    resumeSub: "Pondera a dificultade do rival e onde se xogou. Δ = currículum − puntos reais.",
    resumeCol: "Currículum",
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
    mockNote: "O noso fútbol a través dos datos · modelo predictivo de eficiencia contextual",
    mdTitle: "Previa da xornada", mdSub: "Predición do modelo para cada partido",
    mdExpected: "Resultado esperado", mdOGoals: "Goles esperados", mdDraw: "Empate", mdProb: "Probabilidades", mdNoData: "Aínda non hai xornada dispoñible.", loading: "Cargando datos…", loadErr: "Non se puideron cargar os datos. Proba a recargar.",
    tpBack: "← Volver á clasificación", tpNext: "Próximo partido", tpCalendar: "Calendario",
    tpPlayed: "Xogados", tpUpcoming: "Pendentes", tpHome: "Casa", tpAway: "Fóra", tpJ: "X",
    tpStyle: "Perfil de estilo", tpOffense: "Ataque", tpDefense: "Defensa",
    tpHomePerf: "Local", tpAwayPerf: "Visitante", tpStyleNote: "Nota de estilo (prensa)", tpWin: "Vitoria", tpDraw: "Empate", tpLoss: "Derrota", reportBtn: "↓ Descargar informe do próximo partido (PDF)",
    tpXgTitle: "Rendemento xG", tpXgMatches: "partidos con estatísticas", tpXgFor: "Ataque",
    tpXgAgainst: "Defensa", tpXgGoals: "Goles", tpXgForShort: "a favor", tpXgAgainstShort: "en contra",
    signing: "Obxectivo", games: "Partidos",
    pdGoals: "Goles", pdAssists: "Asistencias", pdGA: "G+A", pdGoals90: "Goles/90",
    pdAssists90: "Asist./90", pdGA90: "G+A/90", pdMinGoal: "Min/gol", pdMinutes: "Minutos",
    pdPassPct: "% pases", pdPassPg: "Pases/part.", pdDuels: "% duelos gañ.", pdDuelsPg: "Duelos/part.",
    pdTackles: "Entradas/part.", pdORavg: "oRating medio", pdORbest: "Mellor oRating",
    pdGames: "partidos", pdMin: "min", pdNoData: "Aínda non hai estatísticas deste xogador.",
    anMerited: "Táboa merecida", anProjection: "Proxección", anObjectives: "Que precisa a UDO", anCompare: "Comparador",
    anMeritedSub: "Clasificación por puntos MERECIDOS (oPts) en vez dos reais.",
    anProjSub: "Onde acabará cada equipo segundo o modelo (posición media e rango).",
    anObjSub: "Puntos estimados para cada obxectivo e canto falta.",
    anModelTitle: "Segundo o modelo", anModelSub: "Probabilidade de cada obxectivo e posición proxectada a final de tempada.", anProjPos: "posición media", anRange: "rango",
    anCompareSub: "Compara dous equipos lado a lado.",
    anMeritedPos: "Merecida", anRealPos: "Real", anAvgPos: "Media", anRange: "Rango",
    anChampion: "Campión", anPlayoffG: "Playoff", anSafety: "Permanencia",
    anNeed: "Faltan", anThreshold: "Obxectivo", anReachable: "Alcanzable", anPts: "pts",
    anPick1: "Equipo 1", anPick2: "Equipo 2",
  },
  es: {
    tagline: "a nosa vida",
    nav: { dashboard: "Clasificación", sim: "Simulador", matchday: "Jornada", analysis: "Análisis", hub: "UD Ourense", squad: "Plantilla", once: "Once" },
    season: "Temporada 2026-27 · 1ª RFEF · Grupo 1",
    team: "Equipo", pld: "PJ", gf: "GF", ga: "GC", gd: "DG", pts: "Pts", form: "Forma",
    oPts: "oPts", diff: "Δ", xg: "xG",
    champ: "Campeón", playoff: "Playoff", releg: "Descenso",
    vTable: "Tabla", vProbs: "Probabilidades",
    vResume: "Currículum",
    resumeTitle: "Currículum — valor real de los puntos",
    resumeSub: "Pondera la dificultad del rival y dónde se jugó. Δ = currículum − puntos reales.",
    resumeCol: "Currículum",
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
    mockNote: "O noso fútbol a través dos datos · modelo predictivo de eficiencia contextual",
    mdTitle: "Previa de la jornada", mdSub: "Predicción del modelo para cada partido",
    mdExpected: "Resultado esperado", mdOGoals: "Goles esperados", mdDraw: "Empate", mdProb: "Probabilidades", mdNoData: "Aún no hay jornada disponible.", loading: "Cargando datos…", loadErr: "No se pudieron cargar los datos. Prueba a recargar.",
    tpBack: "← Volver a la clasificación", tpNext: "Próximo partido", tpCalendar: "Calendario",
    tpPlayed: "Jugados", tpUpcoming: "Pendientes", tpHome: "Casa", tpAway: "Fuera", tpJ: "J",
    tpStyle: "Perfil de estilo", tpOffense: "Ataque", tpDefense: "Defensa",
    tpHomePerf: "Local", tpAwayPerf: "Visitante", tpStyleNote: "Nota de estilo (prensa)", tpWin: "Victoria", tpDraw: "Empate", tpLoss: "Derrota", reportBtn: "↓ Descargar informe del próximo partido (PDF)",
    tpXgTitle: "Rendimiento xG", tpXgMatches: "partidos con estadísticas", tpXgFor: "Ataque",
    tpXgAgainst: "Defensa", tpXgGoals: "Goles", tpXgForShort: "a favor", tpXgAgainstShort: "en contra",
    signing: "Objetivo", games: "Partidos",
    pdGoals: "Goles", pdAssists: "Asistencias", pdGA: "G+A", pdGoals90: "Goles/90",
    pdAssists90: "Asist./90", pdGA90: "G+A/90", pdMinGoal: "Min/gol", pdMinutes: "Minutos",
    pdPassPct: "% pases", pdPassPg: "Pases/part.", pdDuels: "% duelos gan.", pdDuelsPg: "Duelos/part.",
    pdTackles: "Entradas/part.", pdORavg: "oRating medio", pdORbest: "Mejor oRating",
    pdGames: "partidos", pdMin: "min", pdNoData: "Aún no hay estadísticas de este jugador.",
    anMerited: "Tabla merecida", anProjection: "Proyección", anObjectives: "Qué necesita la UDO", anCompare: "Comparador",
    anMeritedSub: "Clasificación por puntos MERECIDOS (oPts) en vez de los reales.",
    anProjSub: "Dónde acabará cada equipo según el modelo (posición media y rango).",
    anObjSub: "Puntos estimados para cada objetivo y cuánto falta.",
    anModelTitle: "Según el modelo", anModelSub: "Probabilidad de cada objetivo y posición proyectada a final de temporada.", anProjPos: "posición media", anRange: "rango",
    anCompareSub: "Compara dos equipos lado a lado.",
    anMeritedPos: "Merecida", anRealPos: "Real", anAvgPos: "Media", anRange: "Rango",
    anChampion: "Campeón", anPlayoffG: "Playoff", anSafety: "Permanencia",
    anNeed: "Faltan", anThreshold: "Objetivo", anReachable: "Alcanzable", anPts: "pts",
    anPick1: "Equipo 1", anPick2: "Equipo 2",
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
  // Logo PERSONALIZADO da marca (icona, cabeceiras, pantalla de carga) desde
  // /public/escudos/logo.png. NON se usa nas clasificacións (alí vai o escudo normal).
  // Mentres non exista o PNG, cae a un placeholder "é" en vermello.
  const [ok, setOk] = useState(true);
  if (ok) {
    return (
      <img src="/escudos/logo.png" alt="Ourense é UD" onError={() => setOk(false)}
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
  const c = { W: "#1a8a4a", D: "#e0a500", L: "#c0392b" };
  return <span className="inline-flex gap-1">{form.map((r, i) => <span key={i} title={r} className="h-2 w-2 rounded-full" style={{ backgroundColor: c[r] }} />)}</span>;
}
function Bar({ value, color }) {
  return <div className="h-2.5 w-full overflow-hidden rounded bg-neutral-200"><div className="h-full rounded transition-all" style={{ width: `${Math.min(100, value)}%`, backgroundColor: color }} /></div>;
}

/* Estado de carga discreto (mentres o backend esperta ou responde). */
function Loading({ text }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-neutral-200 bg-white py-16 text-neutral-400">
      <div className="animate-pulse">
        <BrandCrest size={48} />
      </div>
      {text && <span className="text-sm">{text}</span>}
    </div>
  );
}

/* Cabeceira de táboa clicable para ordenar. Amosa ▲/▼ na columna activa. */
function SortTh({ col, label, sort, onClick, bold, title }) {
  const active = sort.col === col;
  const arrow = active ? (sort.dir === "desc" ? " ▾" : " ▴") : "";
  return (
    <th
      onClick={() => onClick(col)}
      title={title}
      className={`cursor-pointer select-none px-2 py-2.5 text-center font-semibold transition hover:text-neutral-900 ${bold ? "text-neutral-700" : ""} ${active ? "text-neutral-900" : ""}`}
    >
      {label}<span className="text-[10px]">{arrow}</span>
    </th>
  );
}

/* ================================================================ APP ===== */
export default function App() {
  const [lang, setLang] = useState("gl");
  const [section, setSection] = useState("dashboard");
  const [teamSlug, setTeamSlug] = useState(null); // ficha de equipo aberta
  const [isAdmin, setIsAdmin] = useState(() => typeof window !== "undefined" && window.location.hash === "#admin");
  const t = I18N[lang];

  useEffect(() => {
    const onHash = () => setIsAdmin(window.location.hash === "#admin");
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // Páxina de admin OCULTA: só accesible engadindo #admin á URL. Non hai enlace
  // visible na web. Protexida por login (usuario/contrasinal do backend).
  if (isAdmin) return <AdminPanel t={t} onExit={() => { window.location.hash = ""; setIsAdmin(false); }} />;

  const nav = [
    ["dashboard", t.nav.dashboard, "▦"],
    ["matchday", t.nav.matchday, "◷"],
    ["analysis", t.nav.analysis, "◈"],
    ["sim", t.nav.sim, "⇄"],
    ["hub", t.nav.hub, "◆"],
    ["once", t.nav.once, "⬡"],
    ["squad", t.nav.squad, "◫"],
  ];

  return (
    <div className="app-shell flex flex-col sm:flex-row bg-neutral-50 font-sans text-neutral-900">
      {/* ---------- menú lateral (só escritorio) ---------- */}
      <aside className="hidden sm:flex sticky top-0 h-screen w-56 flex-col justify-between border-r border-neutral-200 bg-white">
        <div>
          {/* marca */}
          <div className="flex items-center gap-3 border-b border-neutral-100 px-4 py-5">
            <BrandCrest size={52} />
            <div className="leading-tight">
              <div className="text-lg font-black tracking-tight">Ourense é <span style={{ color: RED }}>UD</span></div>
              <div className="text-xs italic text-neutral-400">{t.tagline}</div>
            </div>
          </div>
          {/* navegación */}
          <nav className="mt-2 px-2">
            {nav.map(([k, label, icon]) => (
              <button key={k} onClick={() => { setSection(k); setTeamSlug(null); }}
                className={`mb-1 flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                  section === k ? "text-white" : "text-neutral-600 hover:bg-neutral-100"
                }`}
                style={section === k ? { backgroundColor: RED } : undefined}>
                <span className="text-base">{icon}</span>
                <span>{label}</span>
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

      {/* ---------- cabeceira móbil (só móbil) ---------- */}
      <header className="safe-t sticky top-0 z-20 flex items-center justify-between border-b border-neutral-200 bg-white px-4 py-2.5 sm:hidden">
        <div className="flex items-center gap-2">
          <BrandCrest size={34} />
          <span className="text-base font-black tracking-tight">Ourense é <span style={{ color: RED }}>UD</span></span>
        </div>
        <div className="flex gap-1">
          {["gl", "es"].map((l) => (
            <button key={l} onClick={() => setLang(l)}
              className={`rounded px-2 py-1 text-xs font-semibold ${lang === l ? "bg-neutral-900 text-white" : "bg-neutral-100 text-neutral-500"}`}>
              {l.toUpperCase()}
            </button>
          ))}
        </div>
      </header>

      {/* ---------- contido ---------- */}
      <main className="min-w-0 flex-1">
        <div className="mx-auto max-w-5xl px-4 py-6 pb-24 sm:px-6 sm:pb-6">
          {teamSlug ? (
            <TeamProfile t={t} slug={teamSlug} onBack={() => setTeamSlug(null)} />
          ) : (
            <>
              {section === "dashboard" && <Dashboard t={t} onTeamClick={setTeamSlug} />}
              {section === "matchday" && <Matchday t={t} />}
              {section === "analysis" && <Analysis t={t} onTeamClick={setTeamSlug} />}
              {section === "sim" && <Simulator t={t} />}
              {section === "hub" && <CommandCenter t={t} />}
              {section === "once" && <Lineup t={t} token={null} />}
              {section === "squad" && <Squad t={t} />}
            </>
          )}
          <p className="mt-6 text-center text-xs text-neutral-400">{t.mockNote}</p>
        </div>
      </main>

      {/* ---------- barra de navegación inferior (só móbil) ---------- */}
      <nav className="safe-b fixed bottom-0 left-0 right-0 z-20 flex border-t border-neutral-200 bg-white sm:hidden">
        {nav.map(([k, label, icon]) => {
          const active = section === k && !teamSlug;
          return (
            <button key={k} onClick={() => { setSection(k); setTeamSlug(null); }}
              className="tap touch-target flex flex-1 flex-col items-center justify-center gap-0.5 py-1.5"
              style={active ? { color: RED } : { color: "#9a9a9a" }}>
              <span className="text-lg leading-none">{icon}</span>
              <span className="text-[10px] font-medium leading-tight">{label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}

/* ============================================================ ADMIN ======= *
 * Páxina oculta (#admin) para meter as cuotas da xornada. Protexida por login.
 * Tras gardar, o backend recalcula todo (simulacións incluídas).                */
function AdminPanel({ t, onExit }) {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState("");
  const [pass, setPass] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState("prev");        // prev | next | settings
  const [msg, setMsg] = useState("");
  // Siguiente (cuotas)
  const [jornada, setJornada] = useState(null);
  const [rows, setRows] = useState([]);
  // Anterior (stats)
  const [prevJornada, setPrevJornada] = useState(null);
  const [prevRows, setPrevRows] = useState([]);   // [{home,away,has_stats,raw}]
  const [ratingsRaw, setRatingsRaw] = useState(""); // volcado da plantilla UDO
  const [ratingsOut, setRatingsOut] = useState([]); // resultado dos oRatings
  const [udoMatch, setUdoMatch] = useState(null);   // último partido real da UDO
  // Plantel (edición)
  const [squad, setSquad] = useState([]);
  const [newSigning, setNewSigning] = useState({ name: "", nick: "", dorsal: "", pos: "DEL", note: "" });
  // Resultados (por partido)
  const [matches, setMatches] = useState(null);
  const [scoreInputs, setScoreInputs] = useState({});   // {key: {hg,ag}}

  const doLogin = async () => {
    setErr(""); setBusy(true);
    let ok = false;
    try {
      const r = await api.login(user.trim(), pass);
      setToken(r.token);
      try { sessionStorage.setItem("udo_token", r.token); } catch { /* noop */ }
      ok = true;
      // as cargas de datos NON deben tirar o login se algunha falla
      Promise.allSettled([loadNext(r.token), loadPrev(r.token), loadSquad(r.token), loadMatches(r.token)]);
    } catch {
      setErr("Usuario ou contrasinal incorrectos.");
    } finally { setBusy(false); }
  };

  const loadSquad = async (tk) => {
    try {
      const sq = await api.adminGetSquad(tk);
      setSquad((sq || []).map((p) => ({
        name: p.name, nick: p.nick || "", dorsal: p.dorsal ?? "",
        pos: p.pos || "", note: p.note || "", signing: !!p.signing,
        oRating: p.oRating,
      })));
    } catch { /* ignora */ }
  };

  const setSquadCell = (i, k, v) => setSquad((s) => s.map((p, j) => j === i ? { ...p, [k]: v } : p));

  const saveSquad = async () => {
    setMsg(""); setBusy(true);
    try {
      const players = squad.map((p) => ({
        name: p.name, nick: p.nick || null,
        dorsal: p.dorsal === "" ? null : parseInt(p.dorsal),
        pos: p.pos || null, note: p.note || null, signing: p.signing,
      }));
      const res = await api.adminSaveSquad(token, players);
      setMsg(`✓ Plantel gardado (${res.saved} xogadores). ${res.storage}`);
    } catch {
      setMsg("✗ Erro ao gardar o plantel.");
    } finally { setBusy(false); }
  };

  const addSigning = async () => {
    if (!newSigning.name.trim()) { setMsg("O fichaxe precisa polo menos un nome."); return; }
    setMsg(""); setBusy(true);
    try {
      await api.adminSaveSquad(token, [{
        name: newSigning.name.trim(), nick: newSigning.nick || null,
        dorsal: newSigning.dorsal === "" ? null : parseInt(newSigning.dorsal),
        pos: newSigning.pos, note: newSigning.note || null, signing: true,
      }]);
      setNewSigning({ name: "", nick: "", dorsal: "", pos: "DEL", note: "" });
      await loadSquad(token);
      setMsg("✓ Fichaxe engadido.");
    } catch {
      setMsg("✗ Erro ao engadir o fichaxe.");
    } finally { setBusy(false); }
  };

  const removeSigning = async (name) => {
    setBusy(true);
    try { await api.adminDeleteSigning(token, name); await loadSquad(token); setMsg("✓ Fichaxe borrado."); }
    catch { setMsg("✗ Erro ao borrar."); }
    finally { setBusy(false); }
  };

  const loadMatches = async (tk) => {
    try { setMatches(await api.adminListMatches(tk)); }
    catch { setMatches({ pending: [], played: [], postponed: [], counts: {} }); }
  };

  const mkey = (m) => `${m.jornada}|${m.home}|${m.away}`;

  const setScore = (m, field, val) => {
    const k = mkey(m);
    setScoreInputs((s) => ({ ...s, [k]: { ...s[k], [field]: val.replace(/[^0-9]/g, "") } }));
  };

  const saveResult = async (m, status) => {
    setMsg(""); setBusy(true);
    try {
      const k = mkey(m);
      const inp = scoreInputs[k] || {};
      const entry = { jornada: m.jornada, home: m.home, away: m.away, status };
      if (status === "played") {
        if (inp.hg === undefined || inp.hg === "" || inp.ag === undefined || inp.ag === "") {
          setMsg("✗ Mete os dous goles."); setBusy(false); return;
        }
        entry.hg = parseInt(inp.hg); entry.ag = parseInt(inp.ag);
      }
      await api.adminSetResult(token, entry);
      setMsg(status === "postponed" ? "✓ Partido marcado como aprazado."
           : status === "pending" ? "✓ Partido devolto a pendente."
           : `✓ Resultado gardado: ${m.home} ${entry.hg}-${entry.ag} ${m.away}.`);
      await loadMatches(token);
    } catch (e) {
      setMsg(`✗ ${String(e.message || "Erro ao gardar o resultado.")}`);
    } finally { setBusy(false); }
  };

  const reloadApi = async () => {
    setMsg(""); setBusy(true);
    try {
      const r = await api.adminReload(token);
      setMsg((r.ok ? "✓ " : "⚠ ") + (r.message || (r.ok ? "Actualizado." : "Non se puido actualizar.")));
      if (r.ok) await loadMatches(token);
    } catch {
      setMsg("✗ Erro ao contactar coa API. Podes meter os resultados a man.");
    } finally { setBusy(false); }
  };

  const loadNext = async (tk) => {
    const md = await api.adminMatchdayOdds(tk);
    setJornada(md.jornada);
    setRows((md.matches || []).map((m) => ({
      ...m, c_home: m.c_home ?? "", c_draw: m.c_draw ?? "", c_away: m.c_away ?? "",
    })));
  };

  const loadPrev = async (tk) => {
    const pm = await api.adminPreviousMatches(tk);
    setPrevJornada(pm.jornada);
    setPrevRows((pm.matches || []).map((m) => ({ ...m, raw: "" })));
    try { setUdoMatch(await api.adminUdoLastMatch(tk)); } catch { /* ignora */ }
  };

  const setCell = (i, k, v) => setRows((rs) => rs.map((r, j) => j === i ? { ...r, [k]: v } : r));
  const setPrevCell = (i, v) => setPrevRows((rs) => rs.map((r, j) => j === i ? { ...r, raw: v } : r));

  const saveOdds = async () => {
    setMsg(""); setBusy(true);
    try {
      const entries = rows
        .filter((r) => r.c_home && r.c_draw && r.c_away)
        .map((r) => ({ home: r.home, away: r.away, jornada: r.jornada,
          c_home: parseFloat(r.c_home), c_draw: parseFloat(r.c_draw), c_away: parseFloat(r.c_away) }));
      if (!entries.length) { setMsg("Mete algunha cuota antes de gardar."); setBusy(false); return; }
      const res = await api.adminSetOdds(token, jornada, entries);
      setMsg(`✓ Gardadas ${res.updated} cuotas. Recalculado. (${res.storage})`);
    } catch {
      setMsg("✗ Erro ao gardar as cuotas.");
    } finally { setBusy(false); }
  };

  const saveStats = async () => {
    setMsg(""); setBusy(true);
    try {
      const entries = prevRows
        .filter((r) => r.raw && r.raw.trim())
        .map((r) => ({ home: r.home, away: r.away, raw: r.raw }));
      if (!entries.length) { setMsg("Pega o volcado dalgún partido antes de gardar."); setBusy(false); return; }
      const res = await api.adminSetStats(token, prevJornada, entries);
      const xgs = res.parsed.map((p) => `${p.xg[0]}-${p.xg[1]}`).join(", ");
      setMsg(`✓ Gardadas estatísticas de ${res.saved} partidos. xG: ${xgs} (${res.storage})`);
      await loadPrev(token);
    } catch {
      setMsg("✗ Erro ao gardar as estatísticas.");
    } finally { setBusy(false); }
  };

  const saveRatings = async () => {
    setMsg(""); setBusy(true); setRatingsOut([]);
    try {
      if (!ratingsRaw.trim()) { setMsg("Pega o volcado das estatísticas dos xogadores da UDO."); setBusy(false); return; }
      // usar a xornada do ÚLTIMO partido real da UDO (non unha xornada abstracta)
      let j = udoMatch?.jornada ?? prevJornada;
      const res = await api.adminSetRatings(token, j, ratingsRaw);
      setRatingsOut(res.ratings || []);
      const ctx = udoMatch?.rival ? ` (partido vs ${udoMatch.rival})` : "";
      setMsg(`✓ Calculados ${res.count} oRatings da xornada ${j}${ctx} (${res.storage}).`);
    } catch {
      setMsg("✗ Erro ao calcular os oRatings. Revisa o formato do volcado.");
    } finally { setBusy(false); }
  };

  const reload = async () => {
    setMsg(""); setBusy(true);
    try {
      const res = await api.adminReload(token);
      setMsg(`✓ Resultados actualizados desde a API (${res.played} partidos xogados). Recalculado.`);
      await Promise.all([loadNext(token), loadPrev(token)]);
    } catch {
      setMsg("✗ Erro ao actualizar resultados. Comproba a clave da API en Render.");
    } finally { setBusy(false); }
  };

  // pantalla de login
  if (!token) {
    return (
      <div className="app-shell flex items-center justify-center bg-neutral-900 px-4">
        <div className="w-full max-w-xs rounded-xl bg-white p-6 shadow-xl">
          <div className="mb-4 flex items-center gap-2">
            <BrandCrest size={36} />
            <span className="text-sm font-black">Admin · Ourense é UD</span>
          </div>
          <input value={user} onChange={(e) => setUser(e.target.value)} placeholder="Usuario" autoComplete="off"
            className="mb-2 w-full rounded-md border border-neutral-300 px-3 py-2 text-sm" />
          <input value={pass} onChange={(e) => setPass(e.target.value)} placeholder="Contrasinal" type="password"
            onKeyDown={(e) => e.key === "Enter" && doLogin()}
            className="mb-3 w-full rounded-md border border-neutral-300 px-3 py-2 text-sm" />
          {err && <p className="mb-2 text-xs text-red-600">{err}</p>}
          <button onClick={doLogin} disabled={busy}
            className="w-full rounded-md py-2 text-sm font-semibold text-white disabled:opacity-50"
            style={{ backgroundColor: RED }}>{busy ? "…" : "Entrar"}</button>
          <button onClick={onExit} className="mt-2 w-full text-center text-xs text-neutral-400">Voltar á web</button>
        </div>
      </div>
    );
  }

  const TABS = [["prev", "Anterior"], ["next", "Seguinte"], ["results", "Resultados"], ["squad", "Plantel"], ["settings", "Axustes"]];

  return (
    <div className="app-shell bg-neutral-50">
      <div className="mx-auto max-w-2xl px-4 py-6">
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-lg font-black">Panel · Ourense é UD</h1>
          <button onClick={onExit} className="text-xs text-neutral-500">Saír</button>
        </div>

        {/* pestanas */}
        <div className="scroll-x mb-4 flex gap-1 rounded-lg border border-neutral-200 bg-white p-1">
          {TABS.map(([k, label]) => (
            <button key={k} onClick={() => { setTab(k); setMsg(""); }}
              className={`tap shrink-0 rounded-md px-4 py-1.5 text-sm font-medium transition ${tab === k ? "text-white" : "text-neutral-600 hover:bg-neutral-100"}`}
              style={tab === k ? { backgroundColor: RED } : undefined}>{label}</button>
          ))}
        </div>

        {/* ---- ANTERIOR: estatísticas xG dos partidos xogados ---- */}
        {tab === "prev" && (
          <>
            <h2 className="mb-1 text-sm font-bold">Estatísticas · Xornada {prevJornada}</h2>
            <p className="mb-4 text-xs text-neutral-500">
              Pega ao lado de cada partido o volcado do Web Scraper de Sofascore (fila "Match overview").
              Extráense xG, tiros, posesión… para o análise das fichas. Non afecta ás predicións.
            </p>
            <div className="space-y-3">
              {prevRows.map((r, i) => {
                const th = T[NAME_TO_KEY[r.home]] || { n: r.home, s: "?" };
                const ta = T[NAME_TO_KEY[r.away]] || { n: r.away, s: "?" };
                return (
                  <div key={i} className="rounded-lg border border-neutral-200 bg-white p-3">
                    <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
                      <span>{th.n} <span className="text-neutral-400">vs</span> {ta.n}</span>
                      {r.has_stats && <span className="rounded bg-green-100 px-1.5 py-0.5 text-[10px] font-bold text-green-700">✓ xa hai</span>}
                    </div>
                    <textarea value={r.raw} onChange={(e) => setPrevCell(i, e.target.value)}
                      rows={2} placeholder="Pega aquí o volcado de Sofascore deste partido…"
                      className="w-full resize-y rounded-md border border-neutral-300 px-2 py-1.5 text-xs font-mono" />
                  </div>
                );
              })}
            </div>
            {msg && <p className="mt-3 text-sm font-medium" style={{ color: msg.startsWith("✓") ? "#1a8a4a" : "#c0392b" }}>{msg}</p>}
            <button onClick={saveStats} disabled={busy}
              className="mt-4 w-full rounded-lg py-3 text-sm font-bold text-white disabled:opacity-50"
              style={{ backgroundColor: RED }}>{busy ? "Gardando…" : "Gardar estatísticas"}</button>

            {/* oRatings da plantilla da UDO */}
            <div className="mt-8 border-t border-neutral-200 pt-5">
              <h2 className="mb-1 text-sm font-bold">oRating · plantilla UD Ourense</h2>
              <p className="mb-2 text-xs text-neutral-500">
                Pega o volcado das estatísticas dos xogadores da UDO (páxina de player stats de
                Sofascore). Calcúlase o oRating de cada un e gárdase.
              </p>
              {udoMatch && udoMatch.played && (
                <div className="mb-3 rounded-md bg-neutral-100 px-3 py-2 text-xs text-neutral-600">
                  Asígnase ao último partido da UDO: <b>J{udoMatch.jornada}</b> · {udoMatch.home} {udoMatch.score?.[0]}-{udoMatch.score?.[1]} {udoMatch.away}
                </div>
              )}
              <textarea value={ratingsRaw} onChange={(e) => setRatingsRaw(e.target.value)}
                rows={4} placeholder="Pega aquí o volcado dos xogadores da UD Ourense…"
                className="w-full resize-y rounded-md border border-neutral-300 px-2 py-1.5 text-xs font-mono" />
              <button onClick={saveRatings} disabled={busy}
                className="mt-3 w-full rounded-lg border border-neutral-800 bg-neutral-800 py-2.5 text-sm font-bold text-white disabled:opacity-50">
                {busy ? "Calculando…" : "Calcular e gardar oRatings"}
              </button>
              {ratingsOut.length > 0 && (
                <div className="mt-3 space-y-1">
                  {ratingsOut.map((p, i) => (
                    <div key={i} className="flex items-center justify-between rounded bg-neutral-50 px-2 py-1 text-xs">
                      <span>{p.name} <span className="text-neutral-400">· {p.pos}</span></span>
                      <span className="tabular-nums font-bold" style={{ color: p.oRating >= 7 ? "#1a8a4a" : p.oRating < 5 ? "#c0392b" : "#666" }}>{p.oRating.toFixed(1)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {/* ---- SEGUINTE: cuotas da próxima xornada ---- */}
        {tab === "next" && (
          <>
            <h2 className="mb-1 text-sm font-bold">Cuotas · próximos partidos</h2>
            <p className="mb-4 text-xs text-neutral-500">
              Mete as cuotas decimais 1-X-2 (de betexplorer) dos próximos partidos. Cada un
              leva a súa xornada (poden estar mesturadas por aprazamentos). Ao gardar,
              recalcúlanse as predicións. Deixa en branco os que non teñan cuota.
            </p>
            <div className="space-y-2">
              {rows.map((r, i) => {
                const th = T[NAME_TO_KEY[r.home]] || { n: r.home };
                const ta = T[NAME_TO_KEY[r.away]] || { n: r.away };
                return (
                  <div key={i} className={`rounded-lg border bg-white p-3 ${r.postponed ? "border-amber-300" : "border-neutral-200"}`}>
                    <div className="mb-1 flex items-center justify-between text-[10px] text-neutral-400">
                      <span>J{r.jornada}{r.postponed && <span className="ml-1 font-bold text-amber-600">· aprazado</span>}</span>
                      <span>{r.date || ""}</span>
                    </div>
                    <div className="mb-2 text-sm font-semibold">{th.n} <span className="text-neutral-400">vs</span> {ta.n}</div>
                    <div className="grid grid-cols-3 gap-2">
                      {[["c_home", "1"], ["c_draw", "X"], ["c_away", "2"]].map(([k, label]) => (
                        <div key={k}>
                          <label className="block text-[10px] uppercase text-neutral-400">{label}</label>
                          <input inputMode="decimal" value={r[k]} onChange={(e) => setCell(i, k, e.target.value)}
                            placeholder="—" className="w-full rounded-md border border-neutral-300 px-2 py-1.5 text-sm tabular-nums" />
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
            {msg && <p className="mt-3 text-sm font-medium" style={{ color: msg.startsWith("✓") ? "#1a8a4a" : "#c0392b" }}>{msg}</p>}
            <button onClick={saveOdds} disabled={busy}
              className="mt-4 w-full rounded-lg py-3 text-sm font-bold text-white disabled:opacity-50"
              style={{ backgroundColor: RED }}>{busy ? "Gardando…" : "Gardar e recalcular"}</button>
          </>
        )}

        {/* ---- RESULTADOS: xestión partido a partido (aprazamentos incluídos) ---- */}
        {tab === "results" && (
          <>
            <h2 className="mb-1 text-sm font-bold">Resultados</h2>
            <p className="mb-3 text-xs text-neutral-500">
              Mete o resultado de cada partido cando se xogue, na orde que sexa. Se un se
              apraza, márcao como <b>aprazado</b> e metes o resultado cando toque. Nada
              depende de "pasar de xornada": cada partido é independente.
            </p>
            <button onClick={reloadApi} disabled={busy}
              className="tap mb-4 w-full rounded-lg border border-neutral-300 py-2.5 text-sm font-semibold text-neutral-700 disabled:opacity-50">
              {busy ? "Actualizando…" : "↻ Probar actualización automática (API)"}
            </button>
            {msg && <p className="mb-3 text-sm font-medium" style={{ color: msg.startsWith("✓") ? "#1a8a4a" : msg.startsWith("⚠") ? "#c99700" : "#c0392b" }}>{msg}</p>}

            {matches === null ? <Loading text={t.loading} /> : (
              <>
                <h3 className="mb-2 text-xs font-bold uppercase text-neutral-500">
                  Pendentes {matches.counts?.pending ? `(${matches.counts.pending})` : ""}
                </h3>
                <div className="space-y-2">
                  {matches.pending.map((m) => {
                    const k = `${m.jornada}|${m.home}|${m.away}`;
                    const inp = scoreInputs[k] || {};
                    return (
                      <div key={k} className="rounded-lg border border-neutral-200 bg-white p-2.5">
                        <div className="mb-1.5 flex items-center justify-between text-[10px] text-neutral-400">
                          <span>J{m.jornada}</span><span>{m.date || ""}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="flex-1 truncate text-right text-sm font-medium">{m.home}</span>
                          <input inputMode="numeric" value={inp.hg ?? ""} onChange={(e) => setScore(m, "hg", e.target.value)}
                            className="w-9 rounded border border-neutral-300 py-1 text-center text-sm tabular-nums" />
                          <span className="text-neutral-300">-</span>
                          <input inputMode="numeric" value={inp.ag ?? ""} onChange={(e) => setScore(m, "ag", e.target.value)}
                            className="w-9 rounded border border-neutral-300 py-1 text-center text-sm tabular-nums" />
                          <span className="flex-1 truncate text-sm font-medium">{m.away}</span>
                        </div>
                        <div className="mt-2 flex gap-2">
                          <button onClick={() => saveResult(m, "played")} disabled={busy}
                            className="tap flex-1 rounded py-1.5 text-xs font-bold text-white disabled:opacity-50" style={{ backgroundColor: RED }}>
                            Gardar resultado
                          </button>
                          <button onClick={() => saveResult(m, "postponed")} disabled={busy}
                            className="tap rounded border border-neutral-300 px-3 py-1.5 text-xs font-medium text-neutral-600 disabled:opacity-50">
                            Aprazar
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {matches.postponed?.length > 0 && (
                  <>
                    <h3 className="mb-2 mt-5 text-xs font-bold uppercase" style={{ color: "#c99700" }}>
                      Aprazados ({matches.postponed.length})
                    </h3>
                    <div className="space-y-2">
                      {matches.postponed.map((m) => {
                        const k = `${m.jornada}|${m.home}|${m.away}`;
                        const inp = scoreInputs[k] || {};
                        return (
                          <div key={k} className="rounded-lg border border-amber-200 bg-amber-50 p-2.5">
                            <div className="mb-1.5 text-[10px] text-amber-700">J{m.jornada} · aprazado</div>
                            <div className="flex items-center gap-2">
                              <span className="flex-1 truncate text-right text-sm font-medium">{m.home}</span>
                              <input inputMode="numeric" value={inp.hg ?? ""} onChange={(e) => setScore(m, "hg", e.target.value)}
                                className="w-9 rounded border border-neutral-300 py-1 text-center text-sm tabular-nums" />
                              <span className="text-neutral-300">-</span>
                              <input inputMode="numeric" value={inp.ag ?? ""} onChange={(e) => setScore(m, "ag", e.target.value)}
                                className="w-9 rounded border border-neutral-300 py-1 text-center text-sm tabular-nums" />
                              <span className="flex-1 truncate text-sm font-medium">{m.away}</span>
                            </div>
                            <button onClick={() => saveResult(m, "played")} disabled={busy}
                              className="tap mt-2 w-full rounded py-1.5 text-xs font-bold text-white disabled:opacity-50" style={{ backgroundColor: RED }}>
                              Xa se xogou · gardar resultado
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </>
                )}

                {matches.played?.length > 0 && (
                  <>
                    <h3 className="mb-2 mt-5 text-xs font-bold uppercase text-neutral-500">Xogados recentes</h3>
                    <div className="space-y-1">
                      {matches.played.slice().reverse().map((m) => {
                        const k = `${m.jornada}|${m.home}|${m.away}`;
                        return (
                          <div key={k} className="flex items-center justify-between rounded bg-neutral-50 px-2.5 py-1.5 text-xs">
                            <span className="truncate">J{m.jornada} · {m.home} <b>{m.hg}-{m.ag}</b> {m.away}</span>
                            <button onClick={() => saveResult(m, "pending")} disabled={busy}
                              className="tap ml-2 shrink-0 text-[11px] text-neutral-400">Desfacer</button>
                          </div>
                        );
                      })}
                    </div>
                  </>
                )}
              </>
            )}
          </>
        )}

        {/* ---- PLANTEL: editar apodo, dorsal, posición, nota + fichaxes ---- */}
        {tab === "squad" && (
          <>
            <h2 className="mb-1 text-sm font-bold">Plantel</h2>
            <p className="mb-4 text-xs text-neutral-500">
              O nome de Sofascore é a referencia interna (non se toca). Podes poñer un apodo
              (o que se ve no frontend), dorsal, demarcación e unha frase curta. Tamén engadir
              fichaxes.
            </p>
            <div className="space-y-2">
              {squad.map((p, i) => (
                <div key={p.name} className="rounded-lg border border-neutral-200 bg-white p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-xs text-neutral-400">{p.name}{p.signing && <span className="ml-1 rounded bg-amber-100 px-1 text-[9px] font-bold text-amber-700">FICHAXE</span>}</span>
                    {p.oRating != null && <span className="text-xs font-bold tabular-nums">{p.oRating.toFixed(1)}</span>}
                  </div>
                  <div className="grid grid-cols-[1fr_54px_70px] gap-2">
                    <input value={p.nick} onChange={(e) => setSquadCell(i, "nick", e.target.value)}
                      placeholder="Apodo (frontend)" className="rounded-md border border-neutral-300 px-2 py-1.5 text-sm" />
                    <input inputMode="numeric" value={p.dorsal} onChange={(e) => setSquadCell(i, "dorsal", e.target.value)}
                      placeholder="Nº" className="rounded-md border border-neutral-300 px-2 py-1.5 text-sm tabular-nums" />
                    <select value={p.pos} onChange={(e) => setSquadCell(i, "pos", e.target.value)}
                      className="rounded-md border border-neutral-300 px-1 py-1.5 text-sm">
                      {["GK", "DEF", "MED", "DEL"].map((o) => <option key={o} value={o}>{o}</option>)}
                    </select>
                  </div>
                  <input value={p.note} onChange={(e) => setSquadCell(i, "note", e.target.value)}
                    placeholder="Frase ou adxectivo curto (opcional)" className="mt-2 w-full rounded-md border border-neutral-300 px-2 py-1.5 text-xs" />
                  {p.signing && (
                    <button onClick={() => removeSigning(p.name)} className="mt-2 text-[11px] text-red-500">Borrar fichaxe</button>
                  )}
                </div>
              ))}
            </div>

            {/* engadir fichaxe */}
            <div className="mt-4 rounded-lg border border-dashed border-neutral-300 bg-white p-3">
              <h3 className="mb-2 text-xs font-bold uppercase text-neutral-500">Engadir fichaxe / obxectivo</h3>
              <div className="grid grid-cols-[1fr_54px_70px] gap-2">
                <input value={newSigning.name} onChange={(e) => setNewSigning((s) => ({ ...s, name: e.target.value }))}
                  placeholder="Nome (Sofascore)" className="rounded-md border border-neutral-300 px-2 py-1.5 text-sm" />
                <input inputMode="numeric" value={newSigning.dorsal} onChange={(e) => setNewSigning((s) => ({ ...s, dorsal: e.target.value }))}
                  placeholder="Nº" className="rounded-md border border-neutral-300 px-2 py-1.5 text-sm tabular-nums" />
                <select value={newSigning.pos} onChange={(e) => setNewSigning((s) => ({ ...s, pos: e.target.value }))}
                  className="rounded-md border border-neutral-300 px-1 py-1.5 text-sm">
                  {["GK", "DEF", "MED", "DEL"].map((o) => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
              <input value={newSigning.nick} onChange={(e) => setNewSigning((s) => ({ ...s, nick: e.target.value }))}
                placeholder="Apodo (opcional)" className="mt-2 w-full rounded-md border border-neutral-300 px-2 py-1.5 text-sm" />
              <input value={newSigning.note} onChange={(e) => setNewSigning((s) => ({ ...s, note: e.target.value }))}
                placeholder="Frase ou adxectivo (opcional)" className="mt-2 w-full rounded-md border border-neutral-300 px-2 py-1.5 text-xs" />
              <button onClick={addSigning} disabled={busy}
                className="mt-3 w-full rounded-lg border border-neutral-800 bg-neutral-800 py-2 text-sm font-bold text-white disabled:opacity-50">
                + Engadir
              </button>
            </div>

            {msg && <p className="mt-3 text-sm font-medium" style={{ color: msg.startsWith("✓") ? "#1a8a4a" : "#c0392b" }}>{msg}</p>}
            <button onClick={saveSquad} disabled={busy}
              className="mt-4 w-full rounded-lg py-3 text-sm font-bold text-white disabled:opacity-50"
              style={{ backgroundColor: RED }}>{busy ? "Gardando…" : "Gardar cambios do plantel"}</button>
          </>
        )}

        {/* ---- AXUSTES ---- */}
        {tab === "settings" && (
          <>
            <h2 className="mb-1 text-sm font-bold">Axustes</h2>
            <p className="mb-4 text-xs text-neutral-500">
              Actualiza os resultados dos partidos desde a API-Football. Faino os días de xornada
              para ver a clasificación actualizada.
            </p>
            <button onClick={reload} disabled={busy}
              className="w-full rounded-lg border border-neutral-300 bg-white py-3 text-sm font-semibold text-neutral-700 hover:bg-neutral-100 disabled:opacity-50">
              {busy ? "…" : "↻ Actualizar resultados desde a API"}
            </button>
            {msg && <p className="mt-3 text-sm font-medium" style={{ color: msg.startsWith("✓") ? "#1a8a4a" : "#c0392b" }}>{msg}</p>}
          </>
        )}
      </div>
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

/* ======================================================== FICHA EQUIPO ==== */
function TeamProfile({ t, slug, onBack }) {
  const [d, setD] = useState(null);
  useEffect(() => {
    let alive = true;
    (async () => {
      try { const x = await api.teamProfile(slug); if (alive) setD(x); }
      catch { if (alive) setD({ error: true }); }
    })();
    return () => { alive = false; };
  }, [slug]);

  const meta = (name, s) => {
    const k = NAME_TO_KEY[name] || s;
    return T[k] ? { ...T[k], k } : { n: name, c: "#888", s: (name || "?").slice(0, 3).toUpperCase(), k: s };
  };
  const back = (
    <button onClick={onBack} className="mb-4 text-xs font-semibold text-neutral-500 hover:text-neutral-900">{t.tpBack}</button>
  );
  if (!d) return <div>{back}<div className="rounded-lg border border-neutral-200 bg-white p-8 text-center text-neutral-400">···</div></div>;
  if (d.error) return <div>{back}<div className="rounded-lg border border-neutral-200 bg-white p-8 text-center text-neutral-400">—</div></div>;

  const team = meta(d.team, d.slug);
  const played = d.fixtures.filter((f) => f.played);
  const upcoming = d.fixtures.filter((f) => !f.played);
  const oDelta = +(d.oPts - d.pts).toFixed(1);

  return (
    <div>
      {back}
      {/* cabeceira */}
      <div className="mb-4 flex items-center gap-4 rounded-xl border border-neutral-200 bg-white p-5" style={team.udo ? { borderColor: RED } : undefined}>
        <Crest team={team} size={64} />
        <div className="flex-1">
          <h1 className="text-2xl font-black tracking-tight" style={team.udo ? { color: RED } : undefined}>{d.team}</h1>
          <div className="mt-1 flex items-center gap-3 text-sm text-neutral-500">
            <span className="font-bold text-neutral-900">{d.pos}º</span>
            <span>{d.pts} {t.pts}</span>
            <FormDots form={d.form} />
          </div>
        </div>
      </div>

      {/* resumo en números */}
      <div className="mb-4 grid grid-cols-3 gap-3 sm:grid-cols-6">
        {[[t.pld, d.pld], [t.pts, d.pts], ["GF", d.gf], ["GC", d.ga], [t.gd, d.gd > 0 ? `+${d.gd}` : d.gd], ["oPts", d.oPts]].map(([label, val]) => (
          <div key={label} className="rounded-lg border border-neutral-200 bg-white p-3 text-center">
            <div className="text-lg font-black tabular-nums">{val}</div>
            <div className="text-[10px] uppercase tracking-wide text-neutral-400">{label}</div>
          </div>
        ))}
      </div>

      {/* oPts vs pts */}
      <div className="mb-4 inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-semibold" style={{ backgroundColor: oDelta > 0.5 ? "#e7f5ec" : oDelta < -0.5 ? "#fbecea" : "#f3f3f3", color: oDelta > 0.5 ? "#1a8a4a" : oDelta < -0.5 ? "#c0392b" : "#777" }}>
        {oDelta > 0.5 ? "▲" : oDelta < -0.5 ? "▼" : "="} oPts {d.oPts} vs {d.pts} reais ({oDelta > 0 ? `+${oDelta}` : oDelta})
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* próximo partido */}
        {d.next && (
          <section className="rounded-lg border border-neutral-200 bg-white p-4">
            <h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-neutral-500">{t.tpNext} · {t.tpJ}{d.next.jornada}</h3>
            <div className="mb-3 flex items-center justify-center gap-3">
              {(() => { const h = meta(d.next.home, d.next.home_slug), a = meta(d.next.away, d.next.away_slug); return (<>
                <div className="flex flex-col items-center gap-1"><Crest team={h} size={34} /><span className="text-[11px]" style={h.udo ? { color: RED } : undefined}>{h.n}</span></div>
                <div className="text-center"><div className="text-xl font-black tabular-nums">{d.next.likely_score[0]}-{d.next.likely_score[1]}</div><div className="text-[9px] uppercase text-neutral-400">{t.mdOGoals}</div>
                  {d.next.likely_1x2 && (
                    <div className="mx-auto mt-1 w-fit rounded-full px-2 py-0.5 text-[10px] font-black text-white"
                      style={{ backgroundColor: d.next.likely_1x2 === "1" ? "#1a8a4a" : d.next.likely_1x2 === "2" ? "#c0392b" : "#e0a500" }}>
                      {d.next.likely_1x2 === "1" ? h.s : d.next.likely_1x2 === "2" ? a.s : t.mdDraw}
                    </div>
                  )}
                </div>
                <div className="flex flex-col items-center gap-1"><Crest team={a} size={34} /><span className="text-[11px]" style={a.udo ? { color: RED } : undefined}>{a.n}</span></div>
              </>); })()}
            </div>
            <div className="flex h-6 overflow-hidden rounded text-[10px] font-bold text-white">
              <div className="grid place-items-center" style={{ width: `${d.next.p_win}%`, backgroundColor: "#1a8a4a" }} title={`${t.tpWin}: ${d.next.p_win}%`}>{d.next.p_win >= 12 ? `${d.next.p_win}%` : ""}</div>
              <div className="grid place-items-center" style={{ width: `${d.next.p_draw}%`, backgroundColor: "#e0a500" }} title={`${t.tpDraw}: ${d.next.p_draw}%`}>{d.next.p_draw >= 12 ? `${d.next.p_draw}%` : ""}</div>
              <div className="grid place-items-center" style={{ width: `${d.next.p_loss}%`, backgroundColor: "#c0392b" }} title={`${t.tpLoss}: ${d.next.p_loss}%`}>{d.next.p_loss >= 12 ? `${d.next.p_loss}%` : ""}</div>
            </div>
            <div className="mt-1 flex justify-between text-[9px] uppercase text-neutral-400">
              <span>{t.tpWin}</span><span>{t.tpDraw}</span><span>{t.tpLoss}</span>
            </div>
            <div className="mt-1 text-center text-[10px] text-neutral-400">{d.next.is_home ? t.tpHome : t.tpAway} · oG {d.next.oGoals_home}-{d.next.oGoals_away}</div>
          </section>
        )}

        {/* calendario */}
        <section className="rounded-lg border border-neutral-200 bg-white p-4">
          <h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-neutral-500">{t.tpCalendar}</h3>
          <div className="max-h-72 space-y-1 overflow-y-auto pr-1">
            {played.map((f, i) => {
              const rv = meta(f.rival, f.rival_slug);
              const col = f.result === "W" ? "#1a8a4a" : f.result === "L" ? "#c0392b" : "#9a9a9a";
              return (
                <div key={`p${i}`} className="flex items-center gap-2 rounded px-2 py-1 text-xs">
                  <span className="w-6 text-neutral-400 tabular-nums">{t.tpJ}{f.jornada}</span>
                  <span className="w-8 text-[9px] uppercase text-neutral-400">{f.is_home ? t.tpHome : t.tpAway}</span>
                  <Crest team={rv} size={16} />
                  <span className="flex-1 truncate text-neutral-700">{rv.n}</span>
                  <span className="font-bold tabular-nums">{f.gf}-{f.ga}</span>
                  <span className="grid h-4 w-4 place-items-center rounded-full text-[9px] font-bold text-white" style={{ backgroundColor: col }}>{f.result}</span>
                </div>
              );
            })}
            {upcoming.map((f, i) => {
              const rv = meta(f.rival, f.rival_slug);
              return (
                <div key={`u${i}`} className="flex items-center gap-2 rounded px-2 py-1 text-xs opacity-70">
                  <span className="w-6 text-neutral-400 tabular-nums">{t.tpJ}{f.jornada}</span>
                  <span className="w-8 text-[9px] uppercase text-neutral-400">{f.is_home ? t.tpHome : t.tpAway}</span>
                  <Crest team={rv} size={16} />
                  <span className="flex-1 truncate text-neutral-600">{rv.n}</span>
                  <span className="text-[10px] text-neutral-400">{f.date || "—"}</span>
                </div>
              );
            })}
          </div>
        </section>
      </div>

      {/* perfil de estilo */}
      {d.style && d.style.played > 0 && (
        <section className="mt-4 rounded-lg border border-neutral-200 bg-white p-4">
          <h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-neutral-500">{t.tpStyle}</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            {[[t.tpOffense, d.style.offense, "#c0392b"], [t.tpDefense, d.style.defense, "#2f6fd0"], [t.tpHomePerf, d.style.home, "#1a8a4a"], [t.tpAwayPerf, d.style.away, "#e0a500"]].map(([label, val, col]) => (
              <div key={label}>
                <div className="mb-0.5 flex justify-between text-xs"><span className="text-neutral-600">{label}</span><span className="font-bold tabular-nums">{val}</span></div>
                <div className="h-2.5 w-full overflow-hidden rounded bg-neutral-200"><div className="h-full rounded" style={{ width: `${val}%`, backgroundColor: col }} /></div>
              </div>
            ))}
          </div>
          {d.style_note && (
            <div className="mt-3 rounded-md bg-neutral-50 p-3 text-xs text-neutral-600">
              <span className="font-semibold">{t.tpStyleNote}: </span>{d.style_note}
            </div>
          )}
        </section>
      )}

      {/* ---- Rendemento xG (capa de análise; só se hai estatísticas metidas) ---- */}
      {d.xg && (
        <section className="mt-5 rounded-lg border border-neutral-200 bg-white p-4">
          <h3 className="mb-1 text-sm font-bold">{t.tpXgTitle}</h3>
          <p className="mb-3 text-[11px] text-neutral-400">{d.xg.stats.matches} {t.tpXgMatches}</p>

          {/* barras goles vs xG */}
          {[["af", d.xg.stats.gf, d.xg.stats.xgf, d.xg.stats.off_diff],
            ["co", d.xg.stats.ga, d.xg.stats.xga, d.xg.stats.def_diff]].map(([kind, goals, xg, diff]) => {
            const max = Math.max(goals, xg, 1);
            const isOff = kind === "af";
            // para ofensiva: diff+ é bo; para defensiva: diff+ é bo tamén (concede menos)
            const good = diff >= 0;
            return (
              <div key={kind} className="mb-3">
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="font-semibold text-neutral-600">{isOff ? t.tpXgFor : t.tpXgAgainst}</span>
                  <span className="tabular-nums font-bold" style={{ color: good ? "#1a8a4a" : "#c0392b" }}>
                    {diff > 0 ? "+" : ""}{diff}
                  </span>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="w-16 text-[10px] text-neutral-400">{t.tpXgGoals}</span>
                    <div className="h-2.5 flex-1 rounded bg-neutral-100">
                      <div className="h-full rounded" style={{ width: `${(goals / max) * 100}%`, backgroundColor: RED }} />
                    </div>
                    <span className="w-7 text-right text-[10px] tabular-nums font-semibold">{goals}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-16 text-[10px] text-neutral-400">xG</span>
                    <div className="h-2.5 flex-1 rounded bg-neutral-100">
                      <div className="h-full rounded bg-neutral-400" style={{ width: `${(xg / max) * 100}%` }} />
                    </div>
                    <span className="w-7 text-right text-[10px] tabular-nums font-semibold">{xg}</span>
                  </div>
                </div>
              </div>
            );
          })}

          {/* análise textual: Gemini se hai, se non as etiquetas por umbrais */}
          <div className="mt-3 rounded-md bg-neutral-50 p-3 text-xs leading-relaxed text-neutral-700">
            {d.xg.analysis
              ? d.xg.analysis
              : (d.xg.insights || []).map((s, i) => <p key={i} className={i > 0 ? "mt-1.5" : ""}>{s}</p>)}
          </div>
        </section>
      )}
    </div>
  );
}


/* ============================================================= ANÁLISE ==== */
function Analysis({ t, onTeamClick }) {
  const [tab, setTab] = useState("merited");
  const tabs = [["merited", t.anMerited], ["projection", t.anProjection], ["objectives", t.anObjectives], ["compare", t.anCompare]];
  return (
    <div>
      <SectionHead title={t.nav.analysis} sub={t.season} />
      <div className="mb-4 inline-flex flex-wrap gap-1 rounded-lg border border-neutral-200 bg-white p-1">
        {tabs.map(([k, label]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${tab === k ? "text-white" : "text-neutral-600 hover:text-neutral-900"}`}
            style={tab === k ? { backgroundColor: RED } : undefined}>{label}</button>
        ))}
      </div>
      {tab === "merited" && <MeritedTable t={t} onTeamClick={onTeamClick} />}
      {tab === "projection" && <Projection t={t} onTeamClick={onTeamClick} />}
      {tab === "objectives" && <Objectives t={t} />}
      {tab === "compare" && <Compare t={t} />}
    </div>
  );
}

const anMeta = (team, slug) => {
  const k = NAME_TO_KEY[team] || slug;
  return T[k] ? { ...T[k], k } : { n: team, c: "#888", s: (team || "?").slice(0, 3).toUpperCase(), k: slug };
};

/* Idea 4 — Táboa merecida */
function MeritedTable({ t, onTeamClick }) {
  const [rows, setRows] = useState(null);
  useEffect(() => { let a = true; (async () => { try { const r = await api.merited(); if (a) setRows(r); } catch { if (a) setRows([]); } })(); return () => { a = false; }; }, []);
  if (!rows) return <Loading text={t.loading} />;
  return (
    <div>
      <p className="mb-3 text-xs text-neutral-500">{t.anMeritedSub}</p>
      <div className="scroll-x rounded-lg border border-neutral-200 bg-white">
        <table className="w-full min-w-[420px] text-sm">
          <thead className="bg-neutral-100 text-xs uppercase text-neutral-500">
            <tr><th className="px-2 py-2.5">{t.anMeritedPos}</th><th className="px-3 py-2.5 text-left">{t.team}</th><th className="px-2 py-2.5">oPts</th><th className="px-2 py-2.5">{t.pts}</th><th className="px-2 py-2.5">{t.anRealPos}</th><th className="px-2 py-2.5">Δ</th></tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const m = anMeta(r.team, r.slug);
              return (
                <tr key={r.slug} onClick={() => onTeamClick && onTeamClick(m.k)} className="tap cursor-pointer border-t border-neutral-100 hover:bg-neutral-50" style={m.udo ? { backgroundColor: "#fdecec" } : undefined}>
                  <td className="px-2 py-2 text-center font-bold tabular-nums">{r.meritedPos}</td>
                  <td className="px-3 py-2"><div className="flex items-center gap-2"><Crest team={m} size={18} /><span className={m.udo ? "font-bold" : ""} style={m.udo ? { color: RED } : undefined}>{m.n}</span></div></td>
                  <td className="px-2 py-2 text-center font-bold tabular-nums">{r.oPts}</td>
                  <td className="px-2 py-2 text-center tabular-nums text-neutral-500">{r.pts}</td>
                  <td className="px-2 py-2 text-center tabular-nums text-neutral-400">{r.realPos}º</td>
                  <td className="px-2 py-2 text-center font-medium tabular-nums" style={{ color: r.delta > 0 ? "#1a8a4a" : r.delta < 0 ? "#c0392b" : "#9a9a9a" }}>{r.delta > 0 ? `+${r.delta}` : r.delta}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* Idea 10 — Proxección (posición media + rango) */
function Projection({ t, onTeamClick }) {
  const [rows, setRows] = useState(null);
  useEffect(() => { let a = true; (async () => { try { const r = await api.probs(); if (a) setRows([...r].sort((x, y) => x.avgPos - y.avgPos)); } catch { if (a) setRows([]); } })(); return () => { a = false; }; }, []);
  if (!rows) return <Loading text={t.loading} />;
  return (
    <div>
      <p className="mb-3 text-xs text-neutral-500">{t.anProjSub}</p>
      <div className="space-y-1.5">
        {rows.map((r) => {
          const m = anMeta(r.team, r.slug);
          const lo = Math.min(r.posBest, r.posWorst), hi = Math.max(r.posBest, r.posWorst);
          const leftPct = ((lo - 1) / 19) * 100, widthPct = ((hi - lo) / 19) * 100;
          const avgPct = ((r.avgPos - 1) / 19) * 100;
          return (
            <div key={r.slug} onClick={() => onTeamClick && onTeamClick(m.k)} className="tap grid cursor-pointer grid-cols-[130px_1fr_54px] items-center gap-2 rounded px-2 py-1 hover:bg-neutral-50" style={m.udo ? { backgroundColor: "#fdecec" } : undefined}>
              <div className="flex items-center gap-2"><Crest team={m} size={18} /><span className={`truncate text-xs ${m.udo ? "font-bold" : "text-neutral-700"}`} style={m.udo ? { color: RED } : undefined}>{m.n}</span></div>
              <div className="relative h-5">
                <div className="absolute top-1/2 h-2 -translate-y-1/2 rounded-full" style={{ left: `${leftPct}%`, width: `${Math.max(2, widthPct)}%`, backgroundColor: m.udo ? "#f4b8b8" : "#d4d4d4" }} />
                <div className="absolute top-1/2 h-4 w-1 -translate-y-1/2 rounded" style={{ left: `${avgPct}%`, backgroundColor: m.udo ? RED : "#555" }} />
              </div>
              <span className="text-right text-xs tabular-nums text-neutral-500">{lo}º-{hi}º</span>
            </div>
          );
        })}
      </div>
      <div className="mt-2 text-[10px] text-neutral-400">{t.anRange} P10-P90 · {t.anAvgPos} = liña</div>
    </div>
  );
}

/* Idea 12 — Que precisa a UDO */
function Objectives({ t }) {
  const [d, setD] = useState(null);
  useEffect(() => { let a = true; (async () => { try { const r = await api.objectives("UD Ourense"); if (a) setD(r); } catch { if (a) setD({ err: true }); } })(); return () => { a = false; }; }, []);
  if (!d) return <Loading text={t.loading} />;
  if (d.err) return <div className="rounded-lg border border-neutral-200 bg-white p-8 text-center text-neutral-400">—</div>;
  const goals = [[t.anChampion, d.champion, "#1a8a4a"], [t.anPlayoffG, d.playoff, "#e0a500"], [t.anSafety, d.safety, "#2f6fd0"]];
  return (
    <div>
      <p className="mb-3 text-xs text-neutral-500">{t.anObjSub}</p>
      <div className="mb-3 rounded-lg border border-neutral-200 bg-white p-3 text-sm">
        <span className="font-bold" style={{ color: RED }}>UD Ourense</span> · {d.current_pts} {t.anPts} · {d.remaining} partidos por xogar
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {goals.map(([label, g, col]) => (
          <div key={label} className="rounded-lg border border-neutral-200 bg-white p-4 text-center">
            <div className="text-xs font-bold uppercase tracking-wide" style={{ color: col }}>{label}</div>
            <div className="mt-2 text-3xl font-black tabular-nums">{g.need}</div>
            <div className="text-[10px] uppercase text-neutral-400">{t.anNeed} ({t.anThreshold} ~{g.threshold})</div>
          </div>
        ))}
      </div>

      {/* Estatísticas do modelo + gráfica de probabilidades */}
      {d.model && (
        <div className="mt-5 rounded-lg border border-neutral-200 bg-white p-4">
          <div className="mb-1 text-xs font-bold uppercase tracking-wide text-neutral-500">
            {t.anModelTitle || "Segundo o modelo"}
          </div>
          <p className="mb-3 text-xs text-neutral-400">
            {t.anModelSub || "Probabilidade de cada obxectivo e posición proxectada a final de tempada."}
          </p>

          {/* posición proxectada */}
          <div className="mb-4 flex items-baseline gap-2">
            <span className="text-3xl font-black tabular-nums">{d.model.proj_pos}º</span>
            <span className="text-xs text-neutral-400">
              {t.anProjPos || "posición media"} · {t.anRange || "rango"} {d.model.pos_best}º–{d.model.pos_worst}º
            </span>
          </div>

          {/* gráfica de barras de probabilidades */}
          <div className="space-y-2.5">
            {[
              [t.anChampion, d.model.p_champion, "#1a8a4a"],
              [t.anPlayoffG, d.model.p_playoff, "#e0a500"],
              [t.anSafety, d.model.p_safety, "#2f6fd0"],
            ].map(([label, pct, col]) => (
              <div key={label}>
                <div className="mb-0.5 flex justify-between text-[11px]">
                  <span className="font-semibold uppercase text-neutral-500">{label}</span>
                  <span className="font-black tabular-nums" style={{ color: col }}>{pct}%</span>
                </div>
                <div className="h-2.5 overflow-hidden rounded-full bg-neutral-100">
                  <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: col }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* Idea 14 — Comparador de dous equipos */
function Compare({ t }) {
  const teams = Object.entries(T).map(([k, v]) => ({ k, n: v.n })).sort((a, b) => a.n.localeCompare(b.n));
  const [s1, setS1] = useState("ourense");
  const [s2, setS2] = useState("ponferradina");
  const [d1, setD1] = useState(null);
  const [d2, setD2] = useState(null);
  useEffect(() => { let a = true; (async () => { try { const x = await api.teamProfile(s1); if (a) setD1(x); } catch { if (a) setD1(null); } })(); return () => { a = false; }; }, [s1]);
  useEffect(() => { let a = true; (async () => { try { const x = await api.teamProfile(s2); if (a) setD2(x); } catch { if (a) setD2(null); } })(); return () => { a = false; }; }, [s2]);

  const sel = (val, setter, exclude) => (
    <select value={val} onChange={(e) => setter(e.target.value)} className="w-full rounded-md border border-neutral-200 bg-white px-2 py-1.5 text-sm">
      {teams.filter((tm) => tm.k !== exclude).map((tm) => <option key={tm.k} value={tm.k}>{tm.n}</option>)}
    </select>
  );
  const rowM = (label, a, b, aBetter) => (
    <div className="grid grid-cols-3 items-center border-t border-neutral-100 py-1.5 text-sm">
      <span className="text-left font-bold tabular-nums" style={aBetter ? { color: RED } : undefined}>{a}</span>
      <span className="text-center text-[10px] uppercase text-neutral-400">{label}</span>
      <span className="text-right font-bold tabular-nums" style={!aBetter ? { color: RED } : undefined}>{b}</span>
    </div>
  );
  return (
    <div>
      <p className="mb-3 text-xs text-neutral-500">{t.anCompareSub}</p>
      <div className="mb-3 grid grid-cols-2 gap-3">{sel(s1, setS1, s2)}{sel(s2, setS2, s1)}</div>
      {(!d1 || !d2) ? <Loading text={t.loading} /> : (
        <div className="rounded-lg border border-neutral-200 bg-white p-4">
          <div className="mb-2 grid grid-cols-3 items-center">
            <div className="flex justify-start"><Crest team={anMeta(d1.team, d1.slug)} size={40} /></div>
            <span className="text-center text-[10px] uppercase text-neutral-400">vs</span>
            <div className="flex justify-end"><Crest team={anMeta(d2.team, d2.slug)} size={40} /></div>
          </div>
          {rowM(t.pos, `${d1.pos}º`, `${d2.pos}º`, d1.pos < d2.pos)}
          {rowM(t.pts, d1.pts, d2.pts, d1.pts > d2.pts)}
          {rowM("oPts", d1.oPts, d2.oPts, d1.oPts > d2.oPts)}
          {rowM("GF", d1.gf, d2.gf, d1.gf > d2.gf)}
          {rowM("GC", d1.ga, d2.ga, d1.ga < d2.ga)}
          {rowM(t.gd, d1.gd, d2.gd, d1.gd > d2.gd)}
        </div>
      )}
    </div>
  );
}

/* =========================================================== DASHBOARD ==== */
function Dashboard({ t, onTeamClick }) {
  const [view, setView] = useState("table");
  const [rows, setRows] = useState(null);   // null = cargando; [] = erro/baleiro
  const [err, setErr] = useState(false);
  const [resume, setResume] = useState(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const rs = await api.resume();
        if (alive && Array.isArray(rs)) setResume(rs);
      } catch { /* sen currículum: a vista amosará aviso */ }
    })();
    return () => { alive = false; };
  }, []);

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
        const probBySlug = Object.fromEntries((pr || []).map((p) => [p.slug, p]));
        const adapted = adaptStandings(st).map((r) => {
          const p = probBySlug[r.k] || {};
          return { ...r, pC: p.pChamp ?? 0, pP: p.pPO ?? 0, pR: p.pRel ?? 0 };
        });
        adapted.sort((a, b) => b.pts - a.pts || b.gd - a.gd || b.gf - a.gf);
        setRows(adapted);
      } catch {
        // backend durmido/caído: amosamos aviso de recarga, NON datos falsos
        if (alive) { setRows([]); setErr(true); }
      }
    })();
    return () => { alive = false; };
  }, []);

  // Ordenación por columna. Por defecto: clasificación real (pts, gd, gf).
  // NOTA: o desempate oficial (enfrontamento directo, etc.) implementarase no
  // backend máis adiante; aquí ordénase polos campos dispoñibles.
  const [sort, setSort] = useState({ col: "default", dir: "desc" });

  const sorted = useMemo(() => {
    if (!rows) return [];
    const arr = [...rows];
    if (sort.col === "default") {
      return arr.sort((a, b) => b.pts - a.pts || b.gd - a.gd || b.gf - a.gf);
    }
    const val = (r) => ({
      pld: r.pld, gf: r.gf, ga: r.ga, gd: r.gd, pts: r.pts,
      opts: r.opts, diff: r.opts - r.pts,
    }[sort.col]);
    const s = sort.dir === "desc" ? -1 : 1;
    return arr.sort((a, b) => (val(a) - val(b)) * s || b.pts - a.pts);
  }, [rows, sort]);

  const toggleSort = (col) =>
    setSort((p) => p.col === col
      ? (p.dir === "desc" ? { col, dir: "asc" } : { col: "default", dir: "desc" })
      : { col, dir: "desc" });

  const zoneOf = (i) => (i === 0 ? "promo" : i <= 4 ? "po" : i >= 15 ? "rel" : null);
  const showZones = sort.col === "default";

  return (
    <div>
      <SectionHead title={t.nav.dashboard} sub={t.season} />
      <div className="mb-4 inline-flex rounded-lg border border-neutral-200 bg-white p-1">
        {[["table", t.vTable], ["probs", t.vProbs], ["resume", t.vResume]].map(([k, label]) => (
          <button key={k} onClick={() => setView(k)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${view === k ? "bg-neutral-900 text-white" : "text-neutral-600 hover:text-neutral-900"}`}>
            {label}
          </button>
        ))}
      </div>

      {rows === null ? (
        <Loading text={t.loading} />
      ) : err ? (
        <div className="rounded-lg border border-neutral-200 bg-white p-8 text-center text-sm text-neutral-400">{t.loadErr}</div>
      ) : view === "table" ? (
        <div className="scroll-x rounded-lg border border-neutral-200 bg-white">
          <table className="w-full min-w-[720px] border-collapse text-sm">
            <thead className="bg-neutral-100 text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th className="px-2 py-2.5 text-center font-semibold">#</th>
                <th className="px-3 py-2.5 text-left font-semibold">{t.team}</th>
                <SortTh col="pld" label={t.pld} sort={sort} onClick={toggleSort} />
                <SortTh col="gf" label={t.gf} sort={sort} onClick={toggleSort} />
                <SortTh col="ga" label={t.ga} sort={sort} onClick={toggleSort} />
                <SortTh col="gd" label={t.gd} sort={sort} onClick={toggleSort} />
                <SortTh col="pts" label={t.pts} sort={sort} onClick={toggleSort} bold />
                <SortTh col="opts" label={t.oPts} sort={sort} onClick={toggleSort} />
                <SortTh col="diff" label={t.diff} sort={sort} onClick={toggleSort} title="oPts - Pts" />
                <th className="px-3 py-2.5 text-center font-semibold">{t.form}</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((r, i) => {
                const z = showZones ? zoneOf(i) : null;
                const delta = +(r.opts - r.pts).toFixed(1);
                return (
                  <tr key={r.k} onClick={() => onTeamClick && onTeamClick(r.k)} className={`tap cursor-pointer border-t border-neutral-100 ${r.udo ? "" : "hover:bg-neutral-50"}`} style={r.udo ? { backgroundColor: "#fdecec" } : undefined}>
                    <td className="relative px-2 py-2 text-center tabular-nums text-neutral-500">
                      {z && <span className="absolute left-0 top-0 h-full w-1.5" style={{ backgroundColor: ZONE[z].bar }} />}
                      {i + 1}
                    </td>
                    <td className="px-3 py-2"><div className="flex items-center gap-2.5"><Crest team={r} /><span className={r.udo ? "font-bold" : "font-medium"} style={r.udo ? { color: RED } : undefined}>{r.n}</span></div></td>
                    <td className="px-2 py-2 text-center tabular-nums text-neutral-600">{r.pld}</td>
                    <td className="px-2 py-2 text-center tabular-nums text-neutral-600">{r.gf}</td>
                    <td className="px-2 py-2 text-center tabular-nums text-neutral-600">{r.ga}</td>
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
      ) : view === "probs" ? (
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
      ) : (
        <ResumeView t={t} resume={resume} />
      )}

      <Legend t={t} />
    </div>
  );
}

/* Vista Currículum: ranking polo valor real dos puntos. */
function ResumeView({ t, resume }) {
  if (!resume) {
    return <div className="rounded-lg border border-neutral-200 bg-white p-8 text-center text-sm text-neutral-400">···</div>;
  }
  const maxRes = Math.max(...resume.map((r) => r.resume), 1);
  const meta = (r) => {
    const k = NAME_TO_KEY[r.team] || r.slug;
    return T[k] ? { ...T[k], k } : { n: r.team, c: "#888", s: (r.team || "?").slice(0, 3).toUpperCase(), k: r.slug };
  };
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4">
      <div className="mb-1 text-sm font-bold">{t.resumeTitle}</div>
      <p className="mb-3 text-xs text-neutral-500">{t.resumeSub}</p>
      <div className="space-y-1.5">
        {resume.map((r, i) => {
          const m = meta(r);
          return (
            <div key={r.slug || i} className="grid grid-cols-[20px_140px_1fr_auto] items-center gap-2 rounded px-2 py-1" style={m.udo ? { backgroundColor: "#fdecec" } : undefined}>
              <span className="text-center text-xs tabular-nums text-neutral-400">{i + 1}</span>
              <div className="flex items-center gap-2">
                <Crest team={m} size={18} />
                <span className={`truncate text-xs ${m.udo ? "font-bold" : "text-neutral-700"}`} style={m.udo ? { color: RED } : undefined}>{m.n}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-2.5 flex-1 overflow-hidden rounded bg-neutral-200">
                  <div className="h-full rounded" style={{ width: `${(r.resume / maxRes) * 100}%`, backgroundColor: m.udo ? RED : "#2f6fd0" }} />
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs tabular-nums">
                <span className="font-bold">{r.resume}</span>
                <span className="text-neutral-400">({r.pts})</span>
                <span className="w-9 text-right font-medium" style={{ color: r.diff > 0.3 ? "#1a8a4a" : r.diff < -0.3 ? "#c0392b" : "#9a9a9a" }}>
                  {r.diff > 0 ? `+${r.diff}` : r.diff}
                </span>
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-3 text-[10px] text-neutral-400">
        {t.resumeCol} · (puntos reais) · Δ
      </div>
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

/* ============================================================= XORNADA ==== */
function Matchday({ t }) {
  const [jornada, setJornada] = useState(null);
  const [matches, setMatches] = useState(null); // null = cargando

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const md = await api.matchday();
        if (!alive) return;
        setJornada(md?.jornada ?? null);
        setMatches(md?.matches || []);
      } catch { if (alive) setMatches([]); }
    })();
    return () => { alive = false; };
  }, []);

  const meta = (name, slug) => {
    const k = NAME_TO_KEY[name] || slug;
    return T[k] ? { ...T[k], k } : { n: name, c: "#888", s: (name || "?").slice(0, 3).toUpperCase(), k: slug };
  };

  return (
    <div>
      <SectionHead title={t.mdTitle} sub={jornada ? `${t.jornada} ${jornada} · ${t.mdSub}` : t.mdSub} />
      {matches === null ? (
        <div className="rounded-lg border border-neutral-200 bg-white p-8 text-center text-sm text-neutral-400">···</div>
      ) : matches.length === 0 ? (
        <div className="rounded-lg border border-neutral-200 bg-white p-8 text-center text-sm text-neutral-400">{t.mdNoData}</div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {matches.map((m, i) => {
            const home = meta(m.home, m.home_slug), away = meta(m.away, m.away_slug);
            const ls = m.likely_score || [0, 0];
            return (
              <div key={i} className="overflow-hidden rounded-xl border border-neutral-200 bg-white">
                {/* emparejamento + marcador esperado */}
                <div className="flex items-center justify-between gap-2 px-4 pt-4">
                  <div className="flex min-w-0 flex-1 flex-col items-center gap-1.5">
                    <Crest team={home} size={38} />
                    <span className={`text-center text-xs leading-tight ${home.udo ? "font-bold" : "text-neutral-700"}`} style={home.udo ? { color: RED } : undefined}>{home.n}</span>
                  </div>
                  <div className="flex flex-col items-center px-2">
                    <div className="text-2xl font-black tabular-nums">{ls[0]}<span className="mx-1 text-neutral-300">-</span>{ls[1]}</div>
                    <div className="text-[9px] uppercase tracking-wide text-neutral-400">{t.mdOGoals}</div>
                    {m.likely_1x2 && (
                      <div className="mt-1 rounded-full px-2 py-0.5 text-[10px] font-black text-white"
                        style={{ backgroundColor: m.likely_1x2 === "1" ? "#1a8a4a" : m.likely_1x2 === "2" ? "#c0392b" : "#e0a500" }}>
                        {m.likely_1x2 === "1" ? `1 ${home.s}` : m.likely_1x2 === "2" ? `2 ${away.s}` : t.mdDraw}
                      </div>
                    )}
                  </div>
                  <div className="flex min-w-0 flex-1 flex-col items-center gap-1.5">
                    <Crest team={away} size={38} />
                    <span className={`text-center text-xs leading-tight ${away.udo ? "font-bold" : "text-neutral-700"}`} style={away.udo ? { color: RED } : undefined}>{away.n}</span>
                  </div>
                </div>
                {/* barra de probabilidades 1-X-2 */}
                <div className="mt-3 px-4 pb-4">
                  <div className="flex h-6 overflow-hidden rounded text-[10px] font-bold text-white">
                    <div className="grid place-items-center" style={{ width: `${m.p_home}%`, backgroundColor: "#1a8a4a" }} title={`1: ${m.p_home}%`}>{m.p_home >= 12 ? `${m.p_home}%` : ""}</div>
                    <div className="grid place-items-center" style={{ width: `${m.p_draw}%`, backgroundColor: "#e0a500" }} title={`X: ${m.p_draw}%`}>{m.p_draw >= 12 ? `${m.p_draw}%` : ""}</div>
                    <div className="grid place-items-center" style={{ width: `${m.p_away}%`, backgroundColor: "#c0392b" }} title={`2: ${m.p_away}%`}>{m.p_away >= 12 ? `${m.p_away}%` : ""}</div>
                  </div>
                  <div className="mt-1 flex justify-between text-[9px] uppercase text-neutral-400">
                    <span>1 {home.s}</span><span>X</span><span>2 {away.s}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* =========================================================== SIMULADOR ==== */
function Simulator({ t }) {
  const [results, setResults] = useState({});   // clave "jornada:idx" → "1"|"X"|"2"
  const [days, setDays] = useState(null);        // [{jornada, fixtures:[[h,a],...]}]
  const [activeDay, setActiveDay] = useState(0);
  const [base, setBase] = useState(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [mds, st] = await Promise.all([
          api.matchdays(3),
          api.standings(),
        ]);
        if (!alive) return;
        const b = {};
        adaptStandings(st).forEach((r) => { b[r.k] = { ...r }; });
        setBase(b);
        const ds = (mds?.jornadas || []).map((jd) => ({
          jornada: jd.jornada,
          fixtures: jd.matches.map((m) => [NAME_TO_KEY[m.home] || m.home_slug, NAME_TO_KEY[m.away] || m.away_slug]),
        }));
        setDays(ds);
      } catch {
        if (alive) { setErr(true); setDays([]); setBase({}); }
      }
    })();
    return () => { alive = false; };
  }, []);

  const baseOrder = useMemo(
    () => base ? Object.values(base).sort((a, b) => b.pts - a.pts || b.gd - a.gd).map((r) => r.k) : [],
    [base]
  );

  // tabla proxectada: aplica TODOS os resultados fixados das 3 xornadas (encadeado)
  const projected = useMemo(() => {
    if (!base || !days) return [];
    const map = Object.fromEntries(Object.entries(base).map(([k, v]) => [k, { ...v }]));
    days.forEach((day) => {
      day.fixtures.forEach(([h, a], i) => {
        const res = results[`${day.jornada}:${i}`];
        if (!res || !map[h] || !map[a]) return;
        if (res === "1") { map[h].pts += 3; map[h].gd += 1; map[a].gd -= 1; }
        else if (res === "2") { map[a].pts += 3; map[a].gd -= 1; map[h].gd += 1; }
        else { map[h].pts += 1; map[a].pts += 1; }
      });
    });
    return Object.values(map).sort((x, y) => y.pts - x.pts || y.gd - x.gd);
  }, [results, base, days]);

  const zoneOf = (i) => (i === 0 ? "promo" : i <= 4 ? "po" : i >= 15 ? "rel" : null);
  const fixedCount = Object.keys(results).filter((k) => results[k]).length;

  if (days === null || base === null) {
    return <div><SectionHead title={t.simTitle} sub={t.simSub} /><Loading text={t.loading} /></div>;
  }
  if (err || days.length === 0) {
    return <div><SectionHead title={t.simTitle} sub={t.simSub} /><div className="rounded-lg border border-neutral-200 bg-white p-8 text-center text-sm text-neutral-400">{err ? t.loadErr : t.mdNoData}</div></div>;
  }

  const day = days[activeDay] || days[0];
  const fixtures = day.fixtures;

  return (
    <div>
      <SectionHead title={t.simTitle} sub={t.simSub} action={fixedCount > 0 && (
        <button onClick={() => setResults({})} className="rounded px-3 py-1 text-xs font-semibold text-neutral-500 hover:bg-neutral-200">↺ {t.reset}</button>
      )} />

      {/* pestanas de xornadas */}
      <div className="mb-4 inline-flex gap-1 rounded-lg border border-neutral-200 bg-white p-1">
        {days.map((d, i) => {
          const fixedInDay = d.fixtures.filter((_, idx) => results[`${d.jornada}:${idx}`]).length;
          return (
            <button key={d.jornada} onClick={() => setActiveDay(i)}
              className={`tap rounded-md px-3 py-1.5 text-sm font-medium transition ${activeDay === i ? "text-white" : "text-neutral-600 hover:bg-neutral-100"}`}
              style={activeDay === i ? { backgroundColor: RED } : undefined}>
              {t.jornada} {d.jornada}{fixedInDay > 0 ? ` ·${fixedInDay}` : ""}
            </button>
          );
        })}
      </div>

      <section className="mb-5 rounded-lg border border-neutral-200 bg-white p-4">
        <div className="grid gap-2 sm:grid-cols-2">
          {fixtures.map(([h, a], i) => {
            const th = T[h] ? { ...T[h], k: h } : { n: h, c: "#888", s: "?", k: h };
            const ta = T[a] ? { ...T[a], k: a } : { n: a, c: "#888", s: "?", k: a };
            const rkey = `${day.jornada}:${i}`;
            return (
            <div key={i} className="flex items-center justify-between gap-1.5 rounded-md border border-neutral-100 px-2 py-2">
              <div className="flex min-w-0 flex-1 items-center justify-end gap-1">
                <span className={`truncate text-[11px] sm:text-xs ${th.udo ? "font-bold" : "text-neutral-700"}`} style={th.udo ? { color: RED } : undefined}>{th.n}</span>
                <Crest team={th} size={22} />
              </div>
              <div className="flex shrink-0 gap-0.5">
                {["1", "X", "2"].map((v) => (
                  <button key={v} onClick={() => setResults((p) => ({ ...p, [rkey]: p[rkey] === v ? undefined : v }))}
                    className={`tap h-7 w-7 rounded text-xs font-bold transition ${results[rkey] === v ? "text-white" : "bg-neutral-100 text-neutral-500 hover:bg-neutral-200"}`}
                    style={results[rkey] === v ? { backgroundColor: RED } : undefined}>{v}</button>
                ))}
              </div>
              <div className="flex min-w-0 flex-1 items-center gap-1">
                <Crest team={ta} size={22} />
                <span className={`truncate text-[11px] sm:text-xs ${ta.udo ? "font-bold" : "text-neutral-700"}`} style={ta.udo ? { color: RED } : undefined}>{ta.n}</span>
              </div>
            </div>
          ); })}
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

/* Fallback do Centro de Mando (mentres non hai datos reais / liga sen empezar). */
const MOCK_HUB = {
  usPos: "-", themPos: "-",
  us: { pts: 0, gf: 0, ga: 0, form: [] },
  them: { pts: 0, gf: 0, ga: 0, form: [] },
};

/* ======================================================= CENTRO DE MANDO == */
function CommandCenter({ t }) {
  // Estado inicial = mock (fallback mentres non cargue ou se a liga non empezou).
  const [data, setData] = useState(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [nx, vs, ev] = await Promise.all([
          api.nextMatch("UD Ourense").catch(() => null),
          api.headToHead("ourense").catch(() => null),
          api.evolution("ourense").catch(() => null),
        ]);
        if (!alive) return;
        setData({ next: nx?.next || null, vs, evo: ev?.evolution || [] });
      } catch { /* queda o mock */ }
    })();
    return () => { alive = false; };
  }, []);

  // ---- valores: reais se hai datos, mock se non ----
  const vs = data?.vs;
  const nx = data?.next;
  const usName = "UD Ourense";
  const themName = vs?.them?.team || nx?.away && nx.home === usName ? nx?.away : (vs?.them?.team || "CD Mirandés");

  // metadatos de escudo/cor por nome
  const teamMeta = (name) => {
    const k = NAME_TO_KEY[name];
    return T[k] ? { ...T[k], k } : { n: name, c: "#888", s: (name || "?").slice(0, 3).toUpperCase(), k: "" };
  };
  const us = teamMeta(usName);
  const them = teamMeta(vs?.them?.team || "CD Mirandés");

  const usPos = vs?.us?.pos ?? MOCK_HUB.usPos;
  const themPos = vs?.them?.pos ?? MOCK_HUB.themPos;
  const usStats = vs?.us || MOCK_HUB.us;
  const themStats = vs?.them || MOCK_HUB.them;

  // próximo partido: quen é local?
  const udoIsHome = nx ? nx.home === usName : false;
  const exp = nx?.expected;
  // 1-X-2 desde a óptica da UDO
  const win = exp ? Math.round((udoIsHome ? exp.home_win : exp.away_win) * 100) : 28;
  const draw = exp ? Math.round(exp.draw * 100) : 23;
  const loss = exp ? Math.round((udoIsHome ? exp.away_win : exp.home_win) * 100) : 49;
  const ogHome = exp?.oGoals_home ?? (udoIsHome ? 1.94 : 2.81);
  const ogAway = exp?.oGoals_away ?? (udoIsHome ? 2.81 : 1.94);
  // marcador esperado en orde LOCAL-VISITANTE (coherente cos escudos)
  const likely = exp?.likely_score || [1, 1];

  // evolución: SÓ datos reais. Se a liga aínda non empezou, queda baleiro e
  // amosaremos un aviso en vez de datos inventados.
  const evo = (data?.evo && data.evo.length)
    ? data.evo.map((e) => [e.jornada, e.pts, e.oPts])
    : [];
  const gap = evo.length ? evo[evo.length-1][2] - evo[evo.length-1][1] : 0;
  const hasEvo = evo.length > 0;

  const next = { win, draw, loss, likely };

  if (data === null) {
    return <div><SectionHead title="UD Ourense" sub={t.nav.hub} accent /><Loading text={t.loading} /></div>;
  }

  return (
    <div>
      <SectionHead title="UD Ourense" sub={t.nav.hub} accent />
      {nx && (
        <a href={api.reportUrl()} target="_blank" rel="noopener noreferrer"
          className="tap mb-4 flex items-center justify-center gap-2 rounded-lg py-3 text-sm font-bold text-white"
          style={{ backgroundColor: RED }}>
          {t.reportBtn || "↓ Descargar informe do próximo partido (PDF)"}
        </a>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        {/* próximo partido */}
        <section className="rounded-lg border border-neutral-200 bg-white p-4">
          <h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-neutral-500">{t.hubNext}</h3>
          <div className="mb-3 flex items-center justify-center gap-3">
            {(() => {
              // local á esquerda, visitante á dereita
              const homeTeam = udoIsHome ? us : them;
              const awayTeam = udoIsHome ? them : us;
              const cell = (tm) => (
                <div className="flex flex-col items-center gap-1">
                  <Crest team={tm} size={40} />
                  <span className={`text-xs ${tm.udo ? "font-bold" : "text-neutral-600"}`} style={tm.udo ? { color: RED } : undefined}>{tm.n}</span>
                </div>
              );
              return (<>{cell(homeTeam)}<span className="text-neutral-300">vs</span>{cell(awayTeam)}</>);
            })()}
          </div>
          <div className="mb-1 flex h-7 overflow-hidden rounded">
            <div className="grid place-items-center text-[10px] font-bold text-white" style={{ width: `${next.win}%`, backgroundColor: "#1a8a4a" }}>{next.win}%</div>
            <div className="grid place-items-center text-[10px] font-bold text-white" style={{ width: `${next.draw}%`, backgroundColor: "#9a9a9a" }}>{next.draw}%</div>
            <div className="grid place-items-center text-[10px] font-bold text-white" style={{ width: `${next.loss}%`, backgroundColor: "#c0392b" }}>{next.loss}%</div>
          </div>
          <div className="mb-3 flex justify-between text-[10px] text-neutral-500"><span>{t.win}</span><span>{t.draw}</span><span>{t.loss}</span></div>
          <div className="grid grid-cols-2 gap-2 text-center">
            <div className="rounded bg-neutral-50 p-2"><div className="text-[10px] text-neutral-500">{t.likely}</div><div className="text-xl font-black tabular-nums">{next.likely[0]}-{next.likely[1]}</div></div>
            <div className="rounded bg-neutral-50 p-2">
              <div className="text-[10px] text-neutral-500">oGoals</div>
              <div className="flex items-center justify-center gap-2">
                <div className="flex flex-col items-center">
                  <span className="text-xl font-black tabular-nums">{ogHome}</span>
                  <span className="text-[9px] uppercase text-neutral-400">{(udoIsHome ? us : them).s}</span>
                </div>
                <span className="text-neutral-300">·</span>
                <div className="flex flex-col items-center">
                  <span className="text-xl font-black tabular-nums">{ogAway}</span>
                  <span className="text-[9px] uppercase text-neutral-400">{(udoIsHome ? them : us).s}</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* cara a cara */}
        <section className="rounded-lg border border-neutral-200 bg-white p-4">
          <h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-neutral-500">{t.h2h}</h3>
          <div className="mb-2 grid grid-cols-3 items-center"><div className="flex justify-start"><Crest team={us} size={28} /></div><span /><div className="flex justify-end"><Crest team={them} size={28} /></div></div>
          {[[t.pos, `${usPos}º`, `${themPos}º`, usPos < themPos],[t.pts, usStats.pts, themStats.pts, usStats.pts > themStats.pts],["GF", usStats.gf, themStats.gf, usStats.gf > themStats.gf],["GC", usStats.ga, themStats.ga, usStats.ga < themStats.ga]].map(([label, a, b, better]) => (
            <div key={label} className="grid grid-cols-3 items-center py-1 text-sm">
              <span className="text-left font-bold tabular-nums" style={better ? { color: RED } : { color: "#bbb" }}>{a}</span>
              <span className="text-center text-[10px] uppercase text-neutral-400">{label}</span>
              <span className={`text-right font-bold tabular-nums ${!better ? "" : "text-neutral-400"}`}>{b}</span>
            </div>
          ))}
          <div className="grid grid-cols-3 items-center pt-1"><div className="flex justify-start"><FormDots form={usStats.form || []} /></div><span className="text-center text-[10px] uppercase text-neutral-400">{t.hubForm}</span><div className="flex justify-end"><FormDots form={themStats.form || []} /></div></div>
        </section>
      </div>

      {/* rendimiento */}
      <section className="mt-4 rounded-lg border border-neutral-200 bg-white p-4">
        <h3 className="mb-1 text-xs font-bold uppercase tracking-wide text-neutral-500">{t.perf}</h3>
        <p className="mb-3 text-xs text-neutral-500">{t.perfSub}</p>
        {hasEvo ? (
          <>
            <div className="mb-3 inline-flex items-center gap-1.5 rounded-md px-3 py-1 text-sm font-bold" style={{ backgroundColor: gap > 0.5 ? "#fbecea" : "#e7f5ec", color: gap > 0.5 ? "#c0392b" : "#1a8a4a" }}>
              {gap > 0.5 ? "▼" : "▲"} {t.deserves} {Math.abs(gap).toFixed(1)} {gap > 0 ? t.morePts : t.lessPts}
            </div>
            <EvoChart evo={evo} t={t} />
          </>
        ) : (
          <div className="py-6 text-center text-sm text-neutral-400">{t.mdNoData}</div>
        )}
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
/* Ficha de xogador: modal cos datos agregados (goles, asist, /90, duelos...). */
function PlayerDetail({ t, name, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let alive = true;
    (async () => {
      try { const r = await api.playerDetail(name); if (alive) setData(r); }
      catch { if (alive) setData({ games: 0, stats: null }); }
      finally { if (alive) setLoading(false); }
    })();
    return () => { alive = false; };
  }, [name]);

  const s = data?.stats;
  const metrics = s ? [
    [t.pdGoals || "Goles", s.goals],
    [t.pdAssists || "Asistencias", s.assists],
    [t.pdGA || "G+A", s.ga],
    [t.pdGoals90 || "Goles/90", s.goals_per90],
    [t.pdAssists90 || "Asist./90", s.assists_per90],
    [t.pdGA90 || "G+A/90", s.ga_per90],
    [t.pdMinGoal || "Min/gol", s.min_per_goal ?? "—"],
    [t.pdMinutes || "Minutos", s.minutes],
    [t.pdPassPct || "% pases", s.pass_pct != null ? `${s.pass_pct}%` : "—"],
    [t.pdPassPg || "Pases/partido", s.passes_pg],
    [t.pdDuels || "% duelos gañ.", s.duels_won_pct != null ? `${s.duels_won_pct}%` : "—"],
    [t.pdDuelsPg || "Duelos gañ./part.", s.duels_won_pg],
    [t.pdTackles || "Entradas/part.", s.tackles_pg],
    [t.pdORavg || "oRating medio", s.orating_avg ?? "—"],
    [t.pdORbest || "Mellor oRating", s.orating_best ?? "—"],
  ] : [];

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4" onClick={onClose}>
      <div className="max-h-[85dvh] w-full max-w-md overflow-y-auto rounded-t-2xl bg-white p-5 sm:rounded-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-lg font-black">{name}</h3>
          <button onClick={onClose} className="tap text-neutral-400">✕</button>
        </div>
        {loading ? <Loading text={t.loading} /> : !s ? (
          <p className="py-8 text-center text-sm text-neutral-400">{t.pdNoData || "Aínda non hai estatísticas deste xogador."}</p>
        ) : (
          <>
            <div className="mb-3 flex items-center gap-3">
              <div className="grid h-14 w-14 place-items-center rounded-xl text-xl font-black text-white" style={{ backgroundColor: s.orating_avg >= 7 ? "#1a8a4a" : s.orating_avg < 5 ? "#c0392b" : "#c99700" }}>
                {s.orating_avg != null ? s.orating_avg.toFixed(1) : "–"}
              </div>
              <div className="text-xs text-neutral-500">
                <div><b>{s.games}</b> {t.pdGames || "partidos"}</div>
                <div>{s.minutes} {t.pdMin || "min"}</div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {metrics.map(([label, val]) => (
                <div key={label} className="rounded-lg bg-neutral-50 px-3 py-2">
                  <div className="text-[10px] uppercase text-neutral-400">{label}</div>
                  <div className="text-base font-bold tabular-nums">{val}</div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function Squad({ t }) {
  const [filter, setFilter] = useState("all");
  const [players, setPlayers] = useState(null);   // null = cargando (nada de mock)
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const sq = await api.squad();
        if (!alive) return;
        setPlayers(Array.isArray(sq) ? sq.map((p) => ({
          ...p,
          born: typeof p.born === "string" ? parseInt(p.born.slice(0, 4)) : p.born,
          oR: p.oRating ?? null,
        })) : []);
      } catch { if (alive) setPlayers([]); }
    })();
    return () => { alive = false; };
  }, []);

  const GROUP = { GK: "gk", POR: "gk", DEF: "df", DF: "df", LI: "df", LD: "df", MED: "mf", MC: "mf", MCO: "mf", DEL: "fw", EI: "fw", ED: "fw", DC: "fw" };
  const POS = { GK: "POR", POR: "POR", DEF: "DEF", DF: "DFC", LI: "LI", LD: "LD", MED: "MED", MC: "MC", MCO: "MCO", DEL: "DEL", EI: "EI", ED: "ED", DC: "DC" };
  const rc = (r) => (r == null ? "#c4c4c4" : r >= 7.0 ? "#1a8a4a" : r >= 6.3 ? "#c99700" : "#b06a3b");
  const fmtMV = (v) => (v == null ? "—" : `${Math.round(v / 1000)} mil €`);
  const list = players === null ? [] : (filter === "all" ? players : players.filter((p) => GROUP[p.pos] === filter));
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
      {players === null ? <Loading text={t.loading} /> : (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {list.map((p) => (
          <div key={p.name} onClick={() => setSelected(p.name)}
            className="tap relative cursor-pointer overflow-hidden rounded-xl border border-neutral-200 bg-white p-3 transition hover:shadow-md">
            <div className="absolute inset-x-0 top-0 h-1" style={{ backgroundColor: p.signing ? "#e0a500" : RED }} />
            <div className="mb-2 flex items-start justify-between">
              <div className="flex items-baseline gap-1.5">
                <span className="text-2xl font-black tabular-nums">{p.dorsal ?? "–"}</span>
                <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-[9px] font-bold uppercase text-neutral-500">{POS[p.pos] || p.pos}</span>
              </div>
              <span className="grid h-9 w-9 place-items-center rounded-lg text-sm font-black text-white" style={{ backgroundColor: rc(p.oR) }}>{p.oR != null ? p.oR.toFixed(1) : "–"}</span>
            </div>
            <h4 className="truncate text-sm font-bold leading-tight">{p.display || p.name}</h4>
            <div className="mt-0.5 text-xs text-neutral-500">
              {p.signing ? <span className="font-semibold text-amber-600">{t.signing || "Obxectivo"}</span> : <>{p.born ? `${2026 - p.born} ${t.years} · ` : ""}{p.nat}</>}
            </div>
            {p.note && <div className="mt-1.5 line-clamp-2 text-[11px] italic text-neutral-500">"{p.note}"</div>}
            {p.games > 0 && <div className="mt-2 border-t border-neutral-100 pt-1.5 text-xs"><span className="text-neutral-400">{t.games || "Partidos"}: </span><span className="font-semibold text-neutral-700">{p.games}</span></div>}
          </div>
        ))}
      </div>
      )}
      <p className="mt-4 text-xs text-neutral-400">{t.ratingHelp}</p>
      {selected && <PlayerDetail t={t} name={selected} onClose={() => setSelected(null)} />}
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
