# Placement rules

Contents: principles · inspection checklist · structure profile · ownership · decision order details · code-organization rules · tests and non-code files · convention notes · when to ask.

## Principles

- There is no universal folder structure. The repository's evidence decides.
- Precedence: user instructions and repository instruction files (per the host's instruction hierarchy) > real framework/build requirements > consistent local patterns of the area being changed > idiomatic minimal structure for the ecosystem.
- If a request conflicts with a technical requirement, explain the consequence and choose a solution that still works. Never silently drop either side.
- A repo with several stacks may have several valid patterns. Keep each area's pattern.
- New repo or area without a pattern: pick the idiomatic structure with the least complexity.
- Old repo: improve incrementally within the task's scope.
- Every structural change needs a concrete benefit: clearer ownership, healthier dependencies, or easier navigation.
- Do not impose Clean Architecture, DDD, microservices, monorepos, or extra layers on simple apps.
- Create folders for real needs, not hypothetical ones.
- Never change the stack, package manager, or repo-wide naming style as a side effect.

## Inspection checklist

Read only what the decision needs, in this order:

1. Instruction files that apply to the target directory (AGENTS.md, CLAUDE.md, GEMINI.md, `.cursor/rules`, `.agents/rules`, CONTRIBUTING, ADRs, an existing conventions/architecture doc).
2. Root markers: `.git`, workspace manifests (`pnpm-workspace.yaml`, `package.json#workspaces`, `turbo.json`, `nx.json`, `lerna.json`, `Cargo.toml [workspace]`, `go.work`, `pyproject.toml` with multiple packages).
3. Manifest and lockfile of the owning package (to know the package manager and scripts; do not change them).
4. Build/test/lint config: `tsconfig*.json` (`paths`, `baseUrl`, `rootDir`, `include`), `vite.config.*`, `next.config.*`, `jest/vitest.config.*`, `pytest.ini`/`pyproject [tool.pytest]`, `setup.cfg`, ESLint boundary rules (`import/no-restricted-paths`, `boundaries`, `dependency-cruiser`), CI workflows.
5. Entrypoints and discovery: router directories, `main`/`exports` fields, `__init__.py`, plugin registries, glob-based loaders.
6. Two or three similar implementations near the target (`rg --files | rg -i <term>`, `rg -l "<symbol>"`).

Skip: dependency folders, build output, caches, binaries, large data, `.env*` and key files. Treat generated code (headers like `@generated`, `DO NOT EDIT`, codegen config) and vendor code as read-only.

## Structure profile (working notes, not a file)

```
Stack: React 18 + Vite 5 (package.json, vite.config.ts)            [explicit]
Owner: apps/web (pnpm workspace member)                              [explicit]
Pattern: src/features/<feature>/{components,hooks,api}/ (cart, auth) [observed: 2 features]
Shared UI: src/components/ui/ (Button, Modal, used by 3 features)    [observed]
Alias: @/ -> src/ (tsconfig.json paths)                              [explicit]
Tests: colocated *.test.tsx (vitest include: src/**/*.test.tsx)       [explicit]
Runtime: client only; server code lives in apps/api                  [observed]
Exception: src/legacy/ predates features/, untouched by recent commits [observed]
Unverified: whether src/lib/ is meant as shared or legacy             [assumption]
```

Update only the parts a change affects. Never present a percentage of confidence.

## Ownership questions

For each file or extracted part answer:
- Responsibility: one sentence, no "and".
- Owner: which feature/domain/package changes when this changes?
- Consumers: who imports it today, who will after the change?
- Runtime: client, server, shared (isomorphic), tooling/build, or test.
- Precedent: where does the closest similar code live?
- Boundaries: which dependency direction must hold; which public entrypoint other modules use.

Two consumers in the same feature do not make code shared. Similar text in two features does not either: merge only when responsibility and behavior are the same.

## Decision order details

1. **Required location** - router files, migrations directories, framework config files, package `exports` targets, test discovery globs. Never move these for tidiness.
2. **Owner's equivalent slot** - if the owner has `components/`, a new component goes there; if it keeps everything flat, stay flat.
3. **Feature-local** - code used by one feature stays in that feature, even if it is generic-looking.
4. **Existing shared module** - only if its responsibility matches and depending on it does not invert a dependency (shared must not import from features or apps).
5. **New shared module** - needs at least two real, current consumers in different owners, and a name that states its responsibility.
6. **New folder or package** - last resort, with the benefit stated.

## Code-organization rules (adapt to local patterns)

- Feature-specific components, hooks, services, schemas, types, constants, and tests live in the feature area when that is the repo's pattern.
- Truly generic UI lives in the agreed shared UI location.
- Do not let `utils`, `helpers`, `common`, `services`, `lib` become dumping grounds. Do not replace one generic folder with another generic folder; name by responsibility (`formatCurrency.ts` in `shared/money/`, not `utils2/`).
- Separate business logic from transport/persistence only when complexity calls for it.
- Keep server code, credentials, and database access out of client dependencies.
- Shared packages never depend back on the apps that consume them.
- Cross-module access goes through an agreed contract or public entrypoint; avoid deep imports into another module's internals.
- Avoid circular dependencies. Do not add barrel files everywhere; add one only where the repo already uses them or a public entrypoint is needed.
- Follow the language/framework naming and the local convention (`PascalCase.tsx` components, `snake_case.py` modules, `kebab-case` where used). Do not convert existing names unless asked.
- File/depth/line limits are review signals only, never rules.

## Tests and non-code files

- Unit tests: colocate or use the `tests/` tree, whichever the repo and its test discovery already use. Check the runner config before placing a test so it is actually discovered.
- Integration/e2e tests, fixtures, migrations, assets, config, and scripts go where the existing tooling expects them.
- Preserve framework convention files, generated files, migration order/identity, and package contracts.
- Keep temporary artifacts, logs, caches, and build output out of source. Touch ignore rules only when relevant to the task.

## Convention notes

- Reuse existing project docs (architecture section, CONTRIBUTING, ADRs, instruction files) and check them against current source and config; stale docs are evidence of intent, not of reality.
- Record only important structural decisions that were agreed or proven: ownership, dependency limits, example locations.
- Write or update notes only during a mutating run where the decision was made, and only when useful. `audit`, `plan`, `place`, `check`, and `--dry-run` never write notes. Never add a note per new file.

## When to ask the user

Ask only when the choice changes a public contract, ownership between teams/packages, or a large architecture decision. Otherwise choose, state the reason in one line, and continue.
