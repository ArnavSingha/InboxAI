"""
Gemini AI client for InboxAI.

Handles all AI operations using Google's Gemini API.
"""
import json
import re
from typing import Optional
import google.generativeai as genai

from app.config import get_settings
from app.utils.logger import get_logger
from app.utils.errors import AIError

logger = get_logger(__name__)

# Configure Gemini
settings = get_settings()
if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)


def get_model(model_name: str = "gemini-1.5-flash"):
    """Get a Gemini model instance."""
    return genai.GenerativeModel(model_name)


async def complete(
    prompt: str,
    system_instruction: Optional[str] = None,
    max_tokens: int = 500,
    temperature: float = 0.7,
    json_mode: bool = False,
) -> str:
    """
    Generate a completion using Gemini.

    Args:
        prompt: The user prompt
        system_instruction: Optional system instruction
        max_tokens: Maximum tokens in response
        temperature: Creativity parameter (0-1)
        json_mode: If True, expect JSON response

    Returns:
        The generated text response

    Raises:
        AIError: If Gemini API fails
    """
    try:
        # Create model with system instruction
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system_instruction,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )

        # Generate response
        response = model.generate_content(prompt)

        if not response.text:
            raise AIError("Empty response from Gemini")

        content = response.text.strip()

        # If JSON mode, try to extract JSON from response
        if json_mode:
            content = extract_json(content)

        logger.debug(f"Gemini response: {content[:100]}...")
        return content

    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise AIError(f"AI service unavailable: {str(e)}")


def extract_json(text: str) -> str:
    """Extract JSON from a response that might have markdown formatting."""
    # Try to find JSON in markdown code blocks
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if json_match:
        return json_match.group(1).strip()

    # Try to find raw JSON object or array
    json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
    if json_match:
        return json_match.group(1).strip()

    return text


async def parse_json_response(
    prompt: str,
    system_instruction: Optional[str] = None,
    default: Optional[dict] = None,
) -> dict:
    """
    Get a JSON response from Gemini.

    Args:
        prompt: The user prompt
        system_instruction: Optional system instruction
        default: Default value if parsing fails

    Returns:
        Parsed JSON as dictionary
    """
    try:
        response = await complete(
            prompt=prompt,
            system_instruction=system_instruction,
            json_mode=True,
        )

        return json.loads(response)

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON from Gemini: {e}")
        return default or {}

    except AIError:
        return default or {}
