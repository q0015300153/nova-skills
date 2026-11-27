# nova-adjutant — output templates

Read the section that matches the artifact being produced. The output sections `[DOC SUMMARY]`, `[NEEDS YOU]` and `[NEXT]` are defined in `SKILL.md`.

## Orientation Templates

### [PROJECT PRIMER]

Use one short paragraph covering project purpose, principal users, main
workflow and system boundary.

Then state:

- **Owner:** documented owner or `[⚠️ UNKNOWN — not provided]`.
- **Scale:** component and concern counts.
- **Run/build:** verified command or `[VERIFY]`.
- **Start here:** maximum five verified files or components.

Do not enumerate architecture or inventory in prose.

### [ARCHITECTURE MAP]

Use Mermaid when at least two components and one confirmed relationship
exist.

Rules:

- Component nodes correspond to verified files, modules, services,
  interfaces or external systems.
- Solid edges require dependency, import, configuration, call or
  data-flow evidence.
- Inferred edges are dashed and labelled `[⚠️ INFERRED]`.
- Actors, decisions and outcomes are conceptual nodes and do not require
  file paths.
- Never fabricate a component or external system.
- The caption states scope and whether the map is a subset.
- If no useful relationship is confirmed, state why no map was emitted.

### [KEY RESOURCES]

| Path or component | Kind | Responsibility | Depends on | Used by |
|---|---|---|---|---|

Every listed path must have been verified this turn.

### [DATA FLOW NARRATIVE]

Use one subsection per `<flow-slug>`.

Each step states:

- process ID;
- trigger or actor;
- input;
- processing component;
- output or resulting state;
- branch, skip, retry or concurrency condition.

Do not repeat the component inventory.

### [GLOSSARY]

| Term | Meaning in this project |
|---|---|

Maximum five project-specific terms. Mark inferred meanings.

---

## Durable Artifact Templates

### [DOCUMENT] — Technical Reference

Report:

```text
[WRITTEN TO] `<path>` — created / updated, write confirmed
[CHANGED IN IT] <changed sections; omit on first creation>
```

Use these headings in exactly this order:

1. **Purpose & Scope**
   - business purpose;
   - technical boundary;
   - audience;
   - repository state or commit reference;
   - document date;
   - related artifacts.
2. **Architecture**
   - short explanation;
   - `Component · Responsibility · Entry point · Depends on · Used by`.
3. **Interfaces & Data**
   - APIs: `Interface · Input · Output · Errors · Implementation`;
   - events/commands:
     `Name · Producer · Consumer · Payload · Trigger`;
   - data:
     `Store/schema · Purpose · Writer · Reader · Migration/owner`.
4. **Project Inventory**
   - verified files, modules and operational resources grouped by layer.
5. **Processes**
   - one subsection per `<flow-slug>`;
   - numbered steps matching `[FLOW DIAGRAM]`.
6. **Build, Test & Operations**
   - verified commands, configuration, deploy and debug procedures.
7. **Security & Dependencies**
   - `Control/dependency · Configured behavior · Scope · Evidence · Gap`.
8. **Known Gaps, Glossary & Related Documents**
   - `Gap · Impact · Evidence needed`;
   - maximum five glossary terms;
   - links to `[FLOW DIAGRAM]`, `[USER GUIDE]`, ADRs and runbooks.

Rules:

- Preserve heading order and existing flow slugs.
- Retain required headings and canonical empty/unread states.
- Use canonical tables.
- Update only changed sections.
- Preserve unrelated human-authored content.
- Do not include click-by-click user training.
- Keep volatile runtime state out unless dated.

### [FLOW DIAGRAM] — Architecture & Process Flow

Default destination:

```text
docs/flows/<scope>.md
```

Report:

```text
[WRITTEN TO] `<path>` — created / updated, write confirmed
[STRUCTURE] <N> component nodes · <N> dependency edges
[PROCESS] <N> workflows · <N> numbered steps
[CHANGED IN IT] <changed diagrams; omit on first creation>
```

Use these headings:

1. **Scope & Evidence**
2. **System Structure**
3. **Operational Flows**
4. **Unverified Relationships**
5. **Related Documents**

Under **System Structure**, include a Mermaid architecture diagram.

Under **Operational Flows**, include one Mermaid flowchart or sequence
diagram per `<flow-slug>`.

Rules:

