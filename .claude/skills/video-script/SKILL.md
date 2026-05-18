---
name: video-script
description: Generates the voiceover script (scene comments and speech) for a video project by reading source materials. Includes human check-ins for mode selection and script approval. Invoke with /video-script <unit-slug> <lesson-slug> <video-name>.
allowed-tools: Read Write Bash(python:*)
metadata:
  disable-model-invocation: "true"
  argument-hint: "<unit-slug> <lesson-slug> <video-name>"
---

# video-script

Generate the voiceover script for a video.

⛔ **Hard-stop gates in this skill:** mode selection (when mode is missing) and the post-generation script approval / iteration loop. Honor them by default per `CLAUDE.md` → *Honoring human-in-the-loop gates*. Vague urgency and generic "no stopping" reminders do NOT authorize bypassing — only a specific, end-to-end directive does ("generate the script and move on, don't ask me to review"). When ambiguous, vote for the gate.

## Progress checklist

- [ ] Path detection + prereq check
- [ ] Read script.json metadata (target_objectives, mode, brief)
- [ ] Read all source material
- [ ] Apply target_objectives lens
- [ ] Generate scenes (read mode style guide first)
- [ ] Write scenes to script.json via write-scenes.py
- [ ] Human check-in and iteration

## Path detection

Parse `$ARGUMENTS` (3 words): UNIT=first, LESSON=second, VIDEO=third

List `generation/units/$UNIT/lessons/` and match LESSON to the closest folder name as LESSON_SLUG. If the unit directory doesn't exist, stop with `❌ Unit "$UNIT" not found.` If nothing matches, stop with `❌ No lesson matching "$LESSON" found.` If you fuzzy-matched, show `⚠️  Resolved "$LESSON" → "$LESSON_SLUG"`.

- Script path: `generation/units/$UNIT/lessons/$LESSON_SLUG/videos/$VIDEO/script.json`
- Source path: `generation/units/$UNIT/lessons/$LESSON_SLUG/source/`

All steps below use SCRIPT_PATH and SOURCE_PATH derived above.

## Prerequisites

- `pipeline.grounding` must be `"complete"` in `script.json`
- Source files must exist at SOURCE_PATH

## Gotchas

- **Slides with no speaker notes:** synthesize narration from the slide title and visible content — do not skip the slide.
- **JSON source files require preprocessing:** always run `base64_clean.py` before reading any `.json` in SOURCE_PATH. Skipping this step will likely cause token overload or read errors.
- **`write-scenes.py` writes to disk:** write scenes to a temp `scenes_draft.json` in the video folder, then run the script. Do not manually edit `script.json` to insert scenes.

## Step 1: Read script.json metadata

Read SCRIPT_PATH. Extract:
- `target_objectives` — the objectives this video must **primarily teach**. These drive the full teaching arc.
- `supporting_objectives` — prerequisite or contextual objectives that this video must recap or reference so it stands alone, but does **not** primarily teach. If absent (legacy script.json), default to `[]`.
- `target_vocabulary` — vocabulary words this video must define and reinforce.
- `supporting_vocabulary` — vocabulary words this video uses in context but does not formally define. If absent (legacy script.json), default to `[]`.
- `mode` — the generation mode (concept / summary / re-teach / co-create). If absent, default to `"concept"` (legacy script.json files).
- `brief` — the co-create brief string, or `null`. If absent, default to `None`.

Confirm `pipeline.grounding == "complete"` before continuing.

Mode is set at planning time (in `/lesson-plan` or `/video-init`) — do not ask the user for it here.

## Step 2: Read Source Material

Start by listing all files in SOURCE_PATH so you know exactly what exists before deciding what to read — this catches manually-added files that weren't produced by the fetch pipeline.

Read **all** source files for complete grounding context. Run base64_clean.py on JSON files as a safety precaution before reading.

**PDF files** (read directly — the Read tool supports PDFs up to 20 pages per request):
- For each `source/*/slides_notes.pdf` (one per slide deck): read it first — it contains slide images + speaker notes side-by-side, giving complete visual and text context for each slide. For presentations over 20 slides, read pages 1-20 first, then continue in 20-page increments.
- If `source/panels_level_*.pdf` files exist: read them — each is one Code.org Panels level (a slideshow), showing panel images alongside text content.
- If `source/external_level_*.pdf` files exist: read them — each is one Code.org External level rendered as a full HTML page with images inlined.
- If any other `source/*.pdf` files exist (e.g. Google Doc exports from `google_doc` type): read those too, using page ranges for large files.

