---
name: work-tracker
description: Track an ordered list of work items across sessions with a small disk-backed tracker - add items, add and tick steps, and remind the user where things stand. Use when the user asks what is next, what is left, to remember a plan, or when a multi-step task spans several turns or workers.
---

# Simple project management

Keep one ordered list of work items on disk, tick steps off as they complete, and use it
to answer "what is next?" without re-reading the whole conversation.

## The tracker

- Code: `lib/work_tracker.py`, inside this skill directory. Load it from there, so it
  works wherever the skill is installed.
- Data: resolved at run time by `default_path()`, in this order:
  1. `$PRIME_WORK_TRACKER_PATH` when set — an explicit override.
  2. In `HUB_MODE`, `<hub>/work-tracker/work-items.json`, where the hub is the directory
     holding `$PRIME_WORKER_WORKSPACES`. Every manager in the hub shares one list.
  3. Otherwise `$RLM_SESSION_DIR/manager/work-tracker/work-items.json` — a list for this
     session only, so a new session starts empty unless the override points elsewhere.

Load it once in the kernel and keep the object:

```python
import importlib.util
# `skill` is this skill's directory; the module sits beside this file.
spec = importlib.util.spec_from_file_location("work_tracker", f"{skill}/lib/work_tracker.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
items = mod.WorkItems.load()          # or WorkItems.load("/some/explicit/path.json")
```

API: `add_item(name, description)`, `add_step(name, text, detail="", status="pending")`,
`insert_step(name, step_number, text, detail="")`, `remove_step(name, step_number)`,
`tick(name, step_number, status="done")`, `note(name, step_number, text)`,
`rename(name, new_name)`, `render(only_open=False)`.
Steps are numbered by position, so inserting or removing renumbers the steps after it.
`save()` is called for you. From a shell: `python3 lib/work_tracker.py` or `--open`.

Statuses: `pending` `[ ]`, `active` `[>]` (a worker is on it now), `done` `[x]`.

## Several managers at once

More than one manager can hold this file. Loading records a digest of the file, and
`save()` refuses to write when the file changed since that load, raising
`WorkItemConflict`. On conflict, do not force: `reload()` to take the other writer's
version, re-apply your change, and save again. If the two changes genuinely collide, ask
the user to resolve it. `save(force=True)` exists for a deliberate overwrite only.

## How to record

- One item per work stream, named in capitals so it can be referred to in conversation
  ("ELIZA", "2br status copy"). The description is one line.
- Steps are ordered. **The current step carries the detail** — paths, decisions, what
  passed, what to review. Later steps stay one sentence and get fleshed out when you
  reach them.
- Tick a step when it is finished, not when it is dispatched. Mark it `active` while a
  worker runs.
- Fold a finished item's leftover notes into the step that closed it, then leave the
  item in place until the user says it is done.

## How to remind

List the items in order, each with its description and its next open step. Keep it
short: the user reads this to re-orient, not to review everything. Report the render
as-is when they ask what is next, and name the item you are about to work on.

## Working agreement

- One small step per dispatch; the user reacts to each result before the next one starts.
- A worker that finds something outside its brief reports it; it does not do it.
- Workers leave changes uncommitted. The manager reviews and commits. Codex
  `workspace-write` cannot write `.git` at all, and cursor needs its prompt as a
  positional argument.
- No wrapper helpers to hide an API. If a call site is clumsy, change the API or leave it.
- Report the outcome first, then paths. Do not paste file contents into chat.
