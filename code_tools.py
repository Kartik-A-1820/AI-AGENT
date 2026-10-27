from langchain.tools import tool
from pydantic import BaseModel, Field
from async_utils import format_exception, retry_blocking
from file_tools import AGENT_DIR
from isolated_runner import run_python

class RunPythonCodeInput(BaseModel):
    code: str = Field(..., description='Python code for an isolated, network-disabled container.')
    filename: str = Field('task_script.py', description='Simple Python filename.')
    timeout_seconds: int = Field(120, ge=1, le=900)
    input_files: list[str] = Field(default_factory=list, max_length=10, description='Workspace-relative inputs explicitly copied into the isolated job.')

def _run_python_code_sync(code, filename, timeout_seconds, input_files=()):
    return run_python(code, filename, timeout_seconds, AGENT_DIR, input_files)

@tool(args_schema=RunPythonCodeInput)
async def run_python_code(code: str, filename: str = 'task_script.py', timeout_seconds: int = 120, input_files: list[str] | None = None) -> str:
    """Run code in a restricted Docker job; disabled unless the owner opts in."""
    try:
        return await retry_blocking(_run_python_code_sync, code, filename, timeout_seconds, input_files or [], attempts=1)
    except Exception as exc:
        return f'Python code blocked or failed: {format_exception(exc)}'

@tool
async def install_python_package(package: str) -> str:
    """Disabled compatibility shim; dependency images must be prepared by the owner."""
    return 'Runtime package installation is disabled. Ask the owner to build a trusted Docker image with the needed dependencies.'
