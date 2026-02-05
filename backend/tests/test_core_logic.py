
import pytest
from app.integrations.gmail_client import GmailClient
from app.services.intent_parser import rule_based_parse, Intent, extract_reply_content

# ==========================================
# 1. GMAIL RESPONSE PARSING
# ==========================================

@pytest.fixture
def mock_gmail_response():
    return {
        "id": "msg-123",
        "threadId": "thread-123",
        "snippet": "Hello world...",
        "payload": {
            "headers": [
                {"name": "From", "value": "Alice <alice@example.com>"},
                {"name": "Subject", "value": "Project Update"},
                {"name": "Date", "value": "Wed, 05 Feb 2025 12:00:00 +0000"}
            ],
            "body": {"data": "SGVsbG8gd29ybGQ="} # "Hello world" in base64
        }
    }

def test_parse_gmail_response(mock_gmail_response):
    """Verify raw Gmail JSON is correctly mapped to Email object."""
    # Instantiate client with mock token
    client = GmailClient(access_token="mock_token")
    
    # Use internal parsing method
    email = client._parse_message(mock_gmail_response)
    
    assert email.id == "msg-123"
    assert email.sender_name == "Alice"
    assert email.sender_email == "alice@example.com"
    assert email.subject == "Project Update"
    assert "Hello world" in email.body

# ==========================================
# 2. INTENT MAPPING (Commands -> Actions)
# ==========================================

@pytest.mark.parametrize("command,expected_intent", [
    ("Show my emails", Intent.READ_EMAILS),
    ("Reply to #1", Intent.REPLY),
    ("Delete #2", Intent.DELETE),
    ("Help", Intent.HELP),
])
def test_command_mapping(command, expected_intent):
    """Verify natural language maps to correct Enum Intent."""
    result = rule_based_parse(command)
    assert result is not None
    assert result.intent == expected_intent

def test_reply_extraction_bug_fix():
    """Regression Test: Ensure 'Reply to #1' does NOT capture 'to #1' as body."""
    # Case 1: Command only
    content1 = extract_reply_content("Reply to #1")
    assert content1 is None  # Should be empty, triggering AI generation
    
    # Case 2: Command + Content
    content2 = extract_reply_content("Reply to #1: I agree")
    assert content2 == "I agree"
