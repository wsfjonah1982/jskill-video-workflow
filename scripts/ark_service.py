"""Ark REST API clients — chat completions, image generation, video generation.

Adapted from jonah-simple-video-flow's service/ark_service.py: plain HTTP calls via
`requests`, not the byteplussdkarkruntime SDK. That SDK's PyPI package name couldn't be
verified/installed reliably, so this skill's scripts talk to the Ark API directly instead —
same request/response shape jonah-simple-video-flow already uses in production.
"""
import base64
import sys
import time
import urllib.request
from pathlib import Path

import requests


def extract_token_usage(usage: dict | None) -> dict:
    """Normalizes an Ark API `usage` dict into {tokens_in, tokens_out, tokens_total} for
    logging. Different endpoints use different key names — chat completions use
    prompt_tokens/completion_tokens, image generation uses input_images/output_tokens (verified
    live: {"input_images": 0, "generated_images": 1, "output_tokens": 16384, "total_tokens":
    16384} — no prompt_tokens/completion_tokens at all). Missing values are None, not 0, so a
    genuine zero-token value is never confused with "not reported"."""
    usage = usage or {}
    tokens_in = usage.get("prompt_tokens")
    if tokens_in is None:
        tokens_in = usage.get("input_tokens")
    tokens_out = usage.get("completion_tokens")
    if tokens_out is None:
        tokens_out = usage.get("output_tokens")
    return {
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tokens_total": usage.get("total_tokens"),
    }


def guess_mime_from_path(path) -> str:
    ext = str(path).rsplit(".", 1)[-1].lower() if "." in str(path) else ""
    if ext in ("jpg", "jpeg"):
        return "image/jpeg"
    if ext == "png":
        return "image/png"
    if ext == "gif":
        return "image/gif"
    if ext == "webp":
        return "image/webp"
    return "application/octet-stream"


def file_to_data_url(path) -> str:
    path = Path(path)
    data = path.read_bytes()
    mime = guess_mime_from_path(path)
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def download_file(url: str, output_path) -> float:
    """Downloads file and returns elapsed seconds."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    with urllib.request.urlopen(url) as resp, output_path.open("wb") as f:
        f.write(resp.read())
    return time.monotonic() - t0


class ArkChatService:
    """Text chat-completions client (e.g. Deepseek models) for writing scripts and prompts."""

    def __init__(self, base_url: str, api_key: str):
        self._url = base_url.rstrip('/') + '/chat/completions'
        self._headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }

    def complete(self, model_id: str, system_prompt: str, user_prompt: str,
                 image_data_urls: list[str] | None = None) -> tuple[str, dict]:
        """Returns (text, usage) — usage is the Ark API's token-usage dict (prompt_tokens,
        completion_tokens, total_tokens), or {} if the response didn't include one."""
        print(f"Chat completion: model={model_id} system_len={len(system_prompt)} "
              f"user_len={len(user_prompt)} images={len(image_data_urls or [])}", file=sys.stderr)

        if image_data_urls:
            user_content = [{"type": "text", "text": user_prompt}] + [
                {"type": "image_url", "image_url": {"url": url}} for url in image_data_urls
            ]
        else:
            user_content = user_prompt

        payload = {
            'model': model_id,
            'messages': [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            'stream': False,
        }
        resp = requests.post(self._url, headers=self._headers, json=payload, timeout=120)
        if resp.status_code != 200:
            raise RuntimeError(f"Ark API error {resp.status_code}: {resp.text}")
        data = resp.json()

        choices = data.get('choices') or []
        if not choices:
            raise RuntimeError(f"Chat completion returned no choices: {data}")
        text = (choices[0].get('message') or {}).get('content', '').strip()
        usage = data.get('usage') or {}
        print(f"Chat completion done: result_len={len(text)} "
              f"tokens_in={usage.get('prompt_tokens')} tokens_out={usage.get('completion_tokens')}", file=sys.stderr)
        return text, usage


class ArkImageService:
    """Seedream image generation/edit client."""

    def __init__(self, base_url: str, api_key: str):
        self._url = base_url.rstrip('/') + '/images/generations'
        self._headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }

    def generate_image(self, model_id: str, prompt: str, image: list[str] | str | None = None,
                        size: str | None = None, watermark: bool | None = None) -> tuple[list[dict], dict]:
        """Returns (images, usage) — usage is the Ark API's token-usage dict, if the response
        included one (image models are not always token-billed), or {} otherwise."""
        img_count = len(image) if isinstance(image, list) else (1 if image else 0)
        print(f"Image generation: model={model_id} prompt_len={len(prompt)} images={img_count} "
              f"size={size} watermark={watermark}", file=sys.stderr)

        payload = {
            'model': model_id,
            'prompt': prompt,
            'response_format': 'url',
        }
        if image:
            payload['image'] = image
        if size is not None:
            payload['size'] = size
        if watermark is not None:
            payload['watermark'] = watermark

        resp = requests.post(self._url, headers=self._headers, json=payload, timeout=300)
        if resp.status_code != 200:
            raise RuntimeError(f"Ark API error {resp.status_code}: {resp.text}")
        data = resp.json()

        images = [
            {'url': img.get('url'), 'b64_json': img.get('b64_json')}
            for img in (data.get('data') or [])
        ]
        usage = data.get('usage') or {}
        print(f"Image generation done: count={len(images)} usage={usage}", file=sys.stderr)
        return images, usage


