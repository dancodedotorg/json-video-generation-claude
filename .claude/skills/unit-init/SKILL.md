---
name: unit-init
description: Initializes a new curriculum unit folder, fetches lesson IDs and unit resources from Code.org, and generates unit.json. One-time setup per unit.
allowed-tools: Bash(python *) Bash(mkdir *) Read Write
metadata:
  disable-model-invocation: "true"
  argument-hint: "<unit-slug>"
---

# unit-init

Initialize a curriculum unit at `generation/units/$ARGUMENTS/`.

The unit slug is the URL slug used on studio.code.org — e.g., `problem-solving-with-ai` for `studio.code.org/s/problem-solving-with-ai`.

## Gotchas

- **Manual fallback requires Tampermonkey** — if Step 2 exits with code 2, the user must have the Tampermonkey browser extension installed before attempting the manual step. If they don't have it, they need to install it first.
- **Never bulk-ground without per-lesson sources.csv review.** Grounding consumes whatever is in sources.csv at the moment it runs, and Code.org's public resources list often omits the teacher slide deck and other essential internal materials. Grounding before review locks in incomplete sources and silently degrades every downstream video. Always require the user to step through `/lesson-init` (which has a mandatory CSV review gate) before grounding. Do not offer or run `ground-all.py` from this skill.

## Step 1: Create folder structure

```bash
mkdir -p generation/units/$ARGUMENTS
```

## Step 2: Fetch lessons and resources

Run the fetch script, which saves `lessons.json` and `resources.json` to `generation/units/$ARGUMENTS/`:

```bash
python scripts/fetch_unit.py $ARGUMENTS
```

The script prints the lesson list on success.

If it exits with code 2, relay the instructions the script printed to the user exactly as printed, then stop. Do not proceed to Step 3 until the user confirms that `resources.json` exists.

## Step 3: Generate unit.json

Run `filter_resources.py` to produce the clean unit.json:

```bash
python scripts/filter_resources.py generation/units/$ARGUMENTS/resources.json generation/units/$ARGUMENTS/lessons.json
```

This writes `generation/units/$ARGUMENTS/unit.json` directly.

## Step 4: Confirm

Print a summary:
```
✅ Unit "$ARGUMENTS" initialized.

  unit.json: N lessons with resources, vocabulary, and objectives
  Location:  generation/units/$ARGUMENTS/

Next steps:
  For each lesson you want to generate videos for:
    /lesson-init $ARGUMENTS <lesson-name>
```

## Step 5: Stop

Output the Step 4 confirmation block as the final response.

Do not offer bulk lesson initialization or bulk grounding from this skill. Each lesson must go through `/lesson-init` individually so the user gets the mandatory sources.csv review before grounding. Bulk paths skip that gate and lock in incomplete sources.
