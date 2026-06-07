import axios, { AxiosInstance, AxiosError } from 'axios'
import { useAuth } from '@clerk/nextjs'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || ''

// Public client (no auth)
export const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

// Create an authenticated client factory (call inside components with useAuth)
export function createAuthClient(getToken: () => Promise<string | null>): AxiosInstance {
  const client = axios.create({
    baseURL: BASE_URL,
    headers: { 'Content-Type': 'application/json' },
    timeout: 60_000,
  })

  client.interceptors.request.use(async (config) => {
    const token = await getToken()
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
  })

  client.interceptors.response.use(
    (res) => res,
    (error: AxiosError) => {
      if (error.response?.status === 401) {
        window.location.href = '/sign-in'
      }
      return Promise.reject(error)
    }
  )

  return client
}

// ─── SSE streaming helper ─────────────────────────────────────────────────────

export async function* streamSSE<T>(
  url: string,
  body: unknown,
  token: string
): AsyncGenerator<T> {
  const response = await fetch(`${BASE_URL}${url}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    const err = await response.json()
    throw new Error(err.detail || 'Stream request failed')
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('No response body')

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6).trim()
        if (data === '[DONE]') return
        try {
          yield JSON.parse(data) as T
        } catch {
          // skip malformed lines
        }
      }
    }
  }
}

// ─── API helpers ──────────────────────────────────────────────────────────────

export function apiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail || error.message || 'Request failed'
  }
  return String(error)
}
