# 🚀 Despregue de "Ourense é UD" — guía paso a paso

Todo preparado para que só teñas que facer clics. Dúas partes:
**frontend en Vercel**, **backend en Render**. Sigue a orde.

---

## Antes de nada: subir o proxecto a GitHub

1. Crea un repositorio novo en GitHub (baleiro, sen README), por exemplo `ourenseeud`.
2. Sube a carpeta do proxecto. Se usas a liña de comandos:
   ```
   cd udo-tracker
   git init
   git add .
   git commit -m "Ourense é UD - versión inicial"
   git branch -M main
   git remote add origin https://github.com/O_TEU_USUARIO/ourenseeud.git
   git push -u origin main
   ```
   > O `.gitignore` xa evita subir datos sensibles (contrasinais, caché).

---

## Parte 1 — Backend en Render (a API + o modelo)

1. Entra en **https://render.com** e rexístrate (podes usar a conta de GitHub).
2. Clic en **New** → **Blueprint**.
3. Escolle o teu repositorio `ourenseeud`. Render detecta o ficheiro `render.yaml`
   automaticamente e propón crear o servizo **ourenseeud-api**.
4. Pediráche encher dúas variables (as marcadas para introducir a man):
   - **API_FOOTBALL_KEY**: a túa chave de API-Football.
     (Sácala gratis en https://www.api-football.com → rexístrate → Dashboard →
     copia a "API Key". Plan Free, 100 peticións/día, dabondo.)
   - **ALLOWED_ORIGIN**: déixao baleiro POLO DE AGORA (enchémolo na Parte 3).
   - **JWT_SECRET**: xa se xera soa, non toques.
5. Clic en **Apply**. Render instala e arranca. Tarda uns minutos a primeira vez.
6. Cando remate, Render dáche unha URL tipo `https://ourenseeud-api.onrender.com`.
   **Cópiaa**, necesítala na Parte 2.
   > Comproba que funciona: abre esa URL no navegador; debe amosar
   > `{"app":"Ourense é UD",...}`.

---

## Parte 2 — Frontend en Vercel (a web)

1. Entra en **https://vercel.com** e rexístrate (coa conta de GitHub).
2. Clic en **Add New** → **Project** → escolle o repo `ourenseeud`.
3. Vercel detecta que é Vite. En **Root Directory**, escolle **`frontend`**.
4. Desprega **Environment Variables** e engade unha:
   - Nome: **VITE_API_URL**
   - Valor: a URL de Render da Parte 1 (ex: `https://ourenseeud-api.onrender.com`)
5. Clic en **Deploy**. Nun minuto tes a web en liña.
6. Vercel dáche unha URL tipo `https://ourenseeud.vercel.app`. **Cópiaa.**

---

## Parte 3 — Conectar as dúas (CORS)

Para que a web poida falar coa API con seguridade:

1. Volve a **Render** → o teu servizo → **Environment**.
2. Edita **ALLOWED_ORIGIN** e pon a URL de Vercel (ex: `https://ourenseeud.vercel.app`,
   sen barra ao final).
3. Garda. Render reinicia só. Listo.

---

## Parte 4 — Crear o teu usuario admin

O login créase unha vez, desde a shell de Render:

1. En Render → o teu servizo → pestana **Shell**.
2. Escribe:
   ```
   python -m app.auth create david O_TEU_CONTRASINAL admin
   ```
   (cambia `O_TEU_CONTRASINAL` polo que queiras). Xa es admin.
3. Para engadir amigos como usuarios normais:
   ```
   python -m app.auth create nome_amigo o_seu_contrasinal user
   ```

---

## Parte 5 — Cargar datos reais (cando arranque a liga)

- Ata o 30/08 a liga está a cero co calendario oficial xa cargado.
- Tras cada xornada, para actualizar resultados desde API-Football:
  entra na app como admin e usa a recarga (ou, desde a Shell de Render:
  `python -m app.ingest --real`).

---

## Notas
- **O backend "dorme"** tras 15 min sen uso (plan gratuíto de Render). A primeira
  visita do día tarda ~30s en espertar; despois vai fino. Normal e sen custo.
- **Os escudos**: coloca os PNG en `frontend/public/escudos/` (ver README aí).
  Mentres non estean, amósanse monogramas.
- **Dominio propio**: se algún día queres `ourenseeud.com` en vez de `.vercel.app`,
  cómprase e engádese en Vercel → Settings → Domains.
- **Seguridade**: os contrasinais gárdanse hasheados; JWT_SECRET xérao Render;
  o CORS queda restrinxido ao teu dominio. Todo listo para uso real.
