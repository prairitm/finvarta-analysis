"""LLM client for OpenAI API interactions."""

import sys
from typing import Optional

from langchain.memory import ConversationBufferMemory
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from openai import OpenAI

from constants import (
    CHARS_PER_TOKEN_CONSERVATIVE,
    CHARS_PER_TOKEN_PLAIN_TEXT,
    DEFAULT_TIMEOUT,
)
from tools import create_internet_search_tool
from cache import SearchCache
from config import get_cache_config


def estimate_tokens(text: str, conservative: bool = True) -> int:
    """
    Estimate token count. Uses more conservative estimate for HTML content.
    
    Args:
        text: Text to estimate tokens for
        conservative: If True, use ~2.5 chars/token (better for HTML).
                      If False, use ~4 chars/token (plain text).
        
    Returns:
        Estimated token count
    """
    chars_per_token = CHARS_PER_TOKEN_CONSERVATIVE if conservative else CHARS_PER_TOKEN_PLAIN_TEXT
    return int(len(text) / chars_per_token)


def analyze_with_llm(
    financial_data: str,
    prompt: str,
    base_url: Optional[str],
    model: str,
    api_key: str,
    timeout: float = DEFAULT_TIMEOUT,
    enable_search: bool = True,
    search_provider: str = "tavily",
    search_api_key: Optional[str] = None,
    conversation_history: Optional[list] = None,
    company_name: Optional[str] = None
) -> tuple[str, dict]:
    """
    Send financial data to an OpenAI model for analysis.
    
    Args:
        financial_data: Cleaned HTML financial data
        prompt: System prompt to use for the analysis
        base_url: Base URL for the OpenAI-compatible API (None => default)
        model: Model name to use (e.g., gpt-4o-mini)
        api_key: OpenAI API key
        timeout: Request timeout in seconds
        enable_search: Whether to enable internet search tool
        search_provider: Search provider ("tavily" or "duckduckgo")
        search_api_key: API key for search provider (Tavily)
        conversation_history: Previous conversation messages for memory
        
    Returns:
        Tuple of (analysis_response, metadata_dict) where metadata contains tool usage info
    """
    metadata = {
        "tool_calls": [],
        "search_queries": [],
        "agentic": enable_search
    }
    
    # If search is disabled, use simple non-agentic approach
    if not enable_search:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout
        ) if base_url else OpenAI(
            api_key=api_key,
            timeout=timeout
        )
        
        messages = [{"role": "system", "content": prompt}]
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": financial_data})
        
        print("Sending request to LLM (non-agentic mode)...", file=sys.stderr)
        response = client.chat.completions.create(
            model=model,
            messages=messages
        )
        print("Received response from LLM", file=sys.stderr)
        
        return response.choices[0].message.content, metadata
    
    # Agentic mode with tools and memory
    print("Initializing agentic LLM with tools and memory...", file=sys.stderr)
    
    # Initialize cache
    cache_enabled, cache_dir, cache_ttl = get_cache_config()
    cache = SearchCache(
        cache_dir=cache_dir,
        ttl_hours=cache_ttl,
        enabled=cache_enabled
    ) if cache_enabled else None
    
    if cache:
        print(f"Cache enabled: dir={cache_dir}, ttl={cache_ttl}h", file=sys.stderr)
    else:
        print("Cache disabled", file=sys.stderr)
    
    # Create LLM instance
    llm_kwargs = {
        "model": model,
        "api_key": api_key,
        "temperature": 0,
        "timeout": timeout
    }
    if base_url:
        llm_kwargs["base_url"] = base_url
    
    llm = ChatOpenAI(**llm_kwargs)
    
    # Create internet search tool with cache
    search_tool_func = create_internet_search_tool(
        provider=search_provider,
        api_key=search_api_key,
        cache=cache,
        company_name=company_name
    )
    
    # Wrap search function as LangChain tool
    from langchain_core.tools import StructuredTool
    
    # Create tool with proper description - make it very explicit
    company_context = f" for {company_name}" if company_name else ""
    search_tool = StructuredTool.from_function(
        func=search_tool_func,
        name="internet_search",
        description=(
            f"CRITICAL TOOL: Search the internet for missing financial data{company_context}. "
            "You MUST use this tool whenever you see 'Not available' or missing data in the HTML. "
            f"Examples: '{company_name or 'CompanyName'} ROCE ratio', "
            f"'{company_name or 'CompanyName'} debt equity ratio 2024', "
            f"'{company_name or 'CompanyName'} industry P/E ratio', "
            f"'{company_name or 'CompanyName'} recent news'. "
            "Always include the company name in your search query. "
            "This tool returns factual financial information that you should use to fill gaps in the HTML data. "
            "Input: A search query string containing the company name and the metric you're looking for."
        ),
        args_schema=None  # Let LangChain infer from function signature
    )
    
    tools = [search_tool]
    
    # Create memory
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )
    
    # Add conversation history to memory if provided
    if conversation_history:
        for msg in conversation_history:
            if msg.get("role") == "user":
                memory.chat_memory.add_user_message(msg.get("content", ""))
            elif msg.get("role") == "assistant":
                memory.chat_memory.add_ai_message(msg.get("content", ""))
    
    # Create agent prompt template with explicit tool usage instructions
    enhanced_prompt = (
        prompt + "\n\n"
        "IMPORTANT: You have access to the internet_search tool. "
        "Whenever you encounter missing data, 'Not available', or incomplete information in the HTML, "
        "you MUST call the internet_search tool immediately. "
        "Do not proceed with 'Not available' without first attempting to search for the information. "
        "The tool is available and ready to use - make sure you use it when needed."
    )
    
    agent_prompt = ChatPromptTemplate.from_messages([
        ("system", enhanced_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])
    
    # Create agent
    agent = create_openai_tools_agent(llm, tools, agent_prompt)
    
    # Create agent executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5,
        max_execution_time=timeout
    )
    
    # Prepare input with explicit instructions about tool usage
    company_context = f"\n\nCompany Name: {company_name}\n" if company_name else ""
    user_input = (
        f"Analyze the following financial data{company_context}"
        f"\n\nIMPORTANT: If any data is missing or marked as 'Not available' in the HTML below, "
        f"you MUST use the internet_search tool to find it. Do not skip searching for missing critical metrics. "
        f"The HTML data follows:\n\n{financial_data}"
    )
    
    print("Running agentic analysis with tool access...", file=sys.stderr)
    if company_name:
        print(f"Company name provided: {company_name}", file=sys.stderr)
    
    try:
        result = agent_executor.invoke({"input": user_input})
        analysis = result.get("output", "")
        
        # Extract tool usage information from intermediate steps
        if "intermediate_steps" in result:
            for step in result["intermediate_steps"]:
                if len(step) >= 2:
                    tool_action = step[0]
                    tool_result = step[1]
                    if hasattr(tool_action, "tool"):
                        tool_name = tool_action.tool
                        metadata["tool_calls"].append(tool_name)
                        if tool_name == "internet_search" and hasattr(tool_action, "tool_input"):
                            query = tool_action.tool_input.get("query", "") if isinstance(tool_action.tool_input, dict) else str(tool_action.tool_input)
                            metadata["search_queries"].append(query)
        
        print(f"Agent completed with {len(metadata['tool_calls'])} tool call(s)", file=sys.stderr)
        if metadata['search_queries']:
            print(f"Search queries used: {metadata['search_queries']}", file=sys.stderr)
        else:
            print("Warning: No search queries were executed. Tool may not have been invoked.", file=sys.stderr)
        
        return analysis, metadata
        
    except Exception as e:
        print(f"Error in agentic execution: {e}", file=sys.stderr)
        # Fallback to non-agentic mode
        print("Falling back to non-agentic mode...", file=sys.stderr)
        return analyze_with_llm(
            financial_data=financial_data,
            prompt=prompt,
            base_url=base_url,
            model=model,
            api_key=api_key,
            timeout=timeout,
            enable_search=False,
            conversation_history=conversation_history,
            company_name=company_name
        )

