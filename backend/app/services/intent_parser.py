"""
Intent Parser - Natural language command understanding.

This module provides:
1. Intent definitions with confidence thresholds
2. AI-powered intent parsing via OpenAI
3. Rule-based fallback parsing for common patterns
4. Safety checks and confirmation requirements
5. Entity extraction (email references, reply content)

Intents:
- READ_EMAILS: View inbox emails
- REPLY: Generate or send a reply
- DELETE: Remove an email
- CATEGORIZE: Group emails by type
- DIGEST: Get daily summary
- CONFIRM: Confirm pending action
- CANCEL: Cancel pending action
- HELP: Get help information
- GREETING: Respond to hello
- UNKNOWN: Unrecognized intent
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List
import re

from app.services.ai_service import parse_intent as ai_parse_intent
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Intent(Enum):
    """Supported user intents."""
    READ_EMAILS = "READ_EMAILS"
    REPLY = "REPLY"
    DELETE = "DELETE"
    CATEGORIZE = "CATEGORIZE"
    DIGEST = "DIGEST"
    CONFIRM = "CONFIRM"
    CANCEL = "CANCEL"
    HELP = "HELP"
    GREETING = "GREETING"
    UNKNOWN = "UNKNOWN"


@dataclass
class ParsedIntent:
    """Result of intent parsing."""
    intent: Intent
    confidence: float
    params: dict
    requires_confirmation: bool = False
    confirmation_message: str = ""
    
    def is_destructive(self) -> bool:
        """Check if this intent performs a destructive action."""
        return self.intent in [Intent.DELETE]
    
    def is_send_action(self) -> bool:
        """Check if this intent sends something."""
        return self.intent in [Intent.REPLY]


# Confidence thresholds
CONFIDENCE_THRESHOLD_HIGH = 0.85    # High confidence - proceed automatically
CONFIDENCE_THRESHOLD_MEDIUM = 0.6   # Medium - proceed with caution
CONFIDENCE_THRESHOLD_LOW = 0.4      # Low - ask for clarification

# Actions that ALWAYS require confirmation
ALWAYS_CONFIRM = [Intent.DELETE, Intent.REPLY]


# =============================================================================
# RULE-BASED PATTERNS (Fast fallback)
# =============================================================================

INTENT_PATTERNS = {
    Intent.READ_EMAILS: [
        r'\b(show|check|read|get|fetch|see|view|display|list|open)\b.*\b(email|inbox|mail|messages?)\b',
        r'\b(what|any|new)\b.*\b(email|mail|inbox)\b',
        r'^(emails?|inbox|mail)$',
        r'\bmy\s+(emails?|inbox|mail)\b',
    ],
    Intent.REPLY: [
        r'\breply\b',
        r'\brespond\b',
        r'\bsend\s+(a\s+)?response\b',
        r'\banswer\b.*\bemail\b',
        r'\bwrite\s+back\b',
    ],
    Intent.DELETE: [
        r'\bdelete\b',
        r'\bremove\b',
        r'\btrash\b',
        r'\bget\s+rid\s+of\b',
        r'\bdiscard\b',
    ],
    Intent.CATEGORIZE: [
        r'\bcategorize\b',
        r'\bgroup\b',
        r'\borganize\b',
        r'\bsort\b',
        r'\bclassify\b',
    ],
    Intent.DIGEST: [
        r'\bdigest\b',
        r'\bsummary\b.*\b(inbox|email|day|today)\b',
        r'\btoday.?s\s+(emails?|summary)\b',
        r'\bdaily\s+(digest|summary|report)\b',
        r'\bwhat.?s\s+(new|happening|important)\b',
    ],
    Intent.CONFIRM: [
        r'^(yes|yeah|yep|yup|sure|ok|okay|confirm|do\s+it|send\s+it|proceed|go\s+ahead)$',
        r'^(y|yes)\s*[.!]?$',
        r'\bconfirm(ed)?\b',
        r'\bapproved?\b',
    ],
    Intent.CANCEL: [
        r'^(no|nope|nah|cancel|stop|abort|nevermind|never\s+mind)$',
        r'^n$',
        r'\bdon.?t\b',
        r'\bcancel\b',
    ],
    Intent.HELP: [
        r'^help$',
        r'\bwhat\s+can\s+you\s+do\b',
        r'\bhow\s+(do|does)\s+(this|it)\s+work\b',
        r'\bcommands?\b',
        r'\bfeatures?\b',
    ],
    Intent.GREETING: [
        r'^(hi|hello|hey|greetings|howdy|good\s+(morning|afternoon|evening))[\s!.]*$',
    ],
}

# Email reference patterns
EMAIL_REF_PATTERNS = {
    "index": [
        r'#(\d+)',                      # #1, #2
        r'\bemail\s*(\d+)\b',           # email 1, email2
        r'\bnumber\s*(\d+)\b',          # number 1
        r'^(\d+)$',                     # just "1"
        r'\b(first|second|third|fourth|fifth|last)\b',  # ordinals
    ],
    "sender": [
        r'\bfrom\s+(\w+)\b',            # from John
        r'\b(\w+).?s\s+email\b',        # John's email
        r'\bthe\s+(\w+)\s+one\b',       # the LinkedIn one
    ],
    "subject": [
        r'\babout\s+(.+)',              # about meeting
        r'\bregarding\s+(.+)',          # regarding project
    ],
}

# Reply content extraction patterns
REPLY_CONTENT_PATTERNS = [
    r'reply:\s*["\']?(.+?)["\']?$',             # reply: content (explicit colon)
    r'reply\s+(?!to\b)["\']?(.+?)["\']?$',      # reply content (no colon, avoid "reply to")
    r'respond\s+with[:\s]+["\']?(.+?)["\']?$',  # respond with: content
    r'say[:\s]+["\']?(.+?)["\']?$',             # say: content
    r'tell\s+them[:\s]+["\']?(.+?)["\']?$',     # tell them: content
]


def rule_based_parse(message: str) -> Optional[ParsedIntent]:
    """
    Fast rule-based intent parsing.
    
    Checks patterns before calling AI for simple commands.
    
    Args:
        message: User's message
        
    Returns:
        ParsedIntent if pattern matches, None otherwise
    """
    message_lower = message.lower().strip()
    
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                # Extract parameters
                params = extract_params(message_lower, intent)
                
                return ParsedIntent(
                    intent=intent,
                    confidence=0.9,  # High confidence for rule matches
                    params=params,
                    requires_confirmation=intent in ALWAYS_CONFIRM,
                )
    
    return None


def extract_params(message: str, intent: Intent) -> dict:
    """
    Extract parameters from message based on intent.
    
    Args:
        message: User's message (lowercase)
        intent: Detected intent
        
    Returns:
        Dict of extracted parameters
    """
    params = {}
    
    # Extract email reference
    email_ref = extract_email_reference(message)
    if email_ref:
        params["email_ref"] = email_ref
    
    # Extract reply content for REPLY intent
    if intent == Intent.REPLY:
        reply_content = extract_reply_content(message)
        if reply_content:
            params["reply_content"] = reply_content
    
    # Extract count for READ_EMAILS
    if intent == Intent.READ_EMAILS:
        count_match = re.search(r'(\d+)\s+emails?', message)
        if count_match:
            params["count"] = int(count_match.group(1))
    
    return params


def extract_email_reference(message: str) -> Optional[str]:
    """
    Extract email reference from message.
    
    Supports:
    - Index: "#1", "email 2", "first"
    - Sender: "from John", "the LinkedIn one"
    - Subject: "about meeting"
    
    Returns:
        Reference string or None
    """
    message_lower = message.lower()
    
    # Check index patterns
    for pattern in EMAIL_REF_PATTERNS["index"]:
        match = re.search(pattern, message_lower)
        if match:
            return match.group(1) if match.groups() else match.group(0)
    
    # Check sender patterns
    for pattern in EMAIL_REF_PATTERNS["sender"]:
        match = re.search(pattern, message_lower)
        if match:
            return match.group(1)
    
    # Check subject patterns
    for pattern in EMAIL_REF_PATTERNS["subject"]:
        match = re.search(pattern, message_lower)
        if match:
            return match.group(1)
    
    return None


def extract_reply_content(message: str) -> Optional[str]:
    """
    Extract the content user wants to include in reply.
    
    Examples:
        "reply to #1: thanks!" → "thanks!"
        "respond with 'I accept'" → "I accept"
    """
    for pattern in REPLY_CONTENT_PATTERNS:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # Check for content after colon
    if ":" in message:
        parts = message.split(":", 1)
        if len(parts) == 2 and len(parts[1].strip()) > 2:
            return parts[1].strip()
    
    return None


async def parse_message(
    message: str,
    has_pending_action: bool = False,
) -> ParsedIntent:
    """
    Parse user message to extract intent and parameters.
    
    Uses rule-based parsing first for speed, falls back to AI.
    
    Args:
        message: User's natural language input
        has_pending_action: Whether there's a pending confirmation
        
    Returns:
        ParsedIntent with intent, confidence, params
        
    Examples:
        >>> await parse_message("show my emails")
        ParsedIntent(intent=READ_EMAILS, confidence=0.95, params={})
        
        >>> await parse_message("reply to #2: thanks for the update!")
        ParsedIntent(intent=REPLY, confidence=0.9, params={"email_ref": "2", "reply_content": "thanks for the update!"})
        
        >>> await parse_message("delete the email from LinkedIn")
        ParsedIntent(intent=DELETE, confidence=0.85, params={"email_ref": "LinkedIn"}, requires_confirmation=True)
        
        >>> await parse_message("yes")  # with pending action
        ParsedIntent(intent=CONFIRM, confidence=0.95, params={})
    """
    # Handle confirmation/cancel first when there's a pending action
    if has_pending_action:
        quick_check = rule_based_parse(message)
        if quick_check and quick_check.intent in [Intent.CONFIRM, Intent.CANCEL]:
            return quick_check
    
    # Try rule-based parsing first (fast)
    rule_result = rule_based_parse(message)
    if rule_result and rule_result.confidence >= CONFIDENCE_THRESHOLD_HIGH:
        logger.info(f"Rule-based parse: {rule_result.intent.value}")
        return rule_result
    
    # Fall back to AI parsing for complex messages
    try:
        ai_result = await ai_parse_intent(message, has_pending_action)
        
        intent_str = ai_result.get("intent", "UNKNOWN")
        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.UNKNOWN
        
        confidence = ai_result.get("confidence", 0.5)
        params = ai_result.get("params", {})
        
        # Merge with any rule-extracted params
        if rule_result:
            params = {**rule_result.params, **params}
        
        parsed = ParsedIntent(
            intent=intent,
            confidence=confidence,
            params=params,
            requires_confirmation=intent in ALWAYS_CONFIRM,
        )
        
        logger.info(f"AI parse: {parsed.intent.value} (confidence: {confidence})")
        return parsed
        
    except Exception as e:
        logger.warning(f"AI parsing failed: {e}")
        
        # Return rule result if available, otherwise unknown
        if rule_result:
            return rule_result
        
        return ParsedIntent(
            intent=Intent.UNKNOWN,
            confidence=0.0,
            params={},
        )


def build_confirmation_message(intent: Intent, email_info: dict) -> str:
    """
    Build a confirmation message for destructive actions.
    
    Args:
        intent: The action intent
        email_info: Dict with email details
        
    Returns:
        Human-readable confirmation prompt
    """
    sender = email_info.get("sender_name", "Unknown")
    subject = email_info.get("subject", "(No Subject)")
    
    if intent == Intent.DELETE:
        return f"Are you sure you want to delete this email?\n\n**From:** {sender}\n**Subject:** {subject}\n\nReply 'yes' to confirm or 'no' to cancel."
    
    elif intent == Intent.REPLY:
        reply_preview = email_info.get("reply_preview", "")
        return f"Ready to send this reply to {sender}?\n\n---\n{reply_preview}\n---\n\nReply 'yes' to send or 'no' to cancel."
    
    return "Confirm this action? Reply 'yes' or 'no'."


def get_low_confidence_message(intent: Intent) -> str:
    """
    Get clarification message for low confidence parses.
    
    Args:
        intent: Best guess intent
        
    Returns:
        Clarification question
    """
    messages = {
        Intent.READ_EMAILS: "Did you want to see your emails?",
        Intent.REPLY: "Would you like to reply to an email? If so, which one?",
        Intent.DELETE: "Did you want to delete an email? Please specify which one.",
        Intent.CATEGORIZE: "Would you like me to organize your emails by category?",
        Intent.DIGEST: "Would you like a summary of today's emails?",
        Intent.UNKNOWN: "I'm not sure what you'd like to do. Try:\n• 'Show my emails'\n• 'Reply to #1'\n• 'Delete email from John'\n• 'Organize my inbox'",
    }
    
    return messages.get(intent, messages[Intent.UNKNOWN])


def get_help_message() -> str:
    """Get help message with available commands."""
    return """Here's what I can do:

**📬 Read Emails**
• "Show my emails"
• "Check my inbox"
• "Any new mail?"

**✉️ Reply to Emails**
• "Reply to #1"
• "Respond to the email from John"
• "Reply to #2: Thanks for the update!"

**🗑️ Delete Emails**
• "Delete #3"
• "Remove the spam email"
• "Delete email from LinkedIn"

**📊 Organize**
• "Categorize my inbox"
• "Group emails by type"

**📋 Daily Digest**
• "Today's summary"
• "What's important today?"

**Tips:**
• Reference emails by number (#1, #2) after viewing them
• You can mention sender names or subjects
• I'll always ask for confirmation before sending or deleting"""


def get_greeting_response() -> str:
    """Get a friendly greeting response."""
    return "Hello! 👋 I'm your email assistant. I can help you read, reply to, and manage your emails. Type 'show my emails' to get started, or 'help' to see all commands."
