# Zatoona — Frontend

The student-facing web app for the **Leo Agent** exam system. Upload your notes → generate a validated exam → answer it → get graded feedback. _Study smart._

Built with **Vite + React + TypeScript + Tailwind v4** and `motion`. Design system in [`../DESIGN.md`](../DESIGN.md); product strategy in [`../PRODUCT.md`](../PRODUCT.md).

## Run it

```bash
npm install
npm run dev      # http://localhost:5173
```

The backend must be running (it's the parent folder of this one):

```bash
cd .. && docker compose up --build   # gateway on http://localhost:80
```

That's it — in dev, Vite **proxies** all API paths (`/auth`, `/upload`, `/generate-exam`, `/submit-answer`, `/history`, `/get-exam`, `/health`) to the nginx gateway. The browser stays same-origin, so there's **no CORS and no preflight** (the gateway's `auth_request` 401s `OPTIONS` preflights — proxying server-side sidesteps that entirely).

## Configuration

| Env var | Default | Use |
|---|---|---|
| `VITE_API_TARGET` | `http://localhost` | Dev proxy target (the gateway). Set if the backend runs elsewhere. |
| `VITE_API_BASE` | `''` (same-origin) | **Production** only. Set to the gateway URL when the built SPA is served from a different origin than the API. Leave empty if served behind the same nginx. |

## Build

```bash
npm run build    # tsc -b && vite build  →  dist/
npm run preview  # serve the production build locally
```

For production, either serve `dist/` behind the same nginx gateway (keep `VITE_API_BASE` empty) or host it separately and set `VITE_API_BASE` to the gateway origin.

## Structure

```
src/
  lib/
    api.ts      typed fetch client for every endpoint + ApiError
    auth.tsx    AuthProvider — tokens in localStorage, transparent refresh-on-401 (withAuth)
    study.tsx   StudyProvider — exam/report/topics, persisted to sessionStorage
    types.ts    API contract types
  components/
    ui.tsx        Button, Input, Textarea, Card, Chip, Alert, Spinner, Field
    Mascot.tsx    the olive, animated to moods (idle/think/cheer/wave/sad/peek)
    StagedBusy.tsx full-screen staged wait (named phases) for long backend calls
    Brand.tsx     wordmark/lockup
    Layout.tsx    app shell (top nav + user menu + theme toggle)
  lib/theme.ts    dark-mode toggle (class on <html>, no-flash init in index.html)
  pages/
    Landing.tsx   public marketing page at /
    Login.tsx · Home.tsx · Exam.tsx · Results.tsx · History.tsx
  main.tsx        router + route guards
```

Routes: `/` = public **Landing** (logged-in users redirect to `/app`); `/login`; the app lives behind auth at **`/app`** (index = study desk, `/app/exam`, `/app/results`, `/app/history`).

**Dark mode** is class-based (`.dark` on `<html>`), applied before paint by an inline script in `index.html`, toggled from the header and remembered in `localStorage`.

## Notes

- **Token refresh is automatic.** `withAuth()` retries once through `/auth/refresh` on a 401, so long uploads/generation don't bounce the user.
- **State survives refresh.** The current exam/report live in `sessionStorage` — reloading mid-generation won't lose your place.
- The mascot is a single PNG (`public/zatoona.png`) animated into every mood. To swap in dedicated expression art later, see `../logo-prompts.md`.
