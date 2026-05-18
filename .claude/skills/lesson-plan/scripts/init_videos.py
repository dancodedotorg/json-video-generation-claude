"""
init_videos.py -- Initialize video folders from an approved video plan.

Reads lesson-plan.json from the lesson folder and creates one video folder per
entry, each with audio/, images/, scenes/ subdirs and a pre-populated script.json.

Usage:
    python generation/tools/init_videos.py <unit-slug> <lesson-slug>

Arguments:
    unit-slug    The unit slug (e.g. aif1-v2-2025)
    lesson-slug  The canonical lesson folder name (e.g. lesson-1-talking-to-machines)

Reads:
    generation/units/<unit>/lessons/<lesson>/lesson-plan.json

Creates for each video in the plan:
    generation/units/<unit>/lessons/<lesson>/videos/<video-name>/audio/
    generation/units/<unit>/lessons/<lesson>/videos/<video-name>/images/
    generation/units/<unit>/lessons/<lesson>/videos/<video-name>/scenes/
    generation/units/<unit>/lessons/<lesson>/videos/<video-name>/script.json

Exit codes:
    0  success
    1  usage error
    2  lesson-plan.json not found or invalid
    3  one or more videos already exist (prints which ones; does not overwrite)
    4  plan-level uniqueness rule violated (an objective or vocab term appears
       as a target in more than one video)
"""

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO_ROOT / "generation" / "tools"))
from paths import lesson_root, lesson_videos_root, video_root, video_script


SCRIPT_TEMPLATE = {
    "width": 1600,
    "height": 900,
    "pipeline": {
        "grounding": "complete",
        "script": "pending",
        "html": "pending",
        "audio_tags": "pending",
        "audio": "pending",
        "assembled": False,
    },
    "tts": {},
    "scenes": [],
}


def load_plan(unit: str, lesson: str) -> dict:
    plan_path = lesson_root(unit, lesson) / "lesson-plan.json"
    if not plan_path.exists():
        print(f"Error: lesson-plan.json not found at {plan_path}", file=sys.stderr)
        print("Run /lesson-plan first to create a plan.", file=sys.stderr)
        sys.exit(2)
    try:
        with open(plan_path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: lesson-plan.json is not valid JSON: {e}", file=sys.stderr)
        sys.exit(2)


def check_existing(unit: str, lesson: str, videos: list) -> list:
    return [v["name"] for v in videos if video_root(unit, lesson, v["name"]).exists()]


def validate_target_uniqueness(videos: list) -> list:
    """Return a list of human-readable error strings if any target_objective
    or target_vocabulary value appears in more than one video. Empty list on
    success. supporting_* arrays are not checked.
    """
    errors = []
    for field in ("target_objectives", "target_vocabulary"):
        seen: dict[str, list[str]] = {}
        for v in videos:
            for value in v.get(field, []) or []:
                seen.setdefault(value, []).append(v["name"])
        for value, owners in seen.items():
            if len(owners) > 1:
                errors.append(
                    f"  {field} value appears in {len(owners)} videos "
                    f"({', '.join(owners)}): {value!r}"
                )
    return errors


def create_video(unit: str, lesson: str, video: dict) -> Path:
    name = video["name"]
    root = video_root(unit, lesson, name)
    (root / "audio").mkdir(parents=True, exist_ok=True)
    (root / "images").mkdir(parents=True, exist_ok=True)
    (root / "scenes").mkdir(parents=True, exist_ok=True)

    script = {
        "video_name": name,
        "unit": unit,
        "lesson": lesson,
        "target_objectives": video.get("target_objectives", []),
        "supporting_objectives": video.get("supporting_objectives", []),
        "target_vocabulary": video.get("target_vocabulary", []),
        "supporting_vocabulary": video.get("supporting_vocabulary", []),
        "mode": video.get("mode", "concept"),
        "brief": video.get("brief", None),
        **SCRIPT_TEMPLATE,
    }

    script_path = video_script(unit, lesson, name)
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)

    return root


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    unit = sys.argv[1]
    lesson = sys.argv[2]

    plan = load_plan(unit, lesson)
    videos = plan.get("videos", [])

    if not videos:
        print("Error: lesson-plan.json contains no videos.", file=sys.stderr)
        sys.exit(2)

    uniqueness_errors = validate_target_uniqueness(videos)
    if uniqueness_errors:
        print(
            "Error: lesson-plan.json violates the target-uniqueness rule.",
            file=sys.stderr,
        )
        print(
            "Each target_objectives or target_vocabulary value must appear in at most one video.",
            file=sys.stderr,
        )
        print(
            "Move duplicates into supporting_objectives / supporting_vocabulary instead.",
            file=sys.stderr,
        )
        for line in uniqueness_errors:
            print(line, file=sys.stderr)
        sys.exit(4)

    existing = check_existing(unit, lesson, videos)
    if existing:
        print(f"Error: the following video folders already exist:", file=sys.stderr)
        for name in existing:
            print(f"  {video_root(unit, lesson, name)}", file=sys.stderr)
        print("Remove them manually or rename videos in lesson-plan.json before re-running.", file=sys.stderr)
        sys.exit(3)

    created = []
    for video in videos:
        root = create_video(unit, lesson, video)
        n_obj = len(video.get("target_objectives", []))
        n_sup_obj = len(video.get("supporting_objectives", []))
        n_vocab = len(video.get("target_vocabulary", []))
        n_sup_vocab = len(video.get("supporting_vocabulary", []))
        print(
            f"  Created {video['name']}/  "
            f"({n_obj} target obj"
            + (f" + {n_sup_obj} supporting" if n_sup_obj else "")
            + f", {n_vocab} target vocab"
            + (f" + {n_sup_vocab} supporting" if n_sup_vocab else "")
            + ")"
        )
        created.append(video["name"])

    print(f"\n{len(created)} video(s) initialized in generation/units/{unit}/lessons/{lesson}/videos/")
    print("\nNext steps for each video:")
    for name in created:
        print(f"  /video-script {unit} {lesson} {name}")


if __name__ == "__main__":
    main()
