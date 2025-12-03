"""Configuration and environment variable management."""

import os
import sys
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore


PROJECT_ROOT = Path(__file__).resolve().parent


def load_environment() -> None:
    """Load environment variables from .env file."""
    if load_dotenv:
        load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)
    else:
        _load_env_from_file(PROJECT_ROOT / ".env")


def _load_env_from_file(env_path: Path) -> None:
    """Basic .env loader when python-dotenv is unavailable."""
    if not env_path.is_file():
        return
    try:
        with env_path.open("r", encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    except OSError as exc:
        print(f"Warning: Unable to read {env_path}: {exc}", file=sys.stderr)


def get_env_bool(var_name: str, default: bool = False) -> bool:
    """Read boolean values from environment variables."""
    value = os.getenv(var_name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def get_env_int(var_name: str, default: int) -> int:
    """Read integer values from environment variables."""
    value = os.getenv(var_name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_env_str(var_name: str, default: Optional[str] = None) -> Optional[str]:
    """Read string values from environment variables."""
    return os.getenv(var_name, default)


# Search configuration defaults
DEFAULT_ENABLE_INTERNET_SEARCH = True
DEFAULT_SEARCH_PROVIDER = "tavily"  # Falls back to "duckduckgo" if Tavily API key not available

# Cache configuration defaults
DEFAULT_ENABLE_CACHE = True
DEFAULT_CACHE_TTL_HOURS = 24
DEFAULT_CACHE_DIR = "./cache"


def get_search_config() -> tuple[bool, str, Optional[str]]:
    """
    Get internet search configuration.
    
    Returns:
        Tuple of (enable_search, provider, api_key)
    """
    enable_search = get_env_bool("ENABLE_INTERNET_SEARCH", DEFAULT_ENABLE_INTERNET_SEARCH)
    provider = get_env_str("SEARCH_PROVIDER", DEFAULT_SEARCH_PROVIDER) or DEFAULT_SEARCH_PROVIDER
    api_key = get_env_str("TAVILY_API_KEY")
    
    return enable_search, provider, api_key


def get_cache_config() -> tuple[bool, str, int]:
    """
    Get cache configuration.
    
    Returns:
        Tuple of (enabled, cache_dir, ttl_hours)
    """
    enabled = get_env_bool("ENABLE_CACHE", DEFAULT_ENABLE_CACHE)
    cache_dir = get_env_str("CACHE_DIR", DEFAULT_CACHE_DIR) or DEFAULT_CACHE_DIR
    ttl_hours = get_env_int("CACHE_TTL_HOURS", DEFAULT_CACHE_TTL_HOURS)
    
    return enabled, cache_dir, ttl_hours


# Load environment variables on module import
load_environment()

