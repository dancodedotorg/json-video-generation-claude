# json-video-player

A Claude Code-powered pipeline for authoring structured JSON video scripts from curriculum source materials. Each output is a single `.json` file describing a sequence of scenes — each scene is a self-contained HTML document, a narration caption, an optional audio track, and timing metadata.

## Requirements

- Python 3.12 or 3.13
- [ffmpeg](https://ffmpeg.org/download.html) on your PATH (used by pydub to encode Gemini TTS audio as MP3)
- Python packages: `pip install -r generation/tools/requirements.txt`
- API keys in `generation/tools/.env`:
  - `ELEVENLABS_API_KEY` — ElevenLabs TTS
  - `GOOGLE_API_KEY` — Gemini TTS and image generation
  - `GOOGLE_SERVICE_ACCOUNT_JSON` — base64-encoded service account JSON (only needed for Google Slides/Docs fetching)

> **Python 3.13:** `audioop` was removed from the stdlib. Uncomment `audioop-lts` in `requirements.txt` before installing.

## Honoring human-in-the-loop gates

Skills in this project define hard-stop gates (sources.csv review in `/lesson-init`, plan approval in `/lesson-plan`, scene-plan and content-spec approvals in `/video-html`, script approval in `/video-script`, etc.) for good reason — they catch problems that silently degrade downstream output. **Bias toward honoring them.**

Only skip a gate when the user's instruction is **specific and end-to-end**, not merely brisk in tone. A pointed directive can authorize skipping; vague urgency cannot.

**Authorizes skipping gates:**
  - "Run the full pipeline end-to-end. Don't check in — ping me when done."
  - "Skip all review gates; I'll look at the result."
  - "Generate the video autonomously."
  - "Make the HTML scenes with mode D — complete the full process."

**Does NOT authorize skipping gates:**
  - "Make a video for X."          (vague scope — gates stay)
  - "Quick — set up lesson 9."     (speed ≠ autonomy)
  - "Work without stopping for clarifying questions."
       (addresses *questions you would invent*, not skill-defined review gates)

When the instruction is ambiguous, treat the ambiguity as a vote for the gate. Surface the conflict to the user ("I see you said X — but this skill has a review gate at Y. Want me to honor it or skip?") rather than silently bypassing.

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
    ├── video-html/              ← Includes references/ folder with design and generation guides
    ├── video-assemble/
    └── video-create/
```

### Generation workflow

```
/unit-init  <unit-slug>                    → one-time: creates unit.json from Code.org API
/lesson-init <unit> <lesson>               → one-time per lesson: creates lesson folder, auto-populates sources.csv
/lesson-ground <unit> <lesson>             → fetches lesson source materials (can re-run to refresh)
/lesson-plan  <unit> <lesson>              → preferred: analyzes objectives, recommends video split, initializes ALL videos
/video-init  <unit> <lesson> <video>       → add a single video outside an existing plan
                                             do NOT call after /lesson-plan — videos are already initialized
/video-create <unit> <lesson> <video>      → orchestrates script → html → audio-tags → audio → assemble
```

Each video's `script.json` stores `unit`, `lesson`, and `target_objectives` so all skills can resolve paths deterministically. The lesson `source/` folder is shared across all videos in that lesson — grounding happens once at the lesson level, not per-video.

Every skill checks `script.json`'s `pipeline` status and skips completed stages. Run any skill at any time — it picks up where you left off. `/video-create` also resumes automatically.

## JSON Video Format

Each video's `script.json` includes `unit`, `lesson`, and `target_objectives`:

```json
{
  "video_name": "objective-1",
  "unit": "problem-solving-with-ai",
  "lesson": "lesson-2-beyond-words",
  "target_objectives": [
    "Experiment with different media inputs to observe AI's interpretation and limitations.",
    "Explain that multimodal AI models process information from multiple types of input."
  ],
  "supporting_objectives": [
    "Describe how AI models generate responses from input data."
  ],
  "target_vocabulary": [
    "multimodal model"
  ],
  "supporting_vocabulary": [
    "AI model"
  ],
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
      "elevenlabs": "[tone] narration text for ElevenLabs",
      "gemini": "[tone] narration text for Gemini TTS",
      "audio": "audio/scene_01.mp3"
    }
  ]
}
```

`pipeline.grounding` is pre-set to `"complete"` at video-init time — grounding happens at the lesson level.

Each video has two pairs of fields for what it covers:

- `target_objectives` / `target_vocabulary` — what the video **primarily teaches**. Drives the full teaching arc in script generation.
- `supporting_objectives` / `supporting_vocabulary` — prerequisites or context the video relies on but does not primarily teach. Script generation treats these as brief recap beats so the video stands alone for a viewer who has not seen sibling videos. `supporting_*` arrays default to `[]` and are always present.

Within a single `lesson-plan.json`, any given objective or vocab word may appear in `target_*` of **at most one** video, but may appear in `supporting_*` of any number of videos. `init_videos.py` enforces this rule. Ad-hoc videos created via `/video-init` are not bound by it.

All four fields are set by `/lesson-plan` (via `init_videos.py`) or manually by `/video-init`.

The `html` field is the primary authoring target. It must be a complete, self-contained HTML document.

`script.json` exists in two states: **pre-assembly** (per-scene `audio` paths, local `<img>` paths) and **post-assembly** (all assets embedded as base64 data URIs, written to `script_assembled_base64.json` — the source `script.json` is never modified). Use `base64_clean.py` before asking Claude to read a post-assembled file.

## Text Conventions

**Always use ASCII-safe punctuation in any text you generate** — narration, captions, vocabulary definitions, objectives, slide copy, comments, everything. This applies across all file types.

| Instead of | Use |
|---|---|
| `'` `'` (curly apostrophe / single quotes) | `'` |
| `"` `"` (curly double quotes) | `"` |
| `–` (en dash) | `-` |
| `—` (em dash) | ` - ` |
| `…` (ellipsis character) | `...` |

