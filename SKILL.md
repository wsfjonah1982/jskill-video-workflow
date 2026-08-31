---
name: video-workflow
description: >
  Generate images and videos via Seedream 5.0 and Seedance 2.5 (BytePlus ARK API), including
  crafting and optimizing the generation prompt itself. Use this skill whenever the user wants
  to generate a video, generate/edit an image, animate an image into a video, create a product
  video or ad, storyboard a short scene, or asks to "make a video", "create an image", "animate
  this photo", "turn this into a video", or to improve/optimize/write a prompt for video or
  image generation. Also trigger when the user describes a scene, character, product, or action
  they want generated or animated but hasn't written a structured prompt yet — this skill
  interviews them and writes one. Always consult this skill before writing a Seedance/Seedream
  prompt from memory, and before running any of this skill's scripts directly — the prompt
  quality and the generation settings (model, duration, aspect ratio, resolution, audio) both
  come from files this skill manages.
---

# Video Workflow Skill

## Overview

This skill does two jobs together: it **writes production-ready prompts** for Seedance 2.5
(video) and Seedream 5.0 (image), and it **runs the generation** via bundled scripts.
Don't skip the prompt-writing step — a good structured prompt is the single biggest lever on
output quality, and it's cheap (no API cost) compared to a wasted generation.

By default, **you** (Claude) write the prompt directly and interactively, informed by
`references/`. There's also an **automated alternative** — three scripts that call a chat
model (Deepseek) to write the script/image-prompt/video-prompt instead of you — for when the
user explicitly wants that automated pipeline rather than talking through the prompt with you.
See "Alternative: Automated Prompt Authoring" below.

All generation settings — model IDs, duration, aspect ratio, resolution, audio, watermark,
style menu — live in `config.json`, not in the scripts or the prompt text. Read it first.

**Always confirm the settings with the user before actually calling a generation script** —
see Step 5. This applies whether you got there by writing the prompt yourself or via the
automated Deepseek pipeline below; either way, the last step before spending real API cost is
the same generation scripts and the same confirmation.

---

## Workflow

### Step 1 — Read `config.json`

Always read `config.json` before doing anything else. It tells you the current model IDs,
`video_duration_seconds`, `video_ratio`, `video_resolution`, `generate_audio`, `watermark`,
`image_size`, and the `styles` menu this skill is tuned for (full profiles in
`references/styles.md`). Every prompt you write must match these settings — don't write
dialogue into a prompt if `generate_audio` is `false`, don't assume a duration or ratio other
than what's configured.

If the user wants different settings than what's configured (different duration, vertical
video, audio/dialogue enabled, a different model), **edit `config.json`** first, then proceed.
That's the only place these settings should change — don't add ad-hoc CLI flags or hardcode
overrides in a script.

### Step 2 — Gather intent

Ask 2–4 targeted questions if the user's request is underspecified: subject, action, style
(offer the `styles` list from config), whether they have a reference image, and — only if
`generate_audio: true` — dialogue/music/SFX. If the user already gave enough detail (e.g. a
full scene description), skip straight to writing the prompt.

### Step 3 — Load references as needed

| Need | Reference file |
|---|---|
| Prompt structure, formula, modes, which script to use, scenario strategies | `references/best-practices.md` |
| Camera angles, movement, lens choices | `references/camera-angles.md` |
| Visual style descriptors and example prompts | `references/styles.md` |
| A generation came back wrong (subtitles, watermark, style drift, twin characters, stutter at joins) | `references/common-issues.md` |
| A character turnaround or storyboard panel — check for a ready-made skeleton first | `prompt/` (see `prompt/README.md`) |

Read `references/best-practices.md` at minimum before writing any prompt — it explains the
core Subject+Motion+Environment+Camera+Aesthetic(+Audio) formula, and which generation script
fits the task.

### Step 4 — Write the prompt to a file

Save the finished prompt as a `.txt` file under `_log/` (create a descriptive filename,
e.g. `_log/product_orbit_prompt.txt`) — `_log/` doubles as the prompt-log: it's the record of
exactly what prompt produced which generation, alongside each run's `.log` JSON transaction
record (Step 6). Two format rules matter:

- **`scripts/generate_image_from_text.py` reads the file line-by-line** — each non-empty line becomes a
  *separate* image. Write one self-contained one-line prompt per line here; don't put a
  multi-line structured block in this file.
- **Every other generation script — `generate_image_from_reference.py`, `generate_video_from_text.py`,
  `generate_video_from_reference.py`, `generate_video_from_multi_references.py` — reads the whole
  file as one prompt** — multi-line structured prompts (style header, shot-by-shot blocks) are
  expected and encouraged here.
- **`scripts/generate_character_sheet.py` doesn't take `--prompt` at all** — give it `--idea`
  (a plain subject description) instead, and it builds the fixed character-sheet prompt itself.
  Skip Steps 3–4 for this one; just write the idea description and go straight to Step 5.

### Step 5 — Confirm settings, then run the script

