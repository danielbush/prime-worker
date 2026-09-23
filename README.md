# prime-worker

You run [prime-agent](https://github.com/PrimeIntellect-ai/prime-agent) and chat
to an agent acting as your managing agent. The manager delegates/routes work
(eg coding, investigation, review) to other agents. Those agents could be
running in cursor, codex, claude-code or natively (using prime-agent via
[RLM](https://www.primeintellect.ai/blog/rlm)]).

You talk to the manager in your own words:

```text
get grok to implement demo 2 in notes.md
get sol to review grok's work
get grok to process sol's review
```

It resolves the name to a model, effort level and harness, launches a worker,
tracks it, and relays the result. It does not investigate, plan, or rewrite what
you asked for unless you want it to.  The manager tracks worker sessions so you
can feed work to an existing worker eg to give feedback.

For smaller things it's very possible to just iterate with the manager as the
go-between.  It can resume the worker agent session and give feedback etc.  For
more involved things I like to get the manager to resume a session for a worker
agent so I can drop in and talk directly to the worker.  See author's notes
below about code architecture and why this might still be necessary.

Inspired by Kun Chen's [firstmate](https://github.com/kunchenguid/firstmate).

## Example session

![A prime-worker session](docs/example-session.png)

What is happening there:

- Feedback for an agent already working is routed to **that** worker, in its existing
  Codex session — `sol-chat-focus-bug`, thread `01a08da6…` — rather than starting a new
  one. Three turns of work, one session.
- The launch does not block. The manager reports what it sent and ends the turn.
- A one-minute heartbeat checks the external worker (external harness) until it exits, then reads its
  output, relays the result, updates the record, and deletes itself.
- Asking "what sol sessions do we have?" is answered from the request record: each
  worker handle, its harness session ID, what it was asked, and its status.

### The author's note

My thoughts and assumptions as at Aug-2026:

- I tend to use HUB_MODE - PROJECT_MODE was used initially to bootstrap this project; it's probably still usable, but I prefer
  to have my working notes, todo's etc in a working dir.
- I'm running on a budget so I'm generally not using intelligence signifcantly above sol 5.6 medium level
- I'm juggling between very modest codex, cursor, claude subscriptions and trying to take advantage of cheap but powerful open weight models via openrouter or similar
- I'm working on slightly novel non-trivial projects, and I'm just not comfortable blackboxing them, I need to understand the code at least as a well-structured system and my obervation is that agents can write great code but architecture is not quite there (this is changing all the time)
- I have various directives for the coding agent to encourage it to structure code so it's not just a bag of functions and to encourage it to focus on entities and data modelling and testable code (eg dependency injection, nulled instances). This is not included here, it's something you put in or link to from your AGENTS.md for the project the coding agent is working on
- My preferred approach is:
  - avoid ai generated plans; faithfully relay or expand the user's words
  - the user's words are much easier for the user to understand
  - the user is not good at reviewing long documents that have hidden catches or assumptions
  - user should try to work in small iterations with immediate demonstrable feedback to keep any planning small
    - also avoids risk of generating lots of code unanchored to some tangible outcome, which is very easy to do with agents.
    - (In other words, agile still wins and waterfall can be weirdly magnified via AI slop)
  - ambiguities and misunderstandings get hammered out in review of each small iteration rather than trying to plan them away up front
- Earlier attempts at a managing agent in pi or prime-agent harness didn't work for me
  - they had project management structures and workflows which I could not decide on
  - it led to a weird combination of scripting and deterministic code mixed with agent discretion
  - you can end up writing lots of "management code" this way, which I ended up throwing away
  - everything took time with workflows: a model might write up a feature or issue, another model would draft a plan, then that plan would be sent to another model to implement, then finally the work would be given to another model to review...
  - "game of telephone" effect: things would get put into the plan that I didn't expect and then were faithfully executed by the coding agent,
  - excessive review not commensurate with the type/scope/intention of the task
  - all of which leads to "paperwork fatigue": too much ai generated verbiage: I'd spend time reading long ai-generated descriptions and plans and reviews
- I've played with using various models to act as the managing agent
  - atm GLM 5.3 flash via openrouter is cheap as chips and quite solid if you can find a fast provider. deepseek v4 flash
    on high also cheap sometimes frustrating; both have large context. You can also use openai models (at
    the time, you can use openai subscription with pi / prime-agent harness).

## Setup

You need Prime Agent installed and authenticated, plus the CLI of any external harness
you use (`codex login`, `cursor-agent login`, `claude`). `tmux` is optional — it is only
needed to [talk to a worker directly](#talking-to-a-worker-yourself).

Procedures like these are not hard-coded. There is an SOP mechanism: the manager reads
an `SOP.md` at the working directory, where the user and manager set up their own
custom procedures — how to resume a worker agent for the user (tmux, iTerm2, zellij,
a plain command in another terminal), how to open codebases, how to use worktrees,
environment quirks and gotchas. What is in `SOP.md` overrides the defaults described
in this README and the skill docs; new discoveries get appended there as they are
confirmed. See [SOP.example.md](./SOP.example.md) for the shape of one.

While a worker runs, the machine is kept awake with `caffeinate` (macOS) or
`systemd-inhibit` (Linux), via [bin/keep-awake](./bin/keep-awake). If neither is
usable, workers still run, just without the lock, and the manager tells you so once.

Put the CLI on your PATH:

```bash
ln -s /path/to/prime-worker/bin/prime-worker ~/.local/bin/prime-worker
```

There is a [Taskfile.yml](./Taskfile.yml).

## Use

### Two modes

**`PROJECT_MODE`**: launch prime-worker inside a project

```bash
cd /path/to/your-project
prime-worker
```

That opens the normal interactive Prime Agent UI with the manager active, in your
project, so its `AGENTS.md` and skills load as usual. Then just talk to it.

**`HUB_MODE`** lets one session drive several projects. Put a `workspaces.toml` in a
folder and launch from there:

```toml
[workspaces]
api = "/path/to/api"
web = "/path/to/web"
```

```bash
cd ~/work        # the folder holding workspaces.toml
prime-worker
```

Now you name the project: "get grok to implement demo 2 in api". Worktrees are not
configured here — they are discovered with `git worktree list` when needed.

The mode is decided by whether `workspaces.toml` is in the directory you launch from.
See [workspaces.example.toml](workspaces.example.toml).

In general:

Prime Agent flags pass through (`prime-worker --resume`, `--model ...`). The script's
own flag is `--models <path>` to use a different alias file. Without it, a `models.toml`
in the directory you launch from is used, else this repo's.

Do not use `-p` / `--print` / `--mode json`: those are one-shot sessions that get torn
down at the end of the turn, cancelling any worker mid-task.

## Configuring agents

[models.toml](models.toml) is the only file you edit. It is keyed by harness, then
agent:

```toml
[defaults]
grok = "cursor"        # the harness grok uses unless you say otherwise

[cursor.grok]
default   = "high"     # the effort used unless you name another
high      = "cursor-grok-4.6-high"
high-fast = "cursor-grok-4.6-high-fast"   # used when you say "fast"

[codex.sol]
default = "medium"
medium  = "gpt-5.6-sol"
high    = "gpt-5.6-sol"
```

Say a harness or an effort to override the default for one request — "get sol high to
review this", "get grok to implement demo 2 with codex". Anything not listed is not
configured: the manager says so rather than assembling a model name.

Work is passed out to external harnesses:

| Say     | Harness     | Model                                                  |
| ------- | ----------- | ------------------------------------------------------ |
| `grok`  | Cursor      | `cursor-grok-4.6-high` (`grok fast` for the fast tier) |
| `sol`   | Codex       | `gpt-5.6-sol` at medium                                |
| `astra` | Codex       | `gpt-6-astra` at low                                   |
| `opus`  | Claude Code | `claude-opus-5` at high                                |
| `fable` | Claude Code | `claude-fable-5-1` at high                             |

Plus native workers for `kimi`, `deeppro`, `deepflash`, and `glm`, which run as Prime
Agent children rather than a separate CLI.

## How it works

- **Skill loading:** the `prime-worker` launcher passes every `skills/*/SKILL.md` in
  this repo to prime-agent as `--skill <dir>`, and sends `/skill:manager` as the first
  message — loading a skill does not activate it, so the manager runs the session and
  pulls in the others (e.g. `external-harnesses` for a CLI worker) on demand. Skills are
  surfaced to the model as metadata (name, path, description); bodies are read at
  runtime, as are `SOP.md`, `models.toml`, and `workspaces.toml`.
- **Runtime:** the manager is a prime-agent session with the `manager` skill active,
  running an RLM Python kernel as its control environment. Model aliases resolve through
  `models.toml`; projects resolve through `workspaces.toml` (HUB_MODE) or the working
  directory (PROJECT_MODE). The launcher exports these as environment variables
  (`PRIME_WORKER_MODELS`, `PRIME_WORKER_MODE`, `PRIME_WORKER_WORKSPACES`,
  `PRIME_WORKER_KEEP_AWAKE`).
- **Worker state:** native workers are RLM children (`rlm.spawn`); results arrive as
  agent messages. External workers are CLI processes (`codex exec resume`, `cursor-agent
  -p --resume`, `claude -p --resume`), each wrapped in `bin/keep-awake`; a one-minute
  heartbeat polls their exit and reads their output files.
- **Records:** the session directory
  `~/.prime/agent/session-artifacts/<session-id>/manager/` holds `requests.md` — one
  entry per request: your wording, the worker handle, the harness session ID, status and
  result — plus each worker's assignment file and output capture. Coordination records
  never land in the target repository.
- **Concurrency:** several workers may share a checkout with no locking. Worktrees are
  opt-in, plain `git worktree` under `<hub>/worktrees/<workspace>/<worker-handle>` in
  HUB_MODE; the manager records ownership and never removes one.
- **Memory:** RLM kernel variables last only until compaction or kernel restart; the
  session directory is the durable layer; `SOP.md` is the environment-procedure layer.
- **Harness state (currently disabled):** prime-agent also provides a "refinement"
  mechanism — `refine.run()` persists prompt notes, memories, and subagent specs into
  the session's `harness_state.json` (plus a global store), injected into future system
  prompts as digests; automatic refinement is governed by `autoRefine.enabled` in
  `~/.prime/agent/settings.json` (currently `false`). This manager does not use it: per
  user instruction, procedure changes go to `AGENTS.md` / `SOP.md` instead, and the
  entries created before the ban were deleted. To re-enable, flip the setting, delete
  the AGENTS.md refine ban, and call `refine.run()`.

## Talking to a worker yourself

Ask for it: `let me talk to grok about demo 2`. The manager hands over the worker's
existing session using the handoff procedure recorded in `SOP.md` (tmux, iTerm2,
zellij, or a plain resume command — if none is recorded yet, it offers to set one up
with you). It always uses the harness's *interactive* resume (`codex resume`,
`cursor-agent --resume`, `claude --resume`, `prime-agent attach`) and never attaches
to your terminal itself — the final command is yours to run.

While you drive the session the manager stands down: it marks the request
`user-driving`, stops resuming it, and asks the worker what you settled rather than
inventing a result it never saw. The session is the same one, so nothing is lost.

## Resuming a manager session

Closing the terminal detaches the client; the worker and its children keep running.

```bash
prime-agent list
prime-agent attach <agent>
```

If the worker has stopped, `prime-worker --resume` from the same project. Resume the
**original** manager session — a new one does not inherit its children. On restore the
manager reconciles its record against the live registry before claiming anything is
still running.

## Known limitations:

- `codex exec resume` takes neither `-C` nor `-s`: set the subprocess working directory
  and use `-c sandbox_mode=`.
- Cursor needs `--trust` for an unseen directory, and bakes the reasoning level and fast
  tier into the model name.

## License

MIT — see [LICENSE](LICENSE).
