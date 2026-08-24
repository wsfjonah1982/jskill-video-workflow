# Workflow 2 — Short-Form Content Influencer

Source: `workflow2.jpg` (BytePlus "AI-Native Applications" reference architecture)

## Use Case

For a digital professional/creator who specializes in producing bite-sized, highly engaging
content — 5–15s vertical/short-form videos. Unlike Workflow 1 (education, manual template
picking) or Workflow 3 (ads, storyboard-heavy), this is the lean creator loop: idea in,
finished short clip out, with an LLM doing the writing so the human doesn't have to hand-craft
prompts.

## Pipeline

```
Input: Topic & Idea
        │
        ▼
Template selection (Type, Format, Style)
        │
        ├───────────────────────────────────────────────────────────┐
        ▼                                                            │ (template context
Script Planning                                                      │  threads through)
  [Deepseek v4 flash]                                                 │
        │                                                            │
        ▼                                                            │
Reference Image Generation                                            │
  [Seedream 5.0 Pro 2K]                                                │
        │                                                            │
        ▼                                                            │
Video Prompt Generation                                                │
  [Deepseek v4 flash]                                                  │
        │                                                            │
        ▼                                                            │
Video Generation  ◄────────────────────────────────────────────────┘
  [Seedance 2.0, 10s]
        │
        └──► loops back into itself (regenerate / re-roll on the same reference + prompt)
```

The loop-back arrow on Video Generation is a re-roll: if a take doesn't land, regenerate from
the same reference image and video prompt rather than restarting the whole pipeline.

## Steps

| # | Step | Model | Purpose |
|---|---|---|---|
| 1 | Template selection | — | Pick content type/format/style up front (e.g. talking-head, product demo, meme format) |
| 2 | Script Planning | Deepseek v4 flash (chat LLM) | Turn the topic + template into a short script/beat sheet |
| 3 | Reference Image Generation | Seedream 5.0 Pro 2K | Generate the subject/scene reference image (identity anchor) |
| 4 | Video Prompt Generation | Deepseek v4 flash (chat LLM) | Convert the script + reference image into a structured Seedance video prompt |
| 5 | Video Generation | Seedance 2.0, 10s | Animate the reference image into the final short-form clip |

(This skill's `config.json` now runs **Seedance 2.5** — the diagram's "2.0" above is transcribed
as-is from the source image; see the version note in the Mapping section below.)

The two "Deepseek v4 flash" steps are a **chat model writing prompts for other models** —
this is the same pattern used in `jonah-simple-video-flow`'s `service/ark_service.py`
(`ArkChatService.complete()` with system/user prompt templates). This skill now bundles that
same pattern directly (`scripts/ark_chat_service.py` + `scripts/prompt_templates/`), as an
alternative to Claude authoring the prompts itself — see `SKILL.md`'s "Alternative: Automated
Prompt Authoring" section.

## Mapping to This Skill

| Diagram step | This skill |
|---|---|
| Template selection | Claude gathers this conversationally (SKILL.md Step 2) either way |
| Script Planning | Either Claude directly, or `scripts/generate_script.py` (`chat_model_id`, e.g. Deepseek) for the automated path |
| Reference Image Generation | `scripts/generate_image_from_text.py`, using a prompt from `scripts/generate_image_prompt.py` (automated path) or written by Claude (interactive path) |
| Video Prompt Generation | Either Claude directly (per `references/best-practices.md` + `styles.md` + `camera-angles.md`), or `scripts/generate_video_prompt.py` (`chat_model_id`/`vlm_model_id`) for the automated path |
| Video Generation | `scripts/generate_video_from_reference.py`, using the reference image as `--img` — runs **Seedance 2.5** (`config.json`'s `video_model_id: dreamina-seedance-2-5-260628`), not the 2.0 shown in the diagram |
| Video Generation loop-back (re-roll) | Just re-run the same script — `config.json`'s settings and the saved prompt file make a re-roll a single command, no new prompt-writing needed |

**Which path to use**: the interactive path (Claude writing prompts per `references/`) is the
default — it's richer (camera language, style profiles, known-issue fixes) and fits this
skill's conversational context. The automated Deepseek path is for when the user explicitly
asks for that pipeline, or wants prompt generation to run unattended without Claude in the
loop for that step.

**`video_duration_seconds` note**: this workflow targets 10s clips, shorter than this skill's
current `config.json` default of 15s. Duration is config-driven (see `SKILL.md` Step 1) — set
`video_duration_seconds: 10` before generating if replicating this workflow.
