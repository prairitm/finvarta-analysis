"""Search results cache with 24-hour TTL."""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import fcntl  # For file locking on Unix


def normalize_company_name(company_name: str) -> str:
    """
    Normalize company name for consistent cache keys.
    
    Args:
        company_name: Company name string
        
    Returns:
        Normalized company name (uppercase, trimmed)
    """
    if not company_name:
        return ""
    # Convert to uppercase and strip whitespace
    normalized = company_name.strip().upper()
    # Remove common suffixes/prefixes that might vary
    normalized = normalized.replace(" LIMITED", "").replace(" LTD", "")
    normalized = normalized.replace(" INCORPORATED", "").replace(" INC", "")
    return normalized.strip()


class SearchCache:
    """File-based cache for search results with TTL."""
    
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        ttl_hours: int = 24,
        enabled: bool = True
    ):
        """
        Initialize search cache.
        
        Args:
            cache_dir: Directory for cache file (default: ./cache)
            ttl_hours: Time-to-live in hours (default: 24)
            enabled: Whether caching is enabled (default: True)
        """
        self.enabled = enabled
        self.ttl_hours = ttl_hours
        
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            # Default to ./cache relative to project root
            self.cache_dir = Path(__file__).parent.parent / "cache"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "search_cache.json"
        self.lock_file = self.cache_dir / "search_cache.lock"
        
        # Load existing cache on initialization
        self._cache_data: Dict[str, Any] = {}
        if self.enabled:
            self._load_cache()
            self._cleanup_expired_entries()
    
    def _load_cache(self) -> None:
        """Load cache from file."""
        if not self.cache_file.exists():
            self._cache_data = {}
            return
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                self._cache_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load cache file: {e}", file=sys.stderr)
            print("Starting with empty cache.", file=sys.stderr)
            self._cache_data = {}
    
    def _save_cache(self) -> None:
        """Save cache to file with atomic write and locking."""
        if not self.enabled:
            return
        
        try:
            # Create backup of existing cache
            if self.cache_file.exists():
                backup_file = self.cache_file.with_suffix('.json.bak')
                try:
                    import shutil
                    shutil.copy2(self.cache_file, backup_file)
                except Exception:
                    pass  # Backup failure is not critical
            
            # Write to temporary file first (atomic write)
            temp_file = self.cache_file.with_suffix('.json.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache_data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            temp_file.replace(self.cache_file)
            
            # Remove backup if write succeeded
            backup_file = self.cache_file.with_suffix('.json.bak')
            if backup_file.exists():
                try:
                    backup_file.unlink()
                except Exception:
                    pass
            
        except IOError as e:
            print(f"Warning: Failed to save cache file: {e}", file=sys.stderr)
    
    def _acquire_lock(self):
        """Acquire file lock for cache operations."""
        if not self.lock_file.exists():
            self.lock_file.touch()
        return open(self.lock_file, 'w')
    
    def _is_cache_valid(self, timestamp_str: str) -> bool:
        """
        Check if cache entry is still valid.
        
        Args:
            timestamp_str: ISO format timestamp string
            
        Returns:
            True if cache is valid (less than TTL hours old)
        """
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            age = datetime.now() - timestamp
            return age < timedelta(hours=self.ttl_hours)
        except (ValueError, TypeError):
            return False
    
    def get_cached_result(self, company_name: str, query: str) -> Optional[str]:
        """
        Get cached search result if available and valid.
        
        Args:
            company_name: Normalized company name
            query: Search query string
            
        Returns:
            Cached result if found and valid, None otherwise
        """
        if not self.enabled:
            return None
        
        normalized_company = normalize_company_name(company_name)
        if not normalized_company:
            return None
        
        if normalized_company not in self._cache_data:
            return None
        
        company_data = self._cache_data[normalized_company]
        
        # Check if cache entry is still valid
        timestamp_str = company_data.get("timestamp")
        if not timestamp_str or not self._is_cache_valid(timestamp_str):
            # Cache expired, remove it
            del self._cache_data[normalized_company]
            self._save_cache()
            return None
        
        # Check if this specific query is cached
        searches = company_data.get("searches", {})
        if query in searches:
            return searches[query]
        
        return None
    
    def set_cached_result(self, company_name: str, query: str, result: str) -> None:
        """
        Store search result in cache.
        
        Args:
            company_name: Normalized company name
            query: Search query string
            result: Search result string
        """
        if not self.enabled:
            return
        
        normalized_company = normalize_company_name(company_name)
        if not normalized_company:
            return
        
        # Initialize company entry if it doesn't exist
        if normalized_company not in self._cache_data:
            self._cache_data[normalized_company] = {
                "timestamp": datetime.now().isoformat(),
                "searches": {}
            }
        
        # Update timestamp to now (refresh TTL)
        self._cache_data[normalized_company]["timestamp"] = datetime.now().isoformat()
        
        # Store the search result
        self._cache_data[normalized_company]["searches"][query] = result
        
        # Save cache
        self._save_cache()
    
    def _cleanup_expired_entries(self) -> None:
        """Remove expired cache entries."""
        if not self.enabled:
            return
        
        expired_companies = []
        for company_name, company_data in self._cache_data.items():
            timestamp_str = company_data.get("timestamp")
            if not timestamp_str or not self._is_cache_valid(timestamp_str):
                expired_companies.append(company_name)
        
        for company in expired_companies:
            del self._cache_data[company]
        
        if expired_companies:
            print(f"Cleaned up {len(expired_companies)} expired cache entries", file=sys.stderr)
            self._save_cache()
    
    def get_all_cached_queries(self, company_name: str) -> Dict[str, str]:
        """
        Get all cached queries for a company (if cache is valid).
        
        Args:
            company_name: Normalized company name
            
        Returns:
            Dictionary of query -> result for valid cache entries
        """
        if not self.enabled:
            return {}
        
        normalized_company = normalize_company_name(company_name)
        if normalized_company not in self._cache_data:
            return {}
        
        company_data = self._cache_data[normalized_company]
        timestamp_str = company_data.get("timestamp")
        
        if not timestamp_str or not self._is_cache_valid(timestamp_str):
            return {}
        
        return company_data.get("searches", {}).copy()

