#!/usr/bin/env python3
"""
Financial Analysis Script using OpenAI

This script extracts financial data from HTML content and analyzes it using
an OpenAI model configured with various analysis prompts.

Usage:
    python analysis.py --company IPL
    python analysis.py --html-file company_data.html
    python analysis.py --html-content "<html>...</html>"
"""

import os
import sys
from typing import Dict, List, Optional, Union

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
except ImportError:  # FastAPI API mode is optional
    FastAPI = None  # type: ignore
    HTTPException = None  # type: ignore
    BaseModel = None  # type: ignore

from analysis_service import perform_analysis
from config import get_env_bool, get_env_int
from constants import DEFAULT_MAX_CONTEXT, DEFAULT_MAX_QUARTERS, DEFAULT_MAX_YEARS, DEFAULT_MODEL
from prompts import DEFAULT_PROMPT, list_prompts

# FastAPI app placeholder for uvicorn mode
app = None

if FastAPI and BaseModel:
    try:
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError:
        CORSMiddleware = None

    class AnalysisRequest(BaseModel):
        """Schema for FastAPI requests."""
        html_file: Optional[str] = None
        html_content: Optional[str] = None
        company: Optional[str] = None
        cookie_header: Optional[str] = None
        base_url: Optional[str] = None
        model: Optional[str] = DEFAULT_MODEL
        api_key: Optional[str] = None
        show_stats: bool = False
        preview: bool = False
        max_years: int = DEFAULT_MAX_YEARS
        max_quarters: int = DEFAULT_MAX_QUARTERS
        sections: Optional[Union[str, List[str]]] = None
        aggressive: bool = False
        max_context: int = DEFAULT_MAX_CONTEXT
        prompt_name: Optional[str] = DEFAULT_PROMPT
        enable_search: Optional[bool] = None  # None means use config default
        search_provider: Optional[str] = None  # None means use config default
        search_api_key: Optional[str] = None  # None means use config default
        conversation_id: Optional[str] = None  # For multi-turn conversations
        conversation_history: Optional[List[Dict[str, str]]] = None  # Previous messages

    app = FastAPI(title="Finvarta Fundamental Analysis API")

    # Add custom CORS middleware that explicitly sets headers
    @app.middleware("http")
    async def add_cors_headers(request, call_next):
        response = await call_next(request)
        origin = request.headers.get("origin", "*")
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Expose-Headers"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "false"
        return response

    if CORSMiddleware:
        # Use regex pattern to allow all origins (more reliable than ["*"])
        import re
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r".*",
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
            allow_headers=["*"],
            expose_headers=["*"],
        )

    # Explicit OPTIONS handler for all routes
    @app.options("/{full_path:path}")
    async def options_handler(full_path: str):
        return {
            "status": "ok",
            "message": "CORS preflight successful"
        }

    @app.post("/analyze")
    def analyze_via_api(payload: AnalysisRequest):
        """HTTP endpoint wrapper around perform_analysis."""
        try:
            return perform_analysis(payload)
        except SystemExit as exc:
            if HTTPException is None:
                raise
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/health")
    def healthcheck():
        """Simple readiness probe."""
        return {"status": "ok"}

    @app.get("/prompts")
    def get_available_prompts():
        """List all available analysis prompts."""
        return {
            "prompts": list_prompts(),
            "default": DEFAULT_PROMPT
        }


def _serve_with_uvicorn(host: str, port: int, reload_server: bool) -> None:
    """Start the FastAPI app using uvicorn."""
    if app is None:
        print(
            "Error: FastAPI is not available. Install fastapi and pydantic to use --serve.",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        import uvicorn  # Local import keeps uvicorn optional for CLI use
    except ImportError:
        print("Error: uvicorn is not installed. Run `pip install uvicorn` to use --serve.", file=sys.stderr)
        sys.exit(1)
    uvicorn.run(app, host=host, port=port, reload=reload_server)


if __name__ == "__main__":
    default_host = os.getenv("ANALYSIS_SERVER_HOST", "0.0.0.0")
    default_port = get_env_int("ANALYSIS_SERVER_PORT", 8000)
    reload_flag = get_env_bool("ANALYSIS_SERVER_RELOAD", False)
    _serve_with_uvicorn(default_host, default_port, reload_flag)
