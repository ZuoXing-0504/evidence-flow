import MarkdownIt from "markdown-it"

const markdown = new MarkdownIt({ html: false, linkify: true, typographer: true })
const RESERVED_WINDOWS_NAMES = /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i

export function renderReportMarkdown(content: string): string {
  return markdown.render(content)
}

export function reportFilename(topic: string): string {
  let stem = topic
    .trim()
    .replace(/[<>:"/\\|?*：／＼＊？＂＜＞｜\u0000-\u001f]/g, "-")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^[. -]+|[. -]+$/g, "")
    .slice(0, 80)

  if (!stem) stem = "research-report"
  if (RESERVED_WINDOWS_NAMES.test(stem)) stem = `report-${stem}`
  return `${stem}.md`
}

export function normalizeReportContent(content: string): string {
  return `${content.trimEnd()}\n`
}

export function formatCitationError(error: string): string {
  if (error === "No accepted evidence is available") return "没有可供引用的已采纳证据"
  if (error === "The report contains no evidence citations") return "报告中没有证据引用"
  const match = /^Citation \[(E\d+)] does not map to accepted evidence$/.exec(error)
  return match ? `引用 [${match[1]}] 未对应任何已采纳证据` : error
}

export function downloadMarkdownReport(topic: string, content: string): void {
  const blob = new Blob([normalizeReportContent(content)], {
    type: "text/markdown;charset=utf-8",
  })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = reportFilename(topic)
  anchor.click()
  URL.revokeObjectURL(url)
}
