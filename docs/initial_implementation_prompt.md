Okay, let's integrate a local Neo4j graph database into the MVP to store communication patterns and use that context to enhance the email analysis.

**Prerequisites (Additions):**

1.  **Docker:** Install Docker Desktop ([https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)). We'll use it to run Neo4j locally easily.
2.  **Neo4j Python Driver:** Install the library:
    ```bash
    pip install neo4j python-dotenv # Ensure dotenv is installed
    ```

**Local Project Setup (Additions):**

1.  **Update `.env` file:** Add Neo4j connection details.

    ```dotenv
    # .env file
    GOOGLE_SERVICE_ACCOUNT_FILE='your-service-account-key.json'
    GOOGLE_GEMINI_API_KEY='YOUR_GEMINI_API_KEY_HERE'
    TARGET_GMAIL_ADDRESS='test-analyzer@yourdomain.com'
    GMAIL_SCOPES='https://www.googleapis.com/auth/gmail.readonly' # Start read-only for safety

    # Neo4j Configuration
    NEO4J_URI='bolt://localhost:7687' # Default Bolt port
    NEO4J_USER='neo4j'
    NEO4J_PASSWORD='YOUR_STRONG_NEO4J_PASSWORD' # Set this password when first running Neo4j
    ```

2.  **Add Neo4j Driver to `.gitignore`:** (Already covered by `venv/` but good practice).

**Run Local Neo4j Instance:**

Open your terminal (not inside the Python venv) and run the following Docker command. Replace `YOUR_STRONG_NEO4J_PASSWORD` with the password you set in your `.env` file.

```bash
docker run \
    --name neo4j-local-analyzer \
    -p 7474:7474 -p 7687:7687 \
    -d \
    -e NEO4J_AUTH=neo4j/YOUR_STRONG_NEO4J_PASSWORD \
    neo4j:latest
```

- `--name`: Gives the container a recognizable name.
- `-p 7474:7474`: Maps the Neo4j Browser port.
- `-p 7687:7687`: Maps the Bolt port used by the driver.
- `-d`: Runs the container in detached mode (in the background).
- `-e NEO4J_AUTH`: Sets the username and password.
- `neo4j:latest`: Uses the latest official Neo4j image.

You can access the Neo4j Browser at `http://localhost:7474` and log in with `neo4j` and your chosen password.

**Updated Python Code (`main.py`):**

````python
import os
import base64
import email
from email import policy
from bs4 import BeautifulSoup
import time
import json # For parsing Gemini response
import re # For extracting email addresses

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import google.generativeai as genai
from neo4j import GraphDatabase # Import Neo4j driver

# --- Configuration & Authentication ---

load_dotenv()

SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY')
TARGET_USER_EMAIL = os.getenv('TARGET_GMAIL_ADDRESS')
SCOPES = os.getenv('GMAIL_SCOPES', 'https://www.googleapis.com/auth/gmail.readonly').split()

NEO4J_URI = os.getenv('NEO4J_URI')
NEO4J_USER = os.getenv('NEO4J_USER')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')

# Configure Gemini Client
if not GEMINI_API_KEY:
    raise ValueError("Gemini API Key not found in .env file")
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest')

# Configure Neo4j Driver (Global instance - manage connections carefully in real apps)
if not all([NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD]):
     raise ValueError("Neo4j connection details not found in .env file")
try:
    neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    neo4j_driver.verify_connectivity() # Check connection on startup
    print("Successfully connected to Neo4j.")
except Exception as e:
    print(f"Error connecting to Neo4j: {e}. Make sure Neo4j is running via Docker.")
    neo4j_driver = None # Set driver to None if connection fails

def get_gmail_service():
    # (Same as before)
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES, subject=TARGET_USER_EMAIL
        )
        service = build('gmail', 'v1', credentials=creds)
        print(f"Successfully authenticated Gmail API for user: {TARGET_USER_EMAIL}")
        return service
    except Exception as e:
        print(f"Error authenticating Gmail API: {e}")
        raise

