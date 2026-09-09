import asyncio
from pathlib import Path

from assistant_state import ASSISTANT_HOME, GRAPH_PATH, WORKSPACE_DIR, ensure_assistant_home
from code_tools import run_python_code
from graph_memory import add_graph_fact, format_graph_context
from media_tools import list_omniroute_media_models


async def main() -> None:
    ensure_assistant_home()
    assert ASSISTANT_HOME.exists(), ASSISTANT_HOME
    assert WORKSPACE_DIR.exists(), WORKSPACE_DIR

    add_graph_fact(
        subject="AI-AGENT",
        relation="uses",
        object_value="local knowledge graph memory",
        subject_type="project",
        object_type="concept",
        evidence="Smoke test graph fact.",
    )
    graph_context = format_graph_context("AI-AGENT memory", limit=3)
    assert "local knowledge graph memory" in graph_context or "AI-AGENT" in graph_context, graph_context

    media = await list_omniroute_media_models.ainvoke({"kind": "all", "max_results": 5})
    assert "output=" in media or "No Omniroute media models" in media, media

    blocked = await run_python_code.ainvoke(
        {
            "code": 'from pathlib import Path\nPath(r"C:\\temp\\ai_agent_blocked.txt").write_text("blocked")',
            "filename": "blocked_outside_path.py",
        }
    )
    assert "outside sandbox is blocked" in blocked, blocked

    allowed = await run_python_code.ainvoke(
        {
            "code": 'from pathlib import Path\nPath("smoke.txt").write_text("ok", encoding="utf-8")\nprint(Path("smoke.txt").resolve())',
            "filename": "allowed_sandbox_write.py",
        }
    )
    assert "exit_code=0" in allowed, allowed

    token_path = ASSISTANT_HOME / "google_token.pickle"
    credentials_path = Path("credentials.json")
    print(f"assistant_home={ASSISTANT_HOME}")
    print(f"workspace={WORKSPACE_DIR}")
    print(f"google_credentials_exists={credentials_path.exists()}")
    print(f"google_token_exists={token_path.exists()}")
    print(f"knowledge_graph_exists={GRAPH_PATH.exists()}")
    print("graph_memory_ok=True")
    print("media_probe_ok=True")
    print("sandbox_code_guard_ok=True")


if __name__ == "__main__":
    asyncio.run(main())
