"""Ordered work items the manager tracks across sessions.

Data lives in `state/work-items.json`; this module is the only writer.
An item has a description and an ordered list of steps. A step carries the
detail we have now; later steps can be a single sentence and get fleshed out
when we reach them.

Usage:
    items = WorkItems.load()
    items.add_item("ELIZA", "description")
    items.add_step("ELIZA", "first step", detail="...")
    items.tick("ELIZA", 1)          # 1-based step number
    print(items.render())
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

def default_path() -> Path:
    """Resolve the work-items file for this session.

    Order: an explicit override, then the hub directory in HUB_MODE, then the
    session directory. The hub gives every manager in it one shared list; a
    project-mode session gets its own.
    """
    override = os.environ.get("PRIME_WORK_TRACKER_PATH")
    if override:
        return Path(override)
    workspaces = os.environ.get("PRIME_WORKER_WORKSPACES")
    if os.environ.get("PRIME_WORKER_MODE") == "HUB_MODE" and workspaces:
        return Path(workspaces).resolve().parent / "work-tracker" / "work-items.json"
    session = os.environ.get("RLM_SESSION_DIR")
    if session:
        return Path(session) / "manager" / "work-tracker" / "work-items.json"
    return Path.home() / ".prime" / "work-tracker" / "work-items.json"


DEFAULT_PATH = default_path()

STATUS_MARKS = {"pending": "[ ]", "active": "[>]", "done": "[x]"}


class WorkItemConflict(RuntimeError):
    """Raised when the file changed on disk after this object loaded it."""


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class WorkItems:
    def __init__(self, path: Path = DEFAULT_PATH, items: dict | None = None, digest: str | None = None):
        self.path = Path(path)
        self.items: dict = items if items is not None else {}
        # Digest of the file this object loaded. None when the file was absent.
        self.digest = digest

    # --- persistence -------------------------------------------------
    @classmethod
    def load(cls, path: Path = DEFAULT_PATH) -> "WorkItems":
        path = Path(path)
        if not path.exists():
            return cls(path, {}, None)
        text = path.read_text()
        return cls(path, json.loads(text).get("items", {}), _digest(text))

    def reload(self) -> "WorkItems":
        """Discard local changes and re-read the file."""
        fresh = self.load(self.path)
        self.items, self.digest = fresh.items, fresh.digest
        return self

    def save(self, force: bool = False) -> None:
        """Write the file, refusing when another writer changed it since load."""
        if not force:
            current = self.path.read_text() if self.path.exists() else None
            current_digest = None if current is None else _digest(current)
            if current_digest != self.digest:
                raise WorkItemConflict(
                    f"{self.path} changed on disk since it was loaded "
                    f"(loaded {self.digest}, found {current_digest}). "
                    "Reload it and re-apply your change, or save(force=True) to overwrite."
                )
        text = json.dumps({"items": self.items}, indent=2) + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(text)
        self.digest = _digest(text)

    # --- editing -----------------------------------------------------
    def add_item(self, name: str, description: str = "") -> dict:
        item = self.items.setdefault(name, {"description": description, "steps": []})
        if description:
            item["description"] = description
        self.save()
        return item

    def add_step(self, name: str, text: str, detail: str = "", status: str = "pending") -> int:
        item = self.add_item(name)
        item["steps"].append({"text": text, "detail": detail, "status": status})
        self.save()
        return len(item["steps"])

    def insert_step(self, name: str, step: int, text: str, detail: str = "",
                    status: str = "pending") -> int:
        """Insert a step before `step` (1-based); use len(steps)+1 to append."""
        item = self.add_item(name)
        index = max(1, min(step, len(item["steps"]) + 1)) - 1
        item["steps"].insert(index, {"text": text, "detail": detail, "status": status})
        self.save()
        return index + 1

    def remove_step(self, name: str, step: int) -> dict:
        """Drop a step. Later steps shift down one number."""
        return self._mutate_step(name, step, lambda steps, i, _s: steps.pop(i))

    def note(self, name: str, step: int, text: str) -> dict:
        """Append a review comment to a step, leaving its text and detail alone."""
        return self._mutate_step(name, step, lambda _steps, _i, s: s.setdefault("notes", []).append(text))

    def tick(self, name: str, step: int, status: str = "done") -> dict:
        return self._mutate_step(name, step, lambda _steps, _i, s: s.__setitem__("status", status))

    def _mutate_step(self, name: str, step: int, change) -> dict:
        """Apply one change to a step and save. `change` takes (steps, index, step)."""
        item = self.items[name]
        index = step - 1
        try:
            step_obj = item["steps"][index]
        except IndexError:
            raise IndexError(f"{name} has no step {step}") from None
        change(item["steps"], index, step_obj)
        self.save()
        return step_obj

    def rename(self, name: str, new_name: str) -> None:
        self.items[new_name] = self.items.pop(name)
        self.save()

    # --- reporting ---------------------------------------------------
    def render(self, only_open: bool = False) -> str:
        lines = []
        for name, item in self.items.items():
            steps = item.get("steps", [])
            if only_open and steps and all(s["status"] == "done" for s in steps):
                continue
            done = sum(1 for s in steps if s["status"] == "done")
            lines.append(f"{name}  ({done}/{len(steps)} done) — {item.get('description', '')}".rstrip(" —"))
            for i, step in enumerate(steps, start=1):
                mark = STATUS_MARKS.get(step["status"], "[ ]")
                lines.append(f"  {mark} {i}. {step['text']}")
                for note in step.get("notes", []):
                    lines.append(f"        - {note}")
        return "\n".join(lines) if lines else "(no work items)"


if __name__ == "__main__":
    import sys

    print(WorkItems.load().render(only_open="--open" in sys.argv))
