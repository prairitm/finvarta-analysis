/** Application constants and configuration. */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
export const API_URL = `${API_BASE_URL}/analyze`
export const PROMPTS_URL = `${API_BASE_URL}/prompts`

// Request timeout in milliseconds (5 minutes)
export const REQUEST_TIMEOUT_MS = 300000

// Default prompt name
export const DEFAULT_PROMPT = 'aswath-damodaran'

