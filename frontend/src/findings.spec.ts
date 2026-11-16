import { describe, expect, it } from "vitest"

import { confidenceLabel, evidenceLabel, summarizeFindings } from "@/findings"
import type { Evidence, Finding } from "@/types"

const findings: Finding[] = [
  {
    id: "f1",
    claim: "结论一",
    supporting_evidence_ids: ["e1"],
    opposing_evidence_ids: [],
    confidence: 0.8,
  },
  {
    id: "f2",
    claim: "结论二",
    supporting_evidence_ids: ["e2"],
    opposing_evidence_ids: ["e3"],
    confidence: 0.6,
  },
]

describe("finding helpers", () => {
  it("summarizes confidence and conflicts", () => {
    expect(summarizeFindings(findings)).toEqual({ averageConfidence: 0.7, conflictCount: 1 })
  })

  it("uses readable Chinese confidence levels", () => {
    expect(confidenceLabel(0.82)).toBe("高 · 82%")
    expect(confidenceLabel(0.55)).toBe("中 · 55%")
    expect(confidenceLabel(0.3)).toBe("低 · 30%")
  })

  it("maps domain evidence ids to citations", () => {
    const evidence = [{ domain_id: "e1", citation_id: "E2", title: "监管报告" }] as Evidence[]
    expect(evidenceLabel(evidence, "e1")).toBe("[E2] 监管报告")
    expect(evidenceLabel(evidence, "missing")).toBe("未映射证据")
  })
})
