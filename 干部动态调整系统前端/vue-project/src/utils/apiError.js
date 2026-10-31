// DRF validation errors may be strings, lists or nested field dictionaries.
export const firstApiError = value => {
  if (typeof value === 'string') return value.trim()
  if (!value || typeof value !== 'object') return ''
  if (!Array.isArray(value) && value.detail) {
    const detail = firstApiError(value.detail)
    if (detail) return detail
  }
  for (const item of Object.values(value)) {
    const error = firstApiError(item)
    if (error) return error
  }
  return ''
}
