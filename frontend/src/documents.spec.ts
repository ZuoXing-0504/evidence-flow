import { describe, expect, it } from "vitest"

import { documentFileError, formatFileSize } from "@/documents"

describe("document upload helpers", () => {
  it("accepts supported knowledge files", () => {
    expect(documentFileError(new File(["研究资料"], "memo.md"))).toBe("")
    expect(documentFileError(new File(["pdf"], "report.PDF"))).toBe("")
  })

  it("rejects unsupported, empty, and oversized files", () => {
    expect(documentFileError(new File(["value"], "data.csv"))).toContain("仅支持")
    expect(documentFileError(new File([], "empty.txt"))).toBe("文件内容为空")
    const large = new File([new Uint8Array(10 * 1024 * 1024 + 1)], "large.txt")
    expect(documentFileError(large)).toBe("文件不能超过 10 MB")
  })

  it("formats file sizes for display", () => {
    expect(formatFileSize(720)).toBe("720 B")
    expect(formatFileSize(2048)).toBe("2 KB")
    expect(formatFileSize(1_572_864)).toBe("1.5 MB")
  })
})
