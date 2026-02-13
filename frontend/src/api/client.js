import { getIdToken } from '../auth/auth'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

async function parseJsonSafe(response) {
  const text = await response.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

export async function apiFetch(path, options = {}) {
  if (!API_BASE_URL) {
    throw new Error('Missing VITE_API_BASE_URL')
  }

  const token = await getIdToken()
  if (!token) {
    throw new Error('Not authenticated')
  }

  const headers = new Headers(options.headers || {})
  headers.set('Authorization', `Bearer ${token}`)

  const hasBody = options.body !== undefined
  if (hasBody && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  })

  const data = await parseJsonSafe(response)

  if (!response.ok) {
    const message = data?.error || data?.message || response.statusText
    throw new Error(message)
  }

  return data
}

export function apiGet(path) {
  return apiFetch(path, { method: 'GET' })
}

export function apiPost(path, body) {
  return apiFetch(path, { method: 'POST', body: JSON.stringify(body) })
}

export function apiPut(path, body) {
  return apiFetch(path, { method: 'PUT', body: JSON.stringify(body) })
}

export function apiDelete(path) {
  return apiFetch(path, { method: 'DELETE' })
}
