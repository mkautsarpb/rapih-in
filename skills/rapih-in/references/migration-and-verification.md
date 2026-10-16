# Migration and verification

Contents: baseline · reference discovery · case-only renames · batch design · applying · after applying · before/after comparison · statuses · run report.

## Baseline (before any mutation)

1. Working tree: with Git, `git status --porcelain=v1 -uall` and `git diff --stat`; record uncommitted and untracked files in scope. Without Git, record hashes of the files in scope (helper `hash`). The baseline is the user's current working tree, not `HEAD`.
2. Checks: discover commands from repo config only (package.json `scripts`, `pyproject`/`tox.ini`/`noxfile.py`, `Makefile`, `justfile`, CI workflow steps). Never invent `npm test` or similar. Run the targeted ones that fit the risk: typecheck, lint (without `--fix`), tests for the affected area, build, an import/package smoke check.
3. Record per check: command, exit status, short result. Commands that cannot run (missing toolchain, needs network or secrets) are recorded as `not runnable` with the reason. Do not install whole toolchains to make a baseline.
4. A failing baseline is recorded as `failing before change`. It never makes the project "healthy", and it never excuses new errors. Compare error identities (file, rule/test name, message) to separate old failures from regressions.

## Reference discovery

For every moved, renamed, or extracted symbol/file, look for:
- Static imports/exports and re-exports, including `index` barrels.
- Path aliases (`tsconfig` `paths`, bundler aliases, Python `package-dir`, Jest `moduleNameMapper`).
- Dynamic imports: `import()`, `require(variable)`, `importlib.import_module`, lazy routes, string-based plugin registries.
- File-system discovery: framework routers, glob loaders (`import.meta.glob`, `require.context`), test discovery globs, Storybook globs, CSS/asset globs.
- String references: mock targets (`jest.mock('path')`, `mock.patch('pkg.mod.x')`), fixture paths, snapshot names, i18n keys tied to file paths.
- Build/CI/scripts: package `exports`/`main`/`bin`, Dockerfiles, CI paths and caches, codegen config, coverage config, CODEOWNERS.
- Documentation and instruction files that name paths (update when part of the scope; otherwise list).

If a dynamic reference cannot be resolved with certainty, do not claim the migration is fully validated; list it under "needs manual check".

## Case-only renames and collisions

- Before any move, check whether the target exists (helper `batch begin --expect target=missing` fails on collision). Never overwrite a target owned by other changes.
- Case-only renames (`button.tsx` -> `Button.tsx`) on case-insensitive filesystems (Windows, default macOS): rename through a temporary name in two steps; with Git, `git mv a tmp && git mv tmp A` so the index records it. Check for imports that differ only by case.

## Batch design

- One batch = one coherent responsibility/module change plus all its reference updates. A batch is never "done" while the new file exists but the source file or callers are not yet adjusted.
- Order batches by dependency: leaf modules first, then their consumers; boundary fixes before cosmetic ones.
- Each batch lists: finding IDs, operations (`create`, `modify`, `move src=>dst`, `delete`), files, symbols, kept contracts, checks to run.

## Applying

- Inside a batch: `batch begin` with every file to be touched, `guard` with expected hashes right before writing, write, and `batch record <path>` after writing each file so an interruption can tell the run's writes from anyone else's.
- Keep user changes and unrelated files intact. If a preimage does not match, do not write: mark a conflict and re-plan from the latest content.
- No global search-and-replace without understanding each match.
- Never change public URLs, API contracts, migration identity, or package exports by accident.
- Update references together with the move, in the same batch.

## After applying

- Run the batch's checks. Distinguish: `passed`, `failing before change` (same failure as baseline), `new regression`, `not run` (with reason).
- Do not weaken tests or lint rules to get a pass.
- On a new regression: fix the cause within the known scope; if that fails, restore the batch (helper `restore`), mark it `failed`, and stop dependent batches. Save the checkpoint and report the blocker.
- Mark `validated` only when the relevant checks ran and passed (or match the baseline failures exactly). Otherwise `applied_unverified` with the missing checks.
- Repeating the same command with no new need must be a no-op: no further structural churn.

## Before/after comparison

- Re-audit with the same scope, exclusions, and method as the baseline audit.
- Report: findings resolved, remaining, new; references still unresolved; check results before vs after.
- Use dependency/boundary tooling results only if the repo has such tooling (for example `madge`, `dependency-cruiser`, ESLint boundaries, `import-linter`). Text search alone does not prove a clean dependency graph; say what was covered.
- Fewer folders, more files moved, or tests passing do not by themselves prove better architecture. Without a baseline, do not invent a comparison.

## Statuses

`planned`, `in_progress`, `applied_unverified`, `validated`, `blocked`, `failed`, `interrupted`, `completed`, plus per finding: `selected`, `not selected`, `resolved`, `resolved as side effect`, `blocked`, `stale`, `already resolved`.
`applied_unverified` is never reported as validated.

## Run report (template)

```
rapih-in all · real application · run R-20261016T091500-a1b2 · audit A-20261016T091200-3f9c2a
Scope: D:\work\shop\src (git, branch main, 2 uncommitted files kept)
Exclusions: src/generated/** (user), node_modules/**, dist/** (default)
Selection: all findings in scope (R001-R004); R004 cosmetic, not applied

Batches
| Batch | Findings | Change | Status | Checks |
| b1 | R001 | extract useCheckout + api/checkout.ts from CheckoutPage.tsx; 2 callers updated | validated | tsc pass; vitest checkout 12/12 |
| b2 | R002 | move src/utils/formatPrice.ts -> src/features/cart/formatPrice.ts; 3 imports | validated | tsc pass; vitest cart pass |
| b3 | R003 | move src/lib/db.ts out of client bundle | blocked | dynamic import in src/plugins/load.ts unresolved |

Before -> after (same scope and method): findings 4 -> 2 (R003 blocked, R004 optional)
Checks: lint failing before change (2 errors in src/legacy, unchanged); no new regressions in run checks
Not run: e2e (needs running backend)
Checkpoint: C:\Users\me\.rapih-in\runs\<key>\R-20261016T091500-a1b2\checkpoint.json · lock released
Next: resolve the dynamic import, then "rapih-in resume" or "restore rapih-in run R-... batch b2"
```
