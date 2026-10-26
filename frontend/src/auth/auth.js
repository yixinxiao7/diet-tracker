import { createClient } from '@supabase/supabase-js'

const BYPASS_EMAIL = 'test@example.com'

let client = null
let bypassSignedIn = true

function isAuthBypass() {
  return ['true', '1'].includes(import.meta.env.VITE_AUTH_BYPASS)
}

export function getAuthConfig() {
  return {
    supabaseUrl: import.meta.env.VITE_SUPABASE_URL,
    supabaseAnonKey: import.meta.env.VITE_SUPABASE_ANON_KEY,
  }
}

export function getAuthConfigErrors() {
  if (isAuthBypass()) return []
  const config = getAuthConfig()
  const missing = []
  if (!config.supabaseUrl) missing.push('VITE_SUPABASE_URL')
  if (!config.supabaseAnonKey) missing.push('VITE_SUPABASE_ANON_KEY')
  return missing
}

function getClient() {
  if (client) return client
  const { supabaseUrl, supabaseAnonKey } = getAuthConfig()
  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error('Supabase is not configured')
  }
  // detectSessionInUrl picks up the session when the user lands back from the
  // email-confirmation link, so no dedicated callback route is needed.
  client = createClient(supabaseUrl, supabaseAnonKey, {
    auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
  })
  return client
}

function createBypassSession() {
  const header = btoa(JSON.stringify({ alg: 'none', typ: 'JWT' }))
  const payload = btoa(JSON.stringify({ email: BYPASS_EMAIL }))
  return {
    access_token: `${header}.${payload}.signature`,
    user: { email: BYPASS_EMAIL },
  }
}

export async function getSession() {
  if (isAuthBypass()) {
    return bypassSignedIn ? createBypassSession() : null
  }
  if (getAuthConfigErrors().length > 0) return null
  const { data, error } = await getClient().auth.getSession()
  if (error) throw error
  return data.session
}

// Returns an unsubscribe function. The callback receives the session or null.
export function onAuthStateChange(callback) {
  if (isAuthBypass() || getAuthConfigErrors().length > 0) return () => {}
  const { data } = getClient().auth.onAuthStateChange((_event, session) => {
    callback(session)
  })
  return () => data.subscription.unsubscribe()
}

export async function signIn(email, password) {
  if (isAuthBypass()) {
    bypassSignedIn = true
    return createBypassSession()
  }
  const { data, error } = await getClient().auth.signInWithPassword({ email, password })
  if (error) throw error
  return data.session
}

// Resolves to { session, needsConfirmation }. When email confirmation is on,
// Supabase returns a user but no session until the link is clicked.
export async function signUp(email, password) {
  if (isAuthBypass()) {
    bypassSignedIn = true
    return { session: createBypassSession(), needsConfirmation: false }
  }
  const { data, error } = await getClient().auth.signUp({
    email,
    password,
    options: { emailRedirectTo: window.location.origin },
  })
  if (error) throw error
  return { session: data.session, needsConfirmation: !data.session }
}

// Kept under its original name so the API client doesn't change. The backend
// verifies the Supabase access token, so that is what gets sent.
export async function getIdToken() {
  const session = await getSession()
  return session?.access_token || null
}

export async function logout() {
  if (isAuthBypass()) {
    bypassSignedIn = false
    return
  }
  await getClient().auth.signOut()
}