# --- Email Parsing Helper ---
def extract_email_address(header_string):
    """Extracts the first email address found in a header string."""
    if not header_string:
        return None
    # Simple regex to find email patterns
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', header_string)
    return match.group(0).lower() if match else None

# --- Email Processing (fetch_unread_emails, get_email_details, parse_email remain mostly the same) ---
def fetch_unread_emails(service, max_results=5):
    # (Same as before)
    try:
        results = service.users().messages().list(
            userId=TARGET_USER_EMAIL,
            labelIds=['INBOX', 'UNREAD'],
            maxResults=max_results
        ).execute()
        messages = results.get('messages', [])
        print(f"Found {len(messages)} unread emails.")
        return [msg['id'] for msg in messages]
    except HttpError as error:
        print(f"An error occurred fetching messages: {error}")
        return []

def get_email_details(service, msg_id):
    # (Same as before)
    try:
        message = service.users().messages().get(
            userId=TARGET_USER_EMAIL,
            id=msg_id,
            format='full'
        ).execute()
        return message
    except HttpError as error:
        print(f"An error occurred fetching email details (ID: {msg_id}): {error}")
        return None

def parse_email(message):
    # (Enhanced to extract sender/recipient emails reliably)
    details = {'id': message['id'], 'headers': {}, 'body': '', 'sender': None, 'recipient': TARGET_USER_EMAIL} # Recipient is our target user
    payload = message.get('payload', {})
    headers = payload.get('headers', [])

    for header in headers:
        name = header.get('name').lower()
        value = header.get('value')
        if name in ['from', 'to', 'subject', 'date', 'reply-to', 'return-path', 'authentication-results']:
            details['headers'][name] = value
            if name == 'from':
                details['sender'] = extract_email_address(value) # Extract sender email

    # Body extraction logic (same as before)
    if 'parts' in payload:
        # ... (same body extraction logic as before) ...
        parts = payload['parts']
        body_plain = ''
        body_html = ''
        for part in parts:
            mime_type = part.get('mimeType')
            body_data = part.get('body', {}).get('data')
            if body_data:
                decoded_data = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='replace')
                if mime_type == 'text/plain':
                    body_plain += decoded_data + "\n"
                elif mime_type == 'text/html':
                    body_html += decoded_data + "\n"
        if body_plain.strip():
            details['body'] = body_plain.strip()
        elif body_html.strip():
            soup = BeautifulSoup(body_html, 'html.parser')
            details['body'] = soup.get_text(separator='\n').strip()
        else:
             details['body'] = "Could not extract plain/HTML body from parts."
    elif 'body' in payload and payload['body'].get('data'):
         body_data = payload['body'].get('data')
         decoded_data = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='replace')
         details['body'] = decoded_data.strip()


    if not details['sender']:
        print(f"  Warning: Could not extract sender email address for message {details['id']}")

    return details


def mark_email_as_read(service, msg_id):
    # (Same as before)
    # ... requires modify scope ...

# --- Graph Database Interaction ---

def get_communication_context(driver, sender_email, recipient_email):
    """Queries Neo4j for historical communication context between sender and recipient."""
    if not driver or not sender_email or not recipient_email:
        return {"error": "Missing driver or email addresses"}

    query = """
    MATCH (sender:EmailAddress {address: $sender_addr})
    MATCH (recipient:EmailAddress {address: $recipient_addr})
    OPTIONAL MATCH (sender)-[r:SENT_EMAIL]->(recipient) // Communication from sender to recipient
    RETURN
        exists((sender)-[:SENT_EMAIL]->(recipient)) AS sent_to_recipient_before,
        count(r) AS emails_sent_to_recipient,
        // Calculate avg risk later if needed
        datetime() AS query_time // Example placeholder data
    """
    parameters = {"sender_addr": sender_email, "recipient_addr": recipient_email}
    context = {
        "history_exists": False,
        "communication_count": 0,
        "error": None
    }
    try:
        with driver.session(database="neo4j") as session: # Use default database 'neo4j'
             result = session.run(query, parameters)
             record = result.single()
             if record:
                 context["history_exists"] = record["sent_to_recipient_before"]
                 context["communication_count"] = record["emails_sent_to_recipient"]
             else: # Should ideally return even if no match, check logic
                 print("No communication context record returned from Neo4j.")

    except Exception as e:
        print(f"  Neo4j Query Error: {e}")
        context["error"] = str(e)

    print(f"  Graph Context: History Exists={context['history_exists']}, Count={context['communication_count']}")
    return context

