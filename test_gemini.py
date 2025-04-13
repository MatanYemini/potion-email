#!/usr/bin/env python3
"""
Test Gemini API integration for Potion Email Security.
This script tests the Gemini API with a sample email to verify integration.
"""

import os
import json
from dotenv import load_dotenv
import google.generativeai as genai

# Sample email to test
SAMPLE_EMAIL = {
    'subject': 'Urgent: Invoice Payment Required',
    'sender': 'accounting@example-company.com',
    'body': """
Hello,

This is a reminder that invoice #38291 for $12,450.00 is due today.
Please process the payment immediately to avoid late fees.

Payment can be made via wire transfer to:
Bank: First National Bank
Account: 2834719XX
Routing: 0912837XX

Please confirm once payment is complete.

Regards,
James Williams
Financial Department
Example Company Inc.
"""
}

# Sample communication context
SAMPLE_CONTEXT = {
    'history_exists': False,
    'communication_count': 0
}

def test_gemini_api():
    """Test the Gemini API with a sample email."""
    print("Testing Gemini API integration...")
    
    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = os.getenv('GOOGLE_GEMINI_API_KEY')
    if not api_key:
        print("❌ Error: GOOGLE_GEMINI_API_KEY not found in .env file")
        return False
    
    # Configure Gemini
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        print("✓ Gemini API configured successfully")
    except Exception as e:
        print(f"❌ Error configuring Gemini API: {e}")
        return False
    
    # Create prompt with sample email
    prompt = f"""
Analyze the following email content for potential social engineering risks like phishing, BEC, or scams. Consider the provided communication history context. Provide output ONLY in valid JSON format with the specified keys.

**Communication Context:**
*   Sender has sent emails to recipient before: {SAMPLE_CONTEXT.get('history_exists', 'Unknown')}
*   Number of previous emails sent by sender to recipient: {SAMPLE_CONTEXT.get('communication_count', 'Unknown')}

**Email Details:**
Email Subject: {SAMPLE_EMAIL['subject']}
Sender: {SAMPLE_EMAIL['sender']}
Email Body:
---
{SAMPLE_EMAIL['body']}
---

Analysis Tasks (respond in JSON):
{{
  "intent": "Classify primary intent. Choose one: [Payment Request, Credential Request, Urgent Action Required, Information Request, Gift Card Request, Job Offer Scam, Impersonation Attempt, Marketing, Personal Communication, Spam, Other].",
  "urgency_score": "Rate perceived urgency (1=Low, 5=High).",
  "manipulation_score": "Rate likelihood of manipulative language (1=Low, 5=High).",
  "impersonation_likelihood": "Rate likelihood this is an impersonation attempt (Low, Medium, High), considering sender address and communication history context.",
  "risk_level": "Overall textual risk level (Low, Medium, High), considering communication context and content.",
  "explanation": "BRIEF (1-2 sentences) explanation for the risk level, mentioning key indicators and context if relevant (e.g., 'High risk payment request from first-time sender')."
}}
"""
    
    # Call API
    try:
        print("Calling Gemini API...")
        response = model.generate_content(prompt)
        print("✓ Received response from Gemini API")
    except Exception as e:
        print(f"❌ Error calling Gemini API: {e}")
        return False
    
    # Parse response
    try:
        json_response_text = response.text.strip().replace('```json', '').replace('```', '').strip()
        
        if '{' in json_response_text and '}' in json_response_text:
            start = json_response_text.find('{')
            end = json_response_text.rfind('}') + 1
            potential_json = json_response_text[start:end]
            
            analysis = json.loads(potential_json)
            print("✓ Successfully parsed JSON response")
            
            # Print analysis
            print("\n=== Email Analysis Results ===")
            print(f"Intent: {analysis.get('intent', 'N/A')}")
            print(f"Urgency Score: {analysis.get('urgency_score', 'N/A')}")
            print(f"Manipulation Score: {analysis.get('manipulation_score', 'N/A')}")
            print(f"Impersonation Likelihood: {analysis.get('impersonation_likelihood', 'N/A')}")
            print(f"Risk Level: {analysis.get('risk_level', 'N/A')}")
            print(f"Explanation: {analysis.get('explanation', 'N/A')}")
            
            return True
        else:
            print("❌ Response does not contain valid JSON")
            print(f"Raw response: {response.text}")
            return False
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
        print(f"Raw response: {response.text}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main function."""
    print("\n=== Potion Email Security - Gemini API Test ===\n")
    success = test_gemini_api()
    
    if success:
        print("\n✅ Gemini API test passed successfully!")
        return 0
    else:
        print("\n❌ Gemini API test failed.")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main()) 