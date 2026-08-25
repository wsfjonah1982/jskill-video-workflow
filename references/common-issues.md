# Common Issues & Workarounds — Seedance 2.5 / Seedream 5.0

This file documents known generation issues, their causes, prompt-level fixes, and
post-production workarounds. Check this when a generation comes back wrong, or proactively
add the relevant negative constraint when a prompt's content matches a known risk pattern.

---

## V-0: `ratio` Rejected for Image-to-Video

**Symptom**: `scripts/generate_video_from_reference.py` fails immediately with
`400 InvalidParameter.TaskTypeConstraint — "For first-frame or first-last-frame generation,
the output ratio follows the first-frame image"`.

**Root cause**: For image-to-video (first-frame) generation, the API derives the output aspect
ratio from the input image and rejects an explicit `ratio` parameter entirely — this only
applies to text-to-video (`scripts/generate_video_from_text.py`), which does need `ratio` set.

**Fix**: Already handled in `scripts/ark_service.py`'s `ArkVideoService.create_task()` — pass
`ratio=None` for image-to-video and it's omitted from the payload. `config.json`'s `video_ratio`
therefore only controls `generate_video_from_text.py`'s output; for image-to-video, the ratio
is whatever the reference image was generated at (Seedream's default `2K` size renders 16:9,
matching this skill's `video_ratio` default anyway — but if you need a specific ratio from
image-to-video, control it via the reference image's generation, not `config.json`).

---

## V-1: Character ID Drift ("Face Swap" Mid-Video)

**Symptom**: Generated character looks different from the reference image, or the
face changes midway through the video.

**Root cause**: In `scripts/generate_video_from_reference.py`, the reference image doubles as full scene/identity
anchor — if it includes multiple people, busy background, or a small/unclear face, the model's
identity lock weakens.

### Prompt-level fix
```
The person's face and identity must remain strictly consistent with the reference image
throughout every shot. Do not alter facial structure, hair colour, or skin tone.
```

### Input preparation fix
- Prefer a reference image where the subject's face is clear, well-lit, and reasonably large
  in frame — generate a clean portrait or product shot first with `scripts/generate_image_from_text.py`/
  `scripts/generate_image_from_reference.py` before animating it
- If a full-body pose is also needed, describe it in the prompt rather than relying on a busy
  reference image with multiple crops

### What to tell the user
> Generate a clean, well-lit reference image first (crop tightly on the subject) and use
> that as the first frame — a clearer reference image is the biggest lever for identity
> consistency.

---

## V-2: Unwanted Subtitles Generated

**Symptom**: Generated video contains subtitles or on-screen text that wasn't requested,
often with errors or wrong language.

**Root cause**: Model trained on subtitle-heavy video data; vertical (9:16) `video_ratio`
significantly increases subtitle probability.

### Prompt-level fix (reduces probability by ~50–70%)
Add to negative constraints:
```
no subtitles, no on-screen text, no captions, subtitle-free
```

### Config fix (most effective)
- Switch `video_ratio` in `config.json` from `9:16` (vertical) to `16:9` (horizontal) —
  drops subtitle rate to <10%. Crop to vertical in post-production if a vertical final export
  is still needed.

### What to tell the user
> There's no 100% guarantee of subtitle-free output — only probability reduction. Use 16:9
> in `config.json` and add "no subtitles, no on-screen text" to the prompt. If subtitles
> still appear, try regenerating (re-roll) or use a subtitle removal tool in post.

---

## V-3: Unwanted Platform Logos / Watermarks

**Symptom**: Generated video contains logos from video platforms that weren't requested.

**Root cause**: Model trained on watermarked platform content; can inherit watermarks
from reference images/videos that already contain them.

### Prompt-level fix
```
no watermark, no logo, no platform branding, no copyright marks
```

### Config fix
- `watermark: false` in `config.json` is already the default for every generation script —
  verify it hasn't been flipped to `true` before assuming this is a prompt-level bug.

### Input fix
- Check reference images for existing platform watermarks and remove before uploading

---

## V-4: Style Drift (Animation → Realistic)

**Symptom**: Prompt asks for 2D anime or 3D CG animation style, but generated video
partially or fully drifts to live-action realistic style.

**Root cause**: Reference images are too photorealistic, or the style isn't reinforced
per shot in a multi-shot prompt.

### Prompt-level fix
Explicitly state the art style and reinforce it per shot:
```
2D Japanese anime style throughout. Maintain flat cel-shading, bold outlines,
no photorealism, no live-action aesthetics.
```

### Input fix
- If animating from a reference image (`scripts/generate_video_from_reference.py`), generate that image in the
  target art style first (via `scripts/generate_image_from_text.py`) rather than using a photorealistic photo

---

## V-5: Periodic Flickering / Horizontal Banding

**Symptom**: Regularly repeating flicker or horizontal stripes across the entire video,
especially visible in large flat colour areas.

**Root cause**: Platform-side watermarking/encoding artifact, model-version dependent.

### Workaround
- Regenerate — this is usually version-specific and intermittent
- If persistent, check whether a newer `video_model_id` is available and update `config.json`

---

## V-6: Video Extension / Multi-Segment Join Stutters

**Symptom**: When multiple segments are stitched together (see `best-practices.md` §7),
there is a visible jump, stutter, or content regression at each join point.

**Root cause**: The first and last frames of adjacent segments overlap slightly, causing a
double-frame or rollback effect when concatenated directly.

### Post-production fix (frame alignment)
1. Import all segments into editing software (CapCut / Premiere / DaVinci Resolve)
2. At each join point:
   - Delete the **last 6 frames** of the preceding clip
   - Delete the **first 1 frame** of the following clip
3. Repeat for all join points, export, and verify smoothness

### Prompt-level prevention
End each segment at a scene cut or transition:
```
Segment 1 ends: [whip pan left] — cut to black.
Segment 2 begins: [fade in] new scene — living room, daytime.
```

---

## V-7: Duplicate / Twin Characters

**Symptom**: Two identical-looking characters appear in the same frame when only
one was intended.

**Root cause**: Model can interpret ambiguous subject descriptions, or a reference image with
multiple angles/crops of the same character, as multiple distinct characters.

### Prompt-level fix
Add to end of prompt:
```
Throughout the entire video, there must be exactly one instance of <Subject1>
visible at any time. Do not duplicate, clone, or mirror any character.
No twin subjects, no split-screen doubles, no identical characters in the same frame.
```

### Character naming fix
When multiple characters exist, label each one clearly at every mention:
```
Subject1 (CEO) enters from the left.
Subject2 (assistant) stands at the desk.
```

---

## A-1: Audio Click / Pop at Video End (only relevant if `generate_audio: true`)

**Symptom**: A sudden "click", "pop", or audio cutoff sound at the very end of
the generated video. More common in videos with TTS narration.

**Root cause**: Audio track is being hard-cut at the generation boundary.

### Prompt-level mitigation
Avoid ending a sentence at the very last moment of the clip:
```
Voiceover finishes: {line here.} — followed by 1s ambient silence before clip ends.
```

### Post-production fix (CapCut / Premiere)
1. Select the audio track
2. Add a keyframe ~0.5s before the end, drag it to 0 dB (silence) — creates a fade-out ramp
3. Export

---

## Quick Reference Table

| Code | Issue | Quick fix |
|---|---|---|
| V-0 | `ratio` rejected on image-to-video | Already fixed in `ark_service.py` — `generate_video_from_reference.py` omits `ratio`, output follows the input image |
| V-1 | Character face changes | Use a clean, well-lit, tightly-cropped reference image as the first frame |
| V-2 | Unwanted subtitles | Add "no subtitles" to prompt; set `video_ratio: "16:9"` in config |
| V-3 | Platform logos/watermarks | Add "no watermark, no logo" to prompt; confirm `watermark: false` in config |
| V-4 | Style drifts to realistic | State art style explicitly per shot; use style-matched reference images |
| V-5 | Periodic flickering | Platform-side — regenerate; check for a newer `video_model_id` |
| V-6 | Stutter at clip joins | Trim last 6 frames of clip A + first 1 frame of clip B |
| V-7 | Duplicate characters | Add "exactly one instance" constraint; label characters clearly |
| A-1 | Audio click at end | Fade audio to 0 in last 0.5s using editing software (audio only) |
