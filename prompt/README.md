# Predefined Prompt Templates

Reusable prompt skeletons for common generation patterns — copy one, replace the `<placeholder>`
tokens with real content, save the result into `_project/prompt/` (per `SKILL.md` Step 4), then
run it through the matching script in `scripts/`.

This is different from `scripts/prompt_templates/`, which holds LLM system/user templates
consumed programmatically by the Deepseek automated-authoring scripts (`.format()`-style
`{placeholders}`). The templates here use `<placeholder>` markers meant for a human or Claude
to fill in directly.

Two shapes of template live here, matching the two prompt-file conventions in
`references/best-practices.md` §2:

- **Single-line** (`three_angle_character_sheet.txt`, `storyboard_panel.txt`) — feed straight
  into `scripts/generate_image_from_text.py`, which treats every non-empty line in a prompt
  file as a separate image request. Don't add comments or extra lines to these files or to the
  copies you make from them.
- **Multi-line, structured** (`house_agent_property_tour.txt`) — feed into a script that reads
  the whole file as one prompt (`scripts/generate_video_from_multi_references.py`,
  `scripts/generate_video_from_reference.py`, `scripts/generate_image_from_reference.py`).
  Shot blocks, dialogue, and audio cues are expected here — see `references/best-practices.md` §11.

| File | Use for | Fill in |
|---|---|---|
| `three_angle_character_sheet.txt` | A character/product identity reference (front/side/back turnaround) — the standard first step before animating a consistent subject with `generate_video_from_reference.py` | `<subject description>`: one concise sentence — species/build, clothing, colours, distinguishing features |
| `storyboard_panel.txt` | One still-image panel representing a single shot from a multi-shot video prompt — lets a user visually approve a shot sequence before paying for video generation (see `workflow/workflow3.md`'s Ads Creation Workflow) | `<style descriptor>`, `[<camera...>]`, `<subject and action...>`, `<environment...>` — pull the camera/action/environment straight from that shot's `Shot N:` line in the video prompt (see `references/best-practices.md` §5) |
| `house_agent_property_tour.txt` | A real-estate/property-tour video: an agent (identity anchor, `@image1`) presenting a property across one or more location reference photos (`@image2`, `@image3`, ...) — for `scripts/generate_video_from_multi_references.py`. Extracted from the Jakarta condo project's video prompt. | `<ratio>`/`<duration>` (mirror `config.json`), `<agent description>`, one `@imageN is <location description>` line per property photo, and per shot: `[<camera...>]`, `<gesture/action>`, `<expression>`, `Dialogue (...): {<line>}`, and the `()`/`<>` music/SFX cues |
| `retail_sports_showcase.txt` | An energetic sports-commercial product video: a character (identity anchor, `@image1`) showing off a product with multiple variants (`@image2`, e.g. a shoe in several colourways) through an action scene, a quick-cut variant montage, then a full lineup reveal — for `scripts/generate_video_from_multi_references.py`. Extracted and genericized from the retail sneaker project's parkour video prompt. | `<ratio>`/`<duration>`, `<character description>`, `<product description>` (incl. its variant list), `<sporty/energetic setting>` + `<action>` per shot, which `<variant N>` appears in each shot, opening/closing `Dialogue (...): {<line>}`, the `()`/`<>` music/SFX cues, and an optional trailing safety constraint if the action calls for one |

To storyboard a multi-shot video prompt: copy `storyboard_panel.txt` once per `Shot N:` line,
fill it in from that shot, and put each on its own line in one file — `generate_image_from_text.py`
will render one panel per line in a single batched call.
