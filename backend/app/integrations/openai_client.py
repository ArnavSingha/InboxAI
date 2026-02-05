"""
OpenAI API client integration.

This module handles:
1. Making requests to OpenAI API
2. Retry logic for transient failures
3. Timeout handling
4. Response parsing

Uses GPT-4o-mini for cost-effective, fast responses.
"""
import json
from typing import Optional

from openai import AsyncOpenAI
from openai import APIError, APIConnectionError, RateLimitError as OpenAIRateLimitError

from app.config import get_settings
from app.utils.logger import get_logger
from app.utils.errors import AIError

logger = get_logger(__name__)
settings = get_settings()

# Initialize OpenAI client
client = AsyncOpenAI(api_key=settings.openai_api_key)

# Model to use
MODEL = "gpt-4o-mini"


async def complete(
    messages: list,
    max_tokens: int = 500,
    temperature: float = 0.7,
    response_format: Optional[dict] = None,
) -> str:
    """
    Get a completion from OpenAI.
    
    Args:
        messages: List of message dicts with role and content
        max_tokens: Maximum response tokens
        temperature: Creativity (0=deterministic, 1=creative)
        response_format: Optional JSON schema for structured output
        
    Returns:
        Generated text response
        
    Raises:
        AIError: On API failure after retries
    """
    max_retries = 2
    
    for attempt in range(max_retries + 1):
        try:
            kwargs = {
                "model": MODEL,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            
            # Add JSON response format if specified
            if response_format:
                kwargs["response_format"] = response_format
            
            response = await client.chat.completions.create(**kwargs)
            
            content = response.choices[0].message.content
            logger.info(f"OpenAI response received, tokens: {response.usage.total_tokens}")
            
            return content.strip()
            
        except OpenAIRateLimitError as e:
            logger.warning(f"OpenAI rate limited (attempt {attempt + 1})")
            if attempt < max_retries:
                import asyncio
                await asyncio.sleep(2)  # Wait before retry
                continue
            raise AIError("AI service is busy. Please try again.")
            
        except APIConnectionError as e:
            logger.error(f"OpenAI connection error: {e}")
            if attempt < max_retries:
                continue
            raise AIError("Couldn't connect to AI service. Please try again.")
            
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise AIError("AI service error. Please try again.")
            
        except Exception as e:
            logger.error(f"Unexpected OpenAI error: {e}")
            raise AIError("AI processing failed. Please try again.")


async def complete_json(
    messages: list,
    max_tokens: int = 500,
    temperature: float = 0.3,
) -> dict:
    """
    Get a JSON response from OpenAI.
    
    Uses lower temperature for more consistent JSON output.
    
    Args:
        messages: List of message dicts
        max_tokens: Maximum response tokens
        temperature: Creativity
        
    Returns:
        Parsed JSON dict
        
    Raises:
        AIError: On API failure or invalid JSON
    """
    response = await complete(
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON response: {e}")
        # Try to extract JSON from response
        try:
            # Sometimes the model wraps JSON in markdown
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except:
            pass
        raise AIError("AI returned invalid response format.")
