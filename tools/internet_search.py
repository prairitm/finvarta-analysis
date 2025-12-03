"""Internet search tool for financial analysis agent."""

import os
import re
import sys
from typing import Any, Optional

from langchain_core.tools import ToolException

try:
    from langchain_community.tools import DuckDuckGoSearchRun
except ImportError:
    DuckDuckGoSearchRun = None

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None


def _search_with_tavily(query: str, api_key: str, max_results: int = 5) -> str:
    """Search using Tavily API."""
    if TavilyClient is None:
        raise ImportError("tavily-python is not installed")
    
    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_answer=True,
            include_raw_content=False
        )
        
        results = []
        if response.get("answer"):
            results.append(f"Answer: {response['answer']}")
        
        if response.get("results"):
            for i, result in enumerate(response["results"], 1):
                title = result.get("title", "No title")
                url = result.get("url", "")
                content = result.get("content", "")
                results.append(f"\n{i}. {title}\n   URL: {url}\n   {content[:300]}...")
        
        return "\n".join(results) if results else "No results found."
    except Exception as e:
        raise ToolException(f"Tavily search failed: {str(e)}")


def _search_with_duckduckgo(query: str, max_results: int = 5) -> str:
    """Search using DuckDuckGo (no API key required)."""
    if DuckDuckGoSearchRun is None:
        raise ImportError("langchain-community is not installed or DuckDuckGoSearchRun is not available")
    try:
        search = DuckDuckGoSearchRun()
        result = search.run(query)
        return result if result else "No results found."
    except Exception as e:
        raise ToolException(f"DuckDuckGo search failed: {str(e)}")


def _extract_company_name_from_query(query: str, default_company: Optional[str] = None) -> Optional[str]:
    """
    Extract company name from search query.
    
    Args:
        query: Search query string
        default_company: Default company name if extraction fails
        
    Returns:
        Extracted company name or default_company
    """
    if default_company:
        return default_company
    
    # Try to extract company name from query
    # Common patterns: "CompanyName metric", "CompanyName financial data", etc.
    # Split by common words and take first significant word/phrase
    query_lower = query.lower()
    
    # Remove common prefixes/suffixes
    query_clean = re.sub(r'^(what is|find|search for|get|show me)\s+', '', query_lower, flags=re.IGNORECASE)
    
    # Split by common financial/metric keywords
    parts = re.split(r'\s+(roce|roe|pe|p/e|debt|equity|ratio|financial|ratios|benchmark|news|recent|2024|2023)', query_clean, flags=re.IGNORECASE)
    
    if parts and parts[0]:
        # Take first part and clean it up
        company_part = parts[0].strip()
        # Remove common words
        company_part = re.sub(r'\b(the|a|an|for|of|in|on|at|to|from)\b', '', company_part, flags=re.IGNORECASE)
        company_part = company_part.strip()
        
        if company_part and len(company_part) > 2:
            return company_part.upper()
    
    return default_company


