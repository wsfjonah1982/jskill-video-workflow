# Video Workflow Skill

Generate images and videos using Seedream 5.0 and Seedance 2.5 via the BytePlus ARK API.

For the full workflow — prompt crafting guided by `references/`, config-driven generation
settings, which script to use — see `SKILL.md`. This file covers plain script usage.

## Prerequisites

- Python 3.10+
- `requests` installed — all scripts talk to the Ark API directly over HTTP (`scripts/ark_service.py`), no vendor SDK required
- API key: a `model_ark_key` environment variable if set, otherwise `credential.json`'s `model_ark_key`
  — copy `credential_tmp.json` to `credential.json` and fill in a real key to get started;
  `credential.json` is gitignored, `credential_tmp.json` is committed as the setup reference
- `config.json` with generation settings (model IDs, duration, aspect ratio, resolution,
  audio, watermark) — every script reads its settings from here, not from CLI flags
  or hardcoded constants

### Arguments

| Argument   | Description                           |
|------------|----------------------------------------|
| `--prompt` | Path to a `.txt` file with the prompt (all generation scripts except `generate_character_sheet.py`) |
| `--idea`   | Path to a `.txt` file with a topic/subject description (`generate_script.py`, `generate_image_prompt.py`, `generate_character_sheet.py`) |
| `--style`  | Art style string, defaults to `config.json`'s `default_style` (`generate_image_prompt.py`, `generate_video_prompt.py`, `generate_character_sheet.py`) |
| `--img`    | Path to an input image file. `generate_image_from_reference.py`, `generate_video_from_multi_references.py`, and `generate_character_sheet.py` accept multiple (space-separated); optional for `generate_character_sheet.py` |
| `--output` | Output file path                      |

---

## Scripts

### `scripts/generate_image_from_text.py` — Text to Image

Generates an image from a text prompt using **Seedream 5.0**. Each non-empty line in the
prompt file is generated as a separate image.

```bash
python scripts/generate_image_from_text.py --prompt _log/step1_image_prompt.txt --output _output/output_image.jpg
```

---

### `scripts/generate_image_from_reference.py` — Image + Prompt to Image

Edits or transforms an existing image guided by a text prompt using **Seedream 5.0**.

```bash
python scripts/generate_image_from_reference.py --img _output/output_image.jpg --prompt _log/edit_prompt.txt --output _output/output_image_edit.jpg
```

---

### `scripts/generate_character_sheet.py` — Idea to Character Reference Sheet

