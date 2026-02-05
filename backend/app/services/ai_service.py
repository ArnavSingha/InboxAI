"""
AI service for email intelligence.

This module provides:
1. Natural language intent parsing
2. Email summarization
3. Reply generation
4. Email categorization
5. Daily digest generation

All AI operations use Google's Gemini for consistent, professional output.
"""
from typing import List, Optional

from app.integrations.gemini_client import complete, parse_json_response
from app.models.email import Email
from app.utils.logger import get_logger
from app.utils.errors import AIError

logger = get_logger(__name__)


# =============================================================================
# INTENT PARSING
# =============================================================================

INTENT_SYSTEM = """You are an AI assistant for an email application. Parse the user's message and extract their intent.

Available intents:
- READ_EMAILS: User wants to see/check/fetch emails
- REPLY: User wants to reply to an email
- DELETE: User wants to delete an email
- CATEGORIZE: User wants to organize/group emails
- DIGEST: User wants a summary of today's emails
- CONFIRM: User is confirming a pending action
- CANCEL: User is canceling a pending action
- HELP: User wants to know what they can do
- GREETING: User is greeting
- UNKNOWN: Cannot determine intent

Extract parameters: email_ref, reply_content, count, query.

Respond ONLY in JSON:
{"intent": "NAME", "confidence": 0.0-1.0, "params": {}}"""


async def parse_intent(message: str, has_pending_action: bool = False) -> dict:
    """
    Parse user message to extract intent and parameters.
    """
    context = ""
    if has_pending_action:
        context = "\nNote: Pending action exists. 'yes/ok' = CONFIRM, 'no/cancel' = CANCEL."

    prompt = f"{message}"

    try:
        result = await parse_json_response(
            prompt=prompt,
            system_instruction=INTENT_SYSTEM + context,
            default={"intent": "UNKNOWN", "confidence": 0, "params": {}},
        )
        logger.info(f"Parsed intent: {result.get('intent')} (confidence: {result.get('confidence', 0)})")
        return result
    except Exception:
        return {"intent": "UNKNOWN", "confidence": 0, "params": {}}


# =============================================================================
# EMAIL SUMMARIZATION
# =============================================================================

async def summarize_email(email: Email) -> str:
    """
    Generate a concise AI summary of an email.
    """
    body = email.body[:2000] if email.body else email.snippet

    prompt = f"""Summarize this email in 1-2 sentences:

From: {email.sender_name} <{email.sender_email}>
Subject: {email.subject}
Date: {email.date}

{body}

Summary:"""

    try:
        summary = await complete(
            prompt=prompt,
            system_instruction="You are an email summarizer. Be concise.",
            max_tokens=100,
            temperature=0.3,
        )
        return summary.strip()
    except AIError:
        logger.warning("AI summarization failed, using snippet")
        return email.snippet[:150] if email.snippet else "Unable to summarize."


async def summarize_emails(emails: List[Email]) -> List[str]:
    """Generate summaries for multiple emails."""
    summaries = []
    for email in emails:
        try:
            summary = await summarize_email(email)
            summaries.append(summary)
        except Exception as e:
            logger.warning(f"Failed to summarize email {email.id}: {e}")
            summaries.append(email.snippet[:150] if email.snippet else "Unable to summarize.")
    return summaries


# =============================================================================
# REPLY GENERATION
# =============================================================================

async def generate_reply(original_email: dict, instruction: str = None) -> str:
    """
    Generate a professional reply to an email.
    """
    body = original_email.get("body", original_email.get("snippet", ""))[:1500]

    if not instruction:
        instruction = "Write a polite, appropriate response"

    prompt = f"""Generate a professional email reply.

Original Email:
From: {original_email['sender_name']} <{original_email['sender_email']}>
Subject: {original_email['subject']}
Content: {body}

User's instruction: {instruction}

Reply (body only, no subject):"""

    system = """You are an email writer. Generate professional but friendly replies.
- Be concise
- Match the tone of the original
- Sign off naturally"""

    try:
        reply = await complete(prompt=prompt, system_instruction=system, max_tokens=300, temperature=0.7)
        return reply.strip()
    except AIError:
        logger.warning("AI reply generation failed")
        raise AIError("Couldn't generate a reply. Please try again or write your own.")


# =============================================================================
# EMAIL CATEGORIZATION
# =============================================================================

CATEGORIZE_SYSTEM = """Categorize emails into groups like Work, Personal, Promotions, Updates, Finance, Urgent.
Respond ONLY in JSON: {"categories": [{"name": "...", "email_indices": [1,2], "summary": "..."}]}"""


async def categorize_emails(emails: List[dict]) -> List[dict]:
    """Categorize emails into logical groups."""
    emails_text = ""
    for email in emails:
        emails_text += f"\n{email['index']}. From: {email['sender_name']}"
        emails_text += f"\n   Subject: {email['subject']}"
        emails_text += f"\n   Preview: {email.get('snippet', '')[:100]}\n"

    prompt = f"Categorize these emails:\n{emails_text}"

    try:
        result = await parse_json_response(
            prompt=prompt,
            system_instruction=CATEGORIZE_SYSTEM,
            default={"categories": []},
        )
        return result.get("categories", [])
    except Exception:
        return [{
            "name": "All Emails",
            "email_indices": [e["index"] for e in emails],
            "summary": f"{len(emails)} emails"
        }]


# =============================================================================
# DAILY DIGEST
# =============================================================================

DIGEST_SYSTEM = """Create a brief daily email digest.
Respond ONLY in JSON:
{"summary": "...", "key_emails": [{"index": 1, "reason": "..."}], "suggested_actions": ["..."]}"""


async def generate_digest(emails: List[dict]) -> dict:
    """Generate a daily email digest."""
    if not emails:
        return {
            "summary": "No emails to summarize today.",
            "key_emails": [],
            "suggested_actions": []
        }

    emails_text = ""
    for email in emails:
        emails_text += f"\n{email['index']}. From: {email['sender_name']}"
        emails_text += f"\n   Subject: {email['subject']}"
        emails_text += f"\n   Preview: {email.get('snippet', '')[:100]}\n"

    prompt = f"Create a digest for these emails:\n{emails_text}"

    try:
        result = await parse_json_response(
            prompt=prompt,
            system_instruction=DIGEST_SYSTEM,
            default={"summary": f"You have {len(emails)} emails today.", "key_emails": [], "suggested_actions": []},
        )
        return result
    except Exception:
        return {
            "summary": f"You have {len(emails)} emails today.",
            "key_emails": [],
            "suggested_actions": ["Review your inbox"]
        }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_fallback_summary(email: Email) -> str:
    """Get fallback summary when AI fails."""
    if email.snippet:
        return email.snippet[:150]
    if email.body:
        return email.body[:150]
    return f"Email from {email.sender_name} about {email.subject}"
