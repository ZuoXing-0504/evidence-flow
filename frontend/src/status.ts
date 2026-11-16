import type { ResearchStatus } from "@/types"

export type DisplayStatus = ResearchStatus | "indexing" | "indexed"

const STATUS_LABELS: Record<DisplayStatus, string> = {
  queued: "排队中",
  running: "进行中",
  completed: "已完成",
  completed_with_warnings: "完成（有警告）",
  failed: "失败",
  cancelled: "已取消",
  indexing: "索引中",
  indexed: "已索引",
}

export function statusLabel(status: DisplayStatus): string {
  return STATUS_LABELS[status]
}
