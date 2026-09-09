from langchain.tools import tool
from pydantic import BaseModel, Field

from assistant_state import (
    add_task as store_task,
    append_memory,
    complete_task as mark_task_done,
    get_profile,
    load_tasks,
    recent_memories,
    update_profile_field,
)


class RememberInput(BaseModel):
    content: str = Field(..., description="The useful fact, preference, note, or decision to remember.")
    kind: str = Field("note", description="Memory type such as preference, project, person, note, or decision.")


@tool(args_schema=RememberInput)
def remember(content: str, kind: str = "note") -> str:
    """Store a durable memory for future assistant sessions."""
    entry = append_memory(kind=kind, content=content)
    return f"Remembered {entry['kind']} memory {entry['id']}."


class ProfileInput(BaseModel):
    field: str = Field(..., description="Profile field to update: name, timezone, preferences, or important_context.")
    value: str = Field(..., description="Value to store.")


@tool(args_schema=ProfileInput)
def update_user_profile(field: str, value: str) -> str:
    """Update the user's durable assistant profile."""
    allowed = {"name", "timezone", "preferences", "important_context"}
    if field not in allowed:
        return f"Unsupported profile field. Use one of: {', '.join(sorted(allowed))}."
    profile = update_profile_field(field, value)
    return f"Profile updated. Current {field}: {profile.get(field)}"


@tool
def recall_context(limit: int = 12) -> str:
    """Recall the user's profile and recent durable memories."""
    profile = get_profile()
    memories = recent_memories(limit=limit)
    memory_text = "\n".join(
        f"- [{item.get('kind', 'note')}] {item.get('content', '')} ({item.get('created_at', '')})"
        for item in memories
    )
    return f"Profile:\n{profile}\n\nRecent memories:\n{memory_text or 'No stored memories yet.'}"


class TaskInput(BaseModel):
    title: str = Field(..., description="Task title.")
    due: str = Field("", description="Optional due date/time in natural language or ISO format.")
    notes: str = Field("", description="Optional task notes.")
    priority: str = Field("normal", description="Priority: low, normal, high, or urgent.")


@tool(args_schema=TaskInput)
def add_personal_task(title: str, due: str = "", notes: str = "", priority: str = "normal") -> str:
    """Add a personal task to the local assistant task list."""
    task = store_task(title=title, due=due, notes=notes, priority=priority)
    return f"Task added: [{task['id']}] {task['title']} due: {task['due'] or 'unscheduled'}."


@tool
def list_personal_tasks(include_done: bool = False) -> str:
    """List locally stored personal tasks."""
    tasks = load_tasks()
    visible = [task for task in tasks if include_done or task.get("status") != "done"]
    if not visible:
        return "No matching tasks."
    return "\n".join(
        f"[{task['id']}] {task['status']} | {task.get('priority', 'normal')} | {task['title']} | due: {task.get('due') or 'unscheduled'}"
        for task in visible
    )


@tool
def complete_personal_task(task_id: str) -> str:
    """Mark a local personal task as done by task ID."""
    if mark_task_done(task_id):
        return f"Task {task_id} marked done."
    return f"No task found with ID {task_id}."


@tool
def daily_brief() -> str:
    """Create a local daily brief from profile, open tasks, and recent memories."""
    profile = get_profile()
    tasks = [task for task in load_tasks() if task.get("status") != "done"]
    memories = recent_memories(limit=5)
    lines = [
        f"Daily brief for {profile.get('name') or 'you'}",
        f"Timezone: {profile.get('timezone', 'Asia/Kolkata')}",
        "",
        "Open tasks:",
    ]
    lines.extend(
        f"- [{task['id']}] {task['title']} ({task.get('priority', 'normal')}, due: {task.get('due') or 'unscheduled'})"
        for task in tasks[:10]
    )
    if not tasks:
        lines.append("- No open local tasks.")
    lines.append("")
    lines.append("Recent context:")
    lines.extend(f"- {memory.get('content', '')}" for memory in memories)
    if not memories:
        lines.append("- No recent stored memories.")
    return "\n".join(lines)
