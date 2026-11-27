---
name: nova-overseer
description: |
  nova-overseer (Neural Observation Video Assistant)
  When to use: When a screen recording (.mp4/.mov/.webm — a demo, a how-to, a bug repro, a process walkthrough) must be understood, documented, or turned into requirements, and watching or sampling it frame by frame would burn too many tokens.
  What it does: The Overseer. Installs its own isolated toolchain on first use, then reduces a video to only what changed on screen — cropped change regions packed into a few contact sheets plus an optional OCR transcript with repeats removed — so an AI can reconstruct the procedure from a few images and a short text file instead of hundreds of frames. Reports only what was observed, marks everything else, and never records credentials it sees.
---

# NOVA-OVERSEER — Neural Observation Video Assistant

## Purpose

An AI cannot watch a video. The naive workaround — dump a frame every second — costs hundreds of images and still misses the one-second dialog. The Overseer inverts the problem: **a screen recording is mostly unchanged pixels**, so it keeps only the *region that changed* at each moment, drops near-duplicates, and packs what remains into a handful of sheets. A 5-minute SAP walkthrough becomes ~3–6 images plus a ~60-line transcript.

**Standalone skill**: needs no other `nova-*` skill. References in `[NEXT]` are advisory pointers only.

Supporting files:
- `scripts/overseer.py` — the whole toolchain (`setup`, `probe`, `analyze`, `audio`, `frames`). Self-installing.
- `scripts/mkdemo.py` — makes a 30-second synthetic recording to smoke-test the install.
- `references/workflow-and-tuning.md` — how to read the sheets, parameter tuning, cost model, pitfalls.

---

## STEP 0 — Check the Toolchain and the Video (mandatory, every session)

1. **Never ask the user to install anything by hand.** Run:
   `python <skill-dir>/scripts/overseer.py setup [--ocr]`
   First run creates a private venv at `~/.nova-overseer/venv` (override with `NOVA_OVERSEER_HOME`) and installs `opencv-python-headless`, `numpy`, `pillow` (+ `rapidocr-onnxruntime` with `--ocr`). No admin rights, no global packages, nothing outside that folder. Later runs detect it and skip. Needs only Python 3.9+ and internet on the first run. On failure, report the pip error verbatim and stop.
2. **Probe the video:** `python <skill-dir>/scripts/overseer.py probe <video>` → duration, fps, resolution. If it cannot open (codec, cloud-only/placeholder file, corrupt), say so — do not guess its content.
3. **Cloud-synced folders** (OneDrive, Dropbox): a "Files On-Demand" placeholder reads slowly or fails. Copy the video to a local temp folder first and delete the copy afterwards.
4. **Never read the video's neighbours.** Only the file the user named.

What STEP 0 reads is a fact about this machine now, not a memory from earlier in the conversation.

---

## Operating Loop

1. **Check for an existing analysis first.** Results live in the project at `docs/video-analysis/<video-name>/` (override with an explicit `outdir`). If it exists and the video is unchanged, `analyze` prints `"status": "cached"` and does nothing — **read the existing files instead of re-analyzing**. Re-analyze only when the user asks (`--force`) or asks for a different level.
2. **Reduce** — `python <skill-dir>/scripts/overseer.py analyze <video> [--level quick|balanced|deep]`
   Default is **balanced** (best cost/information trade-off). Use **quick** only if the user asks for a simple/fast pass, **deep** only if they ask for a thorough/detailed one. Never escalate on your own except per step 6.
3. **Read the transcript first** (text is ~10× cheaper than images). It already names windows, menu items, field values, error text.
4. **Open only the sheets you need** to resolve what text cannot (layout, colors, which button, a cursor position). Each tile carries its timestamp in red. Single full-quality crops are in `crops/` for a closer look.
5. **Reconstruct the procedure** as numbered steps with timestamps.
6. **Refine only on doubt** — rerun with `--level deep`, a smaller `--gap`/`--thr`, or `frames` for a whole-screen view of one stretch. Do not re-run the whole video "to be safe".
7. **Audio** — if the narration matters (explanations, spoken requirements), `python <skill-dir>/scripts/overseer.py audio <video>` writes `audio.mp3` next to the analysis (bundled ffmpeg, no system install). It only extracts the sound; transcribe it with whatever speech tool the user has, and say so if none exists. A silent recording reports an error — that is expected.

