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
        if not settings.gemini_api_key:
            raise AIError("Gemini API key not configured in .env")

        # List of models to try in order of preference
        candidates = [
            "gemini-flash-latest",     # Alias for latest Flash model
            "gemini-2.0-flash",        # Confirmed available for user
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-pro",
        ]

        last_error = None
        
        for model_name in candidates:
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_instruction,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=max_tokens,
                        temperature=temperature,
                    ),
                )

                # Generate response asynchronously
                logger.info(f"Attempting generation with model: {model_name}")
                response = await model.generate_content_async(prompt)
                
                # Check for valid candidates and parts
                if not response.candidates:
                    raise AIError("No candidates returned from Gemini")

                candidate = response.candidates[0]
                finish_reason = candidate.finish_reason

                # Handle specific finish reasons if no text
                if not candidate.content.parts:
                    if finish_reason == 2: # MAX_TOKENS
                         raise AIError(f"Response truncated (Max Tokens reached) with no content. Model: {model_name}")
                    if finish_reason == 3: # SAFETY
                         raise AIError(f"Content blocked by safety filters ({model_name})")
                    if finish_reason == 4: # RECITATION
                         raise AIError(f"Content blocked: Recitation ({model_name})")
                    
                    # Fallback for other empty responses
                    raise AIError(f"Empty response (Finish Reason: {finish_reason}) from {model_name}")
                
                # Safe to access text now
                try:
                    content = response.text.strip()
                except ValueError:
                    # In case .text fails despite checks
                    content = candidate.content.parts[0].text.strip() if candidate.content.parts else ""

                if not content:
                     raise AIError("Received empty text content")
                
                # If JSON mode, try to extract JSON from response
                if json_mode:
                    content = extract_json(content)

                logger.debug(f"Gemini response: {content[:100]}...")
                return content  # Success!
                
            except Exception as e:
                error_str = str(e)
                # If 404 (Not Found) or 400 (Not Supported), try next model
                if "404" in error_str or "not found" in error_str.lower():
                    logger.warning(f"Model {model_name} failed (Not Found), trying next...")
                    last_error = e
                    continue
                # If safety block, stop trying (content specific)
                if "blocked" in error_str.lower():
                    raise AIError(f"Content blocked by safety filters ({model_name})")
                
                # Other errors - fatal
                raise e
        
        # If all failed
        raise last_error or AIError("All AI models failed")


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
