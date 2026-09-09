import os
import pickle
import webbrowser
from pathlib import Path

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

load_dotenv()

from assistant_state import ASSISTANT_HOME, ensure_assistant_home

# Add calendar scope + your previous scopes
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar", # Calendar API scope
    "https://www.googleapis.com/auth/gmail.send", # Gmail send scope
    "https://www.googleapis.com/auth/gmail.readonly", # Gmail read scope
    "https://www.googleapis.com/auth/drive", # Google Drive scope
]

def get_google_credentials(scopes=None):
    scopes = scopes or GOOGLE_SCOPES
    ensure_assistant_home()
    credentials_path = Path(os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")).expanduser()
    token_path = Path(os.getenv("GOOGLE_TOKEN_PATH", str(ASSISTANT_HOME / "google_token.pickle"))).expanduser()

    if not credentials_path.exists():
        raise FileNotFoundError(
            f"Google OAuth credentials file not found at {credentials_path}. "
            "Create a Desktop OAuth client in Google Cloud Console and download it as credentials.json."
        )

    creds = None
    if token_path.exists():
        with token_path.open('rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), scopes)
            browser = os.getenv("GOOGLE_AUTH_BROWSER")
            if browser and Path(browser).exists():
                webbrowser.register("brave", None, webbrowser.BackgroundBrowser(browser))
                browser = "brave"
            creds = flow.run_local_server(port=8080, browser=browser)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with token_path.open('wb') as token:
            pickle.dump(creds, token)
    return creds


if __name__ == "__main__":
    get_google_credentials()
    print("Google OAuth token created.")