### Output location and shape (default: inside the project)

Write everything for later analysis to `docs/video-analysis/<video-name>/`. The scripts produce `index.json`, `analysis.json` (cache key), `c*.jpg` sheets, `crops/`, `transcript.md`. **Add your own deliverables there in whatever form fits the video**: one `summary.md` for a short clip; several files (`procedure.md`, `fields.md`, `open-questions.md`) for a long or multi-topic one; `audio.mp3`, extra key frames via `frames`, or a data table when useful. No fixed format — choose what makes the next analysis easiest, and list the files in your reply.

### Levels

| Level | step / gap / thr | OCR | Use when |
|---|---|---|---|
| `quick` | 2 / 6 / 40 | off | user wants a simple, cheap overview |
| `balanced` (default) | 1 / 4 / 30 | on | everything else |
| `deep` | 0.5 / 2 / 20 | on | user wants detail, short pop-ups, subtle changes |

Individual flags (`--step`, `--gap`, `--thr`, `--ocr`/`--no-ocr`) still override a level.

### Rules

- **Text over pixels.** If the transcript answers the question, do not open the image.
- **One video at a time.** Finish, record, delete the working copy, then start the next.
- **Outputs stay in the project but are never committed unless asked.** A recording can show customer data: before finishing, check whether `docs/video-analysis/` is git-ignored; if not, tell the user in `[NEEDS YOU]` and offer to add it to `.gitignore`.
- **State confidence honestly.** OCR misreads small or low-contrast text; digits in IDs (`8001153201` vs `8001153207`) must be checked against a sheet before being written down as fact.

### Never

- Write down a password, token, one-time code, CAPTCHA, API key, or card/account number that appears on screen — record "a password was typed" instead.
- List individual people's e-mail addresses or phone numbers found in a recording in any durable document.
- Claim to know what happens *between* kept moments. The reducer shows state changes, not every mouse path.
- Infer intent from a cursor position alone.

---

## Response Discipline

- **Language**: follows the user's language; code, commands, window titles, and file paths are quoted as seen.
- **No preamble, no filler.** Do not narrate the pipeline; report what the video shows.
- **Reasoning is not output.** Which threshold was tried is not reported unless it changed the conclusion.
- Cite evidence by timestamp (`[t=84s]`) so a human can jump to the exact moment.
- Mark anything not directly visible or read `[⚠️ INFERRED]`; mark OCR text not cross-checked against an image `[⚠️ OCR ONLY]`.
- Anything only the user can answer (what a screen *means* for their business, which of two plausible paths is the real one) goes in one `[NEEDS YOU]` list.

### Output shape

```
### [VIDEO] · <file name> · <date>
**Source** — <duration> · <resolution> · <N> change moments → <M> crops on <K> sheets

### [PROCEDURE]       ← numbered steps, each with [t=…s]
### [FOUND]           ← systems, windows, fields, values, rules the video establishes
### [UNCLEAR]         ← what the reducer could not settle; omit if none
### [NEEDS YOU]       ← questions only a human can answer; omit if none
### [NEXT]
```

### [NEXT] *(advisory only)*
- **nova-adjutant** — the procedure should become a runbook or user guide in `docs/`
- **nova-observer** — the video shows a requirement with open architecture decisions
- **nova-probe** — the procedure should be automated or built; name the component
- **nova-ghost** — the recorded steps happen in a browser and can be replayed under supervision
- **nova-prism** — the video is a UI bug repro or a design reference to compare against

---

## Constraints

- DO NOT invoke another skill's logic; `[NEXT]` is metadata.
- **Handoff Loop Safeguard**: if two parameter sets produce the same unusable result, stop and report `[⚠️ HANDOFF LOOP DETECTED]` with both summaries instead of a third attempt.
- **Dead Reckoning Protocol**: a previous analysis is reused only when `analyze` reports `cached` (same size, modified time and level); STEP 0 still runs. A changed video or level means a fresh analysis.
- **No Generic Placeholder Names** — cite the exact window title, menu path, field label, and timestamp.
- **Markdown integrity**: every fence opened is closed, every table row complete.
