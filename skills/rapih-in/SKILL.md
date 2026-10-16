---
name: rapih-in
description: Decide where new or moved source files, folders, modules, features, and tests belong, and tidy an existing project's structure by responsibility while preserving behavior. Use when creating files, folders, modules, packages, or features; choosing implementation or test locations; scaffolding; moving or renaming files or folders; or when the user asks to audit, plan, fix, or check folder structure, or to split files that mix responsibilities (extract functions, components, hooks, classes, modules). Explicit modes - help, audit, plan, fix, check, place, all, resume. Do not use for conceptual questions without code changes or small edits inside an already-correct file; a bug fix is not permission to restructure.
---

# rapih-in

Tidy a running project's structure, then keep later file placement consistent.
Decisions come from repository evidence, changes stay minimal and useful, migrations are verified, and every mutating run can be resumed or selectively restored.

Write instructions to yourself in English; write reports in the user's conversation language.

## 1. Activation and dispatch

Decide the mode before doing anything else.

1. **Explicit invocation with no mode and no task** (only the skill name): show short help (see `references/command-modes.md#help-output`) and suggest `audit` for an existing project. Stop.
2. **Explicit mode word** in the mode position (first argument after the skill name): run that mode. A mode word inside a file name or feature description is not a mode.
3. **Explicit invocation with a concrete task but no mode**: follow the intent. An audit request stays read-only; a feature request applies placement rules while building the feature; "split X by responsibility" is a scoped `fix` on X.
4. **Implicit use while coding** (the host loaded this skill because the task creates, moves, renames, or modularizes code): help only with the placement and modularization the current task needs. Never replace the task with help, a full audit, or `all`. Larger restructuring becomes a separate recommendation.
5. **Unknown mode or option, missing option value, option not valid for the mode, or unresolvable scope**: explain the problem, show correct usage, and make no change.

Mode words are only `help audit plan fix check place all resume`. Parse arguments with shell-like quoting so paths with spaces work.

Shortcut commands `rapih-in-<mode>` (for example `/rapih-in-audit src/`) are explicit invocations of that mode with the given arguments; they load this skill and add no rules.

## 2. Modes and options

| Mode | Does | Mutates source |
| --- | --- | --- |
| `help` | Purpose, modes, options, examples, how to start | No |
| `audit [path]` | Structure and responsibility findings with `audit_id`, stable IDs (R001...), evidence, impact, priority | No |
| `plan [path]` | Target structure, source-to-target map (files and symbols), kept contracts, dependencies, batches, validation plan; runs a targeted audit first if needed | No |
| `fix [path]` | Applies a still-valid plan (or audits and plans first), in checkpointed batches, then validates | Yes |
| `check [path]` | Verifies structure, imports/references, and affected behavior with available non-writing checks | No |
| `place <need>` | Recommends location, owner, and reasoning for a new file/feature or a part to extract; creates nothing | No |
| `all [path]` | Always fresh audit, then plan, fix, check, with a checkpoint per batch | Yes |
| `resume` | Continues an unfinished run for this worktree, inheriting its selection, scope, and limits | As the run; never with `--dry-run` |

Options: `[path]`, `--dry-run`, `--exclude <path-or-glob>` (repeatable), `--only <ID,...>` (plan/fix/check/all only).
Full grammar, validation rules, `--only` matching, and the help text: `references/command-modes.md`.

## 3. Hard boundaries

- `help`, `audit`, `plan`, `place`, `check` never modify source, config, instruction files, convention notes, dependencies, or rapih-in run/lock state. In `check`, never run `--write`, `--fix`, or generators that rewrite source; if a build or test writes into the tree, use an isolated copy or skip and report it.
- `--dry-run` inspects and plans, then shows a reviewable preview: file/symbol map plus patch or diff summary, including edits to the source file, new files, contracts, and consumer/import updates. It takes no lock, writes no checkpoint, and never marks steps applied. Checks that need the change are marked "not run", or run on an isolated temporary copy and reported as preview tests.
- `--exclude` is a hard mutation boundary: never move, delete, edit, or create files on excluded paths, including new extraction targets. Work that needs an excluded path is `blocked` with the reason. Dependencies, vendor, caches, build output, and generated code are excluded from tidying by default; manifests and config may still be read.
- `[path]` limits the primary target. Supporting reference edits outside it are allowed only when required, and must appear in the plan. Respect a stricter boundary if the user sets one. Do not follow symlinks out of the workspace.
- A request limited to moving folders, formatting, or a narrower job stays that narrow; `all` never forces a split without clear benefit.
- Never change features, business logic, algorithms, UI design, database schema, public URLs, API contracts, migration identity, package exports, or dependencies as a side effect. Record discovered bugs separately.
- Respect host permission limits. Behavior changes, public API changes, large architecture changes, and unrequested expansion become separate recommendations.
- Installing this skill never starts an audit or tidy-up. Do not create watchers, daemons, or auto-move hooks.

