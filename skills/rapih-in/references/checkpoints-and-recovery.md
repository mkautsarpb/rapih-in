# Checkpoints, locks, resume, and recovery

Contents: helper · state layout · writer lock · busy/blocked · stale lock recovery · checkpoint contents · batch journal · resume · targeted restore · guarantees and limits.

## Helper

`scripts/rapihin_state.py` (relative to the skill root). Python 3.8+, standard library only. Run as `python <skill-dir>/scripts/rapihin_state.py <command>`; use `python3` or `py -3` if `python` is missing. Quote paths with spaces. Each command prints one JSON object. Exit codes: `0` ok, `2` usage, `3` busy/not owner/refused, `4` conflict, `5` not found.

| Command | Purpose | Writes state |
| --- | --- | --- |
| `repo-key <root>` | Normalized worktree root and key (git top-level, symlinks/junctions resolved, case-normalized) | No |
| `new-id audit\|run <root>` | `A-<UTC>-<key6>` / `R-<UTC>-<hex4>` | No |
| `hash <root> <path>...` | sha256 per file (`missing` if absent) | No |
| `fingerprint --kind K --path P [--symbol S]` | Stable finding fingerprint | No |
| `lock status <root>` | Free/held, owner run, diagnostics | No |
| `lock acquire <root> --run-id ID` | Atomic acquire; returns `token` | Yes |
| `lock verify <root> --token T` | Confirms ownership | No |
| `lock release <root> --token T` | Owner-only release | Yes |
| `lock recover <root> --run-id ID --expected-token PREFIX --user-confirmed-owner-inactive` | Atomic takeover of a dead owner's lock | Yes |
| `run init <root> --token T --mode fix\|all\|contextual --scope S [--exclude X]... [--only IDs] [--audit-id A] [--audit-json J] [--plan-json J] [--baseline-json J]` | Create checkpoint; run ID equals the lock's run ID | Yes |
| `run update <root> <run> --token T [--status S] [--next-step TEXT] [--set-json J]` | Update status/fields; scope, exclusions, selection are immutable | Yes |
| `run list <root> [--all]` | Unfinished runs for this worktree | No |
| `run show <root> <run>` | Full checkpoint | No |
| `batch begin <root> <run> --token T --batch B --files F... [--expect path=sha\|missing]... [--findings IDs]` | Snapshot pre-state; `F` is `path`, `create:path`, `modify:path`, `delete:path`, or `move:src=>dst` | Yes |
| `batch record <root> <run> --token T --batch B <path>...` | Record post-write hash of files just written | Yes |
| `batch end <root> <run> --token T --batch B` | Record post-state of all batch files | Yes |
| `batch mark <root> <run> --token T --batch B --status validated\|applied_unverified\|failed\|blocked [--checks-json J] [--note N]` | Result of checks | Yes |
| `guard <root> --token T --expect path=sha\|missing...` | Ownership + preimage check right before a write | No |
| `diagnose <root> <run>` | Per batch/file: `pre`, `post`, `unchanged`, `modified_outside_run`, `changed_unrecorded`; verdict per batch | No |
| `restore <root> <run> --batch B (--dry-run \| --token T) [--partial] [--include-unrecorded P]...` | Targeted restore of one batch | Yes (not with `--dry-run`) |

JSON arguments (`--audit-json` etc.) accept inline JSON, a file path, or `-` for stdin. Keep them small: IDs, fingerprints, paths, symbols, commands, results. Never include secrets or file contents.

State directory: `--state-dir`, else `RAPIH_IN_STATE_DIR`, else `~/.rapih-in`. Never set `HOME`/`USERPROFILE` to redirect it.

## State layout

```
~/.rapih-in/
  locks/<repo-key>/owner.json                    exists only while the lock is held
  runs/<repo-key>/<run-id>/checkpoint.json       atomic writes (temp file + replace)
  runs/<repo-key>/<run-id>/journal.jsonl         append-only, fsynced events
  runs/<repo-key>/<run-id>/snapshots/<batch>/{pre,post}/<hash>.bin
```

`<repo-key>` is derived from the normalized worktree root, so aliases and symlinks to the same worktree share one key and separate Git worktrees get separate keys. All hosts on the same machine and user share this directory. A remote host, container, WSL distro, or cloud agent has its own home and therefore its own state.

## Writer lock

- One lock per normalized repo/worktree root. Two scopes in the same worktree take turns.
- Acquire before any mutation by this workflow: source edits, characterization tests, convention notes, resume, restore. Contextual structural writes use a short lock with run ID `ctx-<UTC>` and release it right after.
- Hold it through the mutation sequence, its validation, and the checkpoint update. Release on completion, controlled failure, or a consistent stopping point. `resume` acquires again.
- Before every write, call `guard` (or `lock verify`) with the token. Only the owner can release.
- Read-only modes and `--dry-run` never acquire, release, or modify locks or runs. When inspecting while files may change, compare hashes before and after; if the snapshot was not stable, label results provisional.

## Busy / blocked

