import { describe, expect, it } from "vitest"

import { formatDuration, nodeLabel } from "@/metrics"

describe("research metrics helpers", () => {
  it("formats durations for operational scanning", () => {
    expect(formatDuration(null)).toBe("--")
    expect(formatDuration(240)).toBe("240 ms")
    expect(formatDuration(2450)).toBe("2.5 s")
    expect(formatDuration(65_000)).toBe("1m 5s")
  })

  it("localizes agent node names", () => {
    expect(nodeLabel("web_scout")).toBe("联网检索")
    expect(nodeLabel("citation_validator")).toBe("引用校验")
  })
})
