import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from assistant_state import ASSISTANT_HOME, WORKSPACE_DIR, ensure_assistant_home


def status(name: str, ok: bool, detail: str) -> None:
    marker = "OK" if ok else "MISSING"
    print(f"[{marker}] {name}: {detail}")


def main() -> int:
    load_dotenv()
    ensure_assistant_home()

    credentials_path = Path(os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")).expanduser()
    token_path = Path(os.getenv("GOOGLE_TOKEN_PATH", str(ASSISTANT_HOME / "google_token.pickle"))).expanduser()
    omniroute_base = os.getenv("OMNIROUTE_BASE_URL", "http://localhost:20128/v1").rstrip("/")

    status("assistant home", ASSISTANT_HOME.exists(), str(ASSISTANT_HOME))
    status("assistant workspace", WORKSPACE_DIR.exists(), str(WORKSPACE_DIR))
    status("Google OAuth client", credentials_path.exists(), str(credentials_path))
    status("Google token", token_path.exists(), str(token_path))
    status("Tavily web search", bool(os.getenv("TAVILY_API_KEY")), "configured" if os.getenv("TAVILY_API_KEY") else "optional, not configured")
    status("Gemini image generation", bool(os.getenv("GEMINI_API_KEY")), "configured" if os.getenv("GEMINI_API_KEY") else "optional, not configured")

    headers = {}
    api_key = os.getenv("OMNIROUTE_API_KEY") or os.getenv("OPENAI_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        response = requests.get(f"{omniroute_base}/models", headers=headers, timeout=5)
        status("OmniRoute endpoint", response.ok, f"{omniroute_base}/models returned HTTP {response.status_code}")
        if response.ok:
            models = response.json().get("data", [])
            media_models = [
                model for model in models
                if {"image", "video"} & set(model.get("output_modalities") or [])
            ]
            status("OmniRoute media routes", bool(media_models), f"{len(media_models)} image/video routes found")
    except requests.RequestException as exc:
        status("OmniRoute endpoint", False, f"{omniroute_base}/models failed: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
