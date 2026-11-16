export function parseApiDate(value: string): Date {
  const includesTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)
  return new Date(includesTimezone ? value : `${value}Z`)
}

export function formatApiDate(value: string): string {
  return parseApiDate(value).toLocaleString()
}

export function formatApiDay(value: string): string {
  return parseApiDate(value).toLocaleDateString()
}
