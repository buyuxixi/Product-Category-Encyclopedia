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
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
      credentials: 'include',
    })
  } catch (error) {
    throw new ApiError(`网络异常：${(error as Error).message || '无法连接服务器'}`, 0)
  }
  const payload = await response.json().catch(() => ({ detail: '请求失败' }))
  if (!response.ok) {
    const detail = Array.isArray(payload.detail)
      ? payload.detail.map((item: { msg?: string }) => item.msg || '参数错误').join('；')
      : payload.detail || '请求失败'
    throw new ApiError(detail, response.status)
  }
  return payload as T
}

export type SseChatEvent =
  | { event: 'text-delta'; data: { delta?: string; textDelta?: string } }
  | { event: 'done'; data: { content?: string } }
  | { event: 'error'; data: { message?: string } }

/** 消费 POST SSE：每条 `data: {...}` 回调一次；遇到 `[DONE]` 结束。 */
export async function apiStreamChat(
  path: string,
  body: unknown,
  onEvent: (event: SseChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify(body),
      credentials: 'include',
      signal,
    })
  } catch (e) {
    if (signal?.aborted) throw e
    throw new ApiError(`网络异常：${(e as Error).message || '无法连接服务器'}`, 0)
  }

  if (!response.ok) {
    const raw = await response.text().catch(() => '')
    let detail = ''
    try {
      const payload = JSON.parse(raw) as { detail?: unknown }
      detail = Array.isArray(payload.detail)
        ? payload.detail.map((item: { msg?: string }) => item.msg || '参数错误').join('；')
        : typeof payload.detail === 'string'
          ? payload.detail
          : ''
    } catch {
      detail = raw.slice(0, 120)
    }
    throw new ApiError(detail || `请求失败（HTTP ${response.status}）`, response.status)
  }
  if (!response.body) throw new ApiError('浏览器不支持流式响应', 0)

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n')
    buffer = parts.pop() || ''
    for (const raw of parts) {
      const line = raw.trimEnd()
      if (!line.startsWith('data:')) continue
      const data = line.slice(5).trim()
      if (!data) continue
      if (data === '[DONE]') return
      try {
        onEvent(JSON.parse(data) as SseChatEvent)
      } catch {
        // 忽略残缺 JSON（流式切分边界）
      }
    }
  }
}
