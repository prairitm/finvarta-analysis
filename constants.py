"""Application constants and default values."""

# Default values for analysis parameters
DEFAULT_MAX_YEARS = 5
DEFAULT_MAX_QUARTERS = 8
DEFAULT_MAX_CONTEXT = 4096
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT = 300.0  # 5 minutes timeout for LLM calls
DEFAULT_REQUEST_TIMEOUT = 20  # seconds for HTTP requests

# Token estimation constants
CHARS_PER_TOKEN_CONSERVATIVE = 2.5  # For HTML content
CHARS_PER_TOKEN_PLAIN_TEXT = 4.0  # For plain text

# Valid sections for HTML extraction
VALID_SECTIONS = [
    "quarters",
    "profit-loss",
    "balance-sheet",
    "cash-flow",
    "ratios",
    "shareholding",
]

# Default sections to include
DEFAULT_SECTIONS = VALID_SECTIONS.copy()

