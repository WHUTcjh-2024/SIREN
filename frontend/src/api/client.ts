export class ApiError extends Error {
  constructor(message: string, public status: number, public payload?: unknown) {
    super(message)
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const response = await fetch(path, { ...init, headers, credentials: 'include' })
  let payload: any = null
  try { payload = await response.json() } catch { /* non-JSON response */ }
  if (!response.ok) {
    const message = payload?.detail || payload?.message || `请求失败 (${response.status})`
    throw new ApiError(message, response.status, payload)
  }
  return payload as T
}

export async function* readNdjson(response: Response): AsyncGenerator<any> {
  if (!response.ok || !response.body) throw new ApiError(`分析请求失败 (${response.status})`, response.status)
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) if (line.trim()) yield JSON.parse(line)
    if (done) break
  }
  if (buffer.trim()) yield JSON.parse(buffer)
}