def add_communication_to_graph(driver, sender_email, recipient_email, message_id, timestamp_ms, risk_level):
    """Adds the current email communication to the Neo4j graph."""
    if not driver or not sender_email or not recipient_email:
        print("  Skipping graph update: Missing driver or email addresses.")
        return

    query = """
    // Ensure sender node exists
    MERGE (sender:EmailAddress {address: $sender_addr})
    // Ensure recipient node exists
    MERGE (recipient:EmailAddress {address: $recipient_addr})
    // Create the relationship representing the email sent
    CREATE (sender)-[r:SENT_EMAIL {
        messageId: $msg_id,
        timestamp: datetime({epochMillis: $ts_ms}), // Store as Neo4j datetime
        riskLevel: $risk_lvl
    }]->(recipient)
    RETURN id(r) // Return ID of the created relationship
    """
    parameters = {
        "sender_addr": sender_email,
        "recipient_addr": recipient_email,
        "msg_id": message_id,
        "ts_ms": int(timestamp_ms), # Gmail provides timestamp in ms epoch
        "risk_lvl": risk_level
    }
    try:
        with driver.session(database="neo4j") as session:
             result = session.run(query, parameters)
             record = result.single()
             if record:
                 print(f"  Graph Update: Added SENT_EMAIL relationship (ID: {record[0]})")
             else:
                 print("  Graph Update: Relationship creation did not return an ID.") # Should not happen if successful
    except Exception as e:
        print(f"  Neo4j Update Error: {e}")


# --- Analysis Modules (Updated Gemini Prompt) ---

def perform_traditional_checks(parsed_email):
    # (Same as before)
    # ... return dict with spf, dkim, dmarc results ...
    results = {}
    headers = parsed_email.get('headers', {})
    auth_results = headers.get('authentication-results', '')
    results['spf'] = 'pass' if 'spf=pass' in auth_results else ('fail' if 'spf=fail' in auth_results else 'neutral/none')
    results['dkim'] = 'pass' if 'dkim=pass' in auth_results else ('fail' if 'dkim=fail' in auth_results else 'neutral/none')
    results['dmarc'] = 'pass' if 'dmarc=pass' in auth_results else ('fail' if 'dmarc=fail' in auth_results else 'neutral/none')
    print(f"  Traditional Checks: SPF={results['spf']}, DKIM={results['dkim']}, DMARC={results['dmarc']}")
    return results


