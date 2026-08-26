# Ourense é UD · Rexistro do proceso

Proxecto: webapp de seguimento estatístico da 1ª RFEF (Grupo 1), foco na UD Ourense.
Dominio previsto: ourenseeud.vercel.app · Marca: "Ourense é UD" / "a nosa vida" (gl/es).

---

## Estado actual (última actualización: J-simulador pendente)

FEITO e probado:
- Motor Python: elo.py (Elo por equipo con ventaxa de campo + margen de vitoria)
  e montecarlo.py (Poisson bivariante + fuerzas ataque/defensa moduladas por Elo,
  shrinkage con poucos partidos, blend con cuotas). 10k sims en ~5,5s.
- Métricas de marca: oGoals (goles esperados do modelo) e oPts (puntos merecidos).
- API FastAPI (main.py): /standings, /probs (cacheado), /match/next (con cuotas),
  /simulate (qué-pasa-si). Todos probados con TestClient.
- store.py: capa de datos JSON. season_2026_27.json de arranque (mock coherente).
- Frontend: home con hero grande + dashboard bilingüe, escudos con monograma de
  respaldo (/public/escudos/{slug}.png), cores do Excel para zonas, oPts/Δ/xG.
- api.js: cliente do frontend.

FEITO:
- Simulador interactivo (udo-simulator.jsx): fixa 1-X-2 da xornada,
  ve táboa + probabilidades lado a lado. Sim. lixeira en cliente + /api/simulate.
- Endpoints novos: /api/matchday (xornada en curso), /api/simulate (agora devolve
  {table, probs}).

FEITO:
- Centro de Mando (udo-command-center.jsx): próximo partido (1-X-2 +
  oGoals + marcador probable), cara a cara (pos/pts/goles/forma/Elo), e gráfico
  de evolución oPts vs Pts estilo Torvik (a brecha = merecido vs conseguido).
- Endpoints: /api/team/{slug}/evolution, /api/team/{slug}/vs, marcador probable
  en match_probs.

PENDENTE: Xerador de lineup PNG (último da orde acordada).

PENDENTE (orde acordada): Simulador → Centro de Mando UDO → Xerador lineup PNG.
Máis adiante: scraping real, sección fichaxes/rumores (admin), multimedia, Twitter.

---

## Verificacións de datos (contra fontes reais)

[OK] 20 equipos do Grupo 1 2026-27 confirmados. O 20º é Arenas Club (de Getxo).
[OK] UD Ourense ascendeu vía playoff en 2025-26; debuta en 1ª RFEF en 2026-27.
[!!] CALENDARIO REAL xa publicado (RFEF PDF, 29/06/2026):
     - J1 (29 ago): UD Ourense - SD Ponferradina
     - J2: CD Mirandés - UD Ourense
     O noso season_2026_27.json ten emparellamentos MOCK que NON coinciden co real.
     → Antes de producción: substituír polo calendario oficial (scrapear PDF RFEF).
[i] Fontes útiles detectadas: RFEF (oficial, PDF calendario), Flashscore, BeSoccer,
    FotMob (dá forma, xogadores, próximos rivais), Futbolme.

---

## Decisións tomadas
- Métrica propia chámase oGoals / oPts (marca Ourense).
- Motor: Poisson + Elo, con blend opcional de cuotas (Bet365 etc.).
- Lineup compartible: saída PNG para redes.
- Escudos: non se incrustan (marca dos clubs); sistema con PNG + monograma fallback.
- Deploy previsto: frontend en Vercel, backend Python en Render/Railway/Fly
  (o Monte Carlo non encaixa en serverless de Vercel).

## ⚠️ BLOQUEANTE ANTES DE PUBLICAR
- Poñer a temporada A CERO: hai 8 xornadas MOCK xogadas en season_2026_27.json
  que hai que borrar (played = []).
- Meter o calendario OFICIAL da RFEF (J1-J38, todos os equipos a 0 puntos).
  A liga arranca o 29/08/2026 (J1: UD Ourense - SD Ponferradina).
- Ata entón, desenvólvese sobre o mock (máis cómodo: ten datos para ver a estética).

