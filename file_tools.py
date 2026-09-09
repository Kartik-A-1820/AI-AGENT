import os

from langchain.tools import tool
from assistant_state import WORKSPACE_DIR, ensure_assistant_home


ensure_assistant_home()
AGENT_DIR = str(WORKSPACE_DIR)
os.makedirs(AGENT_DIR, exist_ok=True)


def _safe_agent_path(filename: str) -> str:
    filepath = os.path.abspath(os.path.join(AGENT_DIR, filename))
    working_dir = os.path.abspath(AGENT_DIR)

    if os.path.commonpath([filepath, working_dir]) != working_dir:
        raise ValueError("Attempt to access outside agent_working is not allowed.")

    return filepath


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