- `lock acquire` exit `3` with `status: busy`: report the owner's run ID, root, acquisition time, and that nothing was applied. Do not poll in a loop; do not advance another run's checkpoint. Suggest waiting for that run, or `resume` if it is the user's own interrupted run.
- `blocked` is a run/batch outcome: a selected change needs an excluded path, an unselected finding, an unresolvable reference, or an unavailable check.

## Stale lock recovery

A lock never expires by age. Recovery requires all of:
1. `lock status` shows the owner; read its run with `run show`/`diagnose`.
2. Show the user the owner run, host, acquisition time, and batch state, and ask whether that session has ended. Only an explicit "yes" from the user in this conversation counts. A dead `invoker_pid` is not proof: the helper runs from short-lived shells, so the owning agent can still be active. A matching run ID is not proof either: another session may be resuming the same run.
3. After that confirmation, call `lock recover ... --expected-token <prefix from status> --user-confirmed-owner-inactive`. The helper still refuses if the recorded process is running on this host, moves the old lock aside atomically only if the owner token still matches, marks the old run `interrupted` if it was `in_progress`, and acquires a new lock.

Never pass `--user-confirmed-owner-inactive` on your own judgment. In a non-interactive session, stop at step 2 and report `blocked: lock held by <run>; confirm that session ended, then resume`. Never delete lock files by hand, kill processes, or treat a timeout as proof.

## Checkpoint contents

Minimum: run ID, root/worktree, skill and helper version, mode, scope, exclusions, audit ID and audit context (finding IDs, fingerprints, kinds, paths, dependencies), selected IDs, timestamps, baseline, batch plan, path/symbol map, per-file pre/post hashes and snapshots, check results, next step, status. The lock owner hint is diagnostic only; an old checkpoint never proves the lock is still owned.

Snapshot only the files a batch touches, including untracked files. Never snapshot `.env*`, keys, credentials, or logs (the helper refuses common patterns). Never copy the whole repo. No `git init`, commits, or branch changes for checkpoints.

If writing the checkpoint fails, do not start a new batch; report the path and error.

## Batch journal

Per batch: `batch begin` before the first write records every file and its pre-state (`missing` for files to be created). For extractions, list the source file, every new target, existing targets, each caller, and each test that will change. A file split is not a rename; model it as `modify` of the source plus `create` of targets plus `modify` of callers.

`batch record` after each written file and `batch end` after the batch let `diagnose` separate the run's own writes from external edits.

## Resume

1. `run list <root>`. None: say there is nothing to resume and suggest `audit` or `all`. Several: show run IDs, modes, scopes, selections, status, last update; let the user choose.
2. Validate the run belongs to this root (the helper rejects runs from another worktree).
3. `diagnose`. Per batch verdict:
   - `as_recorded` / `validated`: keep; do not redo.
   - `interrupted_before_writes`: safe to apply the batch from the start (refresh the plan against current content first).
   - `interrupted_partial`: recorded files are the run's writes; finish the remaining files of the batch only after re-reading them; never re-create files that are already in `post` state (avoids duplicate symbols).
   - `interrupted_needs_inspection` / `changed_unrecorded`: diff each file against its pre snapshot; continue or restore only when the change is clearly the run's own; otherwise ask.
   - `interrupted_with_foreign_edits` / `changed_after_batch`: the user or another tool edited files; adapt the plan to the latest content; never overwrite those edits.
4. Re-check config/instruction changes and moved files since the checkpoint; refresh the plan only for what changed.
5. `lock acquire --run-id <same run>` (or recovery as above), then continue with the inherited scope, exclusions, and selection. New findings from re-inspection are reported, not added. A new `--only` is rejected.
6. `resume --dry-run`: show the diagnosis and remaining plan; no lock, no writes.

## Targeted restore

Triggered by a natural-language request naming a run (and batch). Steps:
1. `restore <root> <run> --batch B --dry-run` and show actions and conflicts.
2. Acquire the lock, `restore ... --token T`. The helper restores only files whose current content equals the run's recorded post-state, deletes run-created files only if unchanged since, and reports every other file as a conflict without touching it.
3. With conflicts, nothing is restored unless `--partial` is passed, which restores only separable files. Check that the partial result leaves no dangling import or duplicate symbol; if it would, do not use `--partial`; report.
4. For `changed_unrecorded` files, inspect the diff first; pass `--include-unrecorded <path>` only when the change belongs solely to this run.
5. Restore later batches before earlier ones when they depend on each other.
6. Run the relevant checks, `run update`, release the lock, and report what was restored, what was kept, and why.

Never use `git reset --hard`, `git clean`, `git checkout .`, or a mass restore. Never promise a perfect undo when snapshots are missing or conflicts remain.

## Guarantees and limits

- The lock coordinates only participants that use this protocol and share the same state directory (same machine/user/filesystem). It does not stop editors, other agents, or other machines.
- `guard` and pre/post hashes detect external changes immediately before a write and stop mismatched patches; there is still a small window between the check and the write against writers that do not use the protocol.
- If atomic directory rename is unavailable or the state directory is not writable, do not mutate: stay in inspection/plan and say why.
- Tested on Windows (NTFS) with concurrent processes; POSIX semantics rely on the same atomic `rename` of a non-empty directory.
