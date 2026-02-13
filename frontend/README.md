# Diet Tracker Frontend

This is the Vite + React SPA for the Diet Tracker. It integrates with Amazon Cognito Hosted UI (OAuth 2.0 + PKCE) and calls the backend API with JWTs.

## Environment Variables

Create a `.env.local` in `frontend/` with:

```
VITE_API_BASE_URL=https://your-api-gateway-domain
VITE_COGNITO_DOMAIN=your-domain.auth.us-east-1.amazoncognito.com
VITE_COGNITO_CLIENT_ID=your_cognito_app_client_id
VITE_COGNITO_REDIRECT_URI=http://localhost:5173
VITE_COGNITO_LOGOUT_URI=http://localhost:5173
VITE_COGNITO_SCOPES=openid email profile
```

Notes:
- `VITE_COGNITO_DOMAIN` can be the full URL or just the domain; `https://` is added automatically if missing.
- Redirect/logout URIs must be registered on the Cognito App Client.

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

## Features

- Cognito Hosted UI login with PKCE
- JWT-aware API client
- Ingredients, meals, meal logs, and summary pages
- Loading and error states for async operations
