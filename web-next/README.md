# Fantasy Scout Control Centre

The component-based replacement for the legacy static dashboard.

## Local development

```bash
npm install
npm run dev
```

The server-side data adapter uses the versioned FastAPI service through `FPL_API_BASE_URL`. It retains `FPL_DATA_BASE_URL` as a temporary migration fallback. Copy `.env.example` to `.env.local` for local integration.

## Validation

```bash
npm run typecheck
npm run build
```

## Architecture

- Next.js App Router and TypeScript
- Server Components for snapshot-backed routes
- Automatic current-gameweek discovery through the official FPL bootstrap cache
- Versioned API integration with a hosted-snapshot fallback
- Reusable application shell, pitch, player and metric components
- Typed model adapter in `lib/model.ts`
- Existing production dashboard remains unchanged until cutover

The production cutover steps and the Telegram safety boundary are documented in the repository's `DEPLOYMENT.md`.
