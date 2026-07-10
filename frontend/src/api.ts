import type { Role } from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export interface Identity {
  id?: number
  actor: string
  role: Role
  provider?: string
}

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: 'include',
  })
  const payload = await response.json().catch(() => ({ detail: '请求失败' }))
  if (!response.ok) {
    const detail = Array.isArray(payload.detail)
      ? payload.detail.map((item: { msg?: string }) => item.msg || '参数错误').join('；')
      : payload.detail || '请求失败'
    throw new ApiError(detail, response.status)
  }
  return payload as T
}
