"""Screener.in client for fetching company HTML data."""

import sys
from typing import Optional

import requests

from constants import DEFAULT_REQUEST_TIMEOUT


def parse_cookie_header(cookie_header: str) -> dict:
    """Convert a raw cookie header string into a dict for requests."""
    cookies = {}
    for part in cookie_header.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


def build_screener_headers() -> dict:
    """Return browser-like headers for screener.in requests."""
    return {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
        "referer": "https://www.screener.in/",
        "sec-ch-ua": "\"Not/A)Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"macOS\"",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }


def fetch_company_html(
    company: str,
    cookie_header: Optional[str] = None,
    timeout: int = DEFAULT_REQUEST_TIMEOUT
) -> str:
    """
    Download Screener HTML for the given company ticker.
    
    Args:
        company: Ticker/symbol as used on Screener (e.g., IPL)
        cookie_header: Raw cookie header string for authenticated access
        timeout: Request timeout in seconds
        
    Returns:
        HTML content as string
        
    Raises:
        SystemExit: If company is empty or request fails
    """
    ticker = company.strip().upper()
    if not ticker:
        print("Error: --company value cannot be empty.", file=sys.stderr)
        sys.exit(1)
    
    url = f"https://www.screener.in/company/{ticker}/"
    headers = build_screener_headers()
    cookies = parse_cookie_header(cookie_header) if cookie_header else None
    
    print(f"Fetching Screener page for {ticker}...", file=sys.stderr)
    try:
        response = requests.get(url, headers=headers, cookies=cookies, timeout=timeout)
        response.raise_for_status()
    except requests.HTTPError as http_err:
        status = http_err.response.status_code if http_err.response else "unknown"
        print(f"Error: Failed to fetch Screener page (status {status}).", file=sys.stderr)
        if status == 403:
            print(
                "Screener returned 403 (forbidden). You may need to provide authenticated cookies via --cookie-header or SCREENER_COOKIE_HEADER.",
                file=sys.stderr
            )
        elif status == 404:
            print(
                f"Screener cannot find ticker '{ticker}'. Double-check the symbol on screener.in.",
                file=sys.stderr
            )
        sys.exit(1)
    except requests.RequestException as req_err:
        print(f"Network error while fetching Screener page: {req_err}", file=sys.stderr)
        sys.exit(1)
    
    print(
        f"✅ Screener HTML fetched successfully for {ticker} ({len(response.text):,} characters).",
        file=sys.stderr
    )
    return response.text

