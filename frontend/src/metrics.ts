import type { ResearchNode } from "@/types"

const NODE_LABELS: Record<ResearchNode, string> = {
  memory_recall: "记忆召回",
  intent_router: "意图路由",
  planner: "研究规划",
  web_scout: "联网检索",
  local_scout: "本地检索",
  evidence_judge: "证据评审",
  analyst: "综合分析",
  reflect: "缺口反思",
  writer: "报告撰写",
  citation_validator: "引用校验",
  memory_commit: "记忆沉淀",
}

export function formatDuration(milliseconds: number | null): string {
  if (milliseconds === null) return "--"
  if (milliseconds < 1000) return `${milliseconds} ms`
  if (milliseconds < 60_000) return `${(milliseconds / 1000).toFixed(1)} s`
  const minutes = Math.floor(milliseconds / 60_000)
  const seconds = Math.round((milliseconds % 60_000) / 1000)
  return `${minutes}m ${seconds}s`
}

export function nodeLabel(node: ResearchNode): string {
  return NODE_LABELS[node]
}