**Before invoking any generation script, show the user the settings that will
actually be used and get their explicit go-ahead.** These are real, paid, non-instant API
calls (video generation in particular can run several minutes) — confirm first rather than
finding out the duration/audio/style was wrong after paying for it. Display a short summary
pulled from the live `config.json` plus what this specific generation will do, e.g.:

```
About to generate:
  Script:    scripts/generate_video_from_reference.py
  Model:     dreamina-seedance-2-5-260628 (Seedance 2.5)
  Duration:  30s        Resolution: 720p        Ratio: follows input image
  Audio:     true (dialogue + music)             Watermark: false
  Reference: _output/singapore_condo_agent_v2.jpg
  Prompt:    _log/singapore_condo_agent_v2_video_prompt_30s_audio.txt

Proceed?
```

Wait for a yes before running. Skip this confirmation only if the user already explicitly
approved these exact settings in the same request (e.g. they just asked you to change
`config.json` to specific values and immediately said to rerun) — don't ask twice for the
same confirmation. If they say to change something, update `config.json` (Step 1) or the
prompt (Step 4) first, then re-show the summary before running.

Pick the script based on what the user has and wants (see `references/best-practices.md` §3):

| Have | Want | Script |
|---|---|---|
| Nothing (or a text idea) | An image | `scripts/generate_image_from_text.py` |
| A subject description (a character/person to keep consistent later) | A three-view turnaround character sheet | `scripts/generate_character_sheet.py` |
| One or more existing images | A modified/edited image | `scripts/generate_image_from_reference.py` (`--img` accepts multiple) |
| Nothing (or a text idea) | A video | `scripts/generate_video_from_text.py` |
| One existing image | A video animated from it | `scripts/generate_video_from_reference.py` |
| Two or more existing images | A video referencing all of them (e.g. a subject shot + a separate scene shot) | `scripts/generate_video_from_multi_references.py` |

The recommended path when identity/framing matters (products, characters) is **two steps**:
generate or edit the image first — a character sheet via `scripts/generate_character_sheet.py`
is the strongest identity anchor when a recurring character matters — then animate it with
`scripts/generate_video_from_reference.py`, rather than going straight to
`scripts/generate_video_from_text.py` from text alone. Confirm before each call — they're
separate generations with separate costs.

```bash
python scripts/generate_image_from_text.py --prompt _log/product_shot_prompt.txt --output _output/product_shot.jpg
python scripts/generate_video_from_reference.py --img _output/product_shot.jpg --prompt _log/product_orbit_prompt.txt --output _output/product_orbit.mp4
```

### Step 6 — Report results, watch for known issues

Each script prints only the output file path to stdout on success; progress goes to stderr,
and a `.log` JSON-lines transaction record is written to `_log/` (named after the output file,
e.g. `_output/product_orbit.mp4` → `_log/product_orbit.mp4.log`) — not next to the output
itself. After a run, skim the log for `status: failed` and check the output against
`references/common-issues.md` if something looks off (subtitles that weren't asked for, a
watermark, style drift, duplicate characters) — most of these have a one-line prompt fix or a
`config.json` fix.

---

## Alternative: Automated Prompt Authoring (Deepseek)