Generates a character turnaround sheet (front/side/back view, full body, clean white
background) from a subject description, using **Seedream 5.0**. Builds its own prompt from a
fixed template (adapted from `jonah-simple-video-flow`'s `prompts/reference_image_prompt.md`)
— no chat model call, no `--prompt` needed. With `--img`, one or more photos anchor the
subject's appearance instead of generating from the description alone.

```bash
python scripts/generate_character_sheet.py --idea _upload/character_idea.txt --style "Cinematic Realism" --output _output/character_sheet.png
```

---

### `scripts/generate_video_from_text.py` — Text to Video

Generates a video from a text prompt using **Seedance 2.5**.

```bash
python scripts/generate_video_from_text.py --prompt _log/step2_video_prompt.txt --output _output/output_video.mp4
```

---

### `scripts/generate_video_from_reference.py` — Image + Prompt to Video

Generates a video using an image as the first frame, guided by a text prompt, using **Seedance 2.5**.

```bash
python scripts/generate_video_from_reference.py --img _output/output_image.jpg --prompt _log/step2_video_prompt.txt --output _output/output_video.mp4
```

---

### `scripts/generate_video_from_multi_references.py` — Multiple Images + Prompt to Video

Generates a video from **two or more** reference images (Seedance's All-Reference mode) — e.g.
a subject identity shot plus a separate background/scene shot — guided by a text prompt, using
**Seedance 2.5**. For a single reference image, use `generate_video_from_reference.py` instead.

```bash
python scripts/generate_video_from_multi_references.py --img _output/subject.jpg _output/scene.jpg --prompt _log/combined_prompt.txt --output _output/output_video.mp4
```

---

## Deepseek Prompt-Authoring Scripts

Adapted from `jonah-simple-video-flow`'s chat-completion pattern. These write prompts using a
chat model instead of a human/Claude writing them — an alternative to the interactive
prompt-crafting workflow described in `SKILL.md`.

### `scripts/generate_script.py` — Idea to Script

Turns a topic/idea into a short scene-by-scene script using `chat_model_id` (e.g. Deepseek).

```bash
python scripts/generate_script.py --idea _upload/idea.txt --output _log/script.txt
```

### `scripts/generate_image_prompt.py` — Idea to Image Prompt

Turns a topic/idea (+ style) into an image-generation prompt using `chat_model_id`. If `--img`
is given, skips the LLM call and uses a plain character-turnaround template instead, since the
reference photo already carries the subject's appearance.

```bash
python scripts/generate_image_prompt.py --idea _upload/idea.txt --style "Cinematic Realism" --output _log/image_prompt.txt
```

### `scripts/generate_video_prompt.py` — Script to Video Prompt

Turns a script (+ style, duration, ratio) into a structured video-generation prompt using
`chat_model_id`. If `--img` is given, attaches the reference image to the call and uses
`vlm_model_id` instead, so the model can see it.

```bash
python scripts/generate_video_prompt.py --script _log/script.txt --img _output/reference.jpg --output _log/video_prompt.txt
```

### `scripts/ark_service.py`

Shared Ark API clients (`ArkChatService`, `ArkImageService`, `ArkVideoService`) that every
script in this folder imports — plain HTTP via `requests`, not run directly.

### `scripts/prompt_templates/`

The fixed system/user prompt templates the three scripts above fill in and send to the chat
model — not the same as `prompt/`, the top-level folder of predefined, human-facing prompt
templates (see Subfolders below).

---

## Typical Two-Step Workflow

```bash
# Step 1: generate image from prompt
python scripts/generate_image_from_text.py --prompt _log/step1_image_prompt.txt --output _output/output_image.jpg

# Step 2: animate the image into a video
python scripts/generate_video_from_reference.py --img _output/output_image.jpg --prompt _log/step2_video_prompt.txt --output _output/output_video.mp4
```

For a recurring character, use `generate_character_sheet.py` instead of `generate_image_from_text.py`
for step 1 — it's a stronger identity anchor for step 2 (turnaround sheet vs. a single angle).

---

## Output

- All scripts print **only the output file path** to stdout on success.
- Progress and status messages go to stderr.
- A `.log` file (JSON lines) is written to `_log/`, named after the output file
  (e.g. `_output/output_video.mp4` → `_log/output_video.mp4.log`) — not next to the output itself.

## Subfolders

| Folder | Purpose |
|--------|---------|
| `references/` | Prompt-engineering knowledge (formula, camera language, styles, known issues) |
| `prompt/` | Predefined, reusable prompt templates (three-angle character sheet, storyboard panel) — see `prompt/README.md` |
| `scripts/prompt_templates/` | System/user templates for the Deepseek prompt-authoring scripts (not the same as `prompt/`) |
| `_upload/` | Files uploaded to the system — images, audio, reference materials |
| `_output/` | Generated results from API calls — images, videos |
| `_log/` | Transaction logs: each run's `.log` JSON record, plus the prompt `.txt` files used to produce it |

## Configuration

- `credential.json` — secrets fallback (`model_ark_key`); every script checks the
  `model_ark_key` environment variable first and only reads this file if that's unset
- `config.json` — everything else: model IDs (including `chat_model_id` / `vlm_model_id` for
  the Deepseek scripts), duration, aspect ratio, resolution, `generate_audio`, `watermark`,
  image size, style menu. Edit this file to change generation behavior; the scripts read it
  at runtime. See `SKILL.md`'s Configuration section for the recorded default values and
  the required pre-generation confirmation step.
