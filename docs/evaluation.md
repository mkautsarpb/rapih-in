# Evaluation

Package version: rapih-in 1.0.0 (helper `VERSION = "1.0.0"`). Evaluated on 2026-10-16.

## Environment

| Item | Value |
| --- | --- |
| OS | Windows 11 Pro 10.0.26200, NTFS |
| Python | 3.12.10 (helper, tools, tests) |
| Node.js | 24.12.0 (fixture tests via `node --test`) |
| Git | 2.50.1.windows.1 |
| Claude Code | 2.1.301, `claude -p --model sonnet`, permission mode `acceptEdits`, tools Bash/Read/Edit/Write/Glob/Grep/Skill |
| Codex CLI | 0.162.0, `codex exec --sandbox workspace-write`, default model |
| Antigravity IDE | 2.5.5 installed; not running, not driven |
| Antigravity App | installed; not driven |
| Cursor Agent, Kimi Code CLI | not installed |
| WSL / Docker | no distribution / not installed (no POSIX run) |

The user's own plugins and settings were active in the Claude Code runs (this is the real host environment), so wording style in reports varies.

## Levels of evidence

1. **Static package validation**: `python tools/validate.py` (frontmatter, size, links, host-neutral core, README parity, LICENSE). Result: all checks pass.
2. **Script tests**: `python -m unittest discover -s tests`, 30 tests (25 state helper, 5 install tool). Result: 30 passed. They use real processes and real files in temporary directories.
3. **Agent behavior**: real agent CLIs on throwaway copies of `evals/fixtures/*`, driven by `evals/run_agent_eval.py`. Each copy lives in a path with a space, is committed to a throwaway git repo, and gets its own `RAPIH_IN_STATE_DIR`, so neither the fixtures nor `~/.rapih-in` were touched. Changed files are measured by hashing the tree before and after, not taken from the agent's report.
4. **Host discovery and invocation**: see the host matrix.

One run per case. Agent output varies between runs; a single passing run is evidence of capability, not a guarantee.

## Script tests (level 2)

| Area | What is proven |
| --- | --- |
| Lock | 8 processes started at the same instant: exactly 1 acquires, 7 get `busy` (exit 3). Release needs the owner token. Junction alias of a worktree shares the key; a second `git worktree` gets its own key and lock. |
| Stale lock | An ancient timestamp and a dead PID never release the lock; recovery without user confirmation or with a wrong owner token is refused; recovery is refused while the recorded process is alive; with confirmation the takeover is atomic, the old token stops working, and the old run is marked `interrupted`. |
| Writes | `run init`, `batch *`, `restore` need the current token. `guard` and `batch begin --expect` detect an external edit / stale preimage / rename-target collision before any write. |
| Interruption | New file written and recorded, source not yet edited: verdict `interrupted_partial`, re-beginning the batch is refused. Unrecorded half-written file: `interrupted_needs_inspection`, restore refuses it unless explicitly included. |
| Restore | Restores run changes and deletes an unchanged run-created file; keeps a user's later edit (conflict, nothing restored without `--partial`; with `--partial` only separable files); restores to the user's uncommitted baseline, not `HEAD`; move is reversible; missing snapshot is reported, not guessed. |
| Isolation | Read-only commands create no state; a run from another worktree is not visible; scope, exclusions, and selection are immutable after `run init`; `.env` and paths escaping the root are refused and never copied into snapshots. |
| Install tool | `plan` writes nothing; install is idempotent and keeps existing `AGENTS.md` text with exactly one block; an unmanaged `rapih-in` folder is not overwritten; drift and local edits are detected; uninstall removes only rapih-in parts; project scope uses one shared `.agents/skills` copy. |

## Agent behavior (level 3)

Fixtures: `web-shop` (frontend, feature folders, mixed `CheckoutPage.js`, long cohesive `currencyTable.js`, generated `apiTypes.js`), `orders-api` (Node backend, route mixing HTTP/pricing/storage), `monorepo` (npm workspaces, shared package importing from an app, two different valid app layouts), `py-billing` (Python `src` layout), `next-app` (App Router, `server-only`), `tidy-notes` (already consistent).

Host: Claude Code unless noted. "Files changed" counts the measured tree diff.