## 4. Placement workflow

Use this for every new file, move, rename, or extraction. Details and code-organization rules: `references/placement-rules.md`. Stack-specific evidence and conditional examples: `references/stack-adapters.md`.

**A. Targeted inspection.** Read the instructions that apply to the target directory. Identify the repo/workspace/package root. Check relevant manifests, lockfiles, build/test config, import aliases, and entrypoints. Find similar implementations and candidate owner modules with `rg --files` / `rg` (or the available equivalent). Skip dependencies, build output, caches, binaries, and secrets. Distinguish hand-written source from generated, vendor, and runtime data. Reuse what you already know; do not rescan the whole repo per file.

**B. Structure profile.** Keep a short working profile: stack/framework, owning package, local patterns, runtime (client/server/shared/tooling/test), dependency rules, notable exceptions. Tie every claim to a manifest/config line or a real example file, and label it `explicit rule`, `observed pattern`, or `unverified assumption`. No invented confidence numbers. Different packages may validly use different patterns; file counts alone do not pick a winner.

**C. Owner and responsibility.** For each file or extracted part, state: responsibility, owning feature/domain/package, consumers, execution environment, where similar code lives, and the dependency direction and public API to preserve. Similar names or snippets do not justify a shared folder.

**D. Location decision order.**
1. Location required by the framework or config.
2. Equivalent location inside the existing owner module/package.
3. Feature-specific code next to that feature.
4. An existing shared module whose responsibility and dependency direction fit.
5. A new shared module only for real cross-consumer need.
6. A new folder or package only when the above do not fit and the benefit is clear.

If several options are reasonable, pick the one most consistent with the surrounding area and say why in one line. Ask the user only when the ambiguity affects a public contract, ownership, or a large architecture decision.

**E. Apply and verify.** For requested routine work, apply the reasoned choice without asking per folder name. For multi-location changes, show the map `source file/symbol | target file/symbol | reason | contracts and references affected | batch | status` before or with the change. Identify symbols and snapshots, not line numbers. Afterwards, use the resulting ownership for later tasks without re-auditing the repo.

Contextual writes that create, move, rename, or extract across files take a short writer lock (section 7) and release it when done; if the lock is held by another run, do not make the structural change and report `busy`.

## 5. Audit findings

- Each audit gets an `audit_id` from `scripts/rapihin_state.py new-id audit <root>` (format `A-<UTC yyyymmddTHHMMSS>-<first 6 of repo key>`) and records: root/worktree, scope, effective exclusions, timestamp. If the helper cannot run, use `A-<UTC yyyymmddTHHMMSS>-nokey`, write "fingerprint: unavailable", and say that `all --only` matching will be weaker.
- Each finding gets a short ID (`R001`, `R002`, ...) that is meaningful only with its `audit_id`, plus: kind, paths/symbols, evidence, impact, priority, suggested change, dependencies on other findings, and a fingerprint from `scripts/rapihin_state.py fingerprint` (kind + normalized paths + symbols). Never identify findings by line number or display order.
- Priority: `P1` affects function or dependencies (runtime boundary leaks, cycles, broken or deep imports); `P2` ownership/consistency; `P3` cosmetic, always labeled optional. Taste differences are not defects. No health scores.
- For each proposed move or extraction give problem, evidence, benefit, reference impact, required checks, and whether a smaller fix (keeping the location) is enough. Show uncertainty about dynamic references or public contracts as a verification limit or blocker.
- An already-tidy scope produces "no findings" and no plan, not invented work.
- Reports appear in chat. Write a report file only when the user asks. Without the report or a checkpoint in a new session, do not claim to reconstruct earlier IDs.

## 6. Splitting files by responsibility

Line count is only an audit signal; never split by size threshold. Split when a file holds responsibilities with different reasons to change, parts are hard to test separately, and the extracted part gets a clear name, input/output, and owner, with benefit larger than the added indirection. Keep cohesive long files, generated code, vendor code, fixtures, snapshots, and migrations intact. Extract one responsibility group per batch, update callers in the same batch, and preserve return values, meaningful errors, side-effect order, async behavior, component identity/lifecycle, client/server boundaries, and public exports (a compatibility re-export is fine when old callers need it). If risky behavior lacks tests, add a targeted characterization test before extracting, only in a mutating mode. If an important risk cannot be verified, do not apply that extraction; report it. Full workflow, UI/backend specifics, and examples: `references/code-refactoring.md`.

