# nova-probe — build templates

Read the section that matches what is being produced.

### `[BUILD ORIGIN]` template (bug-driven rebuilds only)

Distinct from `[ORIGIN BLUEPRINT]` below (the tier plan) — this captures
*why* the rebuild exists, produced first, before anything else, and written
into the blueprint file so it survives the conversation:

```
[BUILD ORIGIN]
Originating skill: <e.g. "nova-raven", "nova-refinery", "nova-observer Bug Profile">
Original symptom: <exact symptom as originally reported/diagnosed>
Root cause: <the diagnosed root cause this build addresses>
This build's role: <what specifically is being rebuilt/added to fix it>
```

This carries forward into the eventual handoff: `nova-immortal` must be
asked to regression-test the *exact original symptom* (not just "test the
new code"), and `nova-adjutant` references these artifacts as the "Fix
applied" field in its `[INCIDENT RECORD]`. A field not actually provided in
the handoff is marked `[⚠️ INFERRED]` or "not provided" — never invented.

### `[DATA EXPOSURE REVIEW]` template (when TIER 1/TIER 3 is in scope)

```
[DATA EXPOSURE REVIEW]
Target: <table/entity being defined>

| Field | Needed for stated use case? | Sensitivity flag | Decision | Reason |
|---|---|---|---|---|
| `user_id` | Yes | — | Include | Required for the core entity relationship |
| `ssn` | No | [⚠️ INFERRED — matches "ssn" pattern] | Exclude | Not needed for this use case |
| `email` | Yes | [⚠️ INFERRED — could be PII depending on context] | Include, pending confirmation | Needed for the stated notification feature — recommend `nova-refinery` classification review before this ships |
```

**Rules:**
- A field flagged sensitive is never silently included by default, even if
  it exists in a source system — it always requires an explicit "Include"
  or "Exclude" decision with a stated reason.
- A flagged field marked "Include" goes to `nova-refinery` for a formal
  Security Classification Review before the build is considered complete,
  and is recorded as `🔒 exposure review pending` in the blueprint file
  until that review lands. Whether the resulting control actually holds is
  proven later by `nova-immortal`, not by this review.
- This review runs during brownfield builds that touch existing fields too,
  not only greenfield ones.

### `[ORIGIN BLUEPRINT]` template *(written to `docs/build/<target>-blueprint.md`)*

```
[ORIGIN BLUEPRINT]
Target: <one-sentence description of what is being built>
Build Scenario: <Greenfield | Brownfield extension | Migration/refactor | Multi-service>
Project Type context: <which row of the Applicability table applies>

Reused existing artifacts:
- <e.g. "`orders` table (existing) — no schema change needed">

| Tier | Artifact | Real path / name | Status |
|---|---|---|---|
| 1 — Data Store | `order_items` table + migration | `migrations/0042_order_items.sql` | 📝 Draft |
| 3 — Domain Model | OrderItem entity | `src/models/orderItem.ts` | 📝 Draft |
| 4 — Interface Contract | OrderItemDTO | `src/types/orderItem.ts` | 📝 Draft |
| 5 — Business Logic | OrderItemService | `src/services/orderItemService.ts` | 📝 Draft `[⚠️ VERIFY IN DOCS]` |

Status values: 📝 Draft · ✅ Confirmed · 🏗️ Built · 🔁 Superseded (by
<what>, reason)

Behavior Parity Check (migration/refactor builds only):
- <what must remain identical from the outside>

Cross-service Build Order (multi-service builds only):
1. <service A contract must ship first>
2. <service B can then consume it>

Assumptions:
- <assumption 1> [⚠️ INFERRED if not confirmed]

Risks / Rollback considerations:
- <e.g. "schema change is additive and backward-compatible" or
  "requires a two-phase migration because column X is being removed">

Open items (carried until resolved):
- 🔒 exposure review pending: <field> — awaiting nova-refinery
- 🔍 docs verification pending: <artifact> — built with [⚠️ VERIFY IN DOCS] unresolved

Awaiting confirmation before generating code.
```

A `📝 Draft` left unconfirmed across turns is surfaced explicitly rather
than silently abandoned or silently re-proposed from scratch. An artifact
built while still carrying `[⚠️ VERIFY IN DOCS]` or `🔒 exposure review
pending` stays listed until the user confirms it is resolved.
