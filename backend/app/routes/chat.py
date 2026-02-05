"""
Chat API endpoint for AI assistant interactions.

This is the main endpoint that handles all user interactions.
Messages are processed through:
1. Intent Parser → Determines what user wants
2. Email Service → Gmail operations
3. AI Service → Summaries, replies, categorization
4. Session Service → State management

Endpoint: POST /api/chat
Request: { "message": "user's natural language input" }
Response: ChatResponse with message, type, data, pending_action

Response Types:
- text: Simple text response
- emails: List of email summaries
- categories: Grouped emails by category
- digest: Daily summary
- draft: Reply draft awaiting confirmation
- confirmation: Delete confirmation
- error: Error message

Sample API Responses:

1. Greeting:
   Request: {"message": "hello"}
   Response: {
     "message": "Hello! 👋 I'm your email assistant...",
     "type": "text",
     "data": null,
     "pending_action": null
   }

2. Read Emails:
   Request: {"message": "show my emails"}
   Response: {
     "message": "Here are your 5 most recent emails:",
     "type": "emails",
     "data": [
       {
         "id": "abc123",
         "index": 1,
         "sender_name": "John Doe",
         "sender_email": "john@example.com",
         "subject": "Meeting Tomorrow",
         "summary": "John is confirming the 3pm meeting tomorrow.",
         "date": "2025-02-05T10:30:00"
       },
       ...
     ],
     "pending_action": null
   }

3. Reply (with confirmation):
   Request: {"message": "reply to #1: Thanks, I'll be there!"}
   Response: {
     "message": "Here's a draft reply to John Doe:\\n\\n---\\nThanks, I'll be there!\\n---\\n\\nSend this reply? (yes/no)",
     "type": "draft",
     "data": {
       "email_id": "abc123",
       "to": "john@example.com",
       "subject": "Re: Meeting Tomorrow",
       "body": "Thanks, I'll be there!"
     },
     "pending_action": "send"
   }

4. Confirm Send:
   Request: {"message": "yes"}
   Response: {
     "message": "✅ Reply sent to John Doe!",
     "type": "text",
     "data": null,
     "pending_action": null
   }

5. Delete (with confirmation):
   Request: {"message": "delete #2"}
   Response: {
     "message": "Delete this email?\\n\\n**From:** LinkedIn <notifications@linkedin.com>\\n**Subject:** New connection request\\n\\n⚠️ Reply 'yes' to delete or 'no' to cancel.",
     "type": "confirmation",
     "data": null,
     "pending_action": "delete"
   }

6. Categorize:
   Request: {"message": "organize my inbox"}
   Response: {
     "message": "I've organized your emails into 3 categories:",
     "type": "categories",
     "data": [
       {
         "category": "Work",
         "count": 2,
         "emails": [...]
       },
       {
         "category": "Promotions",
         "count": 2,
         "emails": [...]
       }
     ],
     "pending_action": null
   }

7. Daily Digest:
   Request: {"message": "today's summary"}
   Response: {
     "message": "📋 **Daily Digest**\\n\\nYou have 5 emails today...",
     "type": "digest",
     "data": {
       "summary": "You have 5 emails today, mostly promotions...",
       "key_emails": [...],
       "suggested_actions": ["Reply to meeting request", "Clean up promotions"]
     },
     "pending_action": null
   }

8. Error:
   Response: {
     "message": "Couldn't connect to Gmail. Please try again.",
     "type": "error",
     "data": null,
     "pending_action": null
   }
"""
from fastapi import APIRouter, Depends, HTTPException, Request

from app.models.chat import ChatRequest, ChatResponse
from app.services.session_service import get_current_session
from app.services.chat_service import ChatService
from app.utils.logger import get_logger
from app.utils.errors import AppError

router = APIRouter()
logger = get_logger(__name__)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    session: dict = Depends(get_current_session)
):
    """
    Process a chat message and return AI response.
    
    This endpoint handles all email operations through natural language:
    - "show my emails" → Fetches and summarizes emails
    - "reply to #1" → Generates a reply draft
    - "delete #2" → Confirms deletion
    - "yes" / "no" → Confirms or cancels pending actions
    
    The response type indicates how the frontend should render the response:
    - "text": Render as plain message bubble
    - "emails": Render as email cards with summaries
    - "draft": Show draft with send/cancel buttons
    - "confirmation": Show confirmation with yes/no buttons
    
    Authentication required via session cookie.
    
    Args:
        request: ChatRequest with user's message
        session: Authenticated user session (injected)
        
    Returns:
        ChatResponse with message, type, optional data, and pending_action
    """
    logger.info(f"Chat request from {session['email']}: {request.message[:50]}...")
    
    try:
        # Create chat service with user session
        chat_service = ChatService(session)
        
        # Process the message through intent parser → handlers
        response = await chat_service.process_message(request.message)
        
        logger.info(f"Chat response type: {response.type}")
        return response
        
    except AppError as e:
        # Known application errors (Gmail, AI, Auth issues)
        logger.error(f"Chat error [{e.code}]: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.to_dict()
        )
        
    except Exception as e:
        # Unexpected errors - log full traceback
        logger.exception(f"Unexpected chat error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": "Something went wrong. Please try again."
            }
        )


@router.get("/chat/status")
async def chat_status(session: dict = Depends(get_current_session)):
    """
    Get current chat state (pending actions, cached emails).
    
    Useful for frontend to restore state after page refresh.
    
    Returns:
        Current pending action and cached email count
    """
    return {
        "pending_action": session.get("pending_action"),
        "has_pending": session.get("pending_action") is not None,
        "cached_email_count": len(session.get("emails_cache", [])),
    }


@router.delete("/chat/pending")
async def clear_pending(session: dict = Depends(get_current_session)):
    """
    Clear any pending action without executing it.
    
    Called when user navigates away or closes chat.
    
    Returns:
        Success confirmation
    """
    session["pending_action"] = None
    session["pending_data"] = None
    
    return {"success": True, "message": "Pending action cleared"}
