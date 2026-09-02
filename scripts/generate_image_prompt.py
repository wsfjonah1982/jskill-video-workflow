import argparse
import os
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from ark_service import ArkChatService

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
OUTPUT_PATH     = BASE_DIR / "_project" / "prompt" / "image_prompt.txt"


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
        description="Write an image-generation prompt from a topic/idea. Uses a chat model "
                    "(e.g. Deepseek) unless --img is given, in which case the reference photo "
                    "already carries the subject's appearance and a plain turnaround template "
                    "is used instead (no LLM call)."
    )
    parser.add_argument("--idea",   required=True, help="Path to a .txt file with the topic/idea")
    parser.add_argument("--style",  default=None, help="Art style (defaults to config.json's default_style)")
    parser.add_argument("--img",    default=None, help="Optional reference photo — if given, skips the LLM call")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output .txt file path for the generated prompt")
    parser.add_argument("--log-dir", default=str(LOG_DIR), help="Directory for the .log JSON record (defaults to _project/log)")
    args = parser.parse_args()

    idea_path   = Path(args.idea)
    output_path = Path(args.output)
    log_path    = Path(args.log_dir) / f"{output_path.name}.log"

    if not idea_path.exists():
        print(f"Error: idea file not found: {idea_path}", file=sys.stderr)
        return 1
    if args.img and not Path(args.img).exists():
        print(f"Error: reference image not found: {args.img}", file=sys.stderr)
        return 1

    t_start = time.monotonic()
    log: dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "idea_file": str(idea_path),
        "output":    str(output_path),
        "has_reference_image": bool(args.img),
    }

    try:
        config   = load_config()
        style    = args.style or config.get("default_style", "")
        idea     = read_idea(idea_path)
        log["style"] = style

        if args.img:
            # The reference photo carries the subject's appearance directly — skip the LLM
            # and use a plain turnaround template, same as jonah-simple-video-flow does when
            # an input photo is present.
            print(f"Reference image given ({args.img}) — using template, no LLM call", file=sys.stderr)
            prompt_text = read_template("reference_image_prompt.md").format(idea=idea)
            log["model"] = None
        else:
            model_id = config["chat_model_id"]
            base_url = config["maas_api_endpoint"]
            log["model"] = model_id

            api_key = load_api_key()
            service = ArkChatService(base_url=base_url, api_key=api_key)

            print(f"Idea: {idea_path} ({len(idea)} chars)  Style: {style}", file=sys.stderr)
            print(f"Model: {model_id}", file=sys.stderr)

            system_prompt = read_template("image_prompt_system.md")
            user_prompt   = read_template("image_prompt_user.md").format(idea=idea, style=style)
            prompt_text   = service.complete(model_id=model_id, system_prompt=system_prompt, user_prompt=user_prompt)

        prompt_text = f"{prompt_text} Art style: {style}."

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(prompt_text, encoding="utf-8")

        total_s = round(time.monotonic() - t_start, 2)
        print(f"Saved: {output_path}  ({total_s}s)", file=sys.stderr)

        log.update({"prompt_chars": len(prompt_text), "total_s": total_s, "status": "succeeded"})
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
