# Analysis Guide

Perform each section below in order and show your reasoning explicitly before generating plans.

## Map objectives to slide sections

Read the `notes` field of each slide in every `source/*/slides_data.json` file. A lesson may have multiple slide decks, each in its own subfolder under `source/`. Look for section markers (e.g. "Warm Up", "Activity", "Wrap Up") and topic headers. For each objective, identify which slides directly address it — cite the deck folder name, slide indices, and notes text as evidence.

## Map objectives to levels

For each level in the levels JSON, read `longInstructions`. Identify which objective(s) each level is practicing. Note which objectives share the same levels.

## Identify coupling

Two or more objectives are **tightly coupled** if they:
- Map to the same slide section(s), AND
- Are practiced by the same levels, OR
- One is a prerequisite for understanding the other

Two objectives are **loosely coupled** (separate video candidates) if they:
- Map to different slide sections (e.g. one is in "AI Predictions", the other in "Prompting AI"), OR
- A student could struggle with one independently of the other

## Assign target vs. supporting objectives

For each proposed video, first assign **target objectives** — the objectives this video primarily teaches. Then identify **supporting objectives** by checking, for each other objective in the lesson:

- Is this concept a prerequisite for understanding the target objectives of this video?
- Would a cold viewer (someone who has not seen any sibling videos) be confused within the first scene without a brief recap of it?

If yes to both, add that objective to this video's `supporting_objectives`. The objective remains a *target* in whichever sibling video primarily teaches it — that constraint is enforced at write time (`init_videos.py` rejects duplicates across `target_objectives`).

Be sparing. Supporting objectives are recap context, not a "related concepts" dumping ground. If a concept can be referenced in one sentence without recapping it, do not list it as supporting. As a rule of thumb: if you would not write a dedicated recap scene or recap beat for it, it does not belong.

## Assign target vs. supporting vocabulary

Apply the same model to vocabulary:

- A term's `target_vocabulary` home is the video that formally defines and reinforces it. Each term targets at most one video in the plan.
- A term that appears in passing in another video — used in narration but not defined there — belongs in that video's `supporting_vocabulary`.

A term may appear in zero, one, or many `supporting_vocabulary` arrays across the plan, but in at most one `target_vocabulary` array.

## Estimate timing

For each proposed video, count the number of scenes it would likely need in re-teach mode. Re-teach mode synthesizes and condenses — expect roughly 1 scene per major concept or slide group, not 1 per slide. At ~10–15 seconds of narration per scene, the maximum is about 12 scenes (≈2.5–3 min). Shorter videos are fine and preferred. Flag any cluster whose scene count would push past 3 minutes.