| Case | Fixture | Input | Files changed | Observed | Result |
| --- | --- | --- | --- | --- | --- |
| E01b | web-shop | `/rapih-in` | 0 | Help text, suggests `audit`. | pass |
| E02 | web-shop | `/rapih-in audit` | 0 | R001 mixed responsibility in `CheckoutPage.js` with evidence and contracts; kept `currencyTable.js` (cohesive) and generated file; cosmetic item optional; noted XSS risk as a separate bug. Helper call was denied by the host permission prompt, so it used a fallback audit ID (led to the fallback rule now in SKILL.md). | pass (with noted fallback) |
| E03 | web-shop | `/rapih-in place fitur notifikasi` | 0 | `src/features/notifications/` with only needed files, reuse `components/ui/Button.js`, keep toast local until a second consumer. | pass |
| E04 | web-shop | `/rapih-in all --dry-run` | 0, no state | Preview with symbol map, patch summary, kept contracts; preview test on a temporary copy labeled as such; copy deleted. | pass |
| E05 | web-shop | `/rapih-in all` | 4 | b0 characterization tests (pass on original), b1 validation extracted, b2 API call extracted; re-exports keep contracts; tests 3/3 -> 8/8; checkpoint with 3 validated batches; lock released; long table and generated file kept. Independently re-ran the new tests against the original code: 8/8 pass. | pass |
| E06 | E05 result | `/rapih-in all` (new session) | 0, no state | No findings, no changes. Did not issue an audit ID. | pass (minor deviation) |
| E07b | E05 result | "Tambahkan komponen CouponInput ... beserta test-nya." | 2 | Skill invoked implicitly; `features/checkout/components/CouponInput.js` + colocated test; no audit, no moves. | pass |
| E08b | web-shop | Small label bug fix | 2 (3 lines) | Skill not invoked; no restructuring. | pass |
| E24 | web-shop | Conceptual question | 0 | Skill not invoked. | pass |
| E09 | monorepo | `/rapih-in audit` | 0 | P1: `packages/shared` imports from `apps/web` (inversion and cycle); P1: deep imports bypass `@acme/shared`; both app layouts kept as valid. | pass |
| E10 | orders-api | `/rapih-in audit` | 0 | R001 route mixes HTTP, pricing, storage; R002 optional; behavior bugs recorded separately. | pass |
| E11 | E10 session | `/rapih-in fix --only R001` | 4 | Characterization tests first, pricing and order storage extracted into `services/`; R002 untouched; 2/2 -> 5/5; 3 validated batches; lock released. Reported its own malformed intermediate edit that it fixed before marking the batch. | pass |
| E12 | web-shop | `/rapih-in fixx --exclude` | 0 | Unknown mode and missing value explained, usage shown. | pass |
| E13 | web-shop | `/rapih-in audit --only R001` | 0 | `--only` invalid for `audit`; no audit context to match IDs. | pass |
| E14 | web-shop | `/rapih-in resume` | 0 | No run to resume; suggests `audit` / `all`. | pass |
| E15 | web-shop, lock held by another run | `/rapih-in fix src/features/checkout/CheckoutPage.js` | 0 | `busy`, owner run named, no polling, no takeover, plan shown read-only. | pass |
| E16 | py-billing | `/rapih-in place modul aturan diskon ...` | 0 | `src/billing/discount.py` + `tests/test_discount.py`, dependency direction, asks about discount-before-tax. | pass |
| E17 | next-app | `/rapih-in place halaman detail produk ...` | 0 | `src/app/(shop)/products/[id]/page.tsx`, client button in `_components/` with `'use client'`, data access stays in `server-only` module. | pass |
| E18 | tidy-notes | `/rapih-in all` | 0, no state | No findings; baseline tests run; no lock or checkpoint. | pass |
| E19 | web-shop | `/rapih-in all <file> --exclude src/features/checkout/api/ --dry-run` | 0, no state | Single-file scope; excluded `api/` target marked as blocker and an allowed alternative proposed. | pass |
| E21 | web-shop, simulated crash | `/rapih-in resume` (before the fix) | 2 | Resumed correctly without duplicating symbols and kept the user's later edit, but **took over the lock on its own judgment** because the recorded PID was dead. | fail, fixed |
| E21b | same setup, after the fix | `/rapih-in resume` | 0 | Diagnosed `interrupted_partial`, left the user edit alone, refused takeover, asked the user to confirm the owner session ended. | pass |
| E21c | E21b session | "Ya, sesi pemilik run itu sudah saya tutup ..." | 2 | Recovered the lock after confirmation, kept the already-written file, finished b1 and b2, tests 3/3, user edit untouched, lock released. | pass |
| E22 | E05 result, new session | "Pulihkan ... run R-... batch b2 saja." | 2 | b2 restored from the checkpoint (source back to post-b1, run-created file deleted), b0/b1 kept, tests 8/8. | pass |
| E23 | E22 result + user edit in a b1 file | "Pulihkan ... batch b1." | 0 | Conflict on the user-edited file, nothing restored, options explained. | pass |
| E20c | web-shop, **Codex CLI** | `$rapih-in audit` | 0 | Skill discovered from `~/.agents/skills`; helper used (audit ID with repo key, fingerprint); R001 with evidence; kept files listed. | pass |
| S01 | web-shop | `/rapih-in-audit src/features/checkout` (shortcut) | 0 | Same audit behavior as `/rapih-in audit`, scope limited to the folder. | pass |
| S02 | web-shop | `/rapih-in-place fitur notifikasi` (shortcut) | 0 | Same placement answer as E03. | pass |
| S03 | web-shop | `/rapih-in-all --dry-run` (shortcut) | 0, no state | Preview only, baseline run, no lock or checkpoint. | pass |
| S04 | web-shop | Feature request (implicit), shortcuts installed | 2 | The host picked the main `rapih-in` skill, not a shortcut; component placed in `features/checkout/components/`. | pass |
| S05 | web-shop, **Codex CLI** | `$rapih-in-audit` (shortcut) | 0 | Shortcut discovered and forwarded to the main skill; helper audit ID and fingerprint. | pass |

