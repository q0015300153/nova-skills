# nova-sensor — inventory, cleanup and triage protocols

STEP 0 (in `SKILL.md`) still runs first in every mode. Output-section selection rules are in `SKILL.md` → Output Selection.

## Resource Inventory Protocol

Use in INVENTORY MODE.

If resource type or detail is ambiguous:

```text
[⚠️ SCOPE NEEDED]

Categories:
- Code
- Data
- Infrastructure
- Process
- Automation
- Observability
- Fleet
- Everything

Detail:
- Overview
- Detailed
```

Report:

```text
### [RESOURCE INVENTORY] · <scope> · scanned at <timestamp>
```

| Category | Resource | Current state | Purpose | Dependencies |
|---|---|---|---|---|

Rules:

- Every identifier must be verified this turn.
- Purpose inferred from naming is `[⚠️ INFERRED PURPOSE]`.
- Detailed inventory includes relevant versions and consumers.
- Inventory is complete or explicitly partial.
- Inventory is a census, not a status or cleanup report.
- Route unused candidates to `[CLEANUP AUDIT]`.

---

## Cleanup Audit Protocol

Use in CLEANUP MODE or when FULL MODE discovers a likely unused resource.

| Resource type | Required reference checks |
|---|---|
| File, module, function or class | imports, calls, entry points, reflection and tests |
| Table or column | queries, models, migrations, reports and jobs |
| API route or event | known clients, public contract, producers and consumers |
| Configuration or feature flag | reads, rollout logic and environment overrides |
| Dependency | imports, plugins, scripts and build tooling |
| Job or automation | registration, trigger reachability and intentional retention |
| UI page or component | routing, links, imports and dynamic registration |
| Branch or pull request | merge state, activity and retention convention |

Absence of accessible usage logs is not proof of no usage.

Report:

```text
### [CLEANUP AUDIT] · <scope> · scanned at <timestamp>
```

Use one Universal Task Format block per candidate.

Confidence:

- `Confirmed unused` — all relevant references were checked.
- `Likely unused [⚠️ INFERRED]` — coverage is incomplete.
- `[⚠️ UNVERIFIED]` — required checks could not run.

Rules:

- Never delete automatically.
- Include Delete, Keep and Verify First when all are defensible.
- State what may break if deletion is wrong.
- Call a candidate `still unused` only when the previous report and current
  references were read.
- A candidate now referenced is shown once as resolved, then removed.

---

## Bug Triage Protocol

Use in TRIAGE MODE.

### Candidate Routes

| Evidence-supported layer | Advisory route |
|---|---|
| Missing, duplicate or corrupted records; migration or schema failure | `[→ nova-refinery]` |
| Exceptions, timeout, wrong calculation or backend failure | `[→ nova-raven]` |
| Blank or incorrect UI, broken interaction or display issue | `[→ nova-prism]` |
| Suspected unauthorized visibility or export | `[→ nova-immortal]`, and `[→ nova-refinery]` when the control itself is unclear |
| Deployment, configuration, dependency or scheduling drift | Resolve as a Sensor task |
| Material ambiguity after evidence gathering | `[→ nova-observer]` |

### Targeted Evidence

Check only candidate layers:

- **Data:** migration state, validation failures and relevant counts.
- **Logic:** deploy/commit history, errors and tests.
- **Frontend:** build state, browser errors when available and recent UI
  changes.
- **Cross-layer:** environment differences, dependency versions, flags and
  job registration.
- **Exposure:** reachable paths and any recorded control contract.

Gather at least one relevant current signal. If no signal is accessible,
mark the route `[⚠️ UNVERIFIED]`.

### Output

```text
### [BUG TRIAGE] · scanned at <timestamp>
**Reported symptom:** <one sentence>
**Evidence:** <specific current findings>
**Likely layer:** <layer or Ambiguous>
**Resolution:** <Sensor task, when resolvable here>
**Route:** <only evidence-supported advisory route(s)>
```

Rules:

- Triage routes; it does not invent a root cause.
- Every route cites evidence and intended investigation.
- Do not list every specialist “just in case.”
- Do not recommend `nova-probe` until a root cause requires rebuilding.
- Repeated triage without new evidence triggers
  `[⚠️ HANDOFF LOOP DETECTED]`.
