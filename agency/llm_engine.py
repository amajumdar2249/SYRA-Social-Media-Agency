# -*- coding: utf-8 -*-
"""
Multi-LLM Engine — 3-tier fallback with retry logic.
OpenRouter (GPT-4o) → DeepSeek → Gemini

Features:
  - Exponential backoff on failures (2s, 4s, 8s)
  - Per-provider error tracking
  - Structured logging (no print())
"""

import os
import time
from dotenv import load_dotenv
from openai import OpenAI
from google import genai

from agency.logger import get_logger
from agency.config import (
    MAX_TOKENS, DEFAULT_TEMPERATURE,
    LLM_RETRY_ATTEMPTS, LLM_RETRY_BASE_DELAY
)

load_dotenv()
log = get_logger("llm_engine")

# ============================================================
# CLIENT INITIALIZATION
# ============================================================
_openrouter_key = os.getenv("OPENROUTER_API_KEY")
_deepseek_key = os.getenv("DEEPSEEK_API_KEY")

openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=_openrouter_key
) if _openrouter_key else None

deepseek_client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key=_deepseek_key
) if _deepseek_key else None

gemini_clients = []
for env_key in ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"]:
    key = os.getenv(env_key)
    if key:
        gemini_clients.append(genai.Client(api_key=key))

# Track provider health
_provider_errors = {"openrouter": 0, "deepseek": 0, "gemini": 0}


def _call_with_retry(provider_name: str, call_fn, max_retries: int = LLM_RETRY_ATTEMPTS) -> str:
    """
    Call an LLM provider with exponential backoff.
    Returns the response text or raises the last exception.
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            result = call_fn()
            _provider_errors[provider_name] = 0  # Reset on success
            return result
        except Exception as e:
            last_error = e
            _provider_errors[provider_name] += 1
            delay = LLM_RETRY_BASE_DELAY * (2 ** attempt)
            log.warning(f"{provider_name} attempt {attempt+1}/{max_retries} failed: {e}. Retrying in {delay}s...")
            time.sleep(delay)

    raise last_error


def call_llm(prompt: str, temperature: float = DEFAULT_TEMPERATURE, max_tokens: int = MAX_TOKENS) -> str:
    """
    3-tier fallback LLM call with retry logic.

    Order: OpenRouter (GPT-4o) → DeepSeek → Gemini
    Each provider gets 3 retry attempts with exponential backoff.

    Args:
        prompt: The text prompt to send
        temperature: Creativity level (0.0 - 1.0)
        max_tokens: Maximum response length

    Returns:
        Generated text string. Empty string on total failure.
    """
    # 1. OpenRouter (GPT-4o)
    if openrouter_client:
        try:
            def _openrouter_call():
                c = openrouter_client.chat.completions.create(
                    model="openai/gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return c.choices[0].message.content.strip()

            result = _call_with_retry("openrouter", _openrouter_call)
            log.debug(f"OpenRouter responded ({len(result)} chars)")
            return result
        except Exception as e:
            log.warning(f"OpenRouter exhausted all retries: {e}. Falling back to DeepSeek.")

    # 2. DeepSeek
    if deepseek_client:
        try:
            def _deepseek_call():
                c = deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return c.choices[0].message.content.strip()

            result = _call_with_retry("deepseek", _deepseek_call)
            log.debug(f"DeepSeek responded ({len(result)} chars)")
            return result
        except Exception as e:
            log.warning(f"DeepSeek exhausted all retries: {e}. Falling back to Gemini.")

    # 3. Gemini Fallback (try each key)
    for i, client in enumerate(gemini_clients):
        try:
            def _gemini_call(c=client):
                r = c.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                return r.text.strip()

            result = _call_with_retry("gemini", _gemini_call, max_retries=1)
            log.debug(f"Gemini key {i+1} responded ({len(result)} chars)")
            return result
        except Exception as e:
            log.warning(f"Gemini key {i+1} failed: {e}")

    log.error("ALL LLM providers failed. Returning empty response.")
    return ""


def get_engine_status() -> dict:
    """Returns the current health status of all LLM providers."""
    return {
        "openrouter": {
            "available": openrouter_client is not None,
            "consecutive_errors": _provider_errors["openrouter"]
        },
        "deepseek": {
            "available": deepseek_client is not None,
            "consecutive_errors": _provider_errors["deepseek"]
        },
        "gemini": {
            "available": len(gemini_clients) > 0,
            "keys_configured": len(gemini_clients),
            "consecutive_errors": _provider_errors["gemini"]
        }
    }
