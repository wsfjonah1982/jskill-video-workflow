# Prompt Best Practices — Seedance 2.5 / Seedream 5.0

Read this file for prompt structure, generation modes, dialogue formatting, multi-segment
stitching, and scenario-specific strategies. Pair with `camera-angles.md` for shot language
and `styles.md` for aesthetic direction. See `common-issues.md` when a generation comes back
wrong and needs a prompt-level fix.

This skill's scripts (`scripts/generate_video_from_text.py`, `scripts/generate_video_from_reference.py`, `scripts/generate_image_from_text.py`,
`scripts/generate_image_from_reference.py`) read their generation settings — model, duration, aspect ratio, resolution,
`generate_audio`, `watermark` — from `config.json`, not from the prompt text. Always read
`config.json` before writing a prompt so the prompt matches what will actually be generated
(see §0).

---

## 0. Config-Driven Settings

Unlike some prompt guides, duration/ratio/resolution/audio are **not** freeform choices you
write into the prompt — they come from `config.json` in this skill's directory:

| Config key | Controls |
|---|---|
| `video_duration_seconds` | Length of generated clips (min/max in `video_duration_min`/`_max`) |
| `video_ratio` | Aspect ratio (`16:9`, `9:16`, `1:1`) |
| `video_resolution` | Output resolution |
| `generate_audio` | Whether the model produces audio at all |
| `watermark` | Whether output carries a watermark |
| `image_size` | Seedream output resolution |
| `default_style` / `styles` | The style menu this skill is tuned for (see `styles.md`) |

**Before writing a prompt**: read `config.json`. State the duration/ratio in the prompt header
to reinforce them (the model responds better to explicit numbers even though the API call also
passes them), but never promise a duration/ratio/audio behavior that contradicts the config —
if the user wants something different (e.g. "make it 9:16" or "add dialogue"), update
`config.json` first, then write the prompt to match.

**Audio-dependent sections**: The Dialogue/TTS and Audio Layering guidance in this file (§8, §9)
only matters when `config.json`'s `generate_audio` is `true`. If it's `false` (the default),
omit dialogue/music/SFX cues from the prompt entirely — the model will not produce audio and
those cues just waste prompt budget. If the user asks for dialogue or sound and `generate_audio`
is `false`, flag it and offer to flip the config setting.

---

## 1. The Core Prompt Formula

Every prompt is built from these layers. Subject and Motion are required for video;
for a still image, Motion is replaced by pose/composition. All other layers are optional
but increase precision and control.

```
Subject + Motion + Environment + Camera/Cut + Aesthetic Description + Audio (video only, if enabled)
```

| Layer | Required | Purpose |
|---|---|---|
| **Subject** | ✅ | Who or what is in the shot |
| **Motion** | ✅ (video) | What they are doing |
| **Environment** | Optional | Where — space, background, time of day |
| **Camera / Cut** | Optional | Shot type, movement, transitions |
| **Aesthetic Description** | Optional | Visual style, colour, lighting mood |
| **Audio** | Optional, video only, requires `generate_audio: true` | Music `()`, SFX `<>`, dialogue `{}` |

### Formula in practice

**Minimal (Subject + Motion)**
```
A tabby cat leaps from a bookshelf onto a pile of cushions below.
```

**Intermediate (+ Environment + Camera)**
```
A tabby cat leaps from a tall bookshelf onto a pile of cushions in a cosy apartment.
[WS tracking shot follows the jump — slow motion on landing]
```

**Full (all layers, audio enabled)**
```
A tabby cat leaps from a tall bookshelf onto a pile of cushions in a cosy apartment.
[WS tracking follows the jump — then cuts to ECU on paws sinking into fabric]
Warm afternoon light through net curtains. Cinematic realism.
<thump of landing> <contented purr immediately after>
```

---

## 2. Prompt Structure Checklist

Use this order when building a complete prompt:

1. **Style + settings header** — style descriptor, aspect ratio, duration (mirrors `config.json`)
2. **Subject definition** — define characters/objects with stable features, if referencing images
3. **Shot-by-shot description** — apply the formula per shot
4. **Dialogue / TTS** — only if `generate_audio: true` (§8)
5. **Audio layering** — only if `generate_audio: true` (§9)
6. **Negative constraints** — explicit exclusions (§14)

For `scripts/generate_image_from_text.py`, each line of the prompt file becomes a **separate** image — write
one self-contained prompt per line, not a multi-line structured block (see §12 note).
For `scripts/generate_image_from_reference.py`, `scripts/generate_video_from_text.py`, and `scripts/generate_video_from_reference.py`, the whole prompt file is
sent as a single prompt, so multi-line structured prompts are fine and encouraged there.

---

## 3. Generation Modes (Which Script to Use)

### Text-Only Image → `scripts/generate_image_from_text.py`
No reference image. Prompt alone drives the result. One prompt per line = one image per line.
Best for: original characters, concept art, first-frame source material.

### Image Edit → `scripts/generate_image_from_reference.py`
Takes `--img` + a prompt describing the change. Best for: refining a generated image,
compositing, style transforms, preparing a first-frame asset for video.

