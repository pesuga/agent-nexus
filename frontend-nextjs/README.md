# Dispatch Frontend (Next.js)

Active frontend for Dispatch.

## Stack

- Next.js App Router
- React
- TypeScript
- Tabler (`@tabler/core`)

## Run Locally

```bash
npm install
npm run dev
```

Default URL: `http://localhost:3001`

## Key Paths

- `src/app/(auth)/login/page.tsx`: Login screen
- `src/app/(dashboard)/...`: Authenticated dashboard pages
- `src/app/api/auth/*`: Session cookie auth routes
- `src/app/api/dispatch/[...path]/route.ts`: Backend proxy
- `src/context/AppContext.tsx`: UI/session/project state
- `src/components/kanban/*`: Kanban UI

## Behavior Notes

- Dashboard routes are protected by middleware/proxy auth checks.
- The UI currently prioritizes the Pesulabs project context.
- Frontend calls backend via same-origin proxy routes where possible.
