"""OpenRouter API client for making LLM requests."""

import asyncio
import httpx
from typing import List, Dict, Any, Optional
from .config import OPENROUTER_API_KEY, OPENROUTER_API_URL


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via OpenRouter API.

    Args:
        model: OpenRouter model identifier
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'content' and optional 'reasoning_details', or None if failed
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            message = data['choices'][0]['message']

            return {
                'content': message.get('content'),
                'reasoning_details': message.get('reasoning_details')
            }

    except Exception as e:
        print(f"Error querying model {model}: {e}")
        return None


async def query_persona(
    model: str,
    system_prompt: str,
    user_message: str,
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query a model with a specific persona system prompt.

    Args:
        model: OpenRouter model identifier
        system_prompt: The persona's system prompt
        user_message: The user's message/question
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'content', or None if failed
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    return await query_model(model, messages, timeout)


async def query_personas_parallel(
    model: str,
    personas: List[Dict[str, Any]],
    user_message: str
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query the same model with multiple personas in parallel.

    Args:
        model: OpenRouter model identifier (same for all)
        personas: List of persona dicts with 'id', 'name', 'system_prompt'
        user_message: The user's message to send to each persona

    Returns:
        Dict mapping persona id to response dict (or None if failed)
    """
    tasks = [
        query_persona(model, p["system_prompt"], user_message)
        for p in personas
    ]

    responses = await asyncio.gather(*tasks)

    return {
        persona["id"]: response
        for persona, response in zip(personas, responses)
    }
