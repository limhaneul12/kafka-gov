# FRONTEND KNOWLEDGE BASE

## OVERVIEW

`frontend/` is a standalone React 19 + TypeScript + Vite app that talks to the backend through the `/api` proxy.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| App bootstrap | `frontend/src/main.tsx` | imports i18n, mounts React root |
| Route map | `frontend/src/App.tsx` | BrowserRouter + layout + top-level pages |
| Shared API calls | `frontend/src/services/api.ts` | Axios instance, endpoint helpers, `/api/` base URL |
| Route-level screens | `frontend/src/pages/` | page orchestration and screen composition |
| Shared UI | `frontend/src/components/` | layout, consumer, schema, topic, ui building blocks |
| Reusable client logic | `frontend/src/hooks/` | websocket, toast, schema hooks |
| Localization | `frontend/src/i18n/index.ts` | Korean default, localStorage-backed language |
| Dev server behavior | `frontend/vite.config.ts` | port `3000`, `/api` proxy to backend `8000` |

## CONVENTIONS

- Keep route registration in `frontend/src/App.tsx`; route-level views live under `frontend/src/pages/`.
- Use the shared Axios client in `frontend/src/services/api.ts` instead of ad hoc fetch wrappers.
- Keep imports relative; this repo does not define TS path aliases in `frontend/tsconfig.json`.
- Expect translations to default to Korean unless `localStorage.language` overrides it.
- Reuse existing toast and hook patterns before adding new notification or websocket plumbing.

## ANTI-PATTERNS

- Do not hardcode backend hostnames in components; the dev proxy and deployed nginx path expect `/api`.
- Do not bypass `frontend/src/services/api.ts` for shared backend endpoints unless the change is truly one-off.
- Do not add child AGENTS files under `frontend/src/` unless contributor behavior clearly diverges from this file.
- Do not duplicate backend feature rules here; frontend file should stay focused on UI structure and client wiring.

## COMMANDS

```bash
npm install
npm run dev
npm run build
npm run lint
```

## NOTES

- `frontend/src/App.tsx` uses `BrowserRouter` and wraps routed pages in `components/layout/Sidebar`.
- The app uses `sonner` toasts globally from the top-level app shell.
