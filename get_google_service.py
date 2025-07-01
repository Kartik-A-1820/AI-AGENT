from langchain.tools import tool
from datetime import datetime, timedelta
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Add calendar scope + your previous scopes
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar", # Calendar API scope
    "https://www.googleapis.com/auth/gmail.send", # Gmail send scope
    "https://www.googleapis.com/auth/gmail.readonly", # Gmail read scope
    "https://www.googleapis.com/auth/drive", # Google Drive scope
]

def get_google_credentials(scopes=None):
    scopes = scopes or GOOGLE_SCOPES
    if os.path.exists('token.json'):
        with open('token.json', 'rb') as token:
            creds = pickle.load(token)
    else:
        creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scopes)
            creds = flow.run_local_server(port=8080)
        with open('token.json', 'wb') as token:
            pickle.dump(creds, token)
    return creds