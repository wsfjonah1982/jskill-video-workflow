import argparse
import os
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from ark_service import ArkVideoService, download_file

# Allow Unicode output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR        = Path(__file__).resolve().parent.parent  # skill root — credential.json/config.json live here, not in scripts/
CREDENTIAL_PATH = BASE_DIR / "credential.json"
CONFIG_PATH     = BASE_DIR / "config.json"
LOG_DIR         = BASE_DIR / "_log"
PROMPT_PATH     = BASE_DIR / "_log" / "script.txt"
OUTPUT_PATH     = BASE_DIR / "_output" / "output_video.mp4"


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    return read_json(CONFIG_PATH)


def read_prompt(path: Path) -> str:
    prompt = path.read_text(encoding="utf-8").strip()
    if not prompt:
        raise ValueError(f"Prompt file is empty: {path}")
    return prompt


def load_api_key() -> str:
    env_key = os.environ.get("model_ark_key")
    if env_key:
        return env_key
    if not CREDENTIAL_PATH.exists():
        raise FileNotFoundError(
            f"model_ark_key env var not set, and credential file not found: {CREDENTIAL_PATH}"
        )
    cred = read_json(CREDENTIAL_PATH)
    api_key = cred.get("model_ark_key")
    if not api_key:
        raise KeyError("model_ark_key env var not set and `model_ark_key` missing in credential.json")
    return api_key


def write_log(log_path: Path, data: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", default=str(PROMPT_PATH), help="Path to prompt text file")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Path for output .mp4")
    args = parser.parse_args()

    prompt_path = Path(args.prompt)
    output_path = Path(args.output)
    log_path    = LOG_DIR / f"{output_path.name}.log"

    t_start = time.monotonic()
    log: dict = {
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "script":      str(prompt_path),
        "output":      str(output_path),
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

        log.update({
            "model":          model_id,
            "duration_s":     duration_seconds,
            "ratio":          ratio,
            "resolution":     resolution,
            "generate_audio": generate_audio,
        })

        api_key = load_api_key()
        prompt  = read_prompt(prompt_path)
        service = ArkVideoService(base_url=base_url, api_key=api_key)
        log["prompt_chars"] = len(prompt)

        print(f"Prompt: {prompt_path} ({len(prompt)} chars)", file=sys.stderr)

        task_id, submit_request_id = service.create_task(
            model_id=model_id, content=[{"type": "text", "text": prompt}],
            duration_seconds=duration_seconds, ratio=ratio, resolution=resolution,
            generate_audio=generate_audio, watermark=watermark,
        )
        log["task_id"]          = task_id
        log["submit_request_id"] = submit_request_id

        video_url, metrics = service.wait_for_video(task_id, duration_seconds, poll_interval_s, max_polls)
        print(f"Video URL: {video_url}", file=sys.stderr)

        dl_s = download_file(video_url, output_path)
        total_s = time.monotonic() - t_start

        print(f"Saved: {output_path}  ({total_s:.1f}s, download {dl_s:.1f}s)", file=sys.stderr)

        log.update({
            "ttft_s":            metrics["ttft_s"],
            "generation_s":      metrics["generation_s"],
            "tpot_s_per_s":      metrics["tpot_s"],
            "download_s":        round(dl_s, 2),
            "total_s":           round(total_s, 2),
            "usage":             metrics["usage"],
            "result_request_id": metrics["request_id"],
            "status":            "succeeded",
        })

        write_log(log_path, log)
        print(str(output_path))
        return 0

    except Exception as exc:
        log["status"] = "failed"
        log["error"]  = str(exc)
        log["total_s"] = round(time.monotonic() - t_start, 2)
        write_log(log_path, log)
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
