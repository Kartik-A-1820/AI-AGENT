import asyncio
from pathlib import Path

from assistant_state import ASSISTANT_HOME, WORKSPACE_DIR, ensure_assistant_home
from media_tools import list_omniroute_media_models


async def main() -> None:
    ensure_assistant_home()
    assert ASSISTANT_HOME.exists(), ASSISTANT_HOME
    assert WORKSPACE_DIR.exists(), WORKSPACE_DIR

    media = await list_omniroute_media_models.ainvoke({"kind": "all", "max_results": 5})
    assert "output=" in media or "No Omniroute media models" in media, media

    token_path = ASSISTANT_HOME / "google_token.pickle"
    credentials_path = Path("credentials.json")
    print(f"assistant_home={ASSISTANT_HOME}")
    print(f"workspace={WORKSPACE_DIR}")
    print(f"google_credentials_exists={credentials_path.exists()}")
    print(f"google_token_exists={token_path.exists()}")
    print("media_probe_ok=True")


if __name__ == "__main__":
    asyncio.run(main())
