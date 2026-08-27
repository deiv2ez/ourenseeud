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
