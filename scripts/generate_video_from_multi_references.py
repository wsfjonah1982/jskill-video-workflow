import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from ark_service import ArkVideoService, download_file, file_to_data_url

# Allow Unicode output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR        = Path(__file__).resolve().parent.parent  # skill root — credential.json/config.json live here, not in scripts/
CREDENTIAL_PATH = BASE_DIR / "credential.json"
CONFIG_PATH     = BASE_DIR / "config.json"
LOG_DIR         = BASE_DIR / "_log"
OUTPUT_PATH     = BASE_DIR / "_output" / "output_video.mp4"


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    return read_json(CONFIG_PATH)


def load_api_key() -> str:
    env_key = os.environ.get("ARK_API_KEY")
    if env_key:
        return env_key
    if not CREDENTIAL_PATH.exists():
        raise FileNotFoundError(
            f"ARK_API_KEY env var not set, and credential file not found: {CREDENTIAL_PATH}"
        )
    cred = read_json(CREDENTIAL_PATH)
    api_key = cred.get("model_ark_key")
    if not api_key:
        raise KeyError("ARK_API_KEY env var not set and `model_ark_key` missing in credential.json")
    return api_key


def write_log(log_path: Path, data: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a video from multiple reference images (e.g. a subject identity "
                    "shot plus a separate scene/background shot) and a text prompt — Seedance's "
                    "All-Reference mode. For a single reference image, use "
                    "generate_video_from_reference.py instead."
    )
    parser.add_argument("--img",    required=True, nargs="+", help="Two or more input image file paths, in the order they should be referenced (@image1, @image2, ...)")
    parser.add_argument("--prompt", required=True, help="Path to prompt text file")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output video file path (e.g. out.mp4)")
    args = parser.parse_args()

    image_paths = [Path(p) for p in args.img]
    prompt_path = Path(args.prompt)
    output_path = Path(args.output)
    log_path    = LOG_DIR / f"{output_path.name}.log"

    if len(image_paths) < 2:
        print("Error: --img needs at least two images for this script — use "
              "generate_video_from_reference.py for a single reference image", file=sys.stderr)
        return 1
    missing = [p for p in image_paths if not p.exists()]
    if missing:
        print(f"Error: input image(s) not found: {', '.join(str(p) for p in missing)}", file=sys.stderr)
        return 1
    if not prompt_path.exists():
        print(f"Error: prompt file not found: {prompt_path}", file=sys.stderr)
        return 1

    prompt = prompt_path.read_text(encoding="utf-8").strip()
    if not prompt:
        print(f"Error: prompt file is empty: {prompt_path}", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)

    t_start = time.monotonic()
    log: dict = {
        "timestamp":  datetime.now(timezone.utc).isoformat(),
        "images":     [str(p) for p in image_paths],
        "prompt":     prompt,
        "output":     str(output_path),
    }

    try:
        config           = load_config()
        model_id         = config["video_model_id"]
        duration_seconds = config["video_duration_seconds"]
        ratio            = config["video_ratio"]
        resolution       = config["video_resolution"]
        generate_audio   = config.get("generate_audio", False)
        watermark        = config.get("watermark", False)
        base_url         = config["maas_api_endpoint"]
        poll_interval_s  = config.get("poll_interval_seconds", 15)
        max_polls        = config.get("max_polls", 120)
        # Multi-image "All-Reference" mode isn't anchored to one first-frame image the way
        # single-reference generation is (see V-0 in references/common-issues.md, where the API
        # rejects an explicit ratio for that mode), so this passes config.json's video_ratio
        # through — unverified against a live call as of writing. If the API rejects it the
        # same way, this needs the same ratio=None fix as generate_video_from_reference.py.

        log.update({
            "model":          model_id,
            "duration_s":     duration_seconds,
            "ratio":          ratio,
            "resolution":     resolution,
            "generate_audio": generate_audio,
        })

        print(f"Input images ({len(image_paths)}): {', '.join(str(p) for p in image_paths)}", file=sys.stderr)
        print(f"Prompt file: {prompt_path}", file=sys.stderr)
        print(f"Prompt: {prompt}", file=sys.stderr)
        print(f"Model: {model_id}  Duration: {duration_seconds}s  Ratio: {ratio}  "
              f"Resolution: {resolution}  Audio: {generate_audio}", file=sys.stderr)
        print(f"Output: {output_path}\n", file=sys.stderr)

        api_key = load_api_key()
        service = ArkVideoService(base_url=base_url, api_key=api_key)
        content = [
            {"type": "image_url", "image_url": {"url": file_to_data_url(p)}}
            for p in image_paths
        ] + [{"type": "text", "text": prompt}]

        task_id, submit_request_id = service.create_task(
            model_id=model_id, content=content,
            duration_seconds=duration_seconds, ratio=ratio, resolution=resolution,
            generate_audio=generate_audio, watermark=watermark,
        )
        log["task_id"] = task_id

        video_url, metrics = service.wait_for_video(task_id, duration_seconds, poll_interval_s, max_polls)

        dl_s    = download_file(video_url, output_path)
        total_s = round(time.monotonic() - t_start, 2)

        print(f"Saved: {output_path}  ({total_s}s, download {dl_s:.1f}s)", file=sys.stderr)

        log.update({
            "ttft_s":       metrics["ttft_s"],
            "generation_s": metrics["generation_s"],
            "tpot_s":       metrics["tpot_s"],
            "download_s":   round(dl_s, 2),
            "total_s":      total_s,
            "video_url":    video_url,
            "status":       "succeeded",
        })
        write_log(log_path, log)

        print(str(output_path))
        return 0

    except Exception as exc:
        log.update({"status": "failed", "error": str(exc), "total_s": round(time.monotonic() - t_start, 2)})
        write_log(log_path, log)
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