Unicode typography characters cause silent failures in TTS pipelines and other downstream tools. `generation/tools/text_utils.py` provides `normalize_text()` (single string) and `normalize_data()` (recursively walks any dict/list) as a safety net — applied at every external data ingestion point (`filter_resources.py`, `google-fetch.py`, `init_lesson.py`) and before every TTS API call. The source text should still be clean before it gets there.

## Slide Design System

All slides follow a fixed-canvas approach: designed at **1600×900px**, scaled to fit the player via CSS viewport units. This means:

- **All sizing in `rem`** — the `:root` sets `font-size: calc(16vh / 9)`, making `1rem = 16px` at the design height of 900px. All dimensions scale proportionally as the viewport resizes. Do not use bare `px` for layout values.
- **All colors via CSS custom properties** — `var(--color-teal)`, `var(--color-purple)`, etc. No hardcoded hex values in slide-specific styles
- **No external dependencies** except Google Fonts (Barlow Semi Condensed + Figtree)
- **Every slide includes the same boilerplate** `<style>` block — never modify it. There is no resize script.

See `.claude/skills/video-html/references/design-guide.md` for the full color palette, typography scale, and layout principles.

## Generating Slides

**Full guidance is in `.claude/skills/video-html/references/`.** Key files:

- `template-selection.md` — visual approach overview (text vs. image gen vs. SVG) and template catalog; used during planning
- `generation-guide.md` — connected sequences, slide text density, HTML requirements, animation guidelines; used during generation
- `svg-patterns.md` — named SVG layout patterns with coordinate formulas for consistent diagram geometry
- `image-generation.md` — Visual Director prompt formula (Technical Spec + Visual Preset + Environment + Subject + Defaults)
- `mode-selection.md` — when to use Mode C (AI image per scene) vs. Mode D (full template toolkit)
- `script-editing.md` — rules for the script evaluation pre-pass that runs before HTML generation

Key points:

- There are three visual approaches: text-based HTML templates, AI image generation, and inline SVG
- Always read the full script before assessing individual scenes — connected sequences must be identified and planned as a group before any generation begins
- Use the `/video-html` skill (`.claude/skills/video-html/`) as the task specification when starting a new slide generation session

## Tools

### Shared libraries (`generation/tools/`)

`paths.py` and `text_utils.py` remain in `generation/tools/` as shared Python libraries — they are not runnable scripts, just modules imported by skill scripts. Skill scripts reference them via `sys.path.insert(0, str(Path.cwd() / "generation" / "tools"))`.

### `generation/tools/text_utils.py`
Shared text sanitization. Two functions:
- `normalize_text(text)` — replaces curly quotes, smart apostrophes, en/em dashes, and ellipsis with ASCII equivalents
- `normalize_data(obj)` — recursively applies `normalize_text` to all string values in any dict or list

Import this in any script that reads data from an external source (Code.org API, Google, LLM output) before saving to a file or calling an external API.

### `generation/tools/paths.py`
Canonical path helper module. Provides functions like `unit_root()`, `lesson_root()`, `video_root()`, `video_script()` etc.

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

### Key scripts invoked by skills

**Audio generation** (`.claude/skills/video-audio/scripts/`):
- `elevenlabs-gen.py` — reads `scenes[].elevenlabs`, calls ElevenLabs, saves a single `audio/voiceover.mp3`, writes `scenes[].duration` back. Voices: Dan, Sam, Adam, Hope. `--fake` skips the API.
- `gemini-audio-gen.py` — reads `scenes[].gemini`, saves per-scene `audio/scene_NN.mp3`, writes `scenes[].duration` and `scenes[].audio` back. Voices: Zephyr, Puck, Aoede, Kore, Fenrir. `--fake` skips the API.

**Assembly** (`.claude/skills/video-assemble/scripts/`):
- `embed-data.py` — embeds all local assets (audio + images) as base64 data URIs; writes to `script_assembled_base64.json` without modifying source.
- `base64_clean.py` — strips base64 payloads before asking Claude to read or edit a post-assembled file; writes to `script_cleaned.json`.

## Shell Commands

Always use `python` (not `python3`) when running scripts from the shell.

**Skill script paths:** Script paths inside skill instructions (e.g., `scripts/foo.py`) are relative to the skill's own directory, not the project root. When running commands from a skill, expand them to their full project-relative form: `.claude/skills/<skill-name>/scripts/foo.py`. For example, `python scripts/fetch_unit.py` in the `unit-init` skill becomes `python .claude/skills/unit-init/scripts/fetch_unit.py`.
