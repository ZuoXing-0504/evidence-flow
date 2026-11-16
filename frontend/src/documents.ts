export const MAX_DOCUMENT_FILE_BYTES = 10 * 1024 * 1024
export const DOCUMENT_FILE_ACCEPT = ".txt,.md,.markdown,.pdf,text/plain,text/markdown,application/pdf"

const SUPPORTED_SUFFIXES = [".txt", ".md", ".markdown", ".pdf"]

export function documentFileError(file: File): string {
  const name = file.name.toLocaleLowerCase()
  if (!SUPPORTED_SUFFIXES.some((suffix) => name.endsWith(suffix))) {
    return "仅支持 TXT、Markdown 和 PDF 文件"
  }
  if (file.size > MAX_DOCUMENT_FILE_BYTES) return "文件不能超过 10 MB"
  if (!file.size) return "文件内容为空"
  return ""
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
