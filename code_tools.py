import os
import re
import subprocess
import sys
from pathlib import Path

from langchain.tools import tool
from pydantic import BaseModel, Field

from async_utils import format_exception, retry_blocking
from file_tools import AGENT_DIR, _safe_agent_path


VENV_DIR = Path(os.getenv("AI_AGENT_VENV", r"D:\AI\venvs\ai-agent" if os.name == "nt" else ".venv")).expanduser()
PYTHON_EXE = VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
FORBIDDEN_CODE_PATTERNS = [
    r"\bos\.remove\b",
    r"\bos\.unlink\b",
    r"\bos\.rmdir\b",
    r"\bshutil\.rmtree\b",
    r"\bPath\s*\([^)]*\)\.unlink\b",
    r"\bPath\s*\([^)]*\)\.rmdir\b",
    r"\bsubprocess\.",
    r"\bRemove-Item\b",
    r"\brm\s+-",
    r"\bdel\s+",
    r"\brmdir\s+",
]


def _python_executable() -> str:
    if PYTHON_EXE.exists():
        return str(PYTHON_EXE)
    return sys.executable


def _reject_unsafe_code(code: str) -> None:
    for pattern in FORBIDDEN_CODE_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            raise ValueError(f"Code contains a blocked filesystem/process operation: {pattern}")

    sandbox = str(Path(AGENT_DIR).resolve()).lower()
    for path in re.findall(r"[A-Za-z]:\\[^'\"\n\r]+", code):
        normalized = str(Path(path).resolve()).lower()
        if not normalized.startswith(sandbox):
            raise ValueError(f"Absolute path outside sandbox is blocked: {path}")


class RunPythonCodeInput(BaseModel):
    code: str = Field(..., description="Python code to run inside the assistant sandbox.")
    filename: str = Field("task_script.py", description="Script filename saved under the sandbox.")
    timeout_seconds: int = Field(120, description="Maximum runtime in seconds.")


def _run_python_code_sync(code: str, filename: str, timeout_seconds: int) -> str:
    _reject_unsafe_code(code)
    script_path = _safe_agent_path(os.path.join("_scripts", filename))
    Path(script_path).parent.mkdir(parents=True, exist_ok=True)
    Path(script_path).write_text(code, encoding="utf-8")
    result = subprocess.run(
        [_python_executable(), script_path],
        cwd=AGENT_DIR,
        text=True,
        capture_output=True,
        timeout=max(1, min(timeout_seconds, 900)),
    )
    output = result.stdout.strip()
    error = result.stderr.strip()
    parts = [f"exit_code={result.returncode}", f"script={script_path}"]
    if output:
        parts.append(f"stdout:\n{output[-6000:]}")
    if error:
        parts.append(f"stderr:\n{error[-6000:]}")
    return "\n\n".join(parts)


@tool(args_schema=RunPythonCodeInput)
async def run_python_code(code: str, filename: str = "task_script.py", timeout_seconds: int = 120) -> str:
    """Run Python code from a sandboxed script using the assistant's dedicated venv."""
    try:
        return await retry_blocking(_run_python_code_sync, code, filename, timeout_seconds, attempts=1)
    except Exception as exc:
        return f"Python code was blocked or failed: {format_exception(exc)}"


class PipInstallInput(BaseModel):
    package: str = Field(..., description="Package specifier to install, for example 'reportlab' or 'beautifulsoup4>=4.12'.")


def _install_python_package_sync(package: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.\-\[\],<>=!~ ]+", package):
        raise ValueError("Package specifier contains unsupported characters.")
    result = subprocess.run(
        [_python_executable(), "-m", "pip", "install", package],
        cwd=AGENT_DIR,
        text=True,
        capture_output=True,
        timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip()[-4000:] or result.stdout.strip()[-4000:])
    return f"Installed into {VENV_DIR}: {package}"


@tool(args_schema=PipInstallInput)
async def install_python_package(package: str) -> str:
    """Install a Python package into the assistant's dedicated virtual environment."""
    try:
        return await retry_blocking(
            _install_python_package_sync,
            package,
            attempts=2,
            base_delay=3,
            max_delay=10,
        )
    except Exception as exc:
        return f"Package install failed after retries: {format_exception(exc)}"
