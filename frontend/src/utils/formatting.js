/** Utility functions for formatting and data transformation. */

/**
 * Convert a key string to a human-readable format.
 * @param {string} key - The key to humanize
 * @returns {string} Humanized key
 */
export const humanizeKey = (key) =>
  key
    .replace(/[_-]/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())

/**
 * Convert a value to a string representation.
 * @param {*} value - The value to stringify
 * @returns {string} String representation of the value
 */
export const stringifyValue = (value) => {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (Array.isArray(value)) {
    return value
      .map((item, index) => `• ${stringifyValue(item) || `Item ${index + 1}`}`)
      .join('\n')
  }
  if (typeof value === 'object') {
    return Object.entries(value)
      .map(([innerKey, innerValue]) => `${humanizeKey(innerKey)}: ${stringifyValue(innerValue)}`)
      .join('\n')
  }
  return ''
}

/**
 * Convert payload data into sections for display.
 * @param {*} payload - The payload to convert
 * @returns {Array<{title: string|null, content: string}>} Array of sections
 */
export const toSections = (payload) => {
  if (!payload) return []
  if (typeof payload === 'string') {
    return payload
      .split(/\n{2,}/)
      .map((block) => block.trim())
      .filter(Boolean)
      .map((block) => ({ title: null, content: block }))
  }
  if (Array.isArray(payload)) {
    return payload.map((entry, index) => ({
      title: `Insight ${index + 1}`,
      content: stringifyValue(entry),
    }))
  }
  if (typeof payload === 'object') {
    return Object.entries(payload).map(([key, value]) => ({
      title: humanizeKey(key),
      content: stringifyValue(value),
    }))
  }
  return [{ title: null, content: String(payload) }]
}

