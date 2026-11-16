import type { Evidence, Finding } from "@/types"

export interface FindingSummary {
  averageConfidence: number
  conflictCount: number
}

export function summarizeFindings(findings: Finding[]): FindingSummary {
  if (!findings.length) return { averageConfidence: 0, conflictCount: 0 }
  return {
    averageConfidence:
      findings.reduce((total, finding) => total + finding.confidence, 0) / findings.length,
    conflictCount: findings.filter((finding) => finding.opposing_evidence_ids.length > 0).length,
  }
}

export function confidenceLabel(value: number): string {
  const percentage = Math.round(value * 100)
  if (value >= 0.75) return `高 · ${percentage}%`
  if (value >= 0.5) return `中 · ${percentage}%`
  return `低 · ${percentage}%`
}

export function evidenceLabel(evidence: Evidence[], id: string): string {
  const item = evidence.find((candidate) => candidate.domain_id === id)
  return item?.citation_id ? `[${item.citation_id}] ${item.title}` : "未映射证据"
}
