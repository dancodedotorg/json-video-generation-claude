# JSON Video Generator

A Claude Code-powered pipeline for authoring structured JSON video scripts from curriculum source materials. Each output is a single `.json` file describing a sequence of scenes — each scene is a self-contained HTML document, a narration caption, an optional audio track, and timing metadata.


https://github.com/user-attachments/assets/14b3238d-160c-4c91-8492-e473e416ef2e


The files that made this video, along with a few video examples from the curriculum, is in this repo for you to explore. You can find them in the generation/units folder. They can help contextualize this process since they are real examples of videos generated this way.

---

## How It Works

A **JSON video** is a `.json` file containing:
- Scene-by-scene HTML slides, narration captions, and durations
- A TTS audio track embedded as base64 data URIs (after assembly)

Because every scene is plain HTML, Claude can generate or edit scenes without video editing tools. The pipeline reads curriculum source materials (slides, docs, objectives), generates narration and slides, synthesizes audio via TTS, and assembles a final player-ready file.

---

## Requirements

- [Claude Code](https://claude.ai/code) CLI or desktop app
- Python 3.12 or 3.13
- [ffmpeg](https://ffmpeg.org/download.html) installed and on your `PATH` (used by `pydub` to encode Gemini TTS audio as MP3)
- Python packages — install from `generation/tools/requirements.txt`:

```bash
pip install -r generation/tools/requirements.txt
```

> **Python 3.13:** `audioop` was removed from the stdlib in 3.13. Uncomment `audioop-lts` in `requirements.txt` before installing.
> **Python 3.12:** `audioop` is still built-in; `audioop-lts` is not needed.

- API keys in `generation/tools/.env`:

```
ELEVENLABS_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
GOOGLE_SERVICE_ACCOUNT_JSON=base64_encoded_service_account_json
```

`GOOGLE_API_KEY` is used for Gemini TTS and image generation. `GOOGLE_SERVICE_ACCOUNT_JSON` is only needed if fetching from Google Slides or Google Docs.

---

## Generation Pipeline

Videos are organized in a unit > lesson > video hierarchy. Setup at the unit and lesson level happens once; video creation repeats for each video.

```
── One-time setup ───────────────────────────────────────────────────
/unit-init    <unit-slug>             → create unit.json from Code.org API
/lesson-init  <unit> <lesson>         → create lesson folder + sources.csv
/lesson-ground <unit> <lesson>        → fetch source materials (slides, docs, levels)

── Per-lesson planning ──────────────────────────────────────────────
/lesson-plan  <unit> <lesson>         → analyze objectives, recommend video split,
                                        initialize all video folders  <- human check-in

── Per-video creation ───────────────────────────────────────────────
/video-create <unit> <lesson> <video> → run full pipeline for one video:
  /video-script     → generate scene narration           <- human check-in
  /video-html       → generate HTML slides               <- human check-in
  /video-audio-tags → add TTS expression tags            <- human check-in
  /video-audio      → synthesize MP3 audio               <- human check-in
  /video-assemble   → embed assets, write final JSON
```

Source materials in `lesson/source/` are fetched once and shared across all videos in that lesson. Each video's `script.json` stores `unit`, `lesson`, and `target_objectives` so all skills resolve paths deterministically.

### Step-by-Step

**1. Initialize the unit (one-time)**
```
/unit-init my-unit
```
Fetches lesson IDs from Code.org and creates `generation/units/my-unit/unit.json`.

**2. Initialize the lesson (one-time per lesson)**
```
/lesson-init my-unit my-lesson
```
Creates the lesson folder and a `sources.csv` template listing source materials to fetch.

**3. Fetch source materials (one-time, refreshable)**
```
/lesson-ground my-unit my-lesson
```
Downloads slide thumbnails, exports Docs as PDFs, fetches Code.org level content — all saved to `generation/units/my-unit/lessons/my-lesson/source/`. Can be re-run to refresh.

**4. Plan videos for the lesson**
```
/lesson-plan my-unit my-lesson
```
Claude reads the lesson objectives and source materials, proposes a video split (one video per objective or group of objectives), and initializes all video folders after you approve. This is the preferred entry point — do not run `/video-init` after this.

**5. Create a video**
```
/video-create my-unit my-lesson my-video
```
Runs all production stages in sequence, pausing at each human check-in point:

- **Script** — Claude generates scene narration and iterates until you approve
- **HTML slides** — Claude evaluates scenes, picks visual approaches, and generates slides after you approve the plan
- **Audio tags** — Claude adds TTS expression tags for ElevenLabs and Gemini. You review and approve
- **Audio** — Claude asks which TTS provider and voice to use, then generates MP3 audio
- **Assemble** — Embeds MP3 audio and any local images as base64 data URIs into the final JSON

### Adding a Single Video Outside a Plan

```
/video-init my-unit my-lesson my-video
```

Then run `/video-create my-unit my-lesson my-video` to produce it.

### Resuming a Partially-Complete Video

Every skill checks `script.json`'s `pipeline` status and skips completed stages. Run any skill at any time — it picks up where you left off. `/video-create` also resumes automatically.

---

## Project Structure

```
json-video-player/
│
├── generation/
│   ├── tools/
│   │   ├── paths.py             ← Shared lib: canonical path helpers
│   │   ├── text_utils.py        ← Shared lib: ASCII text normalization
│   │   ├── script_tool.py       ← CLI utility: read/write/view script.json fields
│   │   ├── script_review.py     ← Standalone review utility
│   │   ├── .env                 ← API credentials (not committed)
│   │   └── generated-images/    ← Output directory for Gemini image gen
│   │
│   └── units/
│       └── <unit-slug>/
│           ├── unit.json                  ← Lesson list with objectives + vocabulary
│           └── lessons/
│               └── <lesson-slug>/
│                   ├── sources.csv        ← Source materials manifest
│                   ├── lesson-state.json  ← Grounding status
│                   ├── source/            ← Fetched artifacts, shared by all videos
│                   └── videos/
│                       └── <video-name>/
│                           ├── script.json                   ← Pipeline state + content
│                           ├── script_assembled_base64.json  ← Player-ready output
│                           ├── audio/                        ← Generated MP3 files
│                           ├── images/                       ← AI-generated scene images
│                           └── scenes/                       ← Individual HTML scene files
│
└── .claude/skills/              ← Claude Code skill pipeline
    ├── unit-init/
    ├── lesson-init/
    ├── lesson-ground/
    ├── lesson-plan/
    ├── video-init/
    ├── video-script/
    ├── video-audio-tags/
    ├── video-audio/
    ├── video-html/              ← Includes design-guide.md, generation-guide.md
    ├── video-assemble/
    └── video-create/
```

---

## JSON Video Format

`script.json` is the central file for each video. It tracks pipeline state and stores all generated content.

```json
{
  "video_name": "my-video",
  "unit": "my-unit",
  "lesson": "my-lesson",
  "target_objectives": [
    "Students will be able to explain X."
  ],
  "target_vocabulary": ["term-one"],
  "supporting_objectives": [],
  "supporting_vocabulary": [],
  "width": 1600,
  "height": 900,
  "pipeline": {
    "grounding": "complete",
    "script": "complete",
    "html": "complete",
    "audio_tags": "complete",
    "audio": "complete",
    "assembled": false
  },
  "tts": {},
  "scenes": [
    {
      "comment": "Scene description",
      "duration": "8.5s",
      "html": "<complete self-contained HTML document>",
      "speech": "Caption text shown to viewer",
      "elevenlabs": "[excited] Narration for ElevenLabs TTS",
      "gemini": "[excited] Narration for Gemini TTS",
      "audio": "audio/scene_01.mp3"
    }
  ]
}
```

`script.json` exists in two states:
- **Pre-assembly** (working state): per-scene `audio` paths, local `<img src="...">` paths
- **Post-assembly** (after `/video-assemble`): top-level `"audio": "data:audio/mpeg;base64,..."` with all local paths replaced by data URIs, written to `script_assembled_base64.json`

Each video has two sets of objective/vocabulary fields:
- `target_*` — what this video primarily teaches; drives the full narration arc
- `supporting_*` — prerequisites this video relies on but does not primarily teach; appear as brief recap beats

---

## Tools Reference

These scripts are invoked by the skills automatically, but can also be run directly.

### `generation/tools/script_tool.py`

Targeted read/write/view utility for `script.json` files — avoids loading large JSON into the LLM context for simple field access.

```bash
# Read a field
python generation/tools/script_tool.py get script.json pipeline.script

# Set a field
python generation/tools/script_tool.py set script.json pipeline.audio complete

# View script with large scene fields omitted
python generation/tools/script_tool.py view script.json
python generation/tools/script_tool.py view script.json --omit html,elevenlabs,gemini
```

Dot-notation path syntax: `pipeline.script`, `scenes.2.speech`, `tts.provider`.

### `generation/tools/text_utils.py`

Shared text sanitization module (not a runnable script). Provides:
- `normalize_text(text)` — replaces curly quotes, smart apostrophes, en/em dashes, and ellipsis with ASCII equivalents
- `normalize_data(obj)` — recursively applies `normalize_text` to all strings in any dict or list

Applied at every external data ingestion point and before every TTS API call.

### `generation/tools/paths.py`

Canonical path helper module (not a runnable script). Provides `unit_root()`, `lesson_root()`, `video_root()`, `video_script()`, and related functions. Imported by all skill scripts.

### Audio generation scripts (invoked by `/video-audio`)

**ElevenLabs** (`elevenlabs-gen.py`):
```bash
python .claude/skills/video-audio/scripts/elevenlabs-gen.py \
  generation/units/<unit>/lessons/<lesson>/videos/<video>/script.json --voice Dan
python .claude/skills/video-audio/scripts/elevenlabs-gen.py \
  generation/units/<unit>/lessons/<lesson>/videos/<video>/script.json --fake
```
Reads `scenes[].elevenlabs`, calls ElevenLabs, saves a single `audio/voiceover.mp3`, writes `scenes[].duration` back to `script.json`. Voices: Dan, Sam, Adam, Hope. `--fake` assigns 3.0s per scene without an API call.

**Gemini TTS** (`gemini-audio-gen.py`):
```bash
python .claude/skills/video-audio/scripts/gemini-audio-gen.py \
  generation/units/<unit>/lessons/<lesson>/videos/<video>/script.json --voice Zephyr
python .claude/skills/video-audio/scripts/gemini-audio-gen.py \
  generation/units/<unit>/lessons/<lesson>/videos/<video>/script.json --fake
```
Reads `scenes[].gemini`, calls Gemini TTS, saves per-scene `audio/scene_NN.mp3` files, writes `scenes[].duration` and `scenes[].audio` back to `script.json`. Voices: Zephyr, Puck, Aoede, Kore, Fenrir.

### Assembly script (invoked by `/video-assemble`)

**`embed-data.py`**:
```bash
python .claude/skills/video-assemble/scripts/embed-data.py \
  generation/units/<unit>/lessons/<lesson>/videos/<video>/script.json \
  generation/units/<unit>/lessons/<lesson>/videos/<video>/script_assembled_base64.json
```
Embeds all local assets (images and audio) as base64 data URIs. Writes to the output file; source `script.json` is never modified.

**`base64_clean.py`**:
```bash
python .claude/skills/video-assemble/scripts/base64_clean.py \
  generation/units/<unit>/lessons/<lesson>/videos/<video>/script.json
# → writes script_cleaned.json (original untouched)
```
Strips base64 payloads before asking Claude to read or edit a post-assembled script.
