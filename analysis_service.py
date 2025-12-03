"""Analysis service orchestration logic."""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from constants import DEFAULT_MAX_CONTEXT, DEFAULT_MAX_QUARTERS, DEFAULT_MAX_YEARS, VALID_SECTIONS
from config import get_search_config
from html_extractor import extract_financial_data
from llm_client import analyze_with_llm, estimate_tokens
from prompts import DEFAULT_PROMPT, get_prompt
from screener_client import fetch_company_html


def load_html_from_file(file_path: Path) -> str:
    """Load HTML content from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file {file_path}: {e}", file=sys.stderr)
        sys.exit(1)


def resolve_api_key(cli_key: Optional[str]) -> str:
    """
    Resolve the API key to use for OpenAI calls.
    
    Priority:
        1. CLI-provided key
        2. OPENAI_API_KEY environment variable
    """
    if cli_key:
        return cli_key
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        return env_key
    print("Error: No OpenAI API key provided. Use --api-key or set OPENAI_API_KEY.", file=sys.stderr)
    sys.exit(1)


def _print_context_reduction_tips(params, include_sections: Optional[list]) -> None:
    """Suggest ways to cut down payload/context size."""
    max_years = max(1, getattr(params, "max_years", DEFAULT_MAX_YEARS))
    max_quarters = max(1, getattr(params, "max_quarters", DEFAULT_MAX_QUARTERS))
    reduced_years = max(1, max_years - 2)
    reduced_quarters = max(1, max_quarters - 4)
    suggestions = [
        f"  1. Reduce years: --max-years {max(3, reduced_years)}",
        f"  2. Reduce quarters: --max-quarters {max(4, reduced_quarters)}",
    ]
    if include_sections is None or len(include_sections) > 3:
        suggestions.append("  3. Limit sections: --sections profit-loss,balance-sheet,ratios")
    suggestions.extend(
        [
            "  4. Enable aggressive compression: --aggressive",
            "  5. Increase context limit: --max-context <new_limit>",
        ]
    )
    for line in suggestions:
        print(line, file=sys.stderr)


def perform_analysis(params) -> Dict[str, Any]:
    """
    Core analysis workflow used by the FastAPI entrypoint (reusable elsewhere).
    
    Params should expose the same attributes defined in AnalysisRequest.
    Returns a dictionary containing analysis output and metadata.
    """
    # Determine HTML source (file, inline, or Screener fetch)
    html_content: Optional[str] = None
    html_source_desc: Optional[str] = None
    cookie_header = getattr(params, "cookie_header", None) or os.getenv("SCREENER_COOKIE_HEADER")
    
    html_file_param = getattr(params, "html_file", None)
    if html_file_param:
        html_path = html_file_param if isinstance(html_file_param, Path) else Path(html_file_param)
        html_content = load_html_from_file(html_path)
        html_source_desc = f"file: {html_path}"
    elif getattr(params, "html_content", None):
        html_content = params.html_content
        html_source_desc = "inline --html-content"
    elif getattr(params, "company", None):
        if not cookie_header:
            print(
                "⚠️  No Screener cookies provided; attempting anonymous fetch (may fail for some users).",
                file=sys.stderr
            )
        html_content = fetch_company_html(params.company, cookie_header=cookie_header)
        html_source_desc = f"screener company {params.company.strip().upper()}"
    else:
        print("Error: Provide HTML input via html_file, html_content, or company parameter.", file=sys.stderr)
        raise SystemExit(1)
    
    print(f"HTML source: {html_source_desc}", file=sys.stderr)
    
    # Parse sections if provided
    include_sections = None
    sections_arg = getattr(params, "sections", None)
    if sections_arg:
        if isinstance(sections_arg, str):
            include_sections = [s.strip() for s in sections_arg.split(',')]
        elif isinstance(sections_arg, (list, tuple)):
            include_sections = [str(s).strip() for s in sections_arg]
        else:
            print("Error: --sections must be a comma-separated string or list.", file=sys.stderr)
            raise SystemExit(1)
        invalid = [s for s in include_sections if s not in VALID_SECTIONS]
        if invalid:
            print(f"Error: Invalid sections: {', '.join(invalid)}", file=sys.stderr)
            print(f"Valid sections: {', '.join(VALID_SECTIONS)}", file=sys.stderr)
            raise SystemExit(1)
    
    # Extract company name from HTML or params
    company_name = None
    if getattr(params, "company", None):
        company_name = params.company.strip().upper()
    else:
        # Try to extract from HTML
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        h1 = soup.find('h1')
        if h1:
            company_name = h1.get_text(strip=True)
    
    # Extract financial data
    print("Extracting financial data from HTML...", file=sys.stderr)
    financial_data = extract_financial_data(
        html_content,
        max_years=getattr(params, "max_years", DEFAULT_MAX_YEARS),
        max_quarters=getattr(params, "max_quarters", DEFAULT_MAX_QUARTERS),
        include_sections=include_sections,
        aggressive=getattr(params, "aggressive", False)
    )
    
    # Get prompt based on prompt_name
    prompt_name = getattr(params, "prompt_name", DEFAULT_PROMPT)
    try:
        prompt = get_prompt(prompt_name)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1)
    
    # Estimate token count (conservative for HTML content)
    system_tokens = estimate_tokens(prompt, conservative=False)
    data_tokens = estimate_tokens(financial_data, conservative=True)
    total_tokens = system_tokens + data_tokens
    
    # Warn if user-set context may exceed server limits
    max_context = getattr(params, "max_context", DEFAULT_MAX_CONTEXT)
    if max_context > 4096:
        print(
            f"⚠️  Note: --max-context {max_context} specified, but many LLM servers cap at 4096 tokens.",
            file=sys.stderr
        )
        print("   If context errors persist, lower this value or increase the server context.", file=sys.stderr)
        print(file=sys.stderr)
    
    # Show HTML size statistics if requested
    if getattr(params, "show_stats", False):
        reduction_pct = ((len(html_content) - len(financial_data)) / len(html_content) * 100) if html_content else 0
        print(f"\nHTML Size Statistics:", file=sys.stderr)
        print(f"  Original: {len(html_content):,} characters", file=sys.stderr)
        print(f"  Cleaned:  {len(financial_data):,} characters", file=sys.stderr)
        print(f"  Reduction: {reduction_pct:.1f}%", file=sys.stderr)
        print(file=sys.stderr)
    
    # Always show token estimates (critical for context management)
    print(f"Token Estimates:", file=sys.stderr)
    print(f"  System prompt: ~{system_tokens:,} tokens", file=sys.stderr)
    print(f"  Financial data: ~{data_tokens:,} tokens", file=sys.stderr)
    print(f"  Total: ~{total_tokens:,} tokens", file=sys.stderr)
    print(f"  Context limit: {max_context:,} tokens", file=sys.stderr)
    
    # Pre-flight validation
    if total_tokens > max_context:
        print(
            f"\n⚠️  WARNING: Estimated tokens ({total_tokens:,}) exceed context limit ({max_context:,})",
            file=sys.stderr
        )
        print(f"\nSuggestions to reduce size:", file=sys.stderr)
        _print_context_reduction_tips(params, include_sections)
        print(f"\nProceeding anyway... (may fail)\n", file=sys.stderr)
    elif total_tokens > max_context * 0.9:
        print(
            f"\n⚠️  WARNING: Approaching context limit ({total_tokens:,} / {max_context:,} tokens)",
            file=sys.stderr
        )
        print(file=sys.stderr)
    else:
        print(f"  Status: ✅ Within context limit", file=sys.stderr)
        print(file=sys.stderr)
    
    # Preview mode
    if getattr(params, "preview", False):
        print("=" * 80)
        print("Preview of cleaned HTML (first 2000 characters):")
        print("=" * 80)
        print(financial_data[:2000])
        if len(financial_data) > 2000:
            print(f"\n... (truncated, total length: {len(financial_data):,} characters)")
        return {
            "preview": financial_data[:2000],
            "html_source": html_source_desc,
            "token_estimates": {
                "system": system_tokens,
                "financial": data_tokens,
                "total": total_tokens,
                "context_limit": max_context,
            }
        }
    
    api_key = resolve_api_key(getattr(params, "api_key", None))
    
    # Get search configuration
    default_enable_search, default_provider, default_search_key = get_search_config()
    print(f"Default search config: enable={default_enable_search}, provider={default_provider}", file=sys.stderr)
    
    # Handle None explicitly - if enable_search is None, use the default
    enable_search_param = getattr(params, "enable_search", None)
    enable_search = enable_search_param if enable_search_param is not None else default_enable_search
    
    search_provider_param = getattr(params, "search_provider", None)
    search_provider = search_provider_param if search_provider_param is not None else default_provider
    
    search_api_key_param = getattr(params, "search_api_key", None)
    search_api_key = search_api_key_param if search_api_key_param is not None else default_search_key
    
    print(f"Final search config: enable={enable_search}, provider={search_provider}, has_api_key={bool(search_api_key)}", file=sys.stderr)
    
    # Get conversation history if provided
    conversation_history = getattr(params, "conversation_history", None)
    
    # Run analysis
    print("Sending to LLM for analysis...", file=sys.stderr)
    print(f"Search configuration: enable_search={enable_search}, provider={search_provider}", file=sys.stderr)
    if enable_search:
        print(f"Agentic mode enabled with {search_provider} search", file=sys.stderr)
    else:
        print("Agentic mode DISABLED - search will not be used", file=sys.stderr)
    try:
        analysis, metadata = analyze_with_llm(
            financial_data,
            prompt=prompt,
            base_url=getattr(params, "base_url", None),
            model=getattr(params, "model", "gpt-4o-mini"),
            api_key=api_key,
            enable_search=enable_search,
            search_provider=search_provider,
            search_api_key=search_api_key,
            conversation_history=conversation_history,
            company_name=company_name
        )
        return {
            "analysis": analysis,
            "metadata": metadata
        }
    except Exception as e:
        error_str = str(e)
        print(f"Error during LLM analysis: {e}", file=sys.stderr)
        
        # Check for context size errors
        if 'context' in error_str.lower() or 'exceed' in error_str.lower() or '400' in error_str:
            print(f"\n❌ Context size error detected!", file=sys.stderr)
            print(f"\nThe data is too large for the LLM's context window.", file=sys.stderr)
            print(f"\nTry these options to reduce size:", file=sys.stderr)
            _print_context_reduction_tips(params, include_sections)
        else:
            print("\nCheck your OpenAI credentials and network connectivity.", file=sys.stderr)
            print("  - Verify that the API key is valid and has access to the selected model.", file=sys.stderr)
            if not getattr(params, "base_url", None):
                print("  - If you are using the public OpenAI API, check https://status.openai.com/", file=sys.stderr)
            else:
                print(f"  - Custom endpoint: {getattr(params, 'base_url')}", file=sys.stderr)
        raise

