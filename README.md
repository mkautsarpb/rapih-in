[English](README.md) | [Bahasa Indonesia](README.id.md)

<p align="center">
  <img src="assets/branding/rapih-in-logo.png" alt="rapih-in logo: a geometric teal r monogram built from code blocks with a mint square, next to the rapih-in wordmark" width="420">
</p>

<p align="center">
  <strong>Tidy the structure of a project that already runs, then keep new files in the right place.</strong><br>
  <em>Tidy structure. Thoughtful refactoring.</em>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-038982" alt="License: MIT"></a>
</p>

rapih-in is an Agent Skill for coding agents (Codex, Claude Code, Google Antigravity, Cursor Agent, Kimi Code CLI). It audits folder structure and file responsibilities, proposes the smallest useful changes, applies them in checkpointed batches that keep behavior intact, and afterwards helps the agent put new files where they belong.

## Contents

- [Why rapih-in](#why-rapih-in)
- [Quick start for an existing project](#quick-start-for-an-existing-project)
- [Installation](#installation)
- [Hosts and invocation](#hosts-and-invocation)
- [Modes](#modes)
- [Options](#options)
- [How a run works](#how-a-run-works)
- [Splitting files by responsibility](#splitting-files-by-responsibility)
- [Everyday use](#everyday-use)
- [Troubleshooting](#troubleshooting)
- [Validation status and limits](#validation-status-and-limits)
- [Contributing](#contributing)
- [Support](#support)
- [Star History](#star-history)
- [License](#license)

## Why rapih-in

Other skills for file organization and architecture exist. rapih-in focuses on the quality of each decision and on migrations you can inspect:

| Goal | What the skill does |
| --- | --- |
| Follow the repo's character | Reads framework config, manifests, and nearby code; each location decision cites a file or config. Different packages may keep different valid layouts. |
| Minimum useful change | Proposes a move or split only with a concrete benefit; cosmetic items are marked optional and are not applied by default; a tidy repo yields no changes. |
| Visible migration impact | Previews show moved files, extracted symbols, edits to the source file, new files, and updated imports, plus the checks to run. |
| Split by responsibility | Extracts functions, components, hooks, classes, or modules that have a clear owner; long but cohesive files stay as they are. |
| Resumable and restorable | One writer lock per worktree, a checkpoint per batch, detection of edits made by you in the meantime, and targeted restore of one batch. |
| Checkable results | Before/after on the same scope and method, with passed, failing-before, new-regression, and not-run checks kept apart. No health scores. |
| Consistency afterwards | Later coding tasks reuse the resulting ownership without re-auditing the repo. |

These are design goals. What has actually been tested is listed in [Validation status and limits](#validation-status-and-limits).

## Quick start for an existing project

1. Install the skill for your agent (see [Installation](#installation)). Installing never starts a tidy-up by itself.
2. In your agent chat, open the project and run an audit (read-only):

   ```text
   /rapih-in audit
   ```

3. Review the full preview. Nothing is changed and no checkpoint is written:

   ```text
   /rapih-in all --dry-run
   ```

4. Apply everything that is worth it, or only the findings you choose:

   ```text
   /rapih-in all
   /rapih-in fix --only R001,R003
   ```

The commands above use the Claude Code and Cursor prefix. Codex uses `$rapih-in`, Kimi uses `/skill:rapih-in`; see [Hosts and invocation](#hosts-and-invocation). If you prefer, `/rapih-in all` runs the whole audit, plan, fix, and check sequence in one go.

## Installation

### Prerequisites

- One or more supported agents installed.
- Python 3.8 or newer for the state helper (`python`, `python3`, or `py -3`). It uses only the standard library. Without it, rapih-in can still audit and plan but will not apply changes.
- Git is optional; with Git, baselines include your uncommitted changes.

### Get the source

```bash
git clone https://github.com/mkautsarpb/rapih-in.git
cd rapih-in
```

The skill itself lives in `skills/rapih-in/`.

### User scope (all projects on this machine)

Run in a terminal from the repository root:

```bash
python tools/sync.py plan      # show what would be installed, change nothing
python tools/sync.py install   # install for the agents detected on this machine
python tools/sync.py verify    # confirm every installed copy matches the source
```

`install` detects Codex, Claude Code, Antigravity (App/IDE and CLI), Cursor, and Kimi, and writes only what each needs:

| Location | Read by |
| --- | --- |
| `~/.agents/skills/rapih-in/` | Codex, Cursor, Kimi Code |
| `~/.claude/skills/rapih-in/` | Claude Code (Cursor also reads it) |
| `~/.gemini/config/skills/rapih-in/` | Antigravity App and IDE |
| `~/.gemini/antigravity-cli/skills/rapih-in/` | Antigravity CLI |

Next to each `rapih-in/` folder it also places seven shortcut folders (`rapih-in-audit`, `rapih-in-all`, ...); see [Shortcut commands](#shortcut-commands).

It also adds a short reminder so agents remember to use the skill: a marked block in `~/.codex/AGENTS.md`, the file `~/.claude/rules/rapih-in.md`, the file `~/.gemini/config/rules/rapih-in.md` (`trigger: always_on`), and a block in `~/.kimi-code/AGENTS.md` when Kimi is present. Cursor User Rules are a UI setting: run `python tools/sync.py reminder` and paste the text into Cursor Settings, Rules, User Rules. Existing instructions are kept; reinstalling never duplicates the reminder.

Choose hosts explicitly with `--hosts codex,claude`. A user-scope install is not visible to cloud agents, SSH remotes, containers, or WSL; install there separately.

### Project scope (one repository)

```bash
python tools/sync.py install --scope project --project /path/to/your/repo
```

This writes `.agents/skills/rapih-in/` (read by Codex, Cursor, Kimi, Antigravity), `.claude/skills/rapih-in/` when Claude Code is targeted, and a reminder block in the repo's `AGENTS.md`. Use either user or project scope for a host, not both, so two copies with the same name do not compete.

### Update

Edit or pull the source, then run `python tools/sync.py install` again and `python tools/sync.py verify`. Every copy is replaced from the single source in `skills/rapih-in/`; `verify` fails if any copy drifted. A copy you edited by hand is reported instead of overwritten.

### Uninstall

```bash
python tools/sync.py uninstall
```

Removes only copies and reminders created by `tools/sync.py` (marked with `.rapih-in-install.json`, rapih-in markers, or a rapih-in header). Other skills and your own instructions stay untouched. Run state in `~/.rapih-in/` is kept; delete it yourself when you no longer need old checkpoints.

## Hosts and invocation

All examples are typed into the agent chat, not into a terminal.

| Host | Explicit invocation | Automatic use | Tested here |
| --- | --- | --- | --- |
| Codex CLI / IDE | `$rapih-in all --dry-run` | Yes | CLI 0.162.0: discovery and `audit` tested |
| Claude Code | `/rapih-in all --dry-run` | Yes | 2.1.301: all modes except `plan`/`check` tested, plus implicit use |
| Cursor Agent | `/rapih-in all --dry-run` | Yes | Not tested (not installed) |
| Kimi Code CLI | `/skill:rapih-in all --dry-run` | Yes | Not tested (not installed) |
| Antigravity App / CLI | `/rapih-in all --dry-run` | Yes | Not tested |
| Antigravity IDE | "Use the rapih-in skill in all mode with --dry-run on this project." | Yes | Installed, not tested |

Details per host, including discovery folders and version notes: [skills/rapih-in/references/host-compatibility.md](skills/rapih-in/references/host-compatibility.md).

### Shortcut commands

Installing also adds one command per mode, so you can pick it from the `/` menu instead of typing the mode:

| Mode | Claude Code, Cursor, Antigravity App/CLI | Codex | Kimi Code |
| --- | --- | --- | --- |
| `audit` | `/rapih-in-audit` | `$rapih-in-audit` | `/skill:rapih-in-audit` |
| `plan` | `/rapih-in-plan` | `$rapih-in-plan` | `/skill:rapih-in-plan` |
| `fix` | `/rapih-in-fix` | `$rapih-in-fix` | `/skill:rapih-in-fix` |
| `check` | `/rapih-in-check` | `$rapih-in-check` | `/skill:rapih-in-check` |
| `place` | `/rapih-in-place` | `$rapih-in-place` | `/skill:rapih-in-place` |
| `all` | `/rapih-in-all` | `$rapih-in-all` | `/skill:rapih-in-all` |
| `resume` | `/rapih-in-resume` | `$rapih-in-resume` | `/skill:rapih-in-resume` |

Each shortcut is a thin entry point: it loads the main `rapih-in` skill and runs that mode with the arguments you type after it, so `/rapih-in-audit src/` behaves exactly like `/rapih-in audit src/`. Shortcuts are manual-only and are never picked automatically; automatic help during normal coding still comes from `rapih-in`. To install without them: `python tools/sync.py install --no-shortcuts`.

## Modes

| Mode | What it does | Changes source |
| --- | --- | --- |
| `help` | Purpose, modes, options, examples | No |
| `audit [path]` | Findings with an `audit_id` and IDs (R001, R002, ...), evidence, impact, priority | No |
| `plan [path]` | Target structure, file and symbol map, kept contracts, batches, checks | No |
| `fix [path]` | Applies a still-valid plan (audits and plans first if needed), then validates | Yes |
| `check [path]` | Verifies imports, references, and affected behavior without auto-fixing | No |
| `place <need>` | Recommends where a new file, feature, or extracted part belongs, and why | No |
| `all [path]` | Fresh audit, then plan, fix, and check, with a checkpoint per batch | Yes |
| `resume` | Continues an unfinished run with its original selection and limits | As the run |

Calling the skill with no mode and no task shows short help. When the agent loads the skill on its own during a normal task, it only helps with the placement that task needs.

## Options

| Option | Modes | Meaning |
| --- | --- | --- |
| `[path]` | audit, plan, fix, check, all | Limits the target to a file or folder. Supporting import updates outside it are shown in the plan. |
| `--dry-run` | fix, all, resume | Preview only: map plus diff summary, no file changes, no lock, no checkpoint. |
| `--exclude <path-or-glob>` | audit, plan, fix, check, all | Never move, edit, delete, or create anything there. Repeatable. |
| `--only <ID,...>` | plan, fix, check, all | Only these findings from a referenced audit or run. |

Examples:

```text
/rapih-in audit src/features/checkout/CheckoutPage.tsx
/rapih-in plan --only R001,R003
/rapih-in fix --only R001,R003 --dry-run
/rapih-in all src/ --exclude src/generated/ --exclude "src/legacy/**"
/rapih-in place notification feature
/rapih-in resume
```

## How a run works

### Finding IDs and `--only`

Each audit has an `audit_id`; each finding gets an ID such as `R001` that only means something together with that audit. A finding also carries a fingerprint built from its kind, paths, and symbols, so `all --only R001` can re-audit and still match the same problem. If an ID is unknown, stale, or ambiguous, rapih-in says so and changes nothing else in its place. If fixing R001 needs a substantive change to an unselected finding, R001 is marked blocked with that dependency.

### Checkpoints, resume, and restore

Mutating runs (`fix`, `all`, `resume`) store their state outside your repo in `~/.rapih-in/runs/<repo-key>/<run-id>/`: scope, exclusions, selected IDs, the plan, and snapshots of exactly the files each batch touches (never `.env` files or keys). If a run stops halfway, `resume` diagnoses each batch, separates the run's own writes from edits you made, and continues without repeating finished work. To undo one batch, ask in plain words, for example "restore rapih-in run R-20261016T091500-a1b2 batch b2". Only files that still match what the run wrote are restored; files you changed later are reported as conflicts and left alone. rapih-in never uses `git reset --hard` or `git clean`.

### Locks and the busy state

Only one rapih-in run writes to a worktree at a time. The lock lives in `~/.rapih-in/locks/<repo-key>/` and is taken atomically. A second run reports `busy` with the owner run and changes nothing. A lock never expires by age: taking over a crashed run's lock requires that the owner is confirmed inactive. The lock coordinates rapih-in runs on the same machine and user only; changes from editors or other tools are detected by content hashes right before each write.

## Splitting files by responsibility

Line count is only a signal. A file is split when it mixes responsibilities that change for different reasons. Illustration (not a fixture result): a `CheckoutPage` that renders the form, keeps form state, validates input, and calls the orders API can become:

| Part | Where it goes | Why |
| --- | --- | --- |
| Page composition | stays in `CheckoutPage` | it wires the sections |
| Validation rules | `features/checkout/validation/` | testable on its own |
| Orders API call | `features/checkout/api/` | transport detail |
| Form state and submit flow | `features/checkout/hooks/` | separate reason to change |

Everything stays inside the checkout feature. A 300-line currency table with two accessors stays one file, and generated code is never split. For the real result on a test fixture, see [docs/evaluation.md](docs/evaluation.md).

## Everyday use

After tidying, normal requests are enough; the agent loads the skill when a task creates, moves, or splits files:

```text
Add a coupon input to the checkout page, with a test.
Use rapih-in to audit this repository.
Move the helpers in src/utils into the features that use them; no other code changes.
Split CheckoutPage by responsibility and keep its behavior and look.
```

A request limited to moving folders stays limited to moves. A small bug fix does not trigger an audit or a split.

## Troubleshooting

| Problem | What to do |
| --- | --- |
| The agent does not know the skill | Run `python tools/sync.py verify`. In Claude Code run `/reload-skills` if `~/.claude/skills` was created during the session; restart Codex or Antigravity sessions. |
| `/rapih-in` does nothing in Codex or Kimi | Use the host syntax: `$rapih-in ...` in Codex, `/skill:rapih-in ...` in Kimi, or name the skill in plain words in Antigravity IDE. |
| "Audit ID not found" or "stale" | IDs belong to one audit. Run `audit` again in the same session, then use the new IDs. |
| "busy" | Another rapih-in run holds the worktree lock. Let it finish, or `resume` it if it is your interrupted run. |
| Checks show "not run" | The repo defines no runnable command for that check, or it needs services that are not available. rapih-in reports this instead of claiming success. |
| Python not found | Install Python 3.8+ or make `python3`/`py -3` available; until then rapih-in only audits and plans. |

## Validation status and limits

Measured results, environment, and every scenario's status are in [docs/evaluation.md](docs/evaluation.md). Summary:

- Implemented: eight modes and four options as instructions in `SKILL.md` and its references; the state helper for lock, checkpoint, snapshot, diagnose, and restore; the install/verify/uninstall tool; a static package validator.
- Tested automatically: 30 script tests (lock with 8 concurrent processes, stale-lock refusal, guard, interruption, restore, install tool) and static package validation, all passing on Windows 11.
- Tested through a real agent: 30 recorded cases on small fixtures (28 with Claude Code 2.1.301, 2 with Codex CLI 0.162.0, including the shortcut commands), each run once. One case failed (the agent took over a crashed run's lock without asking); the contract and helper were fixed and the re-runs pass. Of the 37 planned scenarios, 23 are evidenced, 13 partially, 1 not tested.
- Not tested: `plan` and `check` as standalone modes, a failing-baseline fixture, Cursor Agent and Kimi Code CLI (not installed here), Antigravity behavior (files installed only), POSIX filesystems, remote environments. No comparison with other skills was run, so no superiority is claimed, and passing cases do not guarantee zero regressions in other projects.

## Contributing

Issues and pull requests are welcome once the public repository is published. Keep `SKILL.md` short, put details in `skills/rapih-in/references/`, and keep both READMEs equivalent. Before submitting:

```bash
python -m unittest discover -s tests
python tools/validate.py
```

## Support

Report bugs and ask questions in the [issue tracker](https://github.com/mkautsarpb/rapih-in/issues).

## Star History

The Star History chart will appear here once the repository has stars to chart. Setup steps for maintainers: [docs/maintainers.md](docs/maintainers.md).

## License

[MIT](LICENSE) © 2026 rapih-in contributors.
