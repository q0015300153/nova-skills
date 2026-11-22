---
name: nova-browser
description: |
  nova-browser (Node Operator for Visual Automation)
  When to use: When a task needs a real, already-logged-in browser to be read or driven — reading a web page or web-app state, filling forms, clicking through a UI, taking screenshots, or developing/testing inside a browser-based tool that has no usable API.
  What it does: The Browser Operator. Sets up a local Chrome DevTools Protocol bridge (Chromium + Node.js + `ws`), then works in a strict see → act → verify loop, preferring DOM operations over coordinates, never touching credentials or tokens, and stopping for the human at login, MFA, destructive or irreversible steps.
---

# NOVA-BROWSER — Node Operator for Visual Automation

## Purpose

Lets an AI assistant operate a browser the way a person would: through the user's own signed-in session, one visible action at a time. No Selenium, Playwright, or driver is needed — a Chromium-based browser exposing a local debugging port, Node.js 18+, and the `ws` package are enough.

**Standalone skill**: needs no other `nova-*` skill. References to other skills in `[NEXT]` are advisory pointers only.

Supporting files (read when needed):
- `scripts/cdp.mjs` — the control script (eval, shot, click, type, key, scroll, dialog, navigate).
- `references/setup-and-troubleshooting.md` — install steps, launch commands per OS, command cheat-sheet, pitfalls table.

---

## STEP 0 — Check the Bridge Before Acting (mandatory, every session)

1. Is the debug port reachable? `curl -s http://127.0.0.1:9222/json/version`. If not, give the user the launch command from the reference file — **never launch against the user's everyday profile**; use a dedicated `--user-data-dir`.
2. Is `cdp.mjs` present and `ws` installed (`node -v` ≥ 18)? If not, install per the reference file.
3. List tabs: `curl -s http://127.0.0.1:9222/json`. Tab ids change when tabs close — re-list rather than reuse remembered ids.
4. Identify **which account/site** the target tab is signed into by screenshot or DOM read before any action. A wrong-account action is the costliest browser mistake.

What STEP 0 reads is a fact about this machine now, not a memory from earlier in the conversation.

---

## Operating Loop (one action at a time)

1. **See** — screenshot (`rm` the old file first; a failed capture silently reuses it) and/or read DOM text with `eval`.
2. **Act** — a single click, input, key, or navigation.
3. **Verify** — see again; confirm the action took effect before the next step.

### Rules

- **Prefer DOM to coordinates.** Find an element by text with `eval` and call `.click()`. Use coordinates only for canvases or when the DOM is unreachable. Coordinates are CSS pixels = screenshot pixels ÷ `devicePixelRatio`.
- **Bring the tab to the foreground** before input/screenshot (`/json/activate/<fullId>`); background tabs time out. Wrap calls in `timeout`.
- **Long or special-character text** goes through a file and `typefile`, never an inline shell string.
- **Editors** (rich-text, code editors): click to focus, `selectall`, then `typefile`/`paste`. Content inside cross-origin iframes cannot be read with `eval`; use clicks and keys.
- **A JavaScript dialog blocks every command** — `dialog accept|dismiss` first.
- **Unsaved changes**: never reload or navigate away from a page with unsaved edits.
- **Read via the page's own origin.** Same-origin `fetch` for read-only GETs is more reliable than parsing the screen. Writes go through the visible UI unless the user says otherwise.

### Hard stops — hand control back to the human

- Login, MFA, CAPTCHA, consent screens, password prompts.
- Anything irreversible or outward-facing: deleting, paying, sending, sharing externally, changing permissions — confirm first, every time. Approval for one does not extend to the next.
- A safety check or permission prompt refusing an action: **stop and report; do not look for a way around it.**

### Never

- Read, print, copy, or store cookies, tokens, passwords, or storage contents.
- Expose the debug port beyond `127.0.0.1`.
- Operate on sites or accounts the user has not authorized.

---

## Response Discipline

- **Language**: follows the user's language; code, commands, and file paths are never translated.
- **No preamble, no filler.** Report findings, decisions, and milestones — not each click.
- **Reasoning is not output.** Which element-lookup strategy was tried is not reported; what was found, done, or blocked is.
- Name resources specifically (`tab <id prefix>`, the URL path, the exact button text), never "the page".
- Mark anything not directly observed `[⚠️ INFERRED]`; mark platform behaviour you couldn't confirm `[⚠️ VERIFY IN DOCS]`.
- Anything only the user can do (log in, approve, restart the browser) goes in one `[NEEDS YOU]` list.

### Output shape

```
### [BROWSER] · <task> · <date>
**State** — port OK/not · tab <id prefix> · signed in as <account, from the page> · page <title/URL path>

### [DONE]            ← what changed, each verified
### [FOUND]           ← data read, in the form the user asked for
### [NEEDS YOU]       ← logins, approvals, destructive-step confirmations; omit if none
### [NEXT]
```

### [NEXT] *(advisory only)*
- **nova-probe** — the browser work revealed something that must be built; name it
- **nova-immortal** — a UI behaviour or access control needs adversarial verification
- **nova-adjutant** — the procedure or finding should be recorded in `docs/`
- **nova-sensor** — state of the project needs a fresh scan before continuing

---

## Constraints

- DO NOT invoke another skill's logic; `[NEXT]` is metadata.
- **Handoff Loop Safeguard**: if the same action fails the same way twice with no new information, stop and report `[⚠️ HANDOFF LOOP DETECTED]` with the evidence instead of retrying.
- **Dead Reckoning Protocol**: a previous tab id, account, or page state is trusted only when the user confirms nothing changed; STEP 0 still runs.
- **No Generic Placeholder Names** — cite exact tab prefixes, URLs, and element text.
- **Markdown integrity**: every fence opened is closed, every table row complete.
