from dotenv import load_dotenv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from lambda_function import compose_email_body, send_email

# Load environment variables from .env file
load_dotenv()

# Test data
google_updates = {
    '"Data Science" AND "Video Games"': [
        {'title': 'Article 1', 'link': 'https://example.com/article1', 'date': '2024-06-29'},
        {'title': 'Article 2', 'link': 'https://example.com/article2', 'date': '2024-06-28'},
    ]
}

kaggle_updates = [
    {'title': 'Kaggle Competition 1', 'link': 'https://kaggle.com/competition1', 'date': '2024-07-01'},
    {'title': 'Kaggle Competition 2', 'link': 'https://kaggle.com/competition2', 'date': '2024-07-02'},
]

# Replace with your email for testing
test_email = "bholding@live.com"

# Compose the email body using the test data
email_body = compose_email_body(google_updates, kaggle_updates)

# Send a test email using the imported send_email function
subject = "Test Email: Google Scholar and Kaggle Updates"
email_sent = send_email(subject, email_body, test_email)

if email_sent:
    print("Test email sent successfully.")
else:
    print("Failed to send test email.")