Adapted from `jonah-simple-video-flow`'s chat-completion pattern
(`service/ark_service.py::ArkChatService` + its `prompts/*.md` templates): instead of you
writing the prompt directly, a chat model writes it, driven by fixed system/user prompt
templates in `scripts/prompt_templates/`. Use this chain when the user specifically asks for
the automated/Deepseek pipeline (e.g. "use the script-planning flow", "generate the prompts
with the LLM step") rather than an interactive prompt session — for everyday requests, writing
the prompt yourself per Steps 2–4 above is simpler and lets you use the full
`references/` prompt-engineering library directly, which these templates don't draw on.

```bash
# 1. Idea → short script (chat_model_id, e.g. Deepseek)
python scripts/generate_script.py --idea _upload/idea.txt --output _log/script.txt

# 2. Idea (+ style) → image-generation prompt. With --img, skips the LLM call entirely and
#    uses a plain turnaround template instead, since the photo already carries the subject's
#    appearance (same logic as jonah-simple-video-flow).
python scripts/generate_image_prompt.py --idea _upload/idea.txt --style "Cinematic Realism" --output _log/image_prompt.txt

# 3. Reference image
python scripts/generate_image_from_text.py --prompt _log/image_prompt.txt --output _output/reference.jpg

# 4. Script (+ reference image) → video-generation prompt. With --img, attaches the image to
#    the call and uses vlm_model_id instead of chat_model_id, so the model can see it.
python scripts/generate_video_prompt.py --script _log/script.txt --img _output/reference.jpg --output _log/video_prompt.txt

# 5. Final video, same as the normal path
python scripts/generate_video_from_reference.py --img _output/reference.jpg --prompt _log/video_prompt.txt --output _output/final.mp4
```

Each script reads `chat_model_id` / `vlm_model_id` from `config.json` and the shared
`model_ark_key` from `credential.json` — no separate credentials needed. `scripts/ark_service.py`
holds the shared `ArkChatService` (and `ArkImageService`/`ArkVideoService`, used by the
generation scripts) — plain HTTP via the `requests` package (see Prerequisites), not a vendor SDK.

**Shortcut**: if step 2 doesn't need the LLM at all — i.e. you already have a reference photo
and just want the fixed character-sheet template — steps 2–3 above collapse into one call to
`scripts/generate_character_sheet.py --idea ... --img ... --output ...`, since it's the same
fixed template as `generate_image_prompt.py`'s `--img` path, but goes straight to the generated
image instead of stopping at prompt text.

---

## Configuration (`config.json`)

| Key | Meaning | Recorded default |
|---|---|---|
| `maas_api_endpoint` | BytePlus ARK API base URL | `https://ark.ap-southeast.bytepluses.com/api/v3` |
| `chat_model_id` | Chat model (e.g. Deepseek) for `scripts/generate_script.py` / `generate_image_prompt.py` / `generate_video_prompt.py` | `deepseek-v4-flash-260425` |
| `vlm_model_id` | Vision-capable chat model used by `generate_video_prompt.py` when `--img` is given | `seed-2-0-pro-260328` |
| `image_model_id` | Seedream model for `scripts/generate_image_from_text.py` / `scripts/generate_image_from_reference.py` / `scripts/generate_character_sheet.py` | `seedream-5-0-260128` |
| `image_size` | Seedream output size | `2K` |
| `video_model_id` | Seedance model for `scripts/generate_video_from_text.py` / `scripts/generate_video_from_reference.py` / `scripts/generate_video_from_multi_references.py` | `dreamina-seedance-2-5-260628` |
| `video_resolution` / `video_resolutions` | Current resolution + allowed options | `720p` / `480p, 720p, 1080p, 4K` |
| `video_ratio` / `video_ratios` | Current aspect ratio + allowed options | `16:9` / `16:9, 9:16, 1:1` |
| `video_duration_seconds` / `_min` / `_max` | Current clip length + allowed range | `30` / `5` / `30` |
| `generate_audio` | Whether video generation includes audio (music/SFX/dialogue) | `true` |
| `watermark` | Whether output carries a watermark | `false` |
| `poll_interval_seconds` / `max_polls` | How the scripts poll for video task completion | `15` / `120` |
| `styles` / `default_style` | The style menu this skill's references are tuned for | 15 styles / `Cinematic Realism` |

**This "Recorded default" column is a snapshot for quick reference, not the live source of
truth** — `config.json` always is. Update this table whenever you change `config.json` on the
user's instruction, so this record stays accurate; don't let it silently drift out of sync.

Secrets are resolved at runtime, checked in order: the `model_ark_key` environment variable
first, then `model_ark_key` in `credential.json`. Neither lives in `config.json`.

---

## Prerequisites

- Python 3.10+
- `requests` installed — all scripts talk to the Ark API directly over HTTP (`scripts/ark_service.py`: `ArkChatService`, `ArkImageService`, `ArkVideoService`), no vendor SDK required
- API key: a `model_ark_key` environment variable if set, otherwise `credential.json`'s `model_ark_key` — every script checks the env var first (see Configuration below). `credential_tmp.json` is a committed placeholder template — copy it to `credential.json` and fill in a real key; `credential.json` itself is gitignored and never committed.
- `config.json` present (see above) — every script fails fast with a clear error if missing

### Arguments

| Argument | Description |
|---|---|
| `--prompt` | Path to a `.txt` file with the prompt. Used by `generate_image_from_text.py`, `generate_image_from_reference.py`, `generate_video_from_text.py`, `generate_video_from_reference.py`, `generate_video_from_multi_references.py` (not `generate_character_sheet.py`, which builds its own prompt from `--idea` — see below) |
| `--idea` | Path to a `.txt` file with a topic/subject description. Used by `scripts/generate_script.py`, `generate_image_prompt.py`, and `generate_character_sheet.py` in place of `--prompt` |
| `--style` | Art style string, defaults to `config.json`'s `default_style`. Used by `generate_image_prompt.py`, `generate_video_prompt.py`, `generate_character_sheet.py` |
| `--img` | Path to an input image file. Required for `scripts/generate_image_from_reference.py`, `scripts/generate_video_from_reference.py`; optional for `scripts/generate_character_sheet.py`; accepts multiple values (space-separated) for `scripts/generate_image_from_reference.py`, `scripts/generate_video_from_multi_references.py`, and `scripts/generate_character_sheet.py` |
| `--output` | Output file path |

---

## Subfolders

| Folder | Purpose |
|---|---|
| `references/` | Prompt-engineering knowledge this skill uses — read as needed per Step 3 |
| `prompt/` | Predefined, reusable prompt templates (e.g. three-angle character sheet, storyboard panel) — see `prompt/README.md` |
| `scripts/prompt_templates/` | System/user templates for the Deepseek automated-authoring scripts (see above) — not the same as `prompt/` |
| `_upload/` | Files uploaded to the system — reference images, audio, source material |
| `_output/` | Generated results from API calls — images, videos |
| `_log/` | Transaction logs: each run's `.log` JSON record, plus the prompt `.txt` files you write per Step 4 |

See `README.md` for plain script usage without the prompt-crafting workflow (e.g. re-running
an existing prompt file).