## 7. Mutating runs (fix, all, resume)

Required reading before the first mutation of a run: `references/migration-and-verification.md` and `references/checkpoints-and-recovery.md`.

The helper is `scripts/rapihin_state.py` in this skill's directory (Python 3.8+, standard library only; call it with `python`, `python3`, or `py -3`, whichever exists). State lives outside the repo in `~/.rapih-in/` (`locks/`, `runs/`). If the helper or a writable state directory is unavailable, stop at inspection and planning and say why; prose instructions are not coordination.

Order for every mutating run:
1. Validate arguments; resolve root with `repo-key`; show scope, exclusions, selection.
2. `all`: fresh audit, then plan. `fix`: reuse a referenced plan only after re-verifying root/worktree, scope, exclusions, instructions, config, and the referenced files; otherwise audit and plan for the scope. Apply `--only` rules from `references/command-modes.md`.
3. Baseline: working-tree state (including uncommitted user changes), and the relevant lint/typecheck/test/build commands that the repo actually defines, with results. Pre-existing failures are recorded as such.
4. `lock acquire`. If `busy`, report the owner run and stop without polling. Take over a lock only through `lock recover` after the user explicitly confirms in this conversation that the owning session has ended; a dead process ID or a matching run ID is never enough on its own.
5. Re-check files read during planning against current hashes; `run init` with audit context, selection, plan, and baseline.
6. Per batch: `batch begin` (snapshots every file the batch will create, modify, or move) -> `guard` with expected preimages right before writing -> apply the edits and all reference updates -> `batch end` -> run the batch checks -> `batch mark` as `validated`, `applied_unverified`, `failed`, or `blocked`. On a regression, fix the cause within known scope or `restore` the batch; never continue batches that depend on a failed one.
7. Re-audit with the same scope and method; compare before/after; `run update` final status; `lock release`.

Never use `git reset --hard`, `git clean`, whole-repo checkout, or mass restore. Do not commit, create branches, or `git init` for checkpoints.

**resume**: `run list` for this root; if several candidates, show IDs and scopes and let the user choose; `diagnose`; reacquire the lock; revalidate changed files; continue only still-valid operations. It inherits scope, exclusions, and selected IDs; it rejects a new `--only`; new audit findings are reported, not applied. No checkpoint means no resume: say so and suggest `audit` or `all`.

**Targeted restore** (natural language, for example "restore rapih-in run R-... batch 2"): use `restore` for that run/batch only; files edited after the run are conflicts, never overwritten.

## 8. Report format

Every mode reports, as relevant:
- Mode, scope, exclusions, `audit_id`/run ID, selected IDs, and whether this is a **preview** or a **real application**.
- Structure profile (short) and evidence-based findings; cosmetic items marked optional.
- Before/after on the same scope and method, including what was kept because it already fits.
- Map of moves/renames and extracted symbols, what stayed in the source file, new/changed files, kept contracts, updated references, batches.
- Checks: passed, failing before the change, new regressions, not run.
- Blocked/skipped/remaining work with concrete reasons.
- Mutating runs: run ID, checkpoint path, batch statuses, lock state, and the resume/restore steps that apply. If `busy`, name the known owner and say nothing was applied.
- Counts come from real results. With failures or unrun checks, never summarize the run as validated success, and never promise zero regressions.

## References

Read only what the current step needs.

| File | Read when |
| --- | --- |
| `references/command-modes.md` | Parsing arguments, `--only`/`--exclude`/`--dry-run` rules, help text, invalid input |
| `references/placement-rules.md` | Choosing a location, writing a structure profile, code-organization and test placement rules |
| `references/stack-adapters.md` | Stack detected (React/Vite, Next.js, Node backend, Python, monorepo) or stack unknown |
| `references/code-refactoring.md` | Proposing or applying an extraction or file split |
| `references/migration-and-verification.md` | Before any move/rename/extraction batch; baseline, references, checks, before/after |
| `references/checkpoints-and-recovery.md` | Lock, checkpoint, resume, restore, busy/blocked handling, helper commands |
| `references/examples.md` | Example decisions, reports, and plans |
| `references/host-compatibility.md` | Install locations, invocation syntax, and reminders per host |
