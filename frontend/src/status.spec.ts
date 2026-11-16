import { describe, expect, it } from "vitest"

import { statusLabel } from "@/status"

describe("status labels", () => {
  it("maps research and indexing statuses to Chinese", () => {
    expect(statusLabel("queued")).toBe("排队中")
    expect(statusLabel("completed_with_warnings")).toBe("完成（有警告）")
    expect(statusLabel("indexed")).toBe("已索引")
  })
})
