# Command modes and options

Contents: grammar · parsing · per-mode contract · options · finding selection (`--only`) · invalid input · help output · natural-language requests.

## Grammar

```
rapih-in <help|audit|plan|fix|check|all|resume> [path] [--dry-run] [--exclude <path-or-glob>]... [--only <ID,...>]
rapih-in place <need>
```

This is conversation input for the agent, not a shell command. Each host adds its own prefix (`/rapih-in`, `$rapih-in`, `/skill:rapih-in`, or naming the skill); see `host-compatibility.md`.

## Parsing

- Split the text after the skill name with shell-like quoting: `"src/my feature/"` is one argument.
- The first token is the mode only if it is one of the eight mode words. Otherwise the text is a task (dispatch rule 3 in SKILL.md).
- Options may appear in any order after the mode. `--exclude` and `--only` need a value. `--exclude` repeats; `--only` takes one comma list (repeated `--only` values are merged).
- At most one `[path]`. For `place`, everything after the mode is the need, not a path.
- Resolve `[path]` against the agent's current working directory, then show the resolved absolute scope. Accept a file or a directory. A path that does not exist is invalid input.
- Resolve `--exclude` patterns against the project root. Show the effective exclusion list: user patterns plus detected defaults (dependency dirs such as `node_modules/`, `.venv/`, `vendor/`; build output such as `dist/`, `build/`, `.next/`, `target/`; caches; generated code identified by headers, config, or tool conventions).

## Option validity per mode

| Option | help | audit | plan | fix | check | place | all | resume |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `[path]` | no | yes | yes | yes | yes | (need text) | yes | no (inherited) |
| `--dry-run` | no-op | no-op (already read-only) | no-op | yes | no-op | no-op | yes | yes |
| `--exclude` | no | yes | yes | yes | yes | no | yes | no (inherited) |
| `--only` | no | no | yes | yes | yes | no | yes | no (inherited) |

"no" means invalid input: explain, show usage, mutate nothing. "no-op" means accept and state that the mode is already read-only.

## Per-mode contract

**help** - Print the help output below. Nothing else.

**audit** - Read-only. Targeted inspection of the scope (SKILL.md section 4A-B). Produce: header (audit_id, root, worktree/git state, scope, exclusions, time), structure profile, findings table, items kept on purpose, next steps. No file writes, no lock, no run state. If the scope is already consistent, say so: "no findings".

**plan** - Read-only. Uses findings from a referenced audit in this conversation or a fresh targeted audit if none fits. Produces: target structure (only what changes), mapping table, kept contracts, dependency order between findings, batches, validation plan per batch (real commands from repo config), and the risks/limits. With `--only`, plan only those IDs plus required supporting edits.

**fix** - Mutating. Reuses a plan from this conversation only after re-verifying root/worktree, scope, exclusions, applicable instructions, config, and the content hashes of the files it touches. If there is no plan or it is stale, run a targeted audit and plan for the scope first (no need for the user to run them manually). Then apply in batches with checkpoints and validate.

**check** - Read-only. Verifies structure against the latest plan or the stated intent: imports/references resolve, no new boundary or cycle issues where tooling can tell, and the affected behavior passes the available checks. Never use formatter `--write`, `lint --fix`, codegen, or anything that rewrites tracked files. With `--only`, check just those findings: `resolved`, `still present`, `stale`, or `cannot verify`.

**place** - Read-only. Input is a need ("notification feature", "date formatting used by checkout and invoices", "the API calls inside CheckoutPage.tsx"). Output: recommended path(s), owner, runtime, why (evidence), alternatives considered, and what would change that answer. Never create files or split code in this mode.

**all** - Mutating. Always runs a fresh audit, then plan, fix, check, without asking for confirmation at each stage or per folder name. With `--dry-run` it stops after the preview. Recommended entry point for an old project: `all --dry-run`, then `all`.

**resume** - Continues an unfinished run; see `checkpoints-and-recovery.md#resume`. Inherits scope, exclusions, `--only` selection, and limits. Accepts only `--dry-run`. With `--dry-run` it shows the remaining plan and conflicts without applying anything or advancing the checkpoint.

## `--dry-run`

Preview content, at minimum:
1. The mapping table with status `preview`.
2. For each batch: files created, modified, moved, deleted; for each extraction, the symbols moved, what stays, the new import/export lines, and the consumer edits. A unified diff or a precise patch summary per file. A rename list alone is not enough.
3. Checks: which would run after each batch. Mark them `not run (preview)` unless you ran them on an isolated temporary copy outside the repo, in which case label them `preview test on copy`.
4. No lock, no checkpoint, no convention-note writes, no edits to instruction files or dependency/lock files. A temporary copy for preview tests lives outside the repo and is deleted afterwards.

