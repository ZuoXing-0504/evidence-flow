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
const API_ERROR_MESSAGES: Record<string, string> = {
  "Invalid or missing access token": "登录状态已失效，请重新登录",
  "Email is already registered": "该邮箱已注册",
  "Invalid email or password": "邮箱或密码错误",
  "Document not found": "文档不存在",
  "This document content is already registered": "相同内容的文档已存在",
  "Document vector indexing failed": "文档向量索引失败",
  "Document vectors could not be deleted": "无法删除文档向量",
  "Unsupported document type": "仅支持 TXT、Markdown 和 PDF 文件",
  "Document file is too large": "文件不能超过 10 MB",
  "Document is not valid UTF-8 text": "文本文件必须使用 UTF-8 编码",
  "Document has no extractable text": "文件中没有足够的可提取文字",
  "Extracted document text is too large": "文件提取后的文字超过 100 万字符",
  "Encrypted PDF is not supported": "暂不支持加密 PDF",
  "PDF could not be read": "PDF 文件损坏或无法读取",
  "Research task not found": "研究任务不存在",
  "Research worker is unavailable": "研究任务处理服务暂不可用",
  "Task is already terminal": "任务已经结束",
  "Active research task cannot be deleted": "进行中的研究任务无法删除",
  "Report is not ready": "报告尚未生成",
  "Last-Event-ID must be a non-negative integer": "事件游标必须是非负整数",
}

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
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json")
  }
  const accessToken = token()
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`)

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!response.ok) {
    let detail = `请求失败（状态码 ${response.status}）`
    try {
      const body = (await response.json()) as { detail?: unknown }
      if (typeof body.detail === "string") {
        detail = API_ERROR_MESSAGES[body.detail] ?? body.detail
      } else if (Array.isArray(body.detail)) {
        detail = "提交内容不符合要求，请检查后重试"
      }
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
  remove: (id: string) =>
    request<void>(`/api/research/${id}`, { method: "DELETE" }),
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
  upload: (file: File, title: string | null) => {
    const body = new FormData()
    body.append("file", file)
    if (title) body.append("title", title)
    return request<DocumentRecord>("/api/documents/upload", { method: "POST", body })
  },
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
    throw new ApiError("无法连接研究任务事件流", response.status)
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