## Simulador — decisións
- Alcance inicial: só a xornada en curso (ampliarase despois).
- Ao meter un resultado: actualízanse á vez a TÁBOA (reordénase) e as
  PROBABILIDADES, lado a lado.

## Preguntas abertas para o usuario
- (ver conversa) formato de zonas, cores exactas, orde de features.

## Verificación plantilla UD Ourense 2026-27 (25/08/2026)
- 18 jugadores, valor 1,53 M€, edad media 26,2, estadio O Couto (5.625).
- Siguen (vistos): Rufo Sánchez, Santiago De Prado, Víctor Gamarra, Hugo Busto, Fernando Iglesias...
- Altas verano 2026: S. Baldrich (DEL, UCAM), Xabi Domínguez (DEL, Recreativo), Curro (CEN, Xerez).
- Bajas: Manu Núñez, Pablo Parrilla, Y. Zayzoun.
- DECISIÓN: el generador de lineup NO lleva plantilla hardcodeada. Recibe 11
  nombres + formación (los pone el admin o se scrapean de Transfermarkt).
  El once tipo cambia cada jornada; no debe fijarse en código.
- Lineup: formato 16:9 (Twitter/X), formaciones elegibles, render en backend (Pillow).

## FEITO — Xerador de lineup PNG (completa a orde acordada)
- lineup.py (Pillow): imaxe 16:9 (1600x900) para Twitter/X. Campo con franxas,
  fichas vermellas con dorsal, nomes lexibles, cabeceira coa formación, marca de auga.
- Formacións elexibles: 4-3-3, 4-4-2, 3-5-2, 5-3-2, 4-2-3-1, 3-4-3, 4-1-4-1.
- Xogadores como parámetro (o admin edítaos). Validación de nº de xogadores.
- Endpoints: POST /api/lineup.png · GET /api/formations. Probados.

## RESUMO: as 4 pezas da orde acordada están FEITAS
API ✓ · Simulador ✓ · Centro de Mando ✓ · Lineup PNG ✓
Seguinte fronte (a decidir): scraping real / sección fichaxes-rumores (admin) /
multimedia / integración Twitter / deploy (Vercel + Render).

## CORRECCIÓN plantilla (25/08/2026) — o usuario aporta a plantilla real
- ERRO previo: dei por bos Gamarra e Hugo Busto (do ano pasado). NON seguen.
- Plantilla real 2026-27 guardada en squad.js (22 xogadores con valor de mercado).
  Referencias por valor: Julio Cabrera e Álvaro Bastida (200k€).
- REGRA: a plantilla que dá o usuario manda sobre calquera scraping.

## IDEA rexistrada (para máis adiante)
- Sección "ex-ourensáns": seguimento de xogadores que pasaron pola UDO e onde xogan agora.

## AXUSTE lineup
- Facelo máis parecido á app do Avilés: máis minimalista, xogadores MÁIS GRANDES.

## FEITO — Lineup v2 (estilo Avilés, corrixido)
- Reescrito: fondo vermello sólido con degradado sutil, camisetas GRANDES co dorsal
  dentro, nomes limpos debaixo. Reparto por celdas (sen solapes). Porteiro centrado.
- Probado coa plantilla REAL 2026-27 (4-3-3: Vizoso; Noel-Labrada-Irazu-Cabrera;
  Curro-Bastida-Tejón; Gandarillas-Baldrich-Ferreiro).
- squad.js: plantilla real como fonte de datos do once.

## Sección plantilla — decisións
- Vista: cuadrícula de tarxetas (unha por xogador).
- Mostrar valor de mercado (non protagonista) + NOTA de rendemento.
- NOTA = "oRating" (marca propia, coherente con oGoals/oPts). IMPORTANTE:
  as notas de Sofascore/FlashScore veñen dun feed de eventos por xogador (de pago,
  mala cobertura en 1ª RFEF, non scrapeable fiable). Así que oRating calcúlase co
  que temos: minutos, goles, asistencias, resultado, rendemento vs modelo.
  Deixar hook para un feed mellor no futuro. Non vender como "igual a Sofascore".
