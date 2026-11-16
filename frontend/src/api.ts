import type {
  AuthResponse,
  DocumentRecord,
  Evidence,
  Report,
  ResearchEvent,
  ResearchTask,
  User,
} from "@/types"

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ""
const TOKEN_KEY = "evidence-flow-token"

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message)
  }
}

function token(): string | null {
  return sessionStorage.getItem(TOKEN_KEY)
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set("Accept", "application/json")
  if (options.body) headers.set("Content-Type", "application/json")
  const accessToken = token()
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`)

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      // The status remains useful when an upstream proxy returns a non-JSON response.
    }
    throw new ApiError(detail, response.status)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const authApi = {
  login: (email: string, password: string) =>
    request<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  register: (email: string, password: string, displayName: string) =>
    request<AuthResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, display_name: displayName }),
    }),
  me: () => request<User>("/api/auth/me"),
}

export const researchApi = {
  list: () => request<{ items: ResearchTask[] }>("/api/research"),
  get: (id: string) => request<ResearchTask>(`/api/research/${id}`),
  create: (topic: string, maxIterations: number) =>
    request<ResearchTask>("/api/research", {
      method: "POST",
      body: JSON.stringify({ topic, max_iterations: maxIterations }),
    }),
  cancel: (id: string) =>
    request<ResearchTask>(`/api/research/${id}/cancel`, { method: "POST" }),
  report: (id: string) => request<Report>(`/api/research/${id}/report`),
  evidence: (id: string) => request<Evidence[]>(`/api/research/${id}/evidence`),
}

export const documentsApi = {
  list: () => request<{ items: DocumentRecord[] }>("/api/documents"),
  create: (title: string, content: string, sourceUri: string | null) =>
    request<DocumentRecord>("/api/documents", {
      method: "POST",
      body: JSON.stringify({ title, content, source_uri: sourceUri || null }),
    }),
  remove: (id: string) => request<void>(`/api/documents/${id}`, { method: "DELETE" }),
}

export async function streamResearchEvents(
  taskId: string,
  onEvent: (event: ResearchEvent) => void,
  signal: AbortSignal,
  lastEventId?: number,
): Promise<void> {
  const headers = new Headers({ Accept: "text/event-stream" })
  const accessToken = token()
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`)
  if (lastEventId) headers.set("Last-Event-ID", String(lastEventId))
  const response = await fetch(`${API_BASE}/api/research/${taskId}/events`, {
    headers,
    signal,
  })
  if (!response.ok || !response.body) {
    throw new ApiError("Could not connect to the research event stream", response.status)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value, { stream: !done }).replaceAll("\r\n", "\n")
    let boundary = buffer.indexOf("\n\n")
    while (boundary >= 0) {
      const block = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)
      const lines = block.split("\n")
      const idLine = lines.find((line) => line.startsWith("id:"))
      const dataLines = lines.filter((line) => line.startsWith("data:"))
      if (idLine && dataLines.length) {
        const data = dataLines.map((line) => line.slice(5).trimStart()).join("\n")
        const event = JSON.parse(data) as Omit<ResearchEvent, "id">
        onEvent({ ...event, id: Number(idLine.slice(3).trim()) })
      }
      boundary = buffer.indexOf("\n\n")
    }
    if (done) break
  }
}

export const session = {
  key: TOKEN_KEY,
  get: token,
  set: (value: string) => sessionStorage.setItem(TOKEN_KEY, value),
  clear: () => sessionStorage.removeItem(TOKEN_KEY),
}
