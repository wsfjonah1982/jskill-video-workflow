import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from ark_service import ArkImageService, download_file, file_to_data_url, extract_token_usage

# Allow Unicode output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR        = Path(__file__).resolve().parent.parent  # skill root — credential.json/config.json live here, not in scripts/
CREDENTIAL_PATH = BASE_DIR / "credential.json"
CONFIG_PATH     = BASE_DIR / "config.json"
LOG_DIR         = BASE_DIR / "_project" / "log"
TEMPLATES_DIR   = Path(__file__).resolve().parent / "prompt_templates"
OUTPUT_PATH     = BASE_DIR / "_project" / "output" / "character_sheet.png"


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    return read_json(CONFIG_PATH)


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


def read_template(name: str) -> str:
    return (TEMPLATES_DIR / name).read_text(encoding="utf-8").strip()


def read_idea(path: Path) -> str:
    idea = path.read_text(encoding="utf-8").strip()
    if not idea:
        raise ValueError(f"Idea file is empty: {path}")
    return idea


def write_log(log_path: Path, data: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a character reference sheet (turnaround, three views, full body, "
                    "clean white background) from a subject description, using the fixed template "
                    "from jonah-simple-video-flow's prompts/reference_image_prompt.md — no chat "
                    "model call, deterministic prompt every time. With --img, one or more photos "
                    "anchor the subject's appearance/style instead of generating from the "
                    "description alone."
    )
    parser.add_argument("--idea",   required=True, help="Path to a .txt file describing the subject's appearance")
    parser.add_argument("--style",  default=None, help="Art style (defaults to config.json's default_style)")
    parser.add_argument("--img",    default=None, nargs="+", help="Optional reference photo(s) to anchor appearance/style")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output image file path")
    parser.add_argument("--log-dir", default=str(LOG_DIR), help="Directory for the .log JSON record (defaults to _project/log)")
    args = parser.parse_args()

    idea_path   = Path(args.idea)
    image_paths = [Path(p) for p in args.img] if args.img else []
    output_path = Path(args.output)
    log_path    = Path(args.log_dir) / f"{output_path.name}.log"

    if not idea_path.exists():
        print(f"Error: idea file not found: {idea_path}", file=sys.stderr)
        return 1
    missing = [p for p in image_paths if not p.exists()]
    if missing:
        print(f"Error: reference image(s) not found: {', '.join(str(p) for p in missing)}", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)

    t_start = time.monotonic()
    log: dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "idea_file": str(idea_path),
        "reference_images": [str(p) for p in image_paths],
        "output":    str(output_path),
    }

    try:
        config    = load_config()
        model_id  = config["image_model_id"]
        size      = config["image_size"]
        watermark = config.get("watermark", False)
        base_url  = config["maas_api_endpoint"]
        style     = args.style or config.get("default_style", "")
        idea      = read_idea(idea_path)

        prompt = read_template("reference_image_prompt.md").format(idea=idea)
        prompt = f"{prompt} Art style: {style}."
        log.update({"model": model_id, "style": style, "prompt": prompt})

        print(f"Idea: {idea_path} ({len(idea)} chars)  Style: {style}", file=sys.stderr)
        if image_paths:
            print(f"Reference image(s): {', '.join(str(p) for p in image_paths)}", file=sys.stderr)
        print(f"Prompt: {prompt}", file=sys.stderr)
        print(f"Model: {model_id}  Size: {size}", file=sys.stderr)
        print(f"Output: {output_path}\n", file=sys.stderr)

        api_key = load_api_key()
        service = ArkImageService(base_url=base_url, api_key=api_key)

        image = None
        if image_paths:
            image_data_urls = [file_to_data_url(p) for p in image_paths]
            image = image_data_urls[0] if len(image_data_urls) == 1 else image_data_urls

        print("Generating...", file=sys.stderr)
        images, usage = service.generate_image(model_id=model_id, prompt=prompt, image=image, size=size, watermark=watermark)
        image_url = images[0]["url"] if images else None
        if not image_url:
            raise RuntimeError("No image URL returned")

        dl_s    = download_file(image_url, output_path)
        total_s = round(time.monotonic() - t_start, 2)

        print(f"Saved: {output_path}  ({total_s}s, download {dl_s:.1f}s)", file=sys.stderr)

        log.update({
            "image_url": image_url,
            **extract_token_usage(usage),
            "usage": usage,
            "total_s": total_s,
            "download_s": round(dl_s, 2),
            "status": "succeeded",
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