### Text-to-Video → `scripts/generate_video_from_text.py`
No reference image, prompt alone drives the video. Best for: original scenes, IP-safe content,
abstract concepts.

### Image-to-Video → `scripts/generate_video_from_reference.py`
Takes `--img` (first frame) + a prompt describing what happens next. Best for: character/product
continuity — generate the image first with `scripts/generate_image_from_text.py`/`scripts/generate_image_from_reference.py`, then animate it.
This is the recommended two-step path whenever identity or exact framing matters.

---

## 4. Subject Definition

Define subjects using 2–3 stable, distinctive features so they stay consistent across shots.

### Single subject
```
The subject is a woman in a mustard trench coat with short curly hair — call her <Subject1>.
```

### Multiple subjects
```
Define the tall man in a navy pinstripe suit as <Subject1>.
Define the woman in a white lab coat with wire-rimmed glasses as <Subject2>.
```

### Rules
- Repeat the subject tag (`<Subject1>`) every time the character appears — never omit it
- Use **static** features (outfit, hair, species) — not dynamic ones (expression, pose)
- When animating from a reference image (`scripts/generate_video_from_reference.py`), the image is the identity
  anchor — describe what the subject *does*, not what they look like (the model already sees it)

---

## 5. Shot-by-Shot Description

For each shot, apply the formula in order:

```
Shot N: [Camera angle + movement] Subject + action (limb-level detail).
Environmental detail. Aesthetic note.
```

**Example — 3-shot sequence:**
```
Shot 1: [EWS, drone descending slowly] A suspension bridge stretches across a river
at blue hour. Mist rises from the water. City lights glow on both banks.

Shot 2: [MS, dolly-in from behind] <Subject1> — man in a dark grey coat, silver
hair — walks toward the bridge railing. He stops and grips it with both hands.

Shot 3: [CU, static] His face in profile against the city lights below.
Wind moves his hair slightly. He exhales slowly — breath faintly visible.
```

---

## 6. Text Generation in Video

The model can generate readable on-screen text. Use common characters — avoid rare glyphs
and special symbols for best rendering accuracy.

### 6.1 Slogans / Title Cards

Formula: `[text content] + [timing] + [position] + [text style]`

```
Shot 3: [static, WS] The product sits on the surface.
After 2 seconds, bold white sans-serif text appears at centre frame: "Engineered for Life."
Text fades in gently. Clean, minimal aesthetic.
```

### 6.2 Speech Bubble Dialogue (no audio required)

Speech bubbles are visual, not audio — usable even when `generate_audio: false`:
```
<Subject1> smiles and turns to <Subject2>: {You're late — again.}
A speech bubble appears beside <Subject1>.
<Subject2> shrugs and replies: {But I brought coffee.}
A speech bubble appears beside <Subject2>.
```

### 6.3 Text Style Notes
- Specify colour, weight, position if needed: `bold crimson serif text anchored to the lower left`
- For logo-quality consistency, supply the logo as a reference image
- To suppress all text output: add `no subtitles, no on-screen text` to negative constraints

---

## 7. Multi-Segment Stitching (Videos Longer Than Config Max)

`video_duration_max` in `config.json` caps a single clip. Chain segments for longer videos.

### Workflow
1. **Segment 1**: Generate normally with `scripts/generate_video_from_text.py`. End on a clean handoff frame —
   stable pose, clear composition, no motion blur at the cut point. Save the last frame as an
   image (e.g. with `scripts/generate_image_from_reference.py` or a frame grab) if you need it as the next segment's
   first-frame anchor.
2. **Segment 2**: Feed that frame into `scripts/generate_video_from_reference.py` as `--img`, with a prompt describing
   what happens next. Note continuity explicitly:
   ```
   Continuity: opens on <Subject1> [exact pose/position matching the handoff frame].
   ```
3. Repeat for each additional segment.

### Fix for join stutters
After stitching with ffmpeg or similar:
- Delete **last 6 frames** of each preceding clip
- Delete **first 1 frame** of each following clip
- Re-stitch and verify smoothness

### Planning tip
End each segment on a scene transition (whip pan, cut to black, door opening) so that
join points feel intentional even if minor frame variance remains.

---

## 8. Dialogue & TTS Formatting (requires `generate_audio: true`)

```
Dialogue (<CharacterName>, <emotion>): {line here}
```

Examples:
```
Dialogue (Subject1, curious): {Do you think anyone's actually been up there?}
Dialogue (Subject2, dry): {Based on the state of this place — I doubt it.}
Voiceover (warm female narrator, contemplative): {The city keeps its secrets well.}
```

Rules:
- Keep lines short — one line per 3–5s of the segment
- Dialogue language must stay consistent — no mid-sentence language mixing
- Non-English: `say in Korean {어디 가세요?}` or `say in French {Bonsoir}`

---

## 9. Audio Layering (requires `generate_audio: true`)

Three audio layers can coexist in any shot:

