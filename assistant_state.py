import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_HOME = r"D:\AI\assistant" if os.name == "nt" else os.path.expanduser("~/AI/assistant")
ASSISTANT_HOME = Path(os.getenv("AI_AGENT_HOME", DEFAULT_HOME)).expanduser()
PROFILE_PATH = ASSISTANT_HOME / "profile.json"
MEMORY_PATH = ASSISTANT_HOME / "memory.jsonl"
GRAPH_PATH = ASSISTANT_HOME / "knowledge_graph.json"
TASKS_PATH = ASSISTANT_HOME / "tasks.json"
NOTES_DIR = ASSISTANT_HOME / "notes"
WORKSPACE_DIR = Path(os.getenv("AI_AGENT_WORKSPACE", str(PROJECT_ROOT / "agent_working"))).expanduser()


def ensure_assistant_home() -> None:
    ASSISTANT_HOME.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _load_json(path: Path, default: Any) -> Any:
    ensure_assistant_home()
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _save_json(path: Path, data: Any) -> None:
    ensure_assistant_home()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")


def get_profile() -> dict[str, Any]:
    return _load_json(
        PROFILE_PATH,
        {
            "name": "",
            "timezone": "Asia/Kolkata",
            "preferences": [],
            "important_context": [],
            "updated_at": now_iso(),
        },
    )


def update_profile_field(field: str, value: str) -> dict[str, Any]:
    profile = get_profile()
    if field in {"preferences", "important_context"}:
        items = profile.get(field, [])
        if value not in items:
            items.append(value)
        profile[field] = items
    else:
        profile[field] = value
    profile["updated_at"] = now_iso()
    _save_json(PROFILE_PATH, profile)
    return profile


def append_memory(kind: str, content: str) -> dict[str, str]:
    ensure_assistant_home()
    entry = {
        "id": str(uuid4()),
        "kind": kind,
        "content": content,
        "created_at": now_iso(),
    }
    with MEMORY_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
    return entry


def recent_memories(limit: int = 12) -> list[dict[str, Any]]:
    ensure_assistant_home()
    if not MEMORY_PATH.exists():
        return []
    lines = MEMORY_PATH.read_text(encoding="utf-8").splitlines()
    memories = []
    for line in lines[-max(limit, 1) :]:
        try:
            memories.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return memories


def load_knowledge_graph() -> dict[str, Any]:
    graph = _load_json(GRAPH_PATH, {"nodes": {}, "edges": [], "updated_at": now_iso()})
    if not isinstance(graph, dict):
        return {"nodes": {}, "edges": [], "updated_at": now_iso()}
    graph.setdefault("nodes", {})
    graph.setdefault("edges", [])
    graph.setdefault("updated_at", now_iso())
    return graph


def save_knowledge_graph(graph: dict[str, Any]) -> None:
    graph["updated_at"] = now_iso()
    _save_json(GRAPH_PATH, graph)


def load_tasks() -> list[dict[str, Any]]:
    return _load_json(TASKS_PATH, [])


def save_tasks(tasks: list[dict[str, Any]]) -> None:
    _save_json(TASKS_PATH, tasks)


def add_task(title: str, due: str = "", notes: str = "", priority: str = "normal") -> dict[str, Any]:
    tasks = load_tasks()
    task = {
        "id": str(uuid4())[:8],
        "title": title,
        "due": due,
        "notes": notes,
        "priority": priority,
        "status": "open",
        "created_at": now_iso(),
        "completed_at": "",
    }
    tasks.append(task)
    save_tasks(tasks)
    return task


def complete_task(task_id: str) -> bool:
    tasks = load_tasks()
    completed = False
    for task in tasks:
        if task["id"] == task_id:
            task["status"] = "done"
            task["completed_at"] = now_iso()
            completed = True
            break
    if completed:
        save_tasks(tasks)
    return completed