Total agent cost for the recorded Claude Code runs: about 8 USD.

Shortcut commands (S01-S05) were added after the first round: seven manual-only skills `rapih-in-<mode>` that load the main skill. In the running Claude Code session the model-facing skill list still showed only `rapih-in` after installing them, which is the expected effect of `disable-model-invocation: true`.

Fix made because of evaluation: E21 showed that a dead "invoker" PID was treated as proof of an inactive owner. The helper flag is now `--user-confirmed-owner-inactive`, its diagnostics say a dead PID is not proof, and SKILL.md plus `checkpoints-and-recovery.md` require explicit user confirmation. E21b/E21c verify the new behavior. E02 led to the documented fallback when the helper cannot run in a read-only mode.

## Host matrix (level 4)

| Host | Version / variant | Effective skill source | Reminder | Discovery | Invocation | Behavior tested | Limits |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Claude Code | 2.1.301 CLI (and VS Code extension session) | `~/.claude/skills/rapih-in/` | `~/.claude/rules/rapih-in.md` | Yes: listed live in the running session after install | `/rapih-in ...`, shortcuts `/rapih-in-<mode>`, and implicit (E07b, S04) | 27 cases above | Only `--model sonnet` in `-p` mode |
| Codex | CLI 0.162.0 | `~/.agents/skills/rapih-in/` | block in `~/.codex/AGENTS.md` | Yes (E20c, S05) | `$rapih-in audit`, `$rapih-in-audit` | 2 read-only cases | Mutating modes not run under Codex; IDE extension not tested |
| Antigravity | IDE 2.5.5, App installed | `~/.gemini/config/skills/rapih-in/` | `~/.gemini/config/rules/rapih-in.md` (`trigger: always_on`) | Not verified (app not running) | Not tested | None | Files placed per official docs only |
| Cursor Agent | not installed | would read `~/.agents/skills/` and `~/.claude/skills/` (identical copies) | User Rules text: `python tools/sync.py reminder` | Not tested | Not tested | None | |
| Kimi Code CLI | not installed | would read `~/.agents/skills/` | none written (Kimi not detected) | Not tested | Not tested | None | |

## Scenario coverage (the 37 planned scenarios)

Status: **pass** (evidence above), **partial** (part of the behavior evidenced), **not tested**.

