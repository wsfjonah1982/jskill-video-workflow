# Workflow 3 — Ads Creation Workflow

Source: `workflow3.jpg` (BytePlus "AI-Native Applications" reference architecture)

## Use Case

For non-professional users — template-based operation, low barrier to entry — to create ads
using AIGC. The most elaborate of the three workflows: it adds a full storyboard stage between
the reference image and the final video, so a non-professional can review and steer the ad's
shot sequence before committing to video generation.

## Pipeline

```
Input: Topic & Idea
        │
        ▼
Template selection (Type, Format, Style, Mood)   [Seed 2.1 Turbo]
        │
        ├──────────────────────────────────────────────────────────────┐
        ▼                                                               │ (template
Script Planning                                                        │  context
  [Seed 2.1 Pro]                                                        │  threads
        │                                                               │  through
        ▼                                                               │  every
Reference Image Generation                                              │  step)
  [Seedream 5.0 Pro 2K]                                                  │
        │                                                               │
        ▼                                                               │
        ├────────────────────────┐                                     │
        ▼                        │                                     │
Storyboard Prompt Generation      │ (feeds back for                    │
  [Seed 2.1 Pro]                  │  storyboard revision)               │
        │                        │                                     │
        ▼                        │                                     │
Storyboard Generation ───────────┘                                     │
  [Seedream 5.0 Pro 2K]                                                  │
        │                                                               │
        ▼                                                               │
Video Prompt Generation                                                  │
  [Seed 2.1 Pro]                                                         │
        │                                                               │
        ▼                                                               │
Video Generation  ◄──────────────────────────────────────────────────────┘
  [Seedance 2.0, 10s]
        │
        └──► loops back into itself (regenerate / re-roll)
```

Two loop-backs matter here: Storyboard Generation can revise via Storyboard Prompt
Generation (iterate on the storyboard before touching video), and Video Generation can
re-roll on its own (same pattern as Workflow 2).

## Steps

| # | Step | Model | Purpose |
|---|---|---|---|
| 1 | Template selection | Seed 2.1 Turbo | Type/format/style/mood from the user's topic |
| 2 | Script Planning | Seed 2.1 Pro (chat LLM) | Write the ad's script/narrative beats |
| 3 | Reference Image Generation | Seedream 5.0 Pro 2K | Generate the product/subject identity anchor |
| 4 | Storyboard Prompt Generation | Seed 2.1 Pro (chat LLM) | Turn the script into per-panel storyboard prompts |
| 5 | Storyboard Generation | Seedream 5.0 Pro 2K | Render the storyboard panels as images for review |
| 6 | Video Prompt Generation | Seed 2.1 Pro (chat LLM) | Turn the approved storyboard into a structured Seedance video prompt |
| 7 | Video Generation | Seedance 2.0, 10s | Render the final ad video |

(This skill's `config.json` now runs **Seedance 2.5** — the diagram's "2.0" above is transcribed
as-is from the source image; see the version note in the Mapping section below.)

The storyboard stage renders quickly and cheaply compared to video — its value is catching a
bad narrative or shot sequence as still images *before* committing to full video generation,
which is the slower and heavier step in the pipeline.

## Mapping to This Skill

| Diagram step | This skill |
|---|---|
| Template selection | Claude, conversationally (SKILL.md Step 2) either way |
| Script Planning | Either Claude directly, or `scripts/generate_script.py` (`chat_model_id`) for the automated path — see `SKILL.md`'s "Alternative: Automated Prompt Authoring" |
| Reference Image Generation | `scripts/generate_image_from_text.py`, using a prompt from `scripts/generate_image_prompt.py` (automated) or Claude (interactive) |
| Storyboard Prompt Generation + Storyboard Generation | **Not currently a distinct stage in this skill** — see gap below |
| Video Prompt Generation | Either Claude, per `references/best-practices.md` (shot-by-shot structure in §5 already produces storyboard-equivalent detail inline in the video prompt), or `scripts/generate_video_prompt.py` for the automated path |
| Video Generation | `scripts/generate_video_from_reference.py` — runs **Seedance 2.5** (`config.json`'s `video_model_id: dreamina-seedance-2-5-260628`), not the 2.0 shown in the diagram |
| Storyboard revision loop-back | N/A until storyboard becomes a real stage — see gap |
| Video Generation re-roll | Just re-run the script against the saved prompt file |

**Gap**: this skill currently folds "storyboard" into the video prompt itself (each `Shot N:`
block in a structured prompt, per `references/best-practices.md` §5) rather than rendering
each shot as a separate reviewable image first. That's fine for a single-operator workflow
where Claude and the user iterate on the text prompt together, but it skips the specific value
this diagram is built around: letting a **non-professional user visually approve a storyboard**
before paying for video generation.

If this ads workflow gets built out for real inside this skill, the natural addition is:
generate one panel per `Shot N:` line via `scripts/generate_image_from_text.py` (one prompt
per line — which is exactly how that script already batches multiple images, see
`references/best-practices.md` §12), present the panel set to the user for approval, *then*
proceed to `scripts/generate_video_from_reference.py` for the final render. That reuses the
existing scripts as-is; it's a workflow/SKILL.md sequencing addition, not a new script.

**`video_duration_seconds` note**: same as Workflow 2, this targets 10s clips — set
`config.json`'s `video_duration_seconds: 10` to match this workflow.
