// Cliente de la API. En Vercel, define VITE_API_URL con la URL del backend.
// Quitamos calquera barra final para evitar dobre barra (//api/...) que rompe as peticións.
const RAW_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const BASE = RAW_BASE.replace(/\/+$/, "");

async function get(path, params) {
  const url = new URL(BASE + path);
  if (params) Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  const r = await fetch(url);
  if (!r.ok) throw new Error(`API ${path}: ${r.status}`);
  return r.json();
}

export const api = {
  teams: () => get("/api/teams"),
  standings: () => get("/api/standings"),
  probs: (n_sims) => get("/api/probs", n_sims ? { n_sims } : undefined),
  nextMatch: (team, blend) => get("/api/match/next", { team, ...(blend != null && { blend }) }),
  simulate: async (fixtures, n_sims = 4000) => {
    const r = await fetch(BASE + "/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fixtures, n_sims }),
    });
    if (!r.ok) throw new Error("API simulate: " + r.status);
    return r.json();
  },
};

// Centro de Mando
api.matchday = () => get("/api/matchday");
api.matchdays = (count = 3) => get(`/api/matchdays?count=${count}`);
api.evolution = (slug) => get(`/api/team/${slug}/evolution`);
api.headToHead = (slug) => get(`/api/team/${slug}/vs`);

// Plantilla
api.squad = () => get("/api/squad");

// Currículum / Resume Board
api.resume = () => get("/api/resume");

// Ficha de equipo
api.teamProfile = (slug) => get(`/api/team/${slug}`);

// Analíticas: tabla merecida, objetivos
api.merited = () => get("/api/merited");
api.objectives = (team) => get(`/api/objectives?team=${encodeURIComponent(team)}`);

// --- Admin (login + cuotas) ---
api.login = (username, password) =>
  fetch(`${BASE}/api/login`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  }).then((r) => { if (!r.ok) throw new Error("login"); return r.json(); });

api.adminMatchdayOdds = (token) =>
  fetch(`${BASE}/api/admin/matchday-odds`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then((r) => { if (!r.ok) throw new Error("auth"); return r.json(); });

api.adminSetOdds = (token, jornada, entries) =>
  fetch(`${BASE}/api/admin/odds`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ jornada, entries }),
  }).then((r) => { if (!r.ok) throw new Error("save"); return r.json(); });

api.adminUdoLastMatch = (token) =>
  fetch(`${BASE}/api/admin/udo-last-match`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then((r) => { if (!r.ok) throw new Error("auth"); return r.json(); });

api.adminReload = (token) =>
  fetch(`${BASE}/api/admin/reload`, {
    method: "POST", headers: { Authorization: `Bearer ${token}` },
  }).then((r) => { if (!r.ok) throw new Error("reload"); return r.json(); });

api.adminListMatches = (token) =>
  fetch(`${BASE}/api/admin/matches`, { headers: { Authorization: `Bearer ${token}` } })
    .then((r) => { if (!r.ok) throw new Error("auth"); return r.json(); });

api.adminSetResult = (token, entry) =>
  fetch(`${BASE}/api/admin/result`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(entry),
  }).then(async (r) => { const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || "result"); return j; });

api.adminPreviousMatches = (token) =>
  fetch(`${BASE}/api/admin/previous-matches`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then((r) => { if (!r.ok) throw new Error("auth"); return r.json(); });

api.adminSetStats = (token, jornada, entries) =>
  fetch(`${BASE}/api/admin/stats`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ jornada, entries }),
  }).then((r) => { if (!r.ok) throw new Error("stats"); return r.json(); });

api.adminSetRatings = (token, jornada, raw) =>
  fetch(`${BASE}/api/admin/ratings`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ jornada, raw }),
  }).then((r) => { if (!r.ok) throw new Error("ratings"); return r.json(); });

api.adminGetSquad = (token) =>
  fetch(`${BASE}/api/admin/squad`, { headers: { Authorization: `Bearer ${token}` } })
    .then((r) => { if (!r.ok) throw new Error("auth"); return r.json(); });

api.adminSaveSquad = (token, players) =>
  fetch(`${BASE}/api/admin/squad`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ players }),
  }).then((r) => { if (!r.ok) throw new Error("save"); return r.json(); });

api.adminDeleteSigning = (token, name) =>
  fetch(`${BASE}/api/admin/squad/${encodeURIComponent(name)}`, {
    method: "DELETE", headers: { Authorization: `Bearer ${token}` },
  }).then((r) => { if (!r.ok) throw new Error("del"); return r.json(); });

api.playerDetail = (name) => get(`/api/player/${encodeURIComponent(name)}`);
api.reportUrl = () => `${BASE}/api/report/next?team=${encodeURIComponent("UD Ourense")}`;

api.lineupFormations = () => get("/api/lineup/formations");
api.lineupMatchdays = () => get("/api/lineup/matchdays");
api.lineup = (jornada) => get(`/api/lineup/${jornada}`);
api.adminSaveLineup = (token, jornada, formation, players) =>
  fetch(`${BASE}/api/admin/lineup`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ jornada, formation, players }),
  }).then((r) => { if (!r.ok) throw new Error("save"); return r.json(); });