| # | Scenario | Evidence | Status |
| --- | --- | --- | --- |
| 1 | Component in an existing feature | E07b | pass |
| 2 | Single-feature utility stays local | E03 (toast local), E16 | pass |
| 3 | Generic UI uses shared UI | E03, E07b (`Button`) | pass |
| 4 | Next.js route keeps router and runtime boundary | E17 (place only) | partial |
| 5 | Python module keeps package/test discovery | E16 (place only) | partial |
| 6 | Monorepo feature in owner package, no back-dependency | E09 detects inversion; no feature added | partial |
| 7 | Rename updates references, keeps user changes | helper move/restore tests; no agent rename run | partial |
| 8 | Simple repo gets no extra layers | E18, E03 | pass |
| 9 | Concept question / small change does not refactor | E24, E08b | pass |
| 10 | Rerun on a tidy repo is a no-op | E06, E18 | pass |
| 11 | Shared skill roots stay consistent | `sync.py verify` (3 identical copies), E20c | pass |
| 12 | Unavailable hosts are not claimed | host matrix | pass |
| 13 | Bare invocation shows help; implicit use helps the task | E01b, E07b, S04 | pass |
| 14 | audit/plan/place/check do not change anything | E02, E03, E09, E10, E16, E17, E20c; `plan` and `check` not run as modes | partial |
| 15 | `all --dry-run` leaves tree and state untouched | E04, E19 | pass |
| 16 | fix revalidates an old plan; all re-audits | E11, E05, E06 | partial (no stale-plan case) |
| 17 | Scope, spaces, repeated excludes, invalid input | E12, E13, E19; all work dirs contain a space; repeated `--exclude` only in helper test | partial |
| 18 | Failing baseline separated from regressions | no fixture with a failing baseline | not tested |
| 19 | Interrupted batch diagnosed, no blind replay | helper tests, E21b, E21c | pass |
| 20 | User changes after checkpoint detected; other worktree not used | E21b/E21c, helper tests | pass |
| 21 | Restore keeps user edits, marks conflicts | E22, E23, helper tests | pass |
| 22 | Install only installs | install tool tests, real install | pass |
| 23 | Two packages with different valid layouts kept | E09 | pass |
| 24 | Dynamic references / unclear boundaries reported as limits | reports state the limit (E05, E19); no dedicated fixture | partial |
| 25 | Later feature follows new ownership; real before/after | E07b, E05 | pass |
| 26 | Mixed UI/API/validation file split by responsibility | E05, E11 | pass |
| 27 | Long cohesive / generated files not split | E02, E05, E06, E20c | pass |
| 28 | Closure/state/async/export behavior checked | E05 characterization tests (async, errors, statuses), re-exports; no mutation test that the tests catch a change | partial |
| 29 | Extraction interrupted after new file | helper test, E21b/E21c | pass |
| 30 | Characterization test before risky extraction; none in read-only | E05, E11; E04/E19 wrote nothing | pass |
| 31 | Single-file scope + excluded target; narrow requests stay narrow | E19; folder-only request not run | partial |
| 32 | `--only` fixes only the selection | E11 | pass |
| 33 | Unknown/stale/ambiguous IDs do not redirect work | E13; `all --only` re-matching not run | partial |
| 34 | resume inherits selection; new `--only` rejected | E21c inherits R001; rejection not run | partial |
| 35 | Two writers: exactly one lock; alias vs worktree | helper tests, E15 | pass |
| 36 | Crashed owner / wrong token / old lock | helper tests, E21b | pass |
| 37 | External edit detected before patch; read-only takes no lock | helper `guard` tests; E02/E04/E18 no state | partial (agent-level external edit not run) |

Summary: 23 pass, 13 partial, 1 not tested. No comparison against other skills or against an agent without rapih-in was run, so no claim of superiority is made.

## Reproducing

```bash
python -m unittest discover -s tests
python tools/validate.py
# one agent case (Git Bash on Windows: set MSYS_NO_PATHCONV=1 so "/rapih-in" is not rewritten into a path)
python evals/run_agent_eval.py --case E02-audit --fixture web-shop --prompt "/rapih-in audit"
python evals/run_agent_eval.py --case E20c-codex-audit --host codex --fixture web-shop --prompt '$rapih-in audit'
```

Results land in `<temp>/rapih-in-evals/<case>/result.json`.