```
(slow acoustic guitar plays in the background)       ← background music, always in ()
<elevator doors sliding open>                        ← sound effect, always in <>
Dialogue (Subject1, relieved): {Made it.}            ← TTS dialogue, always in {}
```

---

## 10. Video Editing (via `scripts/generate_video_from_reference.py`)

The image-to-video call also supports element-level edits when the "first frame" is itself
the thing you want changed:

### Add an element
```
In the reference image, add [a half-eaten croissant on the desk beside the keyboard],
then continue the motion described below. Keep all other scene elements unchanged.
```

### Replace an element
```
Replace the glass bottle in the reference image with a ceramic mug, then continue
the motion described below. Preserve all other scene elements.
```

---

## 11. Multi-Image Reference Patterns

### Multi-angle product (image generation)
```
Product rotates on a white surface showing front, side, and back.
Studio overhead lighting. No shadows. Clean white background.
no watermark, no logo, no subtitles
```

### Fixed logo overlay
```
The logo is displayed in the lower-right corner of every frame throughout the video.
Keep the logo position fixed, legible, and unobstructed. Do not animate the logo.
```

---

## 12. Batch Prompts with `scripts/generate_image_from_text.py`

`scripts/generate_image_from_text.py` treats **every non-empty line** in the prompt file as a separate image
request — it will generate one image per line and number the outputs. This is useful for
generating prompt variations or a batch of concept options in one call, but it means:

- Each line must be a complete, self-contained one-line prompt (no multi-line shot blocks)
- Do not use this file for structured video prompts — those go through `scripts/generate_video_from_text.py` /
  `scripts/generate_video_from_reference.py` / `scripts/generate_image_from_reference.py`, which read the whole file as one prompt

---

## 13. Scenario Strategies

### E-Commerce / Product Ad
- Generate the product image first (`scripts/generate_image_from_text.py` or `scripts/generate_image_from_reference.py`), then animate it
  with `scripts/generate_video_from_reference.py` so identity/framing stay locked
- Techniques: 360° orbit, 3D exploded view, hero lighting, lifestyle context
- Specify material: `glass refractions`, `metallic sheen`, `matte fabric texture`

**Example** (image-to-video prompt, product already in the reference frame):
```
3D CG realistic render, studio lighting.
Shot 1: [slow 180° arc, low angle] Camera orbits the headphones.
Cable coil and driver housing stay sharp throughout.
Shot 2: [WS, pull-back] Surface is revealed as a music production desk.

no watermark, no logo, no subtitles, no on-screen text
```

### Short Drama / Short-Form Content
- Write visuals as clean shot blocks; add dialogue only if `generate_audio: true`
- Keep each shot 3–5s for a natural editing pace within the config's duration budget
- Use varied camera angles (MCU, OTS, WS) within one clip
- Use `no subtitles` unless subtitles are intentionally part of the content

### Action / Fantasy
- Declare art style explicitly at the top and reinforce every 2–3 shots
- Use: `energy particle effects`, `slow-motion impact frame`, `speed lines`
- Pair with dramatic low angles and crane moves

### One-Take Tracking Shot
- Write one continuous camera movement visiting each waypoint in order
- Include: `no cuts, single continuous take, smooth camera throughout`

---

## 14. Negative Constraints

### Standard minimum (always include)
```
no watermark, no logo, no subtitles, no on-screen text
```
(Redundant with `watermark: false` in `config.json`, but reinforcing it in-prompt reduces
edge cases — see `common-issues.md` V-3.)

### Add based on content
```
no duplicate characters, no twin subjects              ← V-7: twin character issue
no style drift, maintain [style] throughout             ← V-4: style drift
no flicker, no horizontal banding                        ← V-5: flicker issue
no subtitles, no captions, subtitle-free                 ← V-2: unwanted subtitle
```

---

## 15. Language Rules

- Write prompts in English for best international compatibility
- Dialogue language must be consistent within a scene — no mid-sentence language switching
- For foreign language TTS, always specify: `say in [language] {text}`
- **Never use `--` in prompts** — everything after it is silently dropped by the model

---

## 16. Special Format Characters

| Content | Symbol | Example | Requires `generate_audio: true`? |
|---|---|---|---|
| Background music | `()` | `(upbeat funk guitar loop)` | Yes |
| Sound effects | `<>` | `<rain on a tin roof>` | Yes |
| Dialogue / TTS | `{}` | `{We leave at dawn.}` | Yes |
| Speech bubble text | `{}` (with "speech bubble appears") | see §6.2 | No — visual only |
| On-screen caption | `【】` | `【Day 3 — The Crossing】` | No — visual only |

---

## 17. IP / Moderation Safety

- Never use franchise names, character names, or brand terms
- Replace recognisable features with original descriptors, e.g. a famous armoured
  superhero's glowing chest device → `"crystalline energy core embedded in the chest plate"`
- Add explicit negative constraints for any inferable IP terms
- If rejected, escalate: rename → redesign signature features → change character type entirely

---

## 18. Visual Styles

See `styles.md` for the full style library — descriptors, camera defaults, negative
constraints, and complete example prompts for each style in `config.json`'s `styles` list.