## Finding selection (`--only`)

- Valid for `plan`, `fix`, `check`, `all`. Example: `--only R001,R003`. Validate the entire list before any mutation; duplicate IDs count once.
- IDs come from one clearly referenced audit or run (`audit_id` / run ID) that matches this repo/worktree. If the conversation has several audits, use the one the user names, else the latest one for the same root and scope; if that is still ambiguous, ask.
- Never guess IDs from the order of a fresh audit. If the context is missing (new session, no report or checkpoint), say so and offer a read-only audit; do not run other findings instead and do not fall back to "all findings".
- Unknown IDs: report them, and do nothing for the whole command when the list is invalid.
- `plan`/`fix`/`check`: confirm each selected finding is still relevant by re-reading its evidence.
- `all --only`: run the fresh audit, then match each selected ID to the new findings by fingerprint (helper `fingerprint`). Outcomes per ID:
  - `matched` - same fingerprint present: fix it.
  - `already resolved` - evidence gone: no-op, report it.
  - `stale` - paths/kind overlap but evidence changed meaning, or several candidates match: do not fix; explain.
  New findings outside the selection are reported, never applied automatically.
- Supporting edits the selected fix needs (imports, a targeted test, a compatibility re-export) are allowed and listed in the plan. If finishing a selected finding needs a substantive fix of an unselected finding, mark the dependency and stop that item as `blocked (depends on Rxxx)`.
- If a selected change also resolves an unselected finding with no extra mutation, report it as "resolved as a side effect of Rxxx", not as an expanded selection.
- Exclusions and mutation boundaries still apply to selected findings.
- Natural language has the same limits: "fix only R001 and R003 from the last audit" equals `fix --only R001,R003` against that audit.

## Invalid input

Respond with: what is wrong, the correct usage line for that mode, one corrected example. Then stop. Examples of invalid input: unknown mode-like word with option syntax (`rapih-in fixx`), `--exclude` without a value, `--only` on `audit`/`place`/`help`/`resume`, a `[path]` that does not exist, a scope outside the workspace, two paths.

## Help output

Render this in the user's conversation language (translate the descriptions; keep mode names, shortcut names, options, and paths literal). Add the host's prefix to shortcut names (`/rapih-in-audit` in Claude Code/Cursor/Antigravity, `$rapih-in-audit` in Codex, `/skill:rapih-in-audit` in Kimi). Omit the shortcut column if the shortcuts are not installed next to this skill:

```
rapih-in - tidy an existing project's structure, then keep new files consistent.

Modes                Shortcut
  help                 (skill name alone)  this help
  audit [path]         rapih-in-audit      find structure and responsibility problems (read-only)
  plan  [path]         rapih-in-plan       target structure, file/symbol map, batches, checks (read-only)
  fix   [path]         rapih-in-fix        apply a valid plan in checkpointed batches, then validate
  check [path]         rapih-in-check      verify references and affected behavior (read-only)
  place <need>         rapih-in-place      where should this file/feature/extracted part live (read-only)
  all   [path]         rapih-in-all        fresh audit -> plan -> fix -> check
  resume               rapih-in-resume     continue an unfinished run with its original selection

Options
  [path]                   limit the target (file or folder)
  --dry-run                preview only: map + diff, no changes, no checkpoint
  --exclude <path-or-glob> never touch these paths (repeatable)
  --only <ID,...>          only these findings from a referenced audit (plan/fix/check/all)

Start with an existing project
  1. audit               see what is worth fixing
  2. all --dry-run       review the full preview
  3. all                 apply  (or: fix --only R001,R003)

Restore: "restore rapih-in run <run-id> batch <n>" (only that run's changes; your later edits are kept)
Installing rapih-in never starts a tidy-up by itself.
```

## Natural-language requests

| Request | Treated as |
| --- | --- |
| "Use rapih-in to audit this repo" | `audit` |
| "Where should the notification feature live?" | `place notification feature` |
| "Split CheckoutPage.tsx by responsibility, keep the UI and behavior" | `fix src/.../CheckoutPage.tsx`, extraction allowed |
| "Move the utils folder into the features that use it, no code changes" | `fix` limited to moves and import updates; no splitting |
| "Fix only R001 and R003 from this audit" | `fix --only R001,R003` against that audit |
| "Show me what rapih-in would change" | `all --dry-run` |
| "Continue the rapih-in run" | `resume` |
| "Undo rapih-in batch 2 of run R-..." | targeted restore (`checkpoints-and-recovery.md#targeted-restore`) |
| "Add a profile page" (skill loaded implicitly) | do the task; apply placement rules only |