- Orde de traballo acordada: 1) plantilla → 3) scraping → 2) posta a cero+calendario.

## FEITO — Sección plantilla + oRating
- rating.py: oRating (nota propia 1-10, áncora 6.0). Pondera por posición, goles,
  asistencias, resultado, portería a cero, goles encaixados. season_rating = media.
- Endpoint /api/squad: plantilla + oRating calculado das notas por partido.
  data/squad.json editable polo admin (plantilla real + match_ratings).
- udo-squad.jsx: cuadrícula de tarxetas. Filtro por liña, orde por dorsal/oRating/
  valor/idade. oRating destacado (cor: verde≥7.0, ámbar≥6.3, marrón baixo).
- Nota: oRating NON é Sofascore (feed non dispoñible en 1ª RFEF); é transparente.

SEGUINTE (orde): 3) scraping real → 2) posta a cero + calendario oficial.

## ⏸️ PAUSA — sesión cerrada (25/08/2026)
DECISIÓN PENDENTE para retomar: estratexia de scraping.
- Recomendación dada: RFEF como base fiable (limpo, legal, datos básicos) +
  complementos (BeSoccer/FlashScore) CACHEADOS e opcionais, con degradación
  elegante se fallan. Transfermarkt: só para fase de fichaxes (é o que máis banea).
- Riscos explicados por fonte: RFEF (baixo legal, básico) · FlashScore/BeSoccer
  (zona gris, prohiben scraping, bloquean bots) · Transfermarkt (o máis restritivo).
- Prioridade acordada: 1) clasificación+resultados  2) stats por xogador (oRating).
- Modo: empezar MANUAL, automatizar despois.
- O usuario decide mañá. AO RETOMAR: preguntar decisión e, segundo ela, construír
  o scraper RFEF primeiro (base), con caché en backend.

### Estado global do proxecto (todo probado e en /outputs)
FEITO: motor (elo+montecarlo), API FastAPI, dashboard, simulador, centro de mando,
xerador lineup PNG v2 (estilo Avilés), sección plantilla + oRating.
PENDENTE: scraping → posta a cero + calendario oficial → (despois) fichaxes/rumores,
multimedia, Twitter, ex-ourensáns, deploy (Vercel + Render/Railway).
BLOQUEANTE PUBLICACIÓN: poñer temporada a cero + meter calendario oficial RFEF.

## INVESTIGACIÓN de fontes de datos 1ª RFEF (26/08/2026)
Resultado da investigación pedida polo usuario (APIs, FBref, open data):

APIS que SÍ cobren 1ª RFEF (verificado):
- API-Football (api-sports.io): +1200 ligas, 1ª RFEF incluída. FREE = 100 peticións/día
  (sen tarxeta). De pago desde 19$/mes. JSON, GET-only, header x-apisports-key.
  ⭐ Mellor relación cobertura/prezo para este proxecto. Ollo: xG "inconsistente".
- Sportmonks: di cubrir "Primera Federación" end-to-end. Free tier só 2 ligas
  (danesa+escocesa) → para nós habería que pagar. Máis caro.
- FootyStats: ten "Primera Division RFEF Group 1" con datos por tempada.
- TheStatsAPI: 50$/mes, inclúe xG. Caro para uso persoal.

APIS que NON serven:
- football-data.org: free "for ever" pero só 12 grandes ligas. NON ten 1ª RFEF.
- FBref (Sports Reference): NON cobre 1ª RFEF (España só ata La Liga/Segunda).
  → IMPORTANTE: descarta a idea de sacar xG real estilo Torvik de FBref nesta
    categoría. Reforza usar o noso oGoals propio.

CONCLUSIÓN / recomendación técnica:
- Mellor opción: API-Football plan FREE (100 req/día). Para uso persoal/círculo
  pequeno abonda de sobra se CACHEAMOS no backend (clasificación/resultados cambian
  1 vez/semana). Evita scraping fráxil e é legal (API oficial de datos).
- Fallback/complemento: scraping RFEF (base limpa) + volcado manual a Excel para
  datos difíciles (idea do usuario, moi válida para o que a API non dea).
