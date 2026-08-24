# Predefined Prompt Templates

Reusable prompt skeletons for common generation patterns — copy one, replace the `<placeholder>`
tokens with real content, save the result into `_log/` (per `SKILL.md` Step 4), then run it
through the matching script in `scripts/`.

This is different from `scripts/prompt_templates/`, which holds LLM system/user templates
consumed programmatically by the Deepseek automated-authoring scripts (`.format()`-style
`{placeholders}`). The templates here use `<placeholder>` markers meant for a human or Claude
to fill in directly, then feed straight into `scripts/generate_image_from_text.py`.

Each file is a single line — that matters, because `scripts/generate_image_from_text.py` treats
every non-empty line in a prompt file as a separate image request. Don't add comments or extra
lines to these files or to the copies you make from them.

| File | Use for | Fill in |
|---|---|---|
| `three_angle_character_sheet.txt` | A character/product identity reference (front/side/back turnaround) — the standard first step before animating a consistent subject with `generate_video_from_reference.py` | `<subject description>`: one concise sentence — species/build, clothing, colours, distinguishing features |
| `storyboard_panel.txt` | One still-image panel representing a single shot from a multi-shot video prompt — lets a user visually approve a shot sequence before paying for video generation (see `workflow/workflow3.md`'s Ads Creation Workflow) | `<style descriptor>`, `[<camera...>]`, `<subject and action...>`, `<environment...>` — pull the camera/action/environment straight from that shot's `Shot N:` line in the video prompt (see `references/best-practices.md` §5) |

To storyboard a multi-shot video prompt: copy `storyboard_panel.txt` once per `Shot N:` line,
fill it in from that shot, and put each on its own line in one file — `generate_image_from_text.py`
will render one panel per line in a single batched call.
