# Stack adapters

Each section lists evidence to check, rules to preserve, conditional example locations, when simple is enough, and when splitting by feature/domain/package is justified. All paths are **conditional examples**: use them only when the repo's evidence points that way, and never create the whole example tree.

## React / Vite (client SPA)

- **Evidence**: `package.json` (react, vite), `vite.config.*` (aliases, `root`), `tsconfig*.json` `paths`, `index.html` entry, router setup (`react-router` routes file or `createBrowserRouter`), existing `src/` layout, test runner include globs.
- **Preserve**: `index.html` and `src/main.*` entry, `public/` for static assets served as-is, alias targets, env variable prefix (`VITE_`), router conventions in use.
- **Conditional examples**:
  - Feature-organized repo: new checkout form -> `src/features/checkout/components/CheckoutForm.tsx`.
  - Type-organized small repo (`src/components`, `src/hooks`, `src/pages`): new page -> `src/pages/Profile.tsx`; keep that style.
  - Generic button used by three features -> existing `src/components/ui/Button.tsx`.
- **Simple is enough** when the app has a handful of screens and type-based folders are still easy to navigate.
- **Split by feature** when type folders hold unrelated features side by side, features change independently, and imports cross features through internals.

## Next.js

- **Evidence**: `next.config.*`, `app/` or `pages/` (and whether they live under `src/`), `middleware.*`, `tsconfig` paths, `"use client"` / `"use server"` directives, route handlers (`app/**/route.ts`) or API routes (`pages/api/**`).
- **Preserve**: the router in use (do not migrate `pages/` to `app/` or back), the `src/` decision, file conventions (`page`, `layout`, `loading`, `error`, `route`, `not-found`, `default`), route groups `(group)`, private folders `_folder`, dynamic segments, and server/client boundaries. Never move the app root for tidiness.
- **Conditional examples**:
  - App Router with `src/`: new route -> `src/app/(shop)/orders/page.tsx`; its client-only widget -> `src/app/(shop)/orders/_components/OrderFilters.tsx` (with `"use client"`), or the repo's existing feature folder if it has one.
  - Route handler -> `src/app/api/orders/route.ts`; server-only data access -> the repo's server module (for example `src/server/orders.ts` with `import "server-only"` if the repo uses that package).
  - Pages Router: new page -> `pages/orders/index.tsx`; API -> `pages/api/orders.ts`.
- **Boundary checks**: a module imported by a client component must not import server-only code, secrets, or database clients. Moving a component across the `"use client"` boundary changes behavior; treat it as risky.
- **Simple is enough** when colocating route-specific components inside the route segment covers the need.
- **Split** when the same domain logic is used by several routes and handlers.

## Node.js backend (Express, Fastify, Koa, NestJS, Hono)

- **Evidence**: `package.json` (`type`, `main`, `exports`, scripts), framework, `tsconfig` `rootDir/outDir`, how routes/modules are registered (manual imports, autoload plugin, Nest modules), ORM/migration tool and its directory, test layout.
- **Preserve**: module conventions (Nest `*.module.ts` / `*.controller.ts` / `*.service.ts` per feature module; Fastify autoload directories), migration directory and file order, ESM vs CJS, public HTTP contracts (paths, status codes, payloads), startup order and middleware order.
- **Conditional examples**:
  - Express with `src/routes/` + `src/services/`: new endpoint -> `src/routes/invoices.ts` + `src/services/invoiceService.ts`, following existing pairs.
  - Feature modules (`src/modules/<name>/`): new feature -> `src/modules/invoices/{invoices.routes.ts,invoices.service.ts,invoices.repository.ts}` only for the files actually needed.
  - NestJS: `src/invoices/invoices.module.ts` etc., registered in the parent module.
- **Simple is enough** for a small API where route files call the DB directly and stay short.
- **Split** route/controller, domain logic, and persistence when one file handles HTTP parsing, business rules, and queries for several use cases, or tests need to exercise rules without HTTP.

## Python (package, API, or data pipeline)

- **Evidence**: `pyproject.toml` (build backend, `[tool.setuptools.packages]`, `package-dir`, `[tool.pytest.ini_options]` `testpaths`/`pythonpath`), `setup.cfg`/`setup.py`, `src/` layout vs flat, `__init__.py` presence (regular vs namespace packages), framework (FastAPI, Django apps, Flask blueprints), pipeline tool (Airflow DAG folder, dbt, Prefect), entry points/console scripts.
- **Preserve**: import paths used by consumers and entry points, Django app labels and migrations, Airflow `dags/` discovery, test discovery settings. Check package/import/test discovery before choosing or changing a `src/` layout; do not convert flat to `src/` (or back) for tidiness.
- **Conditional examples**:
  - `src/` layout package: new module -> `src/<pkg>/billing/invoice.py`, tests -> `tests/billing/test_invoice.py` if `testpaths = ["tests"]`.
  - FastAPI: router -> `app/routers/invoices.py`, schemas next to the existing schema module, DB access in the existing `crud`/`repositories` module.
  - Data pipeline: transform step -> the existing `pipelines/<domain>/` or `transforms/` module; DAG file stays in `dags/`.
- **Moving a module changes its import path**: update all imports, `__init__` re-exports, entry points, `mock.patch("pkg.mod.name")` strings, pickled/serialized references, and docs. Keep a compatibility re-export if external users import the old path.

## Monorepo / workspace

- **Evidence**: workspace manifest, each package's `package.json`/`pyproject` (`name`, `exports`, dependencies), TS project references, build graph tool config (Turborepo, Nx tags and `enforce-module-boundaries`), CODEOWNERS.
- **Preserve**: package names and `exports`, dependency direction (apps -> packages, never packages -> apps), build/task pipeline, publishing config.
- **Decide the owner package first**. Then apply the stack section for that package. Different packages may legitimately use different internal layouts.
- **Conditional examples**:
  - Feature only used by `apps/web` -> inside `apps/web`, not a new package.
  - Date formatting used by `apps/web` and `apps/admin` -> existing `packages/utils` if its scope fits, else a focused folder inside it; a new package only when it has a distinct owner, release cadence, or dependency set.
  - Shared types for API contracts -> the existing contracts/types package that both sides already depend on.
- **Do not** turn every shared need into a new package, and do not add a workspace dependency that creates a cycle.

## Unknown or unlisted stack

- Read the manifest and build config; consult the tool's official documentation for required locations; copy the local precedent closest to the target.
- State plainly what is verified and what is assumed. Do not guess framework layouts.
- Prefer leaving structure as-is plus a recommendation over a speculative migration.
