"""Prompt registry for financial analysis prompts."""

from typing import List

from .aswath_damodaran import PROMPT as ASWATH_DAMODARAN_PROMPT
from .warren_buffet import PROMPT as WARREN_BUFFET_PROMPT

# Registry mapping prompt names to their prompt strings
PROMPTS = {
    "aswath-damodaran": ASWATH_DAMODARAN_PROMPT,
    "warren-buffet": WARREN_BUFFET_PROMPT,
}

# Default prompt name
DEFAULT_PROMPT = "aswath-damodaran"


def get_prompt(prompt_name: str) -> str:
    """
    Get a prompt by name.
    
    Args:
        prompt_name: Name of the prompt (e.g., "aswath-damodaran")
        
    Returns:
        The prompt string
        
    Raises:
        ValueError: If prompt_name is not found in registry
    """
    if prompt_name not in PROMPTS:
        available = ", ".join(sorted(PROMPTS.keys()))
        raise ValueError(
            f"Unknown prompt '{prompt_name}'. Available prompts: {available}"
        )
    return PROMPTS[prompt_name]


def list_prompts() -> List[str]:
    """
    List all available prompt names.
    
    Returns:
        List of prompt names sorted alphabetically
    """
    return sorted(PROMPTS.keys())

