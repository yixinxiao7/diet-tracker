import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const authApi = {
  getSession: vi.fn(),
  onAuthStateChange: vi.fn(),
  signInWithPassword: vi.fn(),
  signUp: vi.fn(),
  signOut: vi.fn(),
}
const createClient = vi.fn(() => ({ auth: authApi }))

vi.mock('@supabase/supabase-js', () => ({ createClient }))

async function loadAuth(env = {}) {
  vi.resetModules()
  vi.stubEnv('VITE_AUTH_BYPASS', env.bypass ?? '')
  vi.stubEnv('VITE_SUPABASE_URL', env.url ?? 'https://ref.supabase.co')
  vi.stubEnv('VITE_SUPABASE_ANON_KEY', env.key ?? 'anon-key')
  return import('./auth')
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.stubGlobal('window', { location: { origin: 'http://localhost:5173' } })
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

describe('config', () => {
  it('reports missing Supabase variables', async () => {
    const auth = await loadAuth({ url: '', key: '' })
    expect(auth.getAuthConfigErrors()).toEqual(['VITE_SUPABASE_URL', 'VITE_SUPABASE_ANON_KEY'])
  })

  it('reports nothing missing in bypass mode', async () => {
    const auth = await loadAuth({ bypass: 'true', url: '', key: '' })
    expect(auth.getAuthConfigErrors()).toEqual([])
  })

  it('returns no session without touching Supabase when unconfigured', async () => {
    const auth = await loadAuth({ url: '', key: '' })
    expect(await auth.getSession()).toBeNull()
    expect(createClient).not.toHaveBeenCalled()
  })
})

describe('supabase mode', () => {
  it('creates the client once from the env config', async () => {
    authApi.getSession.mockResolvedValue({ data: { session: null }, error: null })
    const auth = await loadAuth()
    await auth.getSession()
    await auth.getSession()
    expect(createClient).toHaveBeenCalledTimes(1)
    expect(createClient).toHaveBeenCalledWith('https://ref.supabase.co', 'anon-key', expect.any(Object))
  })

  it('getIdToken returns the session access token', async () => {
    authApi.getSession.mockResolvedValue({
      data: { session: { access_token: 'jwt-123', user: { email: 'a@b.com' } } },
      error: null,
    })
    const auth = await loadAuth()
    expect(await auth.getIdToken()).toBe('jwt-123')
  })

  it('getIdToken returns null when signed out', async () => {
    authApi.getSession.mockResolvedValue({ data: { session: null }, error: null })
    const auth = await loadAuth()
    expect(await auth.getIdToken()).toBeNull()
  })

  it('signIn returns the session and throws Supabase errors', async () => {
    const session = { access_token: 'jwt' }
    authApi.signInWithPassword.mockResolvedValueOnce({ data: { session }, error: null })
    const auth = await loadAuth()
    await expect(auth.signIn('a@b.com', 'pw')).resolves.toBe(session)
    expect(authApi.signInWithPassword).toHaveBeenCalledWith({ email: 'a@b.com', password: 'pw' })

    authApi.signInWithPassword.mockResolvedValueOnce({
      data: { session: null },
      error: new Error('Invalid login credentials'),
    })
    await expect(auth.signIn('a@b.com', 'bad')).rejects.toThrow('Invalid login credentials')
  })

  it('signUp flags email confirmation when no session comes back', async () => {
    authApi.signUp.mockResolvedValue({ data: { user: { id: 'u1' }, session: null }, error: null })
    const auth = await loadAuth()
    await expect(auth.signUp('a@b.com', 'secret1')).resolves.toEqual({
      session: null,
      needsConfirmation: true,
    })
    expect(authApi.signUp).toHaveBeenCalledWith({
      email: 'a@b.com',
      password: 'secret1',
      options: { emailRedirectTo: 'http://localhost:5173' },
    })
  })

  it('signUp returns the session when confirmation is off', async () => {
    const session = { access_token: 'jwt' }
    authApi.signUp.mockResolvedValue({ data: { user: { id: 'u1' }, session }, error: null })
    const auth = await loadAuth()
    await expect(auth.signUp('a@b.com', 'secret1')).resolves.toEqual({
      session,
      needsConfirmation: false,
    })
  })

  it('logout signs out of Supabase', async () => {
    authApi.signOut.mockResolvedValue({ error: null })
    const auth = await loadAuth()
    await auth.logout()
    expect(authApi.signOut).toHaveBeenCalled()
  })

  it('onAuthStateChange forwards sessions and unsubscribes', async () => {
    const unsubscribe = vi.fn()
    authApi.onAuthStateChange.mockImplementation((cb) => {
      cb('SIGNED_IN', { access_token: 'jwt' })
      return { data: { subscription: { unsubscribe } } }
    })
    const auth = await loadAuth()
    const callback = vi.fn()
    const stop = auth.onAuthStateChange(callback)
    expect(callback).toHaveBeenCalledWith({ access_token: 'jwt' })
    stop()
    expect(unsubscribe).toHaveBeenCalled()
  })
})

describe('bypass mode', () => {
  it('starts signed in with a fake token and never calls Supabase', async () => {
    const auth = await loadAuth({ bypass: 'true' })
    const token = await auth.getIdToken()
    expect(token.split('.')).toHaveLength(3)
    expect((await auth.getSession()).user.email).toBe('test@example.com')
    expect(createClient).not.toHaveBeenCalled()
  })

  it('logout then signIn toggles the session', async () => {
    const auth = await loadAuth({ bypass: '1' })
    await auth.logout()
    expect(await auth.getSession()).toBeNull()
    expect(await auth.getIdToken()).toBeNull()
    await auth.signIn('x@y.com', 'pw')
    expect(await auth.getIdToken()).toBeTruthy()
  })
})