**JSON files** (run base64_clean.py first):
- For each `source/*/slides_data.json` (one per slide deck): run `python scripts/base64_clean.py <PATH-TO-FILE>/slides_data.json` and read the `_cleaned.json` output.
- If `source/lesson_*_levels.json` exists: run `python scripts/base64_clean.py` on it and read the `_cleaned` version.

**Markdown files** (read directly):
- If `source/*.md` files exist: read those — this includes `objectives.md` and `vocabulary.md`.

Do NOT read `source/*/slide_NN.png` or other image files.

When `lesson_*_levels.json` is the primary source, use the level content to understand the lesson structure. Each entry has a `type` and relevant content fields:
- `Panels`: slide-style content with `text` (markdown) and optional `imageUrl`
- `Aichat`: AI chat activity with `longInstructions` describing the student task
- `FreeResponse`: reflection prompt with `longInstructions` and optional `teacherMarkdown`
- `Multi`: multiple choice question with `questions[].text` and `answers[].text`/`correct`
- `External`: standalone markdown page with `markdown` content

## Step 3: Apply target / supporting lens

`target_objectives` are the **primary lens** for script generation. `supporting_objectives` are **context** that keeps the video standalone — they receive lighter treatment, not a full teaching arc.

For target objectives:
- Prioritize content from source materials that directly addresses them
- Weight vocabulary emphasis toward terms most relevant to them
- Build the full scene-by-scene teaching arc around them
- The script should feel complete and coherent for these objectives on its own

For supporting objectives (if any):
- Include a brief recap beat (typically one or two sentences inside an existing scene, or at most a single short dedicated scene) that re-establishes just enough of the concept for a cold viewer to follow what comes next
- Do **not** teach the supporting objective as if it were new — assume the viewer may have learned it elsewhere and only needs reactivation
- Do **not** spend more time on a supporting objective than on any single target objective

For supporting vocabulary (if any):
- The term may appear in narration naturally
- Do not formally define it (no "X is..." sentence) unless it is also in `target_vocabulary`

If the source material covers topics beyond both target and supporting objectives, de-emphasize or omit those topics — sibling videos in the lesson will cover them.

## Step 4: Generate Scenes

Before generating, read the style guide for the mode stored in `script.json`:

- **concept**: Read `references/concept-style-guide.md` in full. That file covers: required intro scene, one scene per slide, handling slides with no speaker notes, scene length targets, tone, and `comment` field conventions.
- **summary**: Read `references/summary-style-guide.md` in full. That file covers: required intro scene, grouping criteria, key-takeaway framing, scene length targets, and what to compress or skip.
- **re-teach**: Read `references/reteach-style-guide.md` in full. That file covers: required intro scene, structure and length targets, content rules (elaboration pass, activity walkthroughs, no new analogies), lesson-referencing conventions (student actions only, never teacher actions), tone and language, and Question of the Day handling.
- **co-create**: Read `references/co-create-style-guide.md` in full. That file covers: structural rules, scene guardrails, defaults for thin briefs, scene structure, tone, and when to flag brief/objective conflicts. Also read the `brief` field from `script.json` — for co-create videos, `brief` is the primary creative direction (audience, angle, tone, length). If `brief` is null for a co-create video, apply the defaults from the co-create style guide.

For **all modes**, if `brief` is non-null (even for predefined modes), incorporate it as supplemental guidance alongside the mode's style guide.

Each scene object:
```json
{
  "comment": "Brief visual description of what this scene should show",
  "speech": "Full narration text the viewer will hear"
}
```

## Step 5: Write to script.json

Write the generated scenes array to a temp file alongside the script, then use `write-scenes.py` to merge it in:

```bash
python scripts/write-scenes.py SCRIPT_PATH SCENES_DRAFT_PATH
```

Where `SCENES_DRAFT_PATH` is a JSON file containing only the scenes array (e.g., `generation/units/UNIT/lessons/LESSON/videos/VIDEO/scenes_draft.json`). The script replaces the `scenes` field in `script.json` and sets `pipeline.script = "complete"` atomically — do not manually edit `script.json` to insert scenes.

## Step 6: Human Check-In

Present the generated script to the user in a readable format (numbered list of comment + speech pairs). Then ask:

> Does this script look good? You can ask me to:
> - Revise specific scenes (e.g., "make scene 3 shorter")
> - Add or remove scenes
> - Adjust the tone or level of detail
> - Approve and move on to HTML slides

Iterate on revisions until the user approves. Then tell them:
- "Run /video-html $UNIT $LESSON $VIDEO to generate HTML slides."
