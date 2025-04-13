#!/usr/bin/env python3
"""
Test Email Sender for Potion Email Security.
This script sends test emails to the configured target email address 
to help test the social engineering detection system with various risk profiles.
"""

import os
import smtplib
import argparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TARGET_EMAIL = os.getenv('TARGET_GMAIL_ADDRESS')

# Test email templates
EMAIL_TEMPLATES = {
    'low_risk': {
        'subject': 'Team Lunch Next Week',
        'body': """
Hey team,

I'm organizing a team lunch next Wednesday at 12:30 PM. 
We'll be going to the Italian restaurant down the street.
Let me know if you can make it!

Best regards,
Alex
        """
    },
    'medium_risk': {
        'subject': 'Urgent: Please review document',
        'body': """
Hello,

I need you to review this important document as soon as possible.
The deadline is tomorrow, and we need your approval to proceed.

Please check and let me know your thoughts ASAP.

Thanks,
John Smith
        """
    },
    'high_risk': {
        'subject': 'URGENT: Invoice Payment Required Immediately',
        'body': """
URGENT PAYMENT REQUIRED

The payment for invoice #38291 for $12,450.00 is overdue. 
Our financial department has flagged this as critical. 
We need you to process this immediately to avoid service interruption.

Please wire the payment to:
Bank: First National Bank
Account: 2834719XX
Routing: 0912837XX

This is a time-sensitive matter. Please confirm when payment is complete.

Regards,
James Williams
Financial Department
        """
    },
    'impersonation': {
        'subject': 'Quick favor needed',
        'body': """
Hey,

I'm in a meeting but need a quick favor. Can you purchase 5 Amazon gift cards 
($100 each) for our clients? I'll reimburse you later today.

Need them ASAP - please send the codes to this email once you have them.

Thanks,
[CEO Name]
Sent from my iPhone
        """
    }
}

def send_email(sender_email, sender_name, recipient, subject, body, smtp_server, port, username, password):
    """Send an email using the specified SMTP server."""
    # Create message
    msg = MIMEMultipart()
    msg['From'] = f"{sender_name} <{sender_email}>"
    msg['To'] = recipient
    msg['Subject'] = subject
    
    # Attach body
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        # Connect to server
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()  # Enable security
        server.login(username, password)
        
        # Send email
        server.send_message(msg)
        server.quit()
        print(f"Successfully sent test email to {recipient}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def main():
    """Parse arguments and send test email."""
    parser = argparse.ArgumentParser(description='Send test emails to test the social engineering detection system.')
    
    parser.add_argument('risk_level', choices=['low_risk', 'medium_risk', 'high_risk', 'impersonation'],
                        help='Risk profile of the test email to send')
    
    parser.add_argument('--smtp-server', default='smtp.gmail.com', 
                        help='SMTP server to use for sending (default: smtp.gmail.com)')
    
    parser.add_argument('--port', type=int, default=587, 
                        help='SMTP port (default: 587)')
    
    parser.add_argument('--sender-email', required=True,
                        help='Email address to send from')
    
    parser.add_argument('--sender-name', default='Test Sender',
                        help='Name to display as sender (default: "Test Sender")')
    
    parser.add_argument('--username',
                        help='SMTP username (defaults to sender email if not provided)')
    
    parser.add_argument('--password', required=True,
                        help='SMTP password for authentication')
    
    parser.add_argument('--recipient',
                        help=f'Recipient email address (default: {TARGET_EMAIL} from .env file)')
    
    args = parser.parse_args()
    
    # Fallback to default values
    username = args.username or args.sender_email
    recipient = args.recipient or TARGET_EMAIL
    
    if not recipient:
        print("Error: No recipient email specified. Either provide --recipient or set TARGET_GMAIL_ADDRESS in .env file.")
        return 1
    
    # Get template
    template = EMAIL_TEMPLATES[args.risk_level]
    
    # Send email
    print(f"Sending {args.risk_level} test email to {recipient}...")
    success = send_email(
        args.sender_email,
        args.sender_name,
        recipient,
        template['subject'],
        template['body'],
        args.smtp_server,
        args.port,
        username,
        args.password
    )
    
    if success:
        print("Email sent successfully. Run the main analysis script to process it.")
        return 0
    else:
        print("Failed to send email.")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main()) 