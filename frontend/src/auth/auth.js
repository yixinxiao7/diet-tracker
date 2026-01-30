import { generatePkcePair, randomString } from './pkce'

const TOKEN_STORAGE_KEY = 'diet_tracker_tokens'
const PKCE_VERIFIER_KEY = 'diet_tracker_pkce_verifier'
const AUTH_STATE_KEY = 'diet_tracker_auth_state'

function normalizeDomain(domain) {
  if (!domain) return ''
  if (domain.startsWith('https://') || domain.startsWith('http://')) return domain
  return `https://${domain}`
}

export function getAuthConfig() {
  return {
    domain: normalizeDomain(import.meta.env.VITE_COGNITO_DOMAIN),
    clientId: import.meta.env.VITE_COGNITO_CLIENT_ID,
    redirectUri: import.meta.env.VITE_COGNITO_REDIRECT_URI,
    logoutUri: import.meta.env.VITE_COGNITO_LOGOUT_URI,
    scopes: import.meta.env.VITE_COGNITO_SCOPES || 'openid email profile',
  }
}

export function getAuthConfigErrors() {
  const config = getAuthConfig()
  const missing = []
  if (!config.domain) missing.push('VITE_COGNITO_DOMAIN')
  if (!config.clientId) missing.push('VITE_COGNITO_CLIENT_ID')
  if (!config.redirectUri) missing.push('VITE_COGNITO_REDIRECT_URI')
  if (!config.logoutUri) missing.push('VITE_COGNITO_LOGOUT_URI')
  return missing
}

function storeTokens(tokens) {
  localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokens))
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_STORAGE_KEY)
}

export function getStoredTokens() {
  const raw = localStorage.getItem(TOKEN_STORAGE_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

function tokenEndpoint() {
  const { domain } = getAuthConfig()
  return `${domain}/oauth2/token`
}

function buildAuthorizeUrl({ state, challenge }) {
  const { domain, clientId, redirectUri, scopes } = getAuthConfig()
  const params = new URLSearchParams({
    response_type: 'code',
    client_id: clientId,
    redirect_uri: redirectUri,
    scope: scopes,
    code_challenge_method: 'S256',
    code_challenge: challenge,
    state,
  })
  return `${domain}/oauth2/authorize?${params.toString()}`
}

async function exchangeCodeForToken(code, verifier) {
  const { clientId, redirectUri } = getAuthConfig()
  const body = new URLSearchParams({
    grant_type: 'authorization_code',
    client_id: clientId,
    redirect_uri: redirectUri,
    code,
    code_verifier: verifier,
  })

  const res = await fetch(tokenEndpoint(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })

  const data = await res.json()
  if (!res.ok) {
    throw new Error(data.error_description || 'Token exchange failed')
  }

  const expiresAt = Date.now() + Number(data.expires_in || 0) * 1000
  return {
    access_token: data.access_token,
    id_token: data.id_token,
    refresh_token: data.refresh_token,
    expires_at: expiresAt,
  }
}

async function refreshTokens(refreshToken) {
  const { clientId } = getAuthConfig()
  const body = new URLSearchParams({
    grant_type: 'refresh_token',
    client_id: clientId,
    refresh_token: refreshToken,
  })

  const res = await fetch(tokenEndpoint(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })

  const data = await res.json()
  if (!res.ok) {
    throw new Error(data.error_description || 'Token refresh failed')
  }

  const expiresAt = Date.now() + Number(data.expires_in || 0) * 1000
  return {
    access_token: data.access_token,
    id_token: data.id_token,
    refresh_token: refreshToken,
    expires_at: expiresAt,
  }
}

export async function login() {
  const { verifier, challenge } = await generatePkcePair()
  const state = randomString(32)

  sessionStorage.setItem(PKCE_VERIFIER_KEY, verifier)
  sessionStorage.setItem(AUTH_STATE_KEY, state)

  window.location.assign(buildAuthorizeUrl({ state, challenge }))
}

export async function handleAuthCallback() {
  const params = new URLSearchParams(window.location.search)
  const error = params.get('error')
  if (error) {
    return { error: params.get('error_description') || error }
  }

  const code = params.get('code')
  if (!code) return null

  const returnedState = params.get('state')
  const expectedState = sessionStorage.getItem(AUTH_STATE_KEY)
  if (!expectedState || returnedState !== expectedState) {
    return { error: 'Invalid auth state' }
  }

  const verifier = sessionStorage.getItem(PKCE_VERIFIER_KEY)
  if (!verifier) {
    return { error: 'Missing PKCE verifier' }
  }

  const tokens = await exchangeCodeForToken(code, verifier)
  storeTokens(tokens)

  sessionStorage.removeItem(PKCE_VERIFIER_KEY)
  sessionStorage.removeItem(AUTH_STATE_KEY)

  const url = new URL(window.location.href)
  url.searchParams.delete('code')
  url.searchParams.delete('state')
  url.searchParams.delete('error')
  url.searchParams.delete('error_description')
  window.history.replaceState({}, document.title, url.toString())

  return { tokens }
}

export async function getAccessToken() {
  const tokens = getStoredTokens()
  if (!tokens || !tokens.access_token) return null

  const now = Date.now()
  if (tokens.expires_at && tokens.expires_at > now + 30000) {
    return tokens.access_token
  }

  if (!tokens.refresh_token) {
    return tokens.access_token
  }

  try {
    const refreshed = await refreshTokens(tokens.refresh_token)
    storeTokens(refreshed)
    return refreshed.access_token
  } catch {
    clearTokens()
    return null
  }
}

export function logout() {
  const { domain, clientId, logoutUri } = getAuthConfig()
  clearTokens()
  const params = new URLSearchParams({
    client_id: clientId,
    logout_uri: logoutUri,
  })
  window.location.assign(`${domain}/logout?${params.toString()}`)
}

function parseJwt(token) {
  if (!token) return null
  const parts = token.split('.')
  if (parts.length !== 3) return null
  try {
    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')))
    return payload
  } catch {
    return null
  }
}

export function getUserEmail() {
  const tokens = getStoredTokens()
  const payload = parseJwt(tokens?.id_token)
  return payload?.email || null
}
