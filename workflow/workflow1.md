# Workflow 1 — AI Education Workflow

Source: `workflow1.jpg` (BytePlus "AI-Native Applications" reference architecture)

## Use Case

A GenAI class for primary/secondary school students to experience AI video generation
hands-on. Each student picks a topic, gets a short first clip, then extends it into a
second clip — a minimal loop designed to teach the "idea → frame → video" concept
within a single class hour.

## Pipeline

```
Input: Topic & Idea
        │
        ▼
Template selection (Type, Format, Style, Mood)   [Seed 2.1 Turbo]
        │
        ├──────────────────────────────────────────────────┐
        ▼                                                   │ (template context
1st Frame Generation                                        │  feeds every step)
  [Seedream 5.0 Pro 2K]                                      │
        │                                                   │
        ▼                                                   │
1st Video Generation                                         │
  [Seedance, 15s]                                            │
        │                                                   │
        ▼                                                   │
2nd Frame Extraction  ◄────────────────────────────────────┘
        │
        ▼
2nd Video Generation
  [Seedance, 15s]
```

The dashed lines in the diagram show the template's parameters (type, format, style, mood)
being threaded into every downstream generation step, not just the first — style and mood
must stay consistent across both clips.

## Steps

| # | Step | Model | Purpose |
|---|---|---|---|
| 1 | Template selection | Seed 2.1 Turbo | Turn a student's free-text topic/idea into structured parameters: type, format, style, mood |
| 2 | 1st Frame Generation | Seedream 5.0 Pro 2K | Generate the opening image for the first clip |
| 3 | 1st Video Generation | Seedance, 15s (480p mini or 720p) | Animate the first frame into a 15s clip |
| 4 | 2nd Frame Extraction | — | Pull a frame (typically the last) from the 1st video to use as the anchor for continuation |
| 5 | 2nd Video Generation | Seedance, 15s | Continue the story from the extracted frame into a second 15s clip |

For a classroom setting, the 480p mini tier is the practical default resolution — it keeps
generation fast enough for a live class while still teaching the full loop.

## Mapping to This Skill

This workflow is a straightforward application of the **multi-segment stitching** pattern
already documented in `references/best-practices.md` §7, using this skill's scripts directly:

| Diagram step | This skill |
|---|---|
| Template selection | Claude gathers intent conversationally (SKILL.md Step 2) — no separate classification model needed since Claude is already doing the prompt authoring |
| 1st Frame Generation | `scripts/generate_image_from_text.py` |
| 1st Video Generation | `scripts/generate_video_from_reference.py` (image-to-video, using the frame as `--img`) |
| 2nd Frame Extraction | Not currently scripted — see gap below |
| 2nd Video Generation | `scripts/generate_video_from_reference.py` again, on the extracted frame |

**Gap**: this skill has no "frame extraction" script — pulling a still frame out of a
generated `.mp4` (e.g. the last frame, for a clean continuation anchor). `best-practices.md`
§7 currently assumes you regenerate or hand-supply that frame via
`scripts/generate_image_from_reference.py` instead of extracting it from the video. If this
education workflow gets built out for real, the natural addition is a small `ffmpeg`-based
`scripts/extract_frame.py` (e.g. `ffmpeg -sseof -0.1 -i in.mp4 -vframes 1 out.jpg` for the
last frame) rather than resorting to image generation for something that already exists in
the rendered video.
