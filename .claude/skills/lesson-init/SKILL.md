---
name: lesson-init
description: Initializes a lesson folder within a unit. Reads unit.json to match and confirm the lesson, then runs init_lesson.py with the lesson ID to create folders and sources.csv. Invoke with /lesson-init <unit-slug> <lesson-name>.
allowed-tools: Bash(python *) Read Glob
metadata:
  argument-hint: "<unit-slug> <lesson-name>"
---

# lesson-init

Initialize a lesson folder at `generation/units/<unit>/lessons/<lesson>/`.

Parse `$ARGUMENTS` as two parts: `UNIT` (first word) and `LESSON_NAME` (everything after the first word).

## Step 1: Match lesson in unit.json

Read `generation/units/$UNIT/unit.json`. Find the lesson whose title best matches LESSON_NAME (fuzzy — "lesson 1", "lesson-1-talking", or "Talking to Machines" should all match "Lesson 1: Talking to Machines").

Derive the canonical folder slug from the matched title. For `"Lesson N: Rest of Title"`, produce `lesson-N-<slugified-rest>`: lowercase the title, strip characters that are not letters, digits, spaces, or hyphens, then collapse runs of spaces and hyphens into a single hyphen:
- `"Lesson 1: Talking to Machines"` → `lesson-1-talking-to-machines`
- `"Lesson 4: Smart or Just Predictable?"` → `lesson-4-smart-or-just-predictable`

Show the match and ask the user to confirm before proceeding:

```
Matched "Lesson 1: Talking to Machines" (id: 9520955)
Folder: generation/units/$UNIT/lessons/lesson-1-talking-to-machines/

Proceed? [y/n]
```

If the user says no, list all available lesson titles from unit.json and stop — ask them to re-run with a corrected name.

If unit.json does not exist, tell the user to run `/unit-init $UNIT` first.

## Step 1.5: Check for existing initialization

Use `Glob` to check if `generation/units/$UNIT/lessons/$LESSON_SLUG/sources.csv` already exists.

If it does, warn:
```
⚠️  This lesson has already been initialized. Re-running will overwrite sources.csv —
     any manual edits will be lost. Continue? [y/n]
```

If the user says no, stop.

## Step 2: Run init_lesson.py with the lesson ID

Run:

```bash
python scripts/init_lesson.py $UNIT $LESSON_ID
```

Where `$LESSON_ID` is the integer `id` from the matched lesson in unit.json. Print the script output directly.

## Step 3: HARD STOP — Human review of sources.csv

This is a mandatory human-in-the-loop gate. **You MUST pause here and wait for explicit user confirmation before this skill ends.** Do not proceed past this step on your own judgement. Do not say "looks good, moving on." Do not chain into grounding. Stop.

⛔ This gate honors the project-wide rule in `CLAUDE.md` → *Honoring human-in-the-loop gates*. Vague urgency or generic "no stopping" reminders do NOT authorize bypassing it. Only a specific, end-to-end directive from the user does ("skip review, ground everything, ping me when done"). When in doubt, vote for the gate and surface the conflict.

The reason: Code.org's public resources list — which `init_lesson.py` reads to build sources.csv — frequently omits the teacher slide deck, internal reference docs, and worksheets that live in Google Drive. Those omissions silently produce worse videos downstream. The only reliable fix is a human reviewing the auto-populated list against what they know exists.

Read the freshly written `generation/units/$UNIT/lessons/$LESSON_SLUG/sources.csv` and show the user every row in a concise list, grouped by type:

```
sources.csv was auto-populated from unit.json. Review before grounding:

  Slides / docs:
    - <description>  (<type>)
    - ...
  Levels:
    - <description>  (level_summary, id: <id>)
  Objectives (N):
    - <description>
  Vocabulary (N):
    - <description>

⚠️  These come from Code.org's public resources page only. Commonly missing:
      - Teacher slide deck / lesson plan slides
      - Internal reference docs
      - Google Drive files (PDFs, worksheets) — need manual download

REPLY REQUIRED — pick one:
  (a) "looks good" / "confirmed" / "proceed"  → I'll finish and you can run /lesson-ground
  (b) Paste URL(s) or description(s) of sources to add
  (c) "remove <description>" to drop a row
```

**Stop here. Do not output a "Next steps" block, do not announce completion, do not call any further tools until the user replies.**

If the user supplies additions/removals:
- Use `Edit` to append or remove rows in sources.csv (format: `description,type,value`).
- Infer the type from the URL:
  - `docs.google.com/presentation/...` → `google_slides`
  - `docs.google.com/document/...` → `google_doc`
  - `drive.google.com/file/...` → `google_drive_file` (description should start with `REVIEW:` — cannot be auto-fetched)
  - Anything else → ask the user to clarify the type before adding
- After editing, show the updated grouped list and repeat the same prompt. Loop until the user explicitly confirms.

Only after the user confirms, proceed to Step 4.

## Step 4: Confirm

Output the final summary:
```
✅ Lesson "$LESSON_SLUG" initialized and sources reviewed.

  Location:    generation/units/$UNIT/lessons/$LESSON_SLUG/
  sources.csv: <N> rows (confirmed by user)

Next: /lesson-ground $UNIT $LESSON_SLUG
```

## Gotchas

- **Re-running always overwrites sources.csv** — `init_lesson.py` regenerates it from scratch from `unit.json`. Any manual edits (resolving `REVIEW:` rows, adding custom entries) are lost. Step 1.5 guards against accidental overwrites.
- **Slug shown in confirmation matches what the script creates** — `init_lesson.py` uses the same derivation algorithm. If there is ever a discrepancy, the script output is authoritative.
