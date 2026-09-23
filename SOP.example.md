# EXAMPLE SOP.md — copy to your working directory as `SOP.md` and make it yours.
#
# The manager reads `SOP.md` at session setup and follows it whenever a task
# matches an entry. It is the mechanism for environment-specific procedures:
# how hands-offs work on your machine, how codebases open, worktree quirks,
# auth rituals, anything that was learned the hard way.
#
# Entries are terse: what you want, what actually works. The manager proposes
# new entries as they are discovered; you approve and edit. This file is an
# illustration of the shape — do not use it as-is.

## Handing a worker to the user

Recorded procedure for resuming a worker session so the user can drive it. Pick
ONE mechanism and record it precisely — mixed mechanisms are how mistakes happen.

Example (tmux variant):

```bash
# create one session, one window per worker handle
tmux new-session -d -s prime-worker
tmux new-window -d -t prime-worker -n <handle> -c <workdir> <interactive-resume-command>

# the user attaches:
tmux attach -t prime-worker
```

The resume command is the harness's interactive form (`codex resume <id>`,
`cursor-agent --resume <id>`, `claude --resume <id>`, `prime-agent attach <handle>`) —
never the `-p` / exec forms the manager uses for its own launches.

Constants whatever the mechanism:
- The worker must be idle before handover — two writers on one session is unsafe.
- The manager never attaches to the user's terminal; the final command is the
  user's to run.
- The request is marked `user-driving` during the handoff; the manager stops
  resuming and asks the worker afterwards what was settled.

## Harvesting session tokens (if a harness has no API keys)

If a tool only authenticates via browser session, record the harvest ritual:
where to look (eg browser DevTools → Network → filter on the API host → copy the
session header), where the token is stored (eg a dotenv file, never logged), and
the known failure mode (one live token at a time; a 401 means re-harvest).

## Worktrees

Record anything non-obvious about creating worktrees in your projects: symlink
requirements for relative package links, install steps before checks run
(`pnpm install` before `task check`), tool resolution (mise shims on PATH, no
activation step), and who removes a worktree (the user — never the manager).
