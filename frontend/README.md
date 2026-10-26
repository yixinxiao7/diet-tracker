# Diet Tracker Frontend

This is the Vite + React SPA for the Diet Tracker. It signs users in with Supabase Auth (email and password) and calls the backend API with the Supabase access token as a bearer JWT.

## Environment Variables

Copy `.env.example` to `.env.local` in `frontend/` and fill in:

```
VITE_API_BASE_URL=/api
VITE_SUPABASE_URL=https://your-project-ref.supabase.co
VITE_SUPABASE_ANON_KEY=your-publishable-anon-key
```

Notes:
- `VITE_API_BASE_URL` defaults to `/api` (same-origin Vercel Functions) when unset.
- If email confirmation is enabled in Supabase, sign-up shows a "check your email" message; the confirmation link returns to the app origin, which must be listed under Authentication > URL Configuration in Supabase.
- `VITE_AUTH_BYPASS=true` skips Supabase with a fake signed-in session. The Playwright E2E servers set it automatically.

## Development

```
cd frontend
npm install
npm run dev
```

## Build

```
npm run build
```

## Tests

```
npm test          # unit tests (Vitest)
npm run test:e2e  # Playwright E2E against the mock API, with auth bypass
```

## Features

- Supabase Auth sign-in and sign-up with email confirmation
- JWT-aware API client
- Ingredients, meals, meal logs, and summary pages
- Loading and error states for async operations
