# Examples

Illustrations of decisions and report shapes. They are not templates: real decisions come from the repo's evidence. Paths are conditional.

## Placement decisions

**Frontend (React/Vite, feature folders)**
Need: "add a coupon input to checkout".
Evidence: `src/features/checkout/components/` holds `CheckoutForm.tsx`, `OrderSummary.tsx`; `src/components/ui/Input.tsx` used by 4 features; vitest includes `src/**/*.test.tsx`.
Decision: `src/features/checkout/components/CouponInput.tsx` + `CouponInput.test.tsx` beside it, using `@/components/ui/Input`. Not shared: only checkout needs it.

**Backend (Express, routes + services)**
Need: "add invoice PDF export".
Evidence: `src/routes/invoices.ts` registers `/invoices`; business logic in `src/services/invoiceService.ts`; PDF library not yet used; tests in `test/services/*.test.ts`.
Decision: route `GET /invoices/:id/pdf` in `src/routes/invoices.ts`; rendering in `src/services/invoicePdf.ts` (new, invoice-specific); test `test/services/invoicePdf.test.ts`. No new `pdf/` layer: one consumer.

**Monorepo (pnpm, apps/web + apps/admin + packages/ui)**
Need: "date range picker for both web and admin".
Evidence: both apps depend on `packages/ui`; it exports components through `packages/ui/src/index.ts`; it has no app imports.
Decision: `packages/ui/src/DateRangePicker.tsx`, exported from the package index; app-specific presets stay in each app. No new package.

**Same repo, two valid styles**
`apps/web` uses `src/features/*`; `apps/api` (NestJS) uses `src/<module>/<module>.service.ts`. Both are kept. A new API feature follows the Nest module style; a new web feature follows feature folders. The difference is not a finding.

## Audit report (shape)

```
rapih-in audit · read-only · audit_id A-20261016T091200-3f9c2a
Root: D:\work\shop (git main, 2 uncommitted files) · Scope: src/ · Exclusions: src/generated/** (user); node_modules/**, dist/** (default)

Profile: React 18 + Vite (package.json); features/<name>/ pattern in cart, auth (observed); alias @/ -> src (tsconfig); vitest colocated (vitest.config.ts)

| ID | P | Kind | Location | Evidence | Impact | Suggested change | Fingerprint |
| R001 | P1 | boundary-violation | src/features/checkout/CheckoutPage.tsx | imports src/server/db.ts (pg client) | server code in client bundle | move query behind api/checkout.ts call | 9be1c04d2a11 |
| R002 | P2 | mixed-responsibility | src/features/checkout/CheckoutPage.tsx#CheckoutPage | layout + form state + fetch + validation (4 reasons to change) | hard to test submit flow | extract useCheckout, api/checkout.ts | 41f0aa7c93e2 |
| R003 | P2 | misplaced-file | src/utils/formatPrice.ts | only imported by src/features/cart/* (3 files) | generic folder hides owner | move into features/cart/ | 7c2d55e01b8a |
| R004 | P3 | naming (optional) | src/features/auth/login-form.tsx | other components PascalCase | cosmetic | rename only if requested | 0d9e3b7f6a21 |

Dependencies: R002 after R001 (same file). Kept on purpose: src/lib/money/currencyTable.ts (long, cohesive data).
Next: "rapih-in all --dry-run" for a full preview, or "rapih-in fix --only R001,R002".
```

## Plan (shape)

```
rapih-in plan · read-only · from audit A-20261016T091200-3f9c2a · --only R001,R002
| Batch | IDs | Op | From | To | Reason | Kept contracts | References | Checks |
| b1 | R001 | extract | CheckoutPage.tsx#loadOrder (pg query) | src/features/checkout/api/checkout.ts#fetchOrder (fetch /api/orders/:id) | no db client in browser | same Order shape | CheckoutPage.tsx | tsc; vitest checkout |
| b2 | R002 | extract | CheckoutPage.tsx#{useState x5, submit} | hooks/useCheckout.ts#useCheckout | isolate submit flow | CheckoutPage props/export unchanged; submit order of calls | CheckoutPage.tsx | characterization test first; vitest checkout |
Stays in CheckoutPage.tsx: layout and composition.
Supporting edits: CheckoutPage.test.tsx (new characterization test, b2).
Limits: e2e not runnable locally.
```

## Place answer (shape)

```
rapih-in place "notification feature" · read-only
Recommended: src/features/notifications/ (components/NotificationList.tsx, hooks/useNotifications.ts, api/notifications.ts as needed)
Why: repo uses features/<name>/ (cart, auth, checkout); notifications have their own API and UI.
Shared parts: toast UI already exists at src/components/ui/Toast.tsx; reuse it.
Not chosen: src/services/notifications.ts (services/ is legacy; last 12 features went to features/).
Would change if: notifications are also sent by the backend app -> shared contract types belong in packages/contracts.
```

## Contextual use (skill loaded implicitly)

User: "add a password reset page". Agent builds the feature and places files by the profile (`src/features/auth/ResetPasswordPage.tsx`, route added in the existing router file). It does not audit the repo, does not move the long `src/legacy/` folder it noticed, and mentions it in one line as an optional `audit` later.

## No-op

Running `rapih-in all` again on the same scope after a validated run: fresh audit finds only R004 (optional) -> "No changes applied; one optional cosmetic item remains." No diff.
