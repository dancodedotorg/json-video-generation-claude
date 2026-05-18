---
name: video-init
description: Initializes a new video project folder within an existing grounded lesson. Checks lesson grounding, prompts objective selection, creates the video folder with audio/images/scenes, and writes an initial script.json. Invoke with /video-init <unit-slug> <lesson-slug> <video-name>.
allowed-tools: Bash(mkdir *) Write Read
metadata:
  disable-model-invocation: "true"
  argument-hint: "<unit-slug> <lesson-slug> <video-name>"
---

# video-init

Initialize a new video at `generation/units/<unit>/lessons/<lesson>/videos/<video>/`.

Parse `$ARGUMENTS` as three parts: `UNIT` (first word), `LESSON` (second word), `VIDEO` (third word).

Example: `/video-init problem-solving-with-ai lesson-2-beyond-words objective-1`

## Step 0: Resolve lesson slug

List the lesson folders for this unit:
```bash
ls generation/units/$UNIT/lessons/
```

Match LESSON against the folder names to determine LESSON_SLUG. If the unit directory doesn't exist, stop with `❌ Unit "$UNIT" not found.` If no folder matches, stop with `❌ No lesson matching "$LESSON" found.` If ambiguous, ask the user to clarify.

If you fuzzy-matched (the input wasn't the exact folder name), show:
```
⚠️  Resolved "$LESSON" → "$LESSON_SLUG"
```

Use `LESSON_SLUG` for all subsequent paths.

## Step 1: Verify lesson grounding is complete

Read `generation/units/$UNIT/lessons/$LESSON_SLUG/lesson-state.json`.

If the file does not exist, or `grounding != "complete"`, exit with:
```
❌ Lesson "$LESSON" has not been grounded yet.
   Run /lesson-ground $UNIT $LESSON first to fetch source materials.
```

## Step 2: Ask for mode

Read `.claude/skills/video-script/references/mode-guide.md`. Then ask:

```
What type of video do you want to make?

  concept   — one scene per idea; thorough tutorial narration; best for first exposure to a topic
  summary   — 3-8 scenes; thematic grouping; best for review or overview after the lesson
  re-teach  — targeted remediation for students who already completed the lesson
  co-create — you provide a custom brief (audience, angle, tone, length)

Which mode? (concept / summary / re-teach / co-create)
Not sure? Ask me to describe what any mode looks like.
```

Wait for the answer. Store as MODE.

If **co-create**: ask for the brief, following the thin-brief rules in `mode-guide.md` (one follow-up question for the most important gap; never ask multiple). Store as BRIEF.

For all other modes: BRIEF is null unless the user volunteers customization notes, in which case store those as BRIEF.

## Step 3: Load objectives

Read `generation/units/$UNIT/lessons/$LESSON/source/objectives.md` to get the available objectives.

If it doesn't exist, fall back to reading objectives from `generation/units/$UNIT/unit.json` (find the lesson by slug match on title).

Show the user a numbered list of available objectives, then a lettered list of vocabulary terms, and ask:

```
Which objectives should this video TARGET? (the video primarily teaches these — enter numbers, e.g. 1,3)

  1. Analyze patterns in AI-generated responses...
  2. Experiment with different prompts...
  ...

Which objectives should this video reference as SUPPORTING context? (prerequisites the video relies on but does not primarily teach — enter numbers or press Enter to skip)

Which vocabulary terms should this video DEFINE (target)? (enter letters, or press Enter to auto-assign from objectives)

  a. abstraction
  b. artificial intelligence (AI)
  ...

Which vocabulary terms should this video reference as SUPPORTING (used in context but not formally defined here)? (enter letters or press Enter to skip)
```

Wait for the responses. Store as TARGET_OBJECTIVES, SUPPORTING_OBJECTIVES, TARGET_VOCABULARY, SUPPORTING_VOCABULARY. If the user skips target vocabulary, assign terms whose words appear in the selected target objective texts. Supporting arrays default to empty if skipped.

**Ad-hoc note:** unlike `/lesson-plan`, `/video-init` does **not** enforce plan-level uniqueness — you can target an objective that another video in the same lesson already targets. The constraint only applies to plans authored via `/lesson-plan` (and validated by `init_videos.py`). Use ad-hoc creation when you specifically want a video outside the planned structure.

## Step 4: Create folder structure

```bash
mkdir -p generation/units/$UNIT/lessons/$LESSON/videos/$VIDEO/audio
mkdir -p generation/units/$UNIT/lessons/$LESSON/videos/$VIDEO/images
mkdir -p generation/units/$UNIT/lessons/$LESSON/videos/$VIDEO/scenes
```

## Step 5: Write script.json

Write `generation/units/$UNIT/lessons/$LESSON/videos/$VIDEO/script.json`:

```json
{
  "video_name": "$VIDEO",
  "unit": "$UNIT",
  "lesson": "$LESSON",
  "target_objectives": [<TARGET_OBJECTIVES array>],
  "supporting_objectives": [<SUPPORTING_OBJECTIVES array or []>],
  "target_vocabulary": [<TARGET_VOCABULARY array>],
  "supporting_vocabulary": [<SUPPORTING_VOCABULARY array or []>],
  "mode": "<MODE>",
  "brief": <BRIEF string or null>,
  "width": 1600,
  "height": 900,
  "pipeline": {
    "grounding": "complete",
    "script": "pending",
    "audio_tags": "pending",
    "audio": "pending",
    "html": "pending",
    "assembled": false
  },
  "grounding": {},
  "tts": {},
  "scenes": []
}
```

Always include `supporting_objectives` and `supporting_vocabulary` — write `[]` if the user provided none.

`pipeline.grounding` is pre-set to `"complete"` because grounding happens at the lesson level.

## Step 6: Confirm

Print:
```
✅ Video "$VIDEO" initialized in lesson "$LESSON".

  Location: generation/units/$UNIT/lessons/$LESSON/videos/$VIDEO/
  Mode: <MODE>
  Target objectives: <N> selected (+ <M> supporting if any)
  Source materials: shared from generation/units/$UNIT/lessons/$LESSON/source/

Next: /video-script $UNIT $LESSON $VIDEO
```
