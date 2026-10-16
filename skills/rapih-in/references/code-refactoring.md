# Code refactoring and file splitting

Goal: clearer responsibilities and easier change/testing, with observable behavior unchanged.

Contents: split or keep · extraction workflow · behavior-preservation checklist · UI specifics · backend specifics · characterization tests · examples.

## Split or keep

Split when all hold:
- The file mixes responsibilities with different reasons to change (for example UI layout, remote API calls, and input validation), or a part is hard to test on its own.
- The extracted part can get a clear name, explicit input/output, and an owner.
- The benefit outweighs the added indirection: extra files, parameters, and dependencies.

Keep when any holds:
- The file is long but cohesive, with a clear internal structure (a reducer with many cases, a parser, a state machine, a table of route definitions, a long but single-purpose component).
- Extraction would only chase a line count, produce many tiny files, pass many state values or callbacks around, or introduce a cycle.
- The file is generated, vendored, build output, fixture data, a snapshot, or a migration whose identity must be kept.

Do not split every type, constant, or helper into its own file when colocation is clearer. Merge duplicated code only when responsibility and behavior are truly the same, not because the text is similar.

## Extraction workflow

1. **Map** responsibilities, symbols and their callers, public exports, shared state and closures, side effects, async flows, and runtime boundaries. Decide what stays in the source file (usually the composition/orchestration).
2. **Plan** the symbol map (`source#symbol -> target#symbol`), kept contracts, new and changed files, dependency effects, and checks per batch. Start with the clearest boundary. Target locations follow `placement-rules.md`.
3. **Baseline** as in `migration-and-verification.md`. If risky behavior lacks adequate tests, add a targeted characterization test that records current behavior, before extracting, in a mutating mode only. Use existing tooling; do not build a large suite for coverage numbers.
4. **Extract one responsibility group per batch** and update its callers/imports in the same batch. Use a parser, language server, or IDE refactor when available; never rely on global text replace. Do not build a multi-language transformation engine.
5. **Preserve** everything in the checklist below. A compatibility re-export at the old location is acceptable when old callers or external users need it; do not force barrels everywhere.
6. **Check** after each batch with the relevant commands. On regression, fix within known scope or restore the batch before continuing dependents. Lint or build passing alone does not finish a large migration.
7. **Stop** when an important behavioral risk cannot be verified: do not apply that extraction; report the plan and the blocker. Limited changes already applied without enough validation stay `applied_unverified` with the missing checks listed.

## Behavior-preservation checklist

- Return values and their shapes, including `undefined` vs `null`.
- Errors meaningful to callers: type/class, message when callers match on it, sync throw vs rejected promise.
- Order of side effects (logging, analytics, writes, network calls) and how many times they run.
- Async behavior: awaited vs fire-and-forget, cancellation, race handling, debounce/throttle timing.
- Closures: values captured at definition time must not become stale or shared after moving code out.
- Module-level state and singletons: moving a module can create a second instance (duplicate import paths, separate bundles).
- Public exports: names, default vs named, types exported for consumers, package `exports` entries.
- `this` binding when moving methods into functions; decorators and metadata.
- Environment/runtime: no server-only import reaches client code; no Node-only API reaches browser code.

## UI specifics (React and similar)

- Keep component identity and lifecycle: defining a component inside another component, or changing its position/key in the tree, remounts it and resets state.
- Moving state into a custom hook is safe only if the hook is called in the same component, unconditionally, in the same order. Moving state up or down a level changes when it resets and who re-renders.
- Keep effect dependencies identical; do not "fix" dependency arrays in a refactor.
- Keep memoization semantics (`useMemo`, `useCallback`, `React.memo`) when consumers rely on referential stability.
- Context providers: extracting a provider must not change the tree position consumers rely on.
- Client/server boundaries (Next.js App Router): a `"use client"` module and everything it imports is client code; extraction must not pull server-only modules into it, nor drop the directive from a file that needs it.
- Styling: keep class names, CSS module imports, and style order so the rendered UI is unchanged.

## Backend specifics

- Keep request/response contracts: routes, methods, status codes, headers, payload shapes, validation error format.
- Keep the order of middleware, authorization before data access, and transaction boundaries (do not split one transaction into two).
- Keep logging fields others parse, and metrics names.
- Dependency injection registration must still resolve the same instances (scope/lifetime).

## Characterization tests

- Target the behavior at risk, through the public entry (component render + interaction, exported function, HTTP handler).
- Assert current behavior, even if surprising. If the current behavior looks like a bug, record it as a separate finding; do not fix it inside the refactor.
- Place tests where the repo's runner discovers them. Run them before the extraction (must pass on the original) and after.
- Never weaken or delete existing tests, or loosen lint rules, to make checks pass.

## Example: mixed-responsibility file (illustration, not a template)

`src/features/checkout/CheckoutPage.tsx` (React, feature-organized repo) contains page layout, a form with field state, a `fetch` to `/api/orders`, and a validation function used only by the form.

| Part in source file | Conditional target in the same feature | Responsibility |
| --- | --- | --- |
| Page composition | stays in `CheckoutPage.tsx` | Wires the page sections |
| Form with a clear boundary | `components/CheckoutForm.tsx` | Form display and interaction |
| Checkout state/flow worth isolating | `hooks/useCheckout.ts` | State and submit flow |
| Backend call | `api/checkout.ts` | Checkout API access |
| Input validation rules | `validation/checkoutSchema.ts` | Input validation |

Extract only the parts that pay off. If the validation is five lines used once, it can stay next to the form. Everything stays inside `features/checkout/`; nothing moves to shared folders.

## Example: long file kept on purpose

`src/lib/money/currencyTable.ts` is 900 lines: one exported lookup table of currency metadata plus two small accessors. It is cohesive data with one reason to change. Report "kept: cohesive data table; splitting adds indirection without benefit". Same for a 600-line reducer whose cases all serve one state slice, or a generated `schema.d.ts`.
