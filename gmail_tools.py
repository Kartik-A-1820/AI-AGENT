from langchain.tools import tool
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import pickle
from googleapiclient.discovery import build
from get_google_service import get_google_credentials

def get_gmail_service():
    creds = get_google_credentials()
    return build('gmail', 'v1', credentials=creds)

class SendGmailInput(BaseModel):
    recipient: str = Field(..., description="The recipient's email address.")
    subject: str = Field(..., description="The subject of the email.")
    body: str = Field(..., description="The body of the email.")
    attachments: Optional[List[str]] = Field(None, description="A list of local file paths to attach.")

@tool(args_schema=SendGmailInput)
def send_gmail(recipient: str, subject: str, body: str, attachments: Optional[List[str]] = None) -> str:
    """Send an email with optional attachments."""
    try:
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders
        import base64

        service = get_gmail_service()
        message = MIMEMultipart()
        message["to"] = recipient
        message["subject"] = subject
        message.attach(MIMEText(body, "plain"))

        if attachments:
            for file_path in attachments:
                with open(file_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition", f"attachment; filename={os.path.basename(file_path)}"
                )
                message.attach(part)

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        result = service.users().messages().send(userId="me", body={"raw": raw_message}).execute()
        return f"Email sent! Message ID: {result['id']}"
    except Exception as e:
        return f"Failed to send email: {e}"

class ReadGmailInput(BaseModel):
    query: str = Field("", description="The query to search for in emails.")
    max_results: int = Field(5, description="The maximum number of emails to return.")

@tool(args_schema=ReadGmailInput)
def read_gmail(query: str = "", max_results: int = 5) -> str:
    """Read recent emails matching a query."""
    try:
        import base64
        from email import message_from_bytes

        service = get_gmail_service()
        results = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
        messages = results.get("messages", [])
        if not messages:
            return "No emails found."
        summary = ""
        for msg in messages:
            msg_id = msg["id"]
            msg_data = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
            headers = msg_data["payload"].get("headers", [])
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
            from_ = next((h["value"] for h in headers if h["name"] == "From"), "")
            snippet = msg_data.get("snippet", "")
            summary += f"From: {from_}\nSubject: {subject}\nSnippet: {snippet[:250]}...\n{'-'*40}\n"
        return summary
    except Exception as e:
        return f"Failed to read email: {e}"

