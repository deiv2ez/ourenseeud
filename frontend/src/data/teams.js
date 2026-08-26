// Los 20 equipos de 1ª RFEF Grupo 1 (temporada 2026-27).
//
// ESCUDOS: no incluimos los escudos oficiales (son marca registrada de cada club).
// El sistema espera un PNG en /public/escudos/{slug}.png. Mientras no exista,
// se pinta un "monograma" con las iniciales y el color del club como respaldo.
// Cuando coloques los archivos, se muestran automáticamente sin tocar código.
//
// `color` es el color primario aproximado de cada club, solo para el monograma
// de respaldo. El acento rojo de la UD Ourense en la interfaz es aparte.

export const TEAMS = [
  { slug: "arenas",       name: "Arenas Club",          short: "ARE", color: "#000000" },
  { slug: "bilbao-ath",   name: "Bilbao Athletic",      short: "ATH", color: "#c10000" },
  { slug: "barakaldo",    name: "Barakaldo CF",         short: "BAR", color: "#f5c400" },
  { slug: "coria",        name: "CD Coria",             short: "COR", color: "#123f8c" },
  { slug: "extremadura",  name: "CD Extremadura",       short: "EXT", color: "#0b6e3b" },
  { slug: "lugo",         name: "CD Lugo",              short: "LUG", color: "#9b1b30" },
  { slug: "mirandes",     name: "CD Mirandés",          short: "MIR", color: "#b1121b" },
  { slug: "leonesa",      name: "CyD Leonesa",          short: "CUL", color: "#0a1b3d" },
  { slug: "merida",       name: "AD Mérida",            short: "MER", color: "#0b0b0b" },
  { slug: "pontevedra",   name: "Pontevedra CF",        short: "PON", color: "#1a3a7a" },
  { slug: "racing-ferrol",name: "Racing Ferrol",        short: "FER", color: "#0a7a2f" },
  { slug: "fabril",       name: "RC Deportivo Fabril",  short: "FAB", color: "#1874c4" },
  { slug: "aviles",       name: "Real Avilés",          short: "AVI", color: "#ffffff" },
  { slug: "real-union",   name: "Real Unión",           short: "RUN", color: "#c8102e" },
  { slug: "ponferradina", name: "SD Ponferradina",      short: "PFR", color: "#1f5fbf" },
  { slug: "logrones",     name: "UD Logroñés",          short: "LOG", color: "#c8102e" },
  { slug: "ourense",      name: "UD Ourense",           short: "OUR", color: "#C8102E", udo: true },
  { slug: "unionistas",   name: "Unionistas",           short: "UNI", color: "#0a1b3d" },
  { slug: "cacereno",     name: "CP Cacereño",          short: "CAC", color: "#0b6e3b" },
  { slug: "zamora",       name: "Zamora CF",            short: "ZAM", color: "#c8102e" },
];

export const byName = Object.fromEntries(TEAMS.map((t) => [t.name, t]));