- xG real: non dispoñible fiable en 1ª RFEF por ningunha vía → usar oGoals propio.

DECISIÓN do usuario sobre scraping (hoxe):
- Acepta scraping con tempos de espera aleatorios (rate limiting).
- Alternativa válida: volcado manual a Excel subible (scraping manual) para datos difíciles.
- Poucas peticións (uso individual/círculo). Protexer con contrasinal/usuario ao inicio.

## DECISIÓN scraping/datos (26/08)
- FONTE BASE: API-Football (plan FREE) + scraping RFEF de apoio. SEN Excel de entrada.
- Excel manual: NON necesario ao inicio. O oRating xa se calcula de goles/minutos/
  resultado que dá a API. Só faría falta Excel para AXUSTAR notas a man ou datos
  cualitativos (lesionado/sancionado). Se xorde, plantilla trivial de 3-4 columnas.
- ACCESO: usuario+contrasinal POR PERSOA. Admin = usuario "david".
  → Construír: cliente API-Football (cacheado) + auth con roles (admin/user).

## FEITO — Fonte de datos (API-Football) + Autenticación (26/08)
- apifootball.py: cliente API-Football con CACHÉ en disco (TTL 6h) e modo MOCK
  para desenvolver sen chave. Degradación elegante (usa caché vella se a API falla).
  Verificado: coverage de 1ª RFEF ten standings+players+lineups pero NON
  statistics_players → confirma oRating propio. Chave en env API_FOOTBALL_KEY.
- ingest.py: adaptador API-Football → formato interno (store). Illa o provedor.
  Correr manual: `python -m app.ingest [--real]`. Probado en mock.
- auth.py: usuarios+contrasinal por persoa, hash bcrypt, JWT, roles admin/user.
  (Nota: cambiei passlib por bcrypt directo por bug de versión.)
  Usuarios creados: david (ADMIN), afeccionado (user de proba). Chave JWT_SECRET en env.
- main.py: /api/login, /api/me, /api/admin/reload (só admin). Probado todo o fluxo
  (200 login, 401 sen token, 403 user en ruta admin, 200 admin).

PENDENTE (orde orixinal): 2) posta a cero + calendario oficial (BLOQUEANTE publicación).
Despois: fichaxes/rumores (admin), multimedia, Twitter, ex-ourensáns, deploy.

## ⚠️ RECORDATORIO SEGURIDADE antes de producción
- Cambiar JWT_SECRET e contrasinais reais (os de proba son de desenvolvemento).
- Restrinxir CORS ao dominio de Vercel (agora está en "*").
- users.json NON se sobe a git (contén hashes). Engadir a .gitignore.

## ✅ RESOLTO — Posta a cero + calendario oficial (26/08)
- Descargado o PDF OFICIAL da RFEF (Primera_Federacion_Grupo_I.pdf) e parseado.
- season_2026_27.json REXENERADO A CERO: played=[], 380 partidos en remaining,
  38 xornadas, calendario oficial completo con datas. VALIDADO:
  380 partidos, 38/equipo, 20 equipos, todos os nomes canónicos ✓.
- J1 (30/08/2026): UD Ourense - SD Ponferradina (confirmado oficial).
- Verificado na API: standings a 0, matchday=J1, probs de playoff ~25% (5/20,
  correcto con forzas iniciais iguais).
- scripts/import_rfef_calendar.py: ferramenta reutilizable para reimportar o PDF.
- MODO NORMAL de actualización: API-Football (cando a liga arranque, os resultados
  entran solos vía ingest). O PDF foi só a carga inicial.
- ⚠️ BLOQUEANTE DE PUBLICACIÓN: RESOLTO. Xa se pode publicar coa temporada limpa.

### Estado global
FEITO: motor, API, dashboard, simulador, centro de mando, lineup PNG, plantilla+
oRating, cliente API-Football+ingest, auth (david admin), calendario oficial a cero.
PENDENTE: fichaxes/rumores (admin), multimedia, Twitter, ex-ourensáns, xuntar todo
nunha app navegable, deploy (Vercel + Render/Railway).