class ArkVideoService:
    """Seedance video generation client — create a task, then poll until it succeeds."""

    def __init__(self, base_url: str, api_key: str):
        self._url = base_url.rstrip('/') + '/contents/generations/tasks'
        self._headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }

    def create_task(self, model_id: str, content: list, duration_seconds: int, ratio: str | None,
                     resolution: str, generate_audio: bool, watermark: bool) -> tuple[str, str | None]:
        # For first-frame/first-last-frame generation (an image_url in content), the API derives
        # the output ratio from the input image and rejects an explicit `ratio` — pass ratio=None
        # in that case. Text-only generation requires it.
        print(f"Video task create: model={model_id} duration={duration_seconds} ratio={ratio or '(follows input image)'} "
              f"resolution={resolution} generate_audio={generate_audio} watermark={watermark}", file=sys.stderr)
        payload = {
            'model': model_id,
            'content': content,
            'duration': duration_seconds,
            'resolution': resolution,
            'generate_audio': generate_audio,
            'watermark': watermark,
        }
        if ratio is not None:
            payload['ratio'] = ratio
        resp = requests.post(self._url, headers=self._headers, json=payload, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"Ark API error {resp.status_code}: {resp.text}")
        result = resp.json()
        task_id = result.get('id')
        request_id = result.get('request_id')
        if not task_id:
            raise RuntimeError(f"Task created but no id returned: {result}")
        print(f"Video task created: {task_id}", file=sys.stderr)
        return task_id, request_id

    def _get_task(self, task_id: str) -> dict:
        resp = requests.get(f"{self._url}/{task_id}", headers=self._headers, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Ark API error {resp.status_code}: {resp.text}")
        return resp.json()

    def wait_for_video(self, task_id: str, duration_seconds: int,
                        poll_interval_seconds: int = 15, max_polls: int = 120) -> tuple[str, dict]:
        """Returns (video_url, timing_and_usage_dict)."""
        t_submit = time.monotonic()
        t_running = None  # TTFT: time until task enters "running"

        for attempt in range(1, max_polls + 1):
            result = self._get_task(task_id)
            status = result.get('status')
            now = time.monotonic()
            print(f"[{attempt}/{max_polls}] status: {status}  elapsed: {now - t_submit:.1f}s", file=sys.stderr)

            if t_running is None and status == 'running':
                t_running = now

            if status == 'succeeded':
                t_succeeded = now
                content = result.get('content') or {}
                video_url = content.get('video_url')
                if not video_url:
                    raise RuntimeError(f"Task succeeded but no video_url: {result}")

                usage = result.get('usage') or {}
                ttft = (t_running - t_submit) if t_running else None
                gen_time = t_succeeded - (t_running or t_submit)
                metrics = {
                    "ttft_s": round(ttft, 2) if ttft is not None else None,
                    "generation_s": round(gen_time, 2),
                    "tpot_s": round(gen_time / duration_seconds, 2) if duration_seconds else None,
                    "usage": usage,
                    "request_id": result.get('request_id'),
                }
                return video_url, metrics

            if status in ('failed', 'expired'):
                error = result.get('error')
                raise RuntimeError(f"Video generation {status}: {error or result}")

            time.sleep(poll_interval_seconds)

        raise TimeoutError(
            f"Task did not finish after {max_polls * poll_interval_seconds}s. id: {task_id}"
        )
