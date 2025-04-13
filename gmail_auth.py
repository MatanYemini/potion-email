import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

def get_gmail_service():
    """Get authenticated Gmail API service using OAuth 2.0 for personal Gmail accounts."""
    # Load environment variables
    load_dotenv()
    
    # Get target email address from .env
    target_email = os.getenv('TARGET_GMAIL_ADDRESS')
    if not target_email:
        raise ValueError("TARGET_GMAIL_ADDRESS not found in .env file")
    
    print(f"Authenticating Gmail API for user: {target_email}")
    
    creds = None
    # The file token.pickle stores the user's access and refresh tokens
    if os.path.exists('token.pickle'):
        print("Loading cached credentials from token.pickle...")
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If no valid credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired credentials...")
            creds.refresh(Request())
        else:
            print("No valid credentials found. Starting OAuth flow...")
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError(
                    "credentials.json not found. Please download OAuth client ID credentials "
                    "from Google Cloud Console and save as 'credentials.json'"
                )
            
            # Start OAuth flow with the user
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json',
                ['https://www.googleapis.com/auth/gmail.readonly']
            )
            print("A browser window will open. Please authorize the application...")
            creds = flow.run_local_server(port=0)
            print("Authorization successful!")
        
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
            print("Credentials saved to token.pickle")
    
    try:
        # Build and verify the Gmail service
        service = build('gmail', 'v1', credentials=creds)
        # Verify connection with a simple API call
        profile = service.users().getProfile(userId='me').execute()
        print(f"Successfully authenticated Gmail API for: {profile['emailAddress']}")
        return service
    except HttpError as error:
        print(f"Error connecting to Gmail API: {error}")
        raise 