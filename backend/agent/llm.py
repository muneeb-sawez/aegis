"""AEGIS LiteLLM Wrapper (M6).

Abstracts LLM invocations with strict timeouts and automatic fallback chaining:
Configured Provider (Gemini / Groq) -> Ollama (if configured) -> Fallback Rules.
Docs: docs/02-CONTRACTS.md & .agent/rules/01-architecture-and-contracts.md.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
import litellm

from backend.config import settings
from backend.agent.fallback_rules import run_fallback_rules

logger = logging.getLogger("aegis.agent.llm")

# Silence noisy litellm verbose logging
litellm.suppress_debug_info = True


def call_llm(
    messages: list[dict[str, str]],
    context: dict[str, Any],
    timeout: float = 10.0,
    model_override: Optional[str] = None,
) -> str:
    """Execute LLM call across the fallback chain with strict per-call timeout.

    Chain:
    1. Configured provider (Gemini / Groq from backend/config.py)
    2. Local Ollama (if OLLAMA_BASE_URL is configured)
    3. Deterministic Fallback Rules (run_fallback_rules)

    Args:
        messages: List of chat messages (e.g. system + user prompt).
        context: Active graph context dictionary (used for fallback rules).
        timeout: Timeout in seconds for each network call (default: 10.0s).
        model_override: Optional model name to override settings.LLM_MODEL.

    Returns:
        JSON string response from either LLM or fallback rules.
    """
    model = model_override or settings.LLM_MODEL

    # Determine credentials based on provider
    api_key: Optional[str] = None
    if settings.LLM_PROVIDER.lower() == "gemini":
        api_key = settings.GEMINI_API_KEY
    elif settings.LLM_PROVIDER.lower() == "groq":
        api_key = settings.GROQ_API_KEY

    # 1. Primary Attempt: Configured Provider
    try:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "timeout": timeout,
        }
        if api_key:
            kwargs["api_key"] = api_key

        logger.info(f"Calling primary LLM provider '{settings.LLM_PROVIDER}' with model '{model}' (timeout={timeout}s)")
        response = litellm.completion(**kwargs)
        content = response.choices[0].message.content or ""
        if content.strip():
            return content.strip()
    except Exception as e:
        logger.warning(f"Primary LLM provider call failed ({e}). Attempting next provider in chain.")

    # 2. Secondary Attempt: Local Ollama (if provider is ollama or explicitly selected)
    if settings.OLLAMA_BASE_URL and settings.LLM_PROVIDER.lower() == "ollama":
        try:
            ollama_model = "ollama/llama3"
            logger.info(f"Calling fallback Ollama provider at '{settings.OLLAMA_BASE_URL}' (timeout={timeout}s)")
            response = litellm.completion(
                model=ollama_model,
                api_base=settings.OLLAMA_BASE_URL,
                messages=messages,
                timeout=timeout,
            )
            content = response.choices[0].message.content or ""
            if content.strip():
                return content.strip()
        except Exception as e:
            logger.warning(f"Ollama fallback call failed ({e}). Falling back to deterministic rules.")

    # 3. Final Fallback: Deterministic Rules Engine
    logger.info("Executing deterministic fallback rules engine.")
    fallback_result = run_fallback_rules(context)
    return fallback_result.model_dump_json()
