# Potion Email Security

A context-aware social engineering defense system that analyzes emails for potential threats using a combination of traditional checks, LLM-based contextual analysis, and communication patterns stored in a graph database.

## Overview

This project provides a Python-based MVP implementation of an email security system that:

1. Connects to Gmail via the Gmail API
2. Fetches unread emails
3. Analyzes them using:
   - Traditional checks (SPF, DKIM, DMARC)
   - Google Gemini AI for contextual analysis
   - Neo4j graph database for sender-recipient communication history
4. Scores each email for risk based on multiple factors
5. Updates the communication graph with the new email

## Prerequisites

- Python 3.11
- Docker & Docker Compose (for running Neo4j)
- A Google Cloud Project with Gmail API and Gemini API enabled
- OAuth 2.0 credentials for Gmail access
- Google Gemini API key

## Setup

1. Clone the repository
2. Run the setup script to create a virtual environment and install dependencies:
   ```bash
   bash setup.sh
   # or
   make setup
   ```
3. Set up your `.env` file with the necessary API keys and credentials
4. Start the Neo4j container:
   ```bash
   docker-compose up -d neo4j
   # or
   make neo4j-start
   ```

### Apple Silicon / ARM64 Compatibility

If you're running on Apple Silicon (M1/M2/M3) or another ARM64-based system:

- The Neo4j container is configured to run under emulation with `platform: linux/amd64`
- This ensures maximum compatibility but may be slightly slower
- First-time startup may take a minute or two longer than on x86 systems
- If you experience any issues, check the container logs:
  ```bash
  make neo4j-logs
  ```

## OAuth 2.0 Setup for Gmail

This application uses OAuth 2.0 for accessing Gmail, making it suitable for personal Gmail accounts without requiring a Google Workspace subscription.

1. **Create a Google Cloud Project**:

   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or use an existing one
   - Enable the Gmail API and Gemini API

2. **Set up OAuth 2.0 credentials**:

   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Configure the OAuth consent screen (External is fine for testing)
   - Select "Desktop app" as the application type
   - Name your client and create it
   - Download the JSON credentials file and save it as `credentials.json` in the project root

3. **First Run**:
   - When you run the application for the first time, a browser window will open
   - Sign in with your Gmail account and authorize the application
   - After authorization, credentials will be saved in `token.pickle` for future use

## Usage

This project includes a Makefile with common commands for convenience. View available commands with:

```bash
make help
```

### Prerequisite Check

Before running the main application, verify all prerequisites are properly configured:

```bash
./check_prereqs.py
# or
make check
```

This script checks for:

- Properly configured `.env` file
- Valid OAuth credentials
- Valid Gemini API key format
- Neo4j connectivity

### Testing Gemini API Integration

To verify that your Gemini API key is working correctly, you can run the test script:

```bash
./test_gemini.py
# or
make test-gemini
```

This script:

- Configures the Gemini client with your API key
- Sends a request with a sample email
- Parses and displays the analysis results

### Analyzing Emails

Run the main script to analyze unread emails:

```bash
python main.py
# or
make run
```

The script will:

1. Connect to your Gmail account (via OAuth)
2. Fetch unread emails
3. Analyze each email for security risks
4. Print analysis results to the console
5. Update the Neo4j communication graph

### Sending Test Emails

To test the system, you can send emails with different risk profiles using the test sender utility:

```bash
./send_test_email.py low_risk --sender-email your@email.com --password "your-password"
```

Available risk profiles:

- `low_risk` - Benign team lunch invitation
- `medium_risk` - Urgent document review request
- `high_risk` - Payment request with banking details
- `impersonation` - Gift card scam impersonating an executive

For more options:

```bash
./send_test_email.py --help
```

## Neo4j Browser

You can access the Neo4j browser at http://localhost:7474 to visualize and query the communication graph. Log in with username `neo4j` and no password (authentication is disabled by default).