def analyze_with_gemini(parsed_email, graph_context): # Accept graph context
    """Analyzes email content using Google Gemini, incorporating graph context."""
    subject = parsed_email.get('headers', {}).get('subject', 'No Subject')
    sender = parsed_email.get('sender', 'Unknown Sender') # Use extracted sender
    body = parsed_email.get('body', '')

    if not body:
        print("  Gemini Analysis: Skipping - Empty email body.")
        return {'error': 'Empty body'}

    # --- ENHANCED PROMPT ---
    prompt = f"""
Analyze the following email content for potential social engineering risks like phishing, BEC, or scams. Consider the provided communication history context. Provide output ONLY in valid JSON format with the specified keys.

**Communication Context:**
*   Sender has sent emails to recipient before: {graph_context.get('history_exists', 'Unknown')}
*   Number of previous emails sent by sender to recipient: {graph_context.get('communication_count', 'Unknown')}

**Email Details:**
Email Subject: {subject}
Sender: {sender}
Email Body:
---
{body[:4000]}
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
    # --- END OF ENHANCED PROMPT ---

    try:
        print("  Calling Gemini API (with graph context)...")
        response = gemini_model.generate_content(prompt)
        # (Same JSON parsing and error handling as before)
        json_response_text = response.text.strip().replace('```json', '').replace('```', '').strip()
        if '{' in json_response_text and '}' in json_response_text:
             start = json_response_text.find('{')
             end = json_response_text.rfind('}') + 1
             potential_json = json_response_text[start:end]
             try:
                 analysis = json.loads(potential_json)
                 print(f"  Gemini Analysis Received: Risk={analysis.get('risk_level', 'N/A')}, Intent={analysis.get('intent', 'N/A')}")
                 return analysis
             except json.JSONDecodeError as json_e:
                 print(f"  Gemini Analysis: Failed to parse JSON response - {json_e}")
                 return {'error': 'Failed to parse JSON response', 'raw_response': response.text}
        else:
             print("  Gemini Analysis: Response does not appear to contain valid JSON.")
             return {'error': 'Invalid JSON response format', 'raw_response': response.text}

    except Exception as e:
        print(f"  An error occurred calling Gemini API: {e}")
        # (Same safety feedback check as before)
        try:
            if response.prompt_feedback.block_reason:
                 return {'error': f'Blocked by API safety settings: {response.prompt_feedback.block_reason}'}
        except Exception: pass
        return {'error': f'Gemini API call failed: {e}'}


# --- Risk Scoring (Updated) ---

def calculate_risk_score(traditional_results, gemini_results, graph_context): # Accept graph context
    """Combines results into a final risk assessment, incorporating graph context."""
    score = 0
    reasons = []

    # Traditional Checks Weights
    if traditional_results.get('spf') != 'pass': score += 5; reasons.append("SPF Fail/Neutral")
    if traditional_results.get('dkim') != 'pass': score += 5; reasons.append("DKIM Fail/Neutral")
    if traditional_results.get('dmarc') != 'pass': score += 10; reasons.append("DMARC Fail/Neutral")

    # Graph Context Weights (Example)
    is_first_contact = not graph_context.get('history_exists', True) # Default to False if error
    if is_first_contact:
        score += 5 # Slightly increase risk for first contact
        reasons.append("First time sender to recipient")

    # Gemini Checks Weights
    gemini_risk = "Low"
    if 'error' in gemini_results:
        score += 5
        reasons.append(f"Gemini Error: {gemini_results['error']}")
    else:
        gemini_risk = gemini_results.get('risk_level', 'Low').lower()
        gemini_explanation = gemini_results.get('explanation', '')
        gemini_intent = gemini_results.get('intent', 'Other')

        if gemini_risk == 'medium':
            score += 15
            reasons.append(f"Gemini Medium Risk: {gemini_explanation}")
        elif gemini_risk == 'high':
            score += 30
            reasons.append(f"Gemini High Risk: {gemini_explanation}")

        # Modify score based on context + intent
        if is_first_contact and gemini_intent in ["Payment Request", "Credential Request", "Urgent Action Required"]:
            score += 10 # Significantly increase risk for risky intents from new senders
            reasons.append("Risky intent from first-time sender")


    final_risk = "Low"
    if 15 <= score < 30: # Adjusted thresholds
        final_risk = "Medium"
    elif score >= 30:
        final_risk = "High"

    print(f"  Calculated Score: {score}, Final Risk: {final_risk}")
    return final_risk, score, reasons

# --- Main Execution Loop (Updated) ---

def main():
    print("Starting Local Gmail Analyzer with Neo4j...")
    if not neo4j_driver:
        print("Cannot start without Neo4j connection. Exiting.")
        return

    gmail_service = get_gmail_service()
    if not gmail_service:
        return

    processed_count = 0
    max_to_process = 5

    try: # Wrap main loop to ensure driver closes
        while processed_count < max_to_process:
            print("\nFetching unread emails...")
            unread_ids = fetch_unread_emails(gmail_service, max_results=max_to_process - processed_count)

            if not unread_ids:
                print("No more unread emails found.")
                break

            for msg_id in unread_ids:
                if processed_count >= max_to_process:
                    break

                print(f"\n--- Processing Email ID: {msg_id} ---")
                message = get_email_details(gmail_service, msg_id)
                if not message:
                    continue

                parsed_email = parse_email(message)
                sender_email = parsed_email.get('sender')
                recipient_email = parsed_email.get('recipient') # Our target user
                timestamp_ms = message.get('internalDate') # Get timestamp

                if not sender_email:
                     print("  Skipping email: Could not determine sender address.")
                     # Optionally mark as read here if needed
                     continue # Skip if no sender identified

                print(f"  Subject: {parsed_email.get('headers', {}).get('subject', 'N/A')}")
                print(f"  From: {parsed_email.get('headers', {}).get('from', 'N/A')} ({sender_email})")
                print(f"  To: {recipient_email}") # Confirm recipient


                # --- Core Analysis Flow ---
                # 1. Traditional Checks
                traditional_results = perform_traditional_checks(parsed_email)

                # 2. Query Graph DB for Context
                graph_context = get_communication_context(neo4j_driver, sender_email, recipient_email)

                # 3. Analyze with Gemini (using Graph Context)
                gemini_results = analyze_with_gemini(parsed_email, graph_context)

                # 4. Calculate Final Risk (using all inputs)
                final_risk, score, reasons = calculate_risk_score(
                    traditional_results, gemini_results, graph_context
                )

                # 5. Update Graph DB (after analysis)
                if timestamp_ms: # Only update if we have a timestamp
                    add_communication_to_graph(
                        neo4j_driver, sender_email, recipient_email, msg_id, timestamp_ms, final_risk
                    )
                else:
                    print("  Skipping graph update: Missing timestamp.")

                # --- Output Results ---
                print(f"\n--- ANALYSIS COMPLETE (ID: {msg_id}) ---")
                print(f"  Final Risk Level: {final_risk} (Score: {score})")
                print(f"  Reasons / Key Findings:")
                for reason in reasons:
                    print(f"    - {reason}")
                print("----------------------------------------")

                # Mark as read (use cautiously with modify scope)
                # mark_email_as_read(gmail_service, msg_id)

                processed_count += 1
                time.sleep(2) # Slightly longer delay for Neo4j + Gemini calls

    finally:
        # Ensure Neo4j driver is closed gracefully when script exits/fails
        if neo4j_driver:
            neo4j_driver.close()
            print("\nNeo4j driver closed.")

    print(f"\nFinished processing. Analyzed {processed_count} emails.")

if __name__ == '__main__':
    main()
````

**How to Run:**

1.  Make sure Docker is running.
2.  Run the Neo4j container using the `docker run` command provided earlier.
3.  Fill in your `.env` file correctly (including the Neo4j password).
4.  Activate your Python virtual environment.
5.  Run the script: `python main.py`

**What's Happening Now:**

1.  The script connects to both Gmail and your local Neo4j instance.
2.  It fetches unread emails from the target Gmail account.
3.  For each email:
    - It parses the sender, recipient, body, and headers.
    - It performs traditional SPF/DKIM/DMARC checks.
    - **It queries Neo4j** to see if the sender has emailed the recipient before and how many times.
    - **It calls Gemini**, providing the email content _and_ the communication history context from Neo4j.
    - It calculates a risk score based on traditional checks, Gemini's analysis (which now considers context), and the graph context itself (e.g., is this a first-time sender?).
    - **It updates Neo4j**, creating nodes for the sender and recipient (if they don't exist) and adding a `SENT_EMAIL` relationship between them, storing the message ID, timestamp, and calculated risk level.
    - It prints the final analysis to the console.
4.  The Neo4j driver connection is closed when the script finishes.

You can now send test emails to your target account and observe how the script analyzes them and how the communication graph builds up in your local Neo4j instance (viewable via `http://localhost:7474`). This provides a much richer context for making security decisions.
