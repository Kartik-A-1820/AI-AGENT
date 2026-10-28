"""Resolve host-side file tool paths, including existing symlinks."""
from pathlib import Path

def confined_path(root, filename):
    root = Path(root).resolve()
    target = (root / filename).resolve()
    if target == root or not target.is_relative_to(root):
        raise ValueError('Path must be a file inside agent_working')
    return target