def create_internet_search_tool(
    provider: str = "tavily",
    api_key: Optional[str] = None,
    cache: Optional[Any] = None,
    company_name: Optional[str] = None
) -> callable:
    """
    Create an internet search tool for the agent.
    
    Args:
        provider: Search provider ("tavily" or "duckduckgo")
        api_key: API key for Tavily (required if provider is "tavily")
        cache: SearchCache instance for caching results (optional)
        company_name: Default company name for cache key (optional)
        
    Returns:
        LangChain tool function for internet search
    """
    provider = provider.lower()
    
    if provider == "tavily":
        if not api_key:
            api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            print(
                "Warning: TAVILY_API_KEY not found. Falling back to DuckDuckGo.",
                file=sys.stderr
            )
            provider = "duckduckgo"
    
    if provider == "tavily" and api_key:
        def tavily_search(query: str) -> str:
            """Search the internet for financial information, company data, industry benchmarks, or recent news.
            
            Use this tool when:
            - HTML data is missing or incomplete
            - You need industry benchmarks or peer comparisons
            - You need recent news or events about the company
            - You need additional context about the company's business
            
            Args:
                query: Search query string (e.g., "Reliance Industries financial ratios 2024")
                
            Returns:
                Search results with relevant information
            """
            # CRITICAL: Check cache FIRST before any internet search - match by company name only
            # Prioritize passed company_name over extraction from query
            from cache import normalize_company_name
            
            extracted_company = company_name if company_name else _extract_company_name_from_query(query, None)
            
            if cache and extracted_company:
                # Normalize company name for consistent cache lookup
                normalized_company = normalize_company_name(extracted_company)
                print(f"Checking cache for company: '{normalized_company}' (from '{extracted_company}')", file=sys.stderr)
                
                # Check if we have ANY cached data for this company (company name match only)
                all_cached = cache.get_all_cached_queries(normalized_company)
                if all_cached:
                    # Return all cached data for the company (combine all cached queries)
                    print(f"✓ Cache HIT for company '{normalized_company}' - found {len(all_cached)} cached queries", file=sys.stderr)
                    print(f"  Cached queries: {', '.join(list(all_cached.keys())[:5])}", file=sys.stderr)
                    
                    # Combine all cached results
                    combined_results = []
                    for cached_query, cached_result in all_cached.items():
                        combined_results.append(f"=== Cached: {cached_query} ===\n{cached_result}")
                    
                    result = "\n\n".join(combined_results)
                    
                    # Also cache this new query with the combined result for future use
                    cache.set_cached_result(normalized_company, query, result)
                    return result
                else:
                    print(f"✗ Cache MISS - No cached data for company '{normalized_company}'", file=sys.stderr)
            
            # Only perform internet search if cache miss
            print(f"→ Performing internet search for: '{query[:60]}...'", file=sys.stderr)
            result = _search_with_tavily(query, api_key)
            
            # Store in cache
            if cache and extracted_company:
                normalized_company = normalize_company_name(extracted_company)
                cache.set_cached_result(normalized_company, query, result)
                print(f"Cached result for company '{normalized_company}'", file=sys.stderr)
            
            return result
        
        return tavily_search
    else:
        def duckduckgo_search(query: str) -> str:
            """Search the internet for financial information, company data, industry benchmarks, or recent news.
            
            Use this tool when:
            - HTML data is missing or incomplete
            - You need industry benchmarks or peer comparisons
            - You need recent news or events about the company
            - You need additional context about the company's business
            
            Args:
                query: Search query string (e.g., "Reliance Industries financial ratios 2024")
                
            Returns:
                Search results with relevant information
            """
            # CRITICAL: Check cache FIRST before any internet search - match by company name only
            # Prioritize passed company_name over extraction from query
            from cache import normalize_company_name
            
            extracted_company = company_name if company_name else _extract_company_name_from_query(query, None)
            
            if cache and extracted_company:
                # Normalize company name for consistent cache lookup
                normalized_company = normalize_company_name(extracted_company)
                print(f"Checking cache for company: '{normalized_company}' (from '{extracted_company}')", file=sys.stderr)
                
                # Check if we have ANY cached data for this company (company name match only)
                all_cached = cache.get_all_cached_queries(normalized_company)
                if all_cached:
                    # Return all cached data for the company (combine all cached queries)
                    print(f"✓ Cache HIT for company '{normalized_company}' - found {len(all_cached)} cached queries", file=sys.stderr)
                    print(f"  Cached queries: {', '.join(list(all_cached.keys())[:5])}", file=sys.stderr)
                    
                    # Combine all cached results
                    combined_results = []
                    for cached_query, cached_result in all_cached.items():
                        combined_results.append(f"=== Cached: {cached_query} ===\n{cached_result}")
                    
                    result = "\n\n".join(combined_results)
                    
                    # Also cache this new query with the combined result for future use
                    cache.set_cached_result(normalized_company, query, result)
                    return result
                else:
                    print(f"✗ Cache MISS - No cached data for company '{normalized_company}'", file=sys.stderr)
            
            # Only perform internet search if cache miss
            print(f"→ Performing internet search for: '{query[:60]}...'", file=sys.stderr)
            result = _search_with_duckduckgo(query)
            
            # Store in cache
            if cache and extracted_company:
                normalized_company = normalize_company_name(extracted_company)
                cache.set_cached_result(normalized_company, query, result)
                print(f"Cached result for company '{normalized_company}'", file=sys.stderr)
            
            return result
        
        return duckduckgo_search

