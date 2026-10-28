import os

from langchain.tools import tool
from workspace_paths import confined_path
from assistant_state import WORKSPACE_DIR, ensure_assistant_home


ensure_assistant_home()
AGENT_DIR = str(WORKSPACE_DIR)
os.makedirs(AGENT_DIR, exist_ok=True)


def _safe_agent_path(filename: str) -> str:
    return str(confined_path(AGENT_DIR, filename))


@tool
def write_to_file(filename: str, content: str) -> str:
    """
    Writes text content to a file within the 'agent_working' directory.
    """
    try:
        filepath = _safe_agent_path(filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {filename}."
    except Exception as e:
        return f"Write failed: {str(e)}"


@tool
def read_from_file(filename: str) -> str:
    """
    Reads the contents of a file from 'agent_working'.
    """
    try:
        filepath = _safe_agent_path(filename)
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Read failed: {str(e)}"
