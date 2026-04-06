"""
LLM Integration for Woodchopping Handicap Predictions

This module handles communication with the Ollama API for AI-enhanced
time predictions.

Functions:
    call_ollama() - Send prompts to local Ollama instance and receive responses
    check_ollama_connection() - Check if Ollama is available (cached)
    reset_ollama_status() - Reset connection status cache
"""

import time
from typing import Optional

import requests

from config import llm_config

# Connection status cache to avoid spamming error messages
_ollama_status = {
    "available": None,  # None = unknown, True = available, False = unavailable
    "last_check": 0,
    "error_shown": False,
    "check_interval": 60,  # Re-check every 60 seconds
}


def check_ollama_connection(force: bool = False) -> bool:
    """
    Check if Ollama is available. Results are cached to avoid repeated checks.

    Args:
        force: Force a fresh check even if recently checked

    Returns:
        bool: True if Ollama is available, False otherwise
    """
    global _ollama_status

    current_time = time.time()

    # Return cached result if recent (unless forced)
    if not force and _ollama_status["available"] is not None:
        if current_time - _ollama_status["last_check"] < _ollama_status["check_interval"]:
            return _ollama_status["available"]

    # Perform connection check with short timeout
    try:
        response = requests.get(
            "http://localhost:11434/api/tags",  # Quick endpoint to check if Ollama is up
            timeout=5,
        )
        _ollama_status["available"] = response.status_code == 200
        _ollama_status["last_check"] = current_time
        _ollama_status["error_shown"] = False  # Reset error flag on successful connection
        return _ollama_status["available"]
    except Exception:
        _ollama_status["available"] = False
        _ollama_status["last_check"] = current_time
        return False


def reset_ollama_status():
    """Reset the connection status cache. Call this to force a fresh check."""
    global _ollama_status
    _ollama_status["available"] = None
    _ollama_status["last_check"] = 0
    _ollama_status["error_shown"] = False


def call_ollama(prompt: str, model: str = None, num_predict: int = None) -> Optional[str]:
    """
    Send prompt to local Ollama instance and return response.

    Features:
    - Connection status caching (avoids spamming errors)
    - Retry logic with exponential backoff
    - Single error message per session (not per call)

    Args:
        prompt: Text prompt to send to the model
        model: Ollama model name (defaults to config value)
        num_predict: Maximum tokens to generate (defaults to 50 for fast predictions)
                     Use higher values for detailed analysis responses:
                     - 50: Time predictions (single number)
                     - 200: Short analysis (3-4 sentences)
                     - 5000: Comprehensive fairness assessment (detailed multi-paragraph)

    Returns:
        Model response text, or None if error occurs

    Example:
        >>> response = call_ollama("Predict cutting time for...")
        >>> if response:
        ...     print(response)
    """
    global _ollama_status

    # Quick check: if we know Ollama is unavailable, don't even try
    if _ollama_status["available"] is False:
        current_time = time.time()
        # Only re-check after the interval
        if current_time - _ollama_status["last_check"] < _ollama_status["check_interval"]:
            return None  # Silently return None - error already shown

    if model is None:
        model = llm_config.DEFAULT_MODEL

    if num_predict is None:
        num_predict = 50  # Default for backward compatibility

    # Retry logic with exponential backoff
    max_retries = llm_config.MAX_RETRIES

    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                llm_config.OLLAMA_URL,
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Low creativity for consistent predictions
                        "num_predict": num_predict,  # Configurable response length
                    },
                },
                timeout=llm_config.TIMEOUT_SECONDS,
            )

            if response.status_code == 200:
                # Success - mark Ollama as available
                _ollama_status["available"] = True
                _ollama_status["last_check"] = time.time()
                _ollama_status["error_shown"] = False
                data = response.json()
                if not isinstance(data, dict) or "response" not in data:
                    print(f"\n[WARN] Unexpected Ollama response structure: {data}")
                    return None
                return data["response"].strip()
            else:
                # Non-200 response - might be recoverable, retry
                if attempt < max_retries:
                    time.sleep(1 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    if not _ollama_status["error_shown"]:
                        print(f"\n[WARN] Ollama error: {response.status_code}")
                        _ollama_status["error_shown"] = True
                    return None

        except requests.exceptions.ConnectionError:
            # Mark as unavailable
            _ollama_status["available"] = False
            _ollama_status["last_check"] = time.time()

            # Only show error once per session
            if not _ollama_status["error_shown"]:
                print("\n" + "=" * 60)
                print("[WARN] OLLAMA NOT AVAILABLE")
                print("=" * 60)
                print("Cannot connect to Ollama. LLM predictions will be skipped.")
                print("To enable AI predictions, run: ollama serve")
                print("System will continue with Baseline and ML predictions only.")
                print("=" * 60 + "\n")
                _ollama_status["error_shown"] = True
            return None

        except requests.exceptions.Timeout:
            # Timeout - might be recoverable, retry
            if attempt < max_retries:
                if attempt == 0:
                    print("  [Ollama timeout, retrying...]")
                time.sleep(2 * (attempt + 1))  # Longer backoff for timeouts
                continue
            else:
                if not _ollama_status["error_shown"]:
                    print(f"\n[WARN] Ollama timeout after {llm_config.TIMEOUT_SECONDS}s")
                    print("  Consider increasing TIMEOUT_SECONDS in config.py")
                    _ollama_status["error_shown"] = True
                return None

        except Exception as e:
            if attempt < max_retries:
                time.sleep(1 * (attempt + 1))
                continue
            else:
                if not _ollama_status["error_shown"]:
                    print(f"\n[WARN] Ollama error: {e}")
                    _ollama_status["error_shown"] = True
                return None

    return None