- Code/component nodes correspond to verified repository evidence.
- User actors, manual tasks, decisions and outcomes are conceptual nodes
  and do not require file paths.
- External systems are named only when verified.
- Structural dependencies do not automatically imply execution order.
- Solid structural and process edges require corresponding evidence.
- Inferred relationships are dashed and labelled
  `[⚠️ INFERRED — unconfirmed]`.
- Process labels include the matching `<flow-slug>.F#`.
- Never fabricate paths or components to make a diagram look complete.

### [USER GUIDE] — End-User Training

Default destination:

```text
docs/user-guides/<scope>.md
```

Report:

```text
[WRITTEN TO] `<path>` — created / updated, write confirmed
[CHANGED IN IT] <changed tasks; omit on first creation>
```

Use these headings in exactly this order:

1. **Audience & Outcome**
2. **Access & Prerequisites**
3. **Screen or Command Guide**
4. **User Tasks**
5. **End-to-End Processes**
6. **Errors & Recovery**
7. **Getting Help**

Use these tables:

| Requirement | Why needed | How the user recognizes it |
|---|---|---|

| Screen, control or command | What the user sees | Purpose | When to use it |
|---|---|---|---|

| What the user sees | Meaning | Recovery | Escalate when |
|---|---|---|---|

Each task contains:

```text
## Task — <user-visible outcome>

Goal:
Before you begin:
Steps:
1.
2.
3.
Expected result:
If it does not work:
```

Rules:

- Use user-visible labels and plain language.
- Include only controls, commands and outcomes read this turn.
- Use matching `<flow-slug>.F#` IDs in End-to-End Processes.
- Do not include internal inventory or implementation detail.
- Do not expose raw stack traces, secrets or guessed root causes.
- Update a task only when user-visible behavior changed.
- Internal refactoring alone does not require rewriting unaffected tasks.
- If no user-facing workflow exists, state
  `— not applicable: no user-facing workflow in scope`.

---

## Additional Documentation Types

| Output | Required content |
|---|---|
| `[STATIC ANALYSIS]` | purpose, inputs, outputs, logic, runtime/framework version and the next maintainer constraint |
| `[ANNOTATED SOURCE]` | parameters, returns, side effects, errors, version-sensitive behavior and non-obvious rationale |
| `[DEPRECATION]` | affected API/pattern, confirmed version, replacement and migration path |
| `[VERSION RECORD]` | component, version/schema, consumers, date and upgrade trigger |
| `[CHANGE LOG]` | change, reason, downstream impact and follow-up |
| `[ADR]` | status, context, decision, alternatives, consequences, evidence and date |
| `[RUNBOOK]` | trigger, prerequisites, diagnosis, procedure, verification, rollback and escalation |
| `[OWNERSHIP RECORD]` | owner, escalation contact, scope, review date and reviewed version |

Rules:

- Provide the complete source file when replacing it.
- Otherwise edit only the relevant sections.
- Never overwrite an unread file.
- Mark unconfirmed deprecation or migration claims
  `[⚠️ VERIFY IN DOCS]`.
- Do not invent ADR alternatives that were never considered.
- Do not describe a runbook command as safe unless verified.
- Current drift belongs in the response, not an undated durable claim.

---

## [INCIDENT RECORD] — Type G

Triggered by a `[FIX VALIDATED]` handoff or a direct request to record a
resolved incident.

Write to `INCIDENTS.md` or the project's existing convention.

| Field | Detail |
|---|---|
| Original symptom | Exact observed or reported symptom |
| Reported via | User report, monitoring alert or named handoff |
| Affected layer | Data, Logic, Frontend, Operations or Cross-layer |
| Root cause | Exact underlying defect, not a restated symptom |
| Prior occurrence | Earlier record with the same root-cause pattern |
| Fix applied | Specific files, configuration or commit when known |
| Regression test | Confirmed test path and test name |
| Resources involved | Specific files, services, stores or endpoints |
| Date resolved | ISO `YYYY-MM-DD` |
| Recurrence risk | Low, Medium or High with one-line evidence |

Rules:

- Read prior records before claiming first occurrence.
- A workaround is not a confirmed root cause.
- If a field cannot be determined, state `undetermined` and why.
- Never invent a regression-test reference.
- A second instance of the same cause is `[RECURRENCE]`.
- An incident existing only in chat is not recorded.
- Report only symptom, root cause, regression test and destination in
  chat; keep the complete table in the file.
