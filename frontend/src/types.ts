export type ResearchStatus =
  | "queued"
  | "running"
  | "completed"
  | "completed_with_warnings"
  | "failed"
  | "cancelled"

export type ResearchNode =
  | "memory_recall"
  | "intent_router"
  | "planner"
  | "web_scout"
  | "local_scout"
  | "evidence_judge"
  | "analyst"
  | "reflect"
  | "writer"
  | "citation_validator"
  | "memory_commit"

export interface User {
  id: string
  email: string
  display_name: string
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: "bearer"
  expires_in: number
  user: User
}

export interface ResearchTask {
  id: string
  user_id: string
  topic: string
  status: ResearchStatus
  iteration: number
  max_iterations: number
  cancel_requested: boolean
  warnings: string[]
  errors: string[]
  created_at: string
  updated_at: string
  started_at: string | null
  completed_at: string | null
}

export interface Evidence {
  domain_id: string
  source_type: "web" | "local" | "memory"
  title: string
  url: string | null
  content: string
  relevance_score: number | null
  credibility_score: number | null
  decision: "pending" | "accepted" | "rejected" | "duplicate"
  citation_id: string | null
  published_at: string | null
  retrieved_at: string
}

export interface Report {
  task_id: string
  content: string
  citation_errors: string[]
  created_at: string
  updated_at: string
}

export interface Finding {
  id: string
  claim: string
  supporting_evidence_ids: string[]
  opposing_evidence_ids: string[]
  confidence: number
}

export interface NodeMetric {
  node: ResearchNode
  run_count: number
  duration_ms: number
}

export interface ResearchMetrics {
  total_duration_ms: number | null
  queue_duration_ms: number | null
  iteration_count: number
  agent_run_count: number
  evidence_count: number
  finding_count: number
  citation_count: number
  evidence_by_source: Record<"web" | "local" | "memory", number>
  node_metrics: NodeMetric[]
}

export interface ResearchEvent {
  id: number
  task_id: string
  node: ResearchNode | null
  type:
    | "task_created"
    | "node_started"
    | "node_progress"
    | "node_completed"
    | "node_failed"
    | "task_completed"
    | "task_failed"
    | "task_cancelled"
  payload: Record<string, unknown>
  created_at: string
}

export interface DocumentRecord {
  id: string
  user_id: string
  title: string
  source_uri: string | null
  content_hash: string
  status: "indexing" | "indexed" | "failed"
  chunk_count: number
  error: string | null
  created_at: string
  updated_at: string
}
