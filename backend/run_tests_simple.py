
import asyncio
import sys
import unittest
from unittest.mock import AsyncMock, patch, MagicMock

# Add project root to path
import os
sys.path.append(os.getcwd())

from app.services.intent_parser import rule_based_parse, Intent
from app.integrations.gmail_client import GmailClient

# Simple color output
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

def print_result(name, success, error=None):
    if success:
        print(f"{GREEN}[PASS]{RESET} {name}")
    else:
        print(f"{RED}[FAIL]{RESET} {name}")
        if error:
            print(f"  Error: {error}")

async def test_gmail_client():
    print("\n--- Testing Gmail Client ---")
    try:
        client = GmailClient("token")
        
        # Test 1: Fetch Emails with Query (Signature check)
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"messages": []}
            await client.fetch_emails(count=5, query="test")
            
            # Check if query was passed in params
            call_args = mock_req.call_args
            params = call_args[1].get('params', {})
            if params.get('q') == "test":
                print_result("fetch_emails passes query param", True)
            else:
                print_result("fetch_emails passes query param", False, f"Params: {params}")

    except Exception as e:
        print_result("Gmail Client Tests", False, str(e))

def test_intent_parser():
    print("\n--- Testing Intent Parser ---")
    try:
        # Test 1: Read Emails
        result = rule_based_parse("show my emails")
        if result and result.intent == Intent.READ_EMAILS:
            print_result("Parse 'show my emails'", True)
        else:
            print_result("Parse 'show my emails'", False, f"Got {result}")

        # Test 2: Natural Language Search coverage
        result = rule_based_parse("show emails about invoice")
        if result and result.intent == Intent.READ_EMAILS:
            print_result("Parse 'show emails about invoice'", True)
        else:
            print_result("Parse 'show emails about invoice'", False, f"Got {result}")
            
    except Exception as e:
        print_result("Intent Parser Tests", False, str(e))

async def main():
    test_intent_parser()
    await test_gmail_client()

if __name__ == "__main__":
    asyncio.run(main())