## AXUSTES aplicados (26/08, tras revisar preview)
- Escudo UDO en vez de "é" (BrandCrest, placeholder ata ter o PNG).
- Escudos na clasificación (Crest carga /escudos/{k}.png con fallback monograma).
- Playoff en AMARELO (#e0a500) en vez de azul.
- oGoals: UDO en vermello RESPECTANDO orde local/visitante (se xoga fóra, é o 2º).
- MOTOR: peso extra a partidos FÓRA (AWAY_WEIGHT=1.15). Probado: gañar fóra dá
  algo máis de forza que gañar na casa, moderado. Probs seguen sumando 1.
- Feedback usuario: sección UD Ourense "fantástica"; plantilla gústalle (fotos despois).

## 💡 IDEAS FUTURAS do usuario (para valorar e implementar máis adiante)
Seccións analíticas:
- Posibles fichaxes / xogadores da categoría destacados.
- Eficacia por Game State: rendemento en contextos concretos (ex: empatando fóra
  nos últimos 20 min). O modelo táctico cambia segundo o marcador.
- "Vitorias baleiras": menos valor a vitoria se o rival tivo expulsión temperá.
- Semellanza histórica: correlación % da UDO actual con tempadas/equipos icónicos.
- Gráficos radiais de estilo (PPDA, posesión tercio rival, eficacia defensiva).
- Game Flow: xG acumulado ao longo dos 90 min alterando prob. de vitoria.
- "Currículum/Resume Board": ponderar valor real dos puntos (gañar fóra a un
  candidato vale máis que na casa ao colista). [Conecta co AWAY_WEIGHT xa feito.]
- Táboa mestra ordenable por calquera columna (Puntos, xG, xGA, xPts).
- Filtros de temporalidade ("desde X1", "tras cambio de adestrador").

Novas FONTES de datos propostas (a valorar):
- Football-Data.co.uk (Buchdahl): CSV históricos con cuotas de peche. Sen bloqueos.
  → ideal para calibrar Poisson e validar Monte Carlo con prob. implícitas.
- ClubElo (api.clubelo.com/...): Elo baseline por CSV/URL. [OLLO: cobre 1ª RFEF? verificar]
- StatsBomb Open Data (statsbombpy): eventos alta fidelidade para CALIBRAR (non cobre
  1ª RFEF pero serve para adestrar algoritmos propios).
- Endpoints internos FotMob: JSON limpo, cobre 1ª RFEF (aliñacións, eventos, forma).
- Actas oficiais RFEF: JSON vía Network tab (sancións, minutos, tarxetas). Fonte da verdade.
- Paquetes: soccerdata / worldfootballR (xestionan caché, estandarizan extracción).

## FEITO — Preparación de DEPLOY (26/08)
- Recomendación: backend en RENDER (máis fácil de manter; dorme tras 15min, ok
  para uso persoal). Frontend en Vercel.
- render.yaml: config do backend (só clic "Apply"). JWT_SECRET auto, API_FOOTBALL_KEY
  e ALLOWED_ORIGIN a introducir na web.
- CORS restrinxido a ALLOWED_ORIGIN (env). Pendente de seguridade RESOLTO.
- Frontend: andamiaxe Vite completo (package.json, vite/tailwind/postcss config,
  index.html con título "Ourense é UD · a nosa vida" e favicon do escudo).
  BUILD PROBADO: 31 módulos, 53KB gzip, OK.
- vercel.json (SPA rewrites), .env.example (VITE_API_URL).
- public/escudos/ con README (onde poñer os PNG).
- .gitignore: NON sobe users.json, api_cache, node_modules, .env.
- DEPLOY.md: guía paso a paso só-clics (GitHub → Render → Vercel → CORS → admin).
- Backend verificado: carga cos 14 endpoints. Frontend verificado: build OK.

## ESTADO: LISTO PARA DESPREGAR
Todo o esencial + infraestrutura feito e probado. O usuario só ten que seguir
DEPLOY.md (clics). Pendente só-usuario: subir a GitHub, chave API-Football, PNG escudos.
Seccións futuras (ideas guardadas): fichaxes, ex-ourensáns, analíticas avanzadas.
