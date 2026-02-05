"""
Chat Service - Main orchestrator for chat interactions.

This module ties together:
1. Intent parsing (intent_parser)
2. Email operations (email_service)
3. AI features (ai_service)
4. Session state (session_service)

It handles the full lifecycle of a chat message:
User message → Parse intent → Execute action → Return response
"""
from typing import Optional

from app.models.chat import ChatResponse, EmailSummary, DraftReply
from app.services.intent_parser import (
    parse_message, Intent, ParsedIntent,
    build_confirmation_message, get_help_message, get_greeting_response,
    get_low_confidence_message, CONFIDENCE_THRESHOLD_LOW,
)
from app.services.email_service import EmailService
from app.services.ai_service import (
    summarize_emails, generate_reply, categorize_emails, generate_digest,
)
from app.services.session_service import update_session
from app.utils.logger import get_logger
from app.utils.errors import EmailNotFoundError, AIError, GmailError

logger = get_logger(__name__)


class ChatService:
    """
    Chat service orchestrating user interactions.
    
    Usage:
        service = ChatService(session)
        response = await service.process_message("show my emails")
    """
    
    def __init__(self, session: dict):
        """
        Initialize chat service with user session.
        
        Args:
            session: User session dict with tokens, cache, pending actions
        """
        self.session = session
        self.email_service = EmailService(session)
    
    async def process_message(self, message: str) -> ChatResponse:
        """
        Process a user message and return appropriate response.
        
        Flow:
        1. Check for pending confirmation
        2. Parse intent from message
        3. Validate confidence level
        4. Execute action based on intent
        5. Return formatted response
        
        Args:
            message: User's natural language input
            
        Returns:
            ChatResponse with message, type, and optional data
        """
        # Check if there's a pending action awaiting confirmation
        has_pending = self.session.get("pending_action") is not None
        
        # Parse the message
        parsed = await parse_message(message, has_pending_action=has_pending)
        
        logger.info(f"Processing: intent={parsed.intent.value}, confidence={parsed.confidence}")
        
        # Handle low confidence
        if parsed.confidence < CONFIDENCE_THRESHOLD_LOW and parsed.intent == Intent.UNKNOWN:
            return ChatResponse(
                message=get_low_confidence_message(parsed.intent),
                type="text",
            )
        
        # Route to appropriate handler
        try:
            return await self._handle_intent(parsed)
        except EmailNotFoundError as e:
            return ChatResponse(
                message=e.message,
                type="error",
            )
        except AIError as e:
            return ChatResponse(
                message=e.message,
                type="error",
            )
        except GmailError as e:
            return ChatResponse(
                message=e.message,
                type="error",
            )
        except Exception as e:
            logger.error(f"Unexpected error processing message: {e}")
            return ChatResponse(
                message="Something went wrong. Please try again.",
                type="error",
            )
    
    async def _handle_intent(self, parsed: ParsedIntent) -> ChatResponse:
        """Route intent to appropriate handler."""
        handlers = {
            Intent.READ_EMAILS: self._handle_read_emails,
            Intent.REPLY: self._handle_reply,
            Intent.DELETE: self._handle_delete,
            Intent.CATEGORIZE: self._handle_categorize,
            Intent.DIGEST: self._handle_digest,
            Intent.CONFIRM: self._handle_confirm,
            Intent.CANCEL: self._handle_cancel,
            Intent.HELP: self._handle_help,
            Intent.GREETING: self._handle_greeting,
            Intent.UNKNOWN: self._handle_unknown,
        }
        
        handler = handlers.get(parsed.intent, self._handle_unknown)
        return await handler(parsed)
    
    # =========================================================================
    # INTENT HANDLERS
    # =========================================================================
    
    async def _handle_read_emails(self, parsed: ParsedIntent) -> ChatResponse:
        """Handle READ_EMAILS intent - fetch and display emails."""
        count = parsed.params.get("count", 5)
        query = parsed.params.get("query")
        
        # Fetch emails from Gmail
        emails = await self.email_service.fetch_emails(count=count, query=query)
        
        if not emails:
            msg = "No emails found matching your search." if query else "Your inbox is empty! 📭"
            return ChatResponse(
                message=msg,
                type="text",
            )
        
        # Generate AI summaries
        try:
            summaries = await summarize_emails(emails)
        except Exception as e:
            logger.warning(f"AI summarization failed: {e}")
            summaries = [e.snippet[:100] for e in emails]
        
        # Format for response
        email_summaries = self.email_service.format_emails_for_chat(emails, summaries)
        
        intro = f"Here are the {len(emails)} most recent emails about '{query}':" if query else f"Here are your {len(emails)} most recent emails:"
        
        return ChatResponse(
            message=intro,
            type="emails",
            data=[s.model_dump() for s in email_summaries],
        )
    
    async def _handle_reply(self, parsed: ParsedIntent) -> ChatResponse:
        """Handle REPLY intent - generate and confirm reply."""
        email_ref = parsed.params.get("email_ref")
        reply_content = parsed.params.get("reply_content")
        
        # Need email reference
        if not email_ref:
            return ChatResponse(
                message="Which email would you like to reply to? You can say 'reply to #1' or 'reply to the email from John'.",
                type="text",
            )
        
        # Resolve email reference
        email = self.email_service.resolve_email_reference(email_ref)
        if not email:
            return ChatResponse(
                message=f"I couldn't find an email matching '{email_ref}'. Try 'show my emails' first, then reference by number (e.g., '#1').",
                type="text",
            )
        
        # Generate reply if no content provided
        if not reply_content:
            try:
                reply_content = await generate_reply(email)
            except AIError as e:
                return ChatResponse(
                    message=f"Couldn't generate a reply. Please provide what you'd like to say, e.g., 'reply to #{email['index']}: Thanks for the update!'",
                    type="error",
                )
        
        # Store pending action for confirmation
        self.session["pending_action"] = "send"
        self.session["pending_data"] = {
            "email_id": email["id"],
            "email": email,
            "reply_body": reply_content,
        }
        
        # Create draft for display
        draft = DraftReply(
            email_id=email["id"],
            to=email["sender_email"],
            subject=f"Re: {email['subject']}",
            body=reply_content,
        )
        
        return ChatResponse(
            message=f"Here's a draft reply to {email['sender_name']}:\n\n---\n{reply_content}\n---\n\nSend this reply? (yes/no)",
            type="draft",
            data=draft.model_dump(),
            pending_action="send",
        )
    
    async def _handle_delete(self, parsed: ParsedIntent) -> ChatResponse:
        """Handle DELETE intent - confirm before deleting."""
        email_ref = parsed.params.get("email_ref")
        
        if not email_ref:
            return ChatResponse(
                message="Which email would you like to delete? You can say 'delete #1' or 'delete the email from LinkedIn'.",
                type="text",
            )
        
        # Resolve email reference
        email = self.email_service.resolve_email_reference(email_ref)
        if not email:
            return ChatResponse(
                message=f"I couldn't find an email matching '{email_ref}'. Try 'show my emails' first.",
                type="text",
            )
        
        # Store pending action for confirmation
        self.session["pending_action"] = "delete"
        self.session["pending_data"] = {
             "email_id": email["id"],
             "email": email,
        }
        
        return ChatResponse(
            message=f"Delete this email?\n\n**From:** {email['sender_name']} <{email['sender_email']}>\n**Subject:** {email['subject']}\n\n⚠️ Reply 'yes' to delete or 'no' to cancel.",
            type="confirmation",
            pending_action="delete",
        )
    
    async def _handle_categorize(self, parsed: ParsedIntent) -> ChatResponse:
        """Handle CATEGORIZE intent - group emails by AI categories."""
        # Auto-fetch more emails if cache is small
        cache = self.email_service.get_cached_emails()
        
        if not cache or len(cache) < 10:
            # Fetch last 20 emails for better categorization
            logger.info("Fetching larger batch (20) for categorization")
            await self.email_service.fetch_emails(count=20)
            cache = self.email_service.get_cached_emails()
        
        if not cache:
            return ChatResponse(
                message="No emails found to organize.",
                type="text",
            )
        
        try:
            categories = await categorize_emails(cache)
            
            formatted = []
            for cat in categories:
                formatted.append({
                    "category": cat.get("name", "Unknown"),
                    "count": len(cat.get("email_indices", [])),
                    "emails": [cache[i-1] for i in cat.get("email_indices", []) if i <= len(cache)],
                })
            
            return ChatResponse(
                message=f"I've organized your emails into {len(categories)} categories:",
                type="categories",
                data=formatted,
            )
        except AIError as e:
            return ChatResponse(
                message=e.message,
                type="error",
            )
    
    async def _handle_digest(self, parsed: ParsedIntent) -> ChatResponse:
        """Handle DIGEST intent - generate daily summary."""
        cache = self.email_service.get_cached_emails()
        
        if not cache:
            # Fetch emails first
            emails = await self.email_service.fetch_emails(count=5)
            if not emails:
                return ChatResponse(
                    message="No emails to summarize today. Your inbox is empty! 🎉",
                    type="text",
                )
            cache = self.email_service.get_cached_emails()
        
        try:
            digest = await generate_digest(cache)
            
            return ChatResponse(
                message=f"📋 **Daily Digest**\n\n{digest.get('summary', 'No summary available.')}",
                type="digest",
                data=digest,
            )
        except AIError as e:
            return ChatResponse(
                message=e.message,
                type="error",
            )
    
    async def _handle_confirm(self, parsed: ParsedIntent) -> ChatResponse:
        """Handle CONFIRM intent - execute pending action."""
        pending_action = self.session.get("pending_action")
        pending_data = self.session.get("pending_data")
        
        if not pending_action or not pending_data:
            return ChatResponse(
                message="No pending action to confirm. What would you like to do?",
                type="text",
            )
        
        # Clear pending state
        self.session["pending_action"] = None
        self.session["pending_data"] = None
        
        if pending_action == "send":
            # Send the reply
            email = pending_data["email"]
            reply_body = pending_data["reply_body"]
            
            await self.email_service.send_reply(
                email_id=email["id"],
                body=reply_body,
                original_email=email,
            )
            
            return ChatResponse(
                message=f"✅ Reply sent to {email['sender_name']}!",
                type="text",
            )
        
        elif pending_action == "delete":
            # Delete the email
            email = pending_data["email"]
            
            await self.email_service.delete_email(email["id"])
            
            return ChatResponse(
                message=f"🗑️ Email from {email['sender_name']} deleted.",
                type="text",
            )
        
        return ChatResponse(
            message="Unknown pending action.",
            type="error",
        )
    
    async def _handle_cancel(self, parsed: ParsedIntent) -> ChatResponse:
        """Handle CANCEL intent - cancel pending action."""
        pending_action = self.session.get("pending_action")
        
        # Clear pending state
        self.session["pending_action"] = None
        self.session["pending_data"] = None
        
        if pending_action:
            action_name = "Reply" if pending_action == "send" else "Delete"
            return ChatResponse(
                message=f"❌ {action_name} cancelled. What else can I help with?",
                type="text",
            )
        
        return ChatResponse(
            message="Nothing to cancel. What would you like to do?",
            type="text",
        )
    
    async def _handle_help(self, parsed: ParsedIntent) -> ChatResponse:
        """Handle HELP intent - show available commands."""
        return ChatResponse(
            message=get_help_message(),
            type="text",
        )
    
    async def _handle_greeting(self, parsed: ParsedIntent) -> ChatResponse:
        """Handle GREETING intent - friendly response."""
        return ChatResponse(
            message=get_greeting_response(),
            type="text",
        )
    
    async def _handle_unknown(self, parsed: ParsedIntent) -> ChatResponse:
        """Handle UNKNOWN intent - ask for clarification."""
        return ChatResponse(
            message=get_low_confidence_message(Intent.UNKNOWN),
            type="text",
        )
