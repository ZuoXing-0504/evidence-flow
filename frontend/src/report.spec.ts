import { describe, expect, it } from "vitest"

import {
  formatCitationError,
  normalizeReportContent,
  renderReportMarkdown,
  reportFilename,
} from "@/report"

describe("report helpers", () => {
  it("keeps Chinese topics while removing unsafe filename characters", () => {
    expect(reportFilename('中国金融：Agent/应用*现状?')).toBe("中国金融-Agent-应用-现状.md")
    expect(reportFilename("CON")).toBe("report-CON.md")
    expect(reportFilename("   ")).toBe("research-report.md")
  })

  it("normalizes downloaded Markdown to one trailing newline", () => {
    expect(normalizeReportContent("# 报告\n\n正文\n\n")).toBe("# 报告\n\n正文\n")
  })

  it("renders Markdown without allowing raw HTML", () => {
    const rendered = renderReportMarkdown("# 标题\n\n<script>alert('xss')</script>\n\n[E1]")

    expect(rendered).toContain("<h1>标题</h1>")
    expect(rendered).not.toContain("<script>")
    expect(rendered).toContain("&lt;script&gt;")
  })

  it("localizes citation validation errors", () => {
    expect(formatCitationError("No accepted evidence is available")).toBe(
      "没有可供引用的已采纳证据",
    )
    expect(formatCitationError("Citation [E9] does not map to accepted evidence")).toBe(
      "引用 [E9] 未对应任何已采纳证据",
    )
  })
})
