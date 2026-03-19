#!/usr/bin/env python3
"""
Full refresh of README.md (English) and README.ja.md (Japanese) for all code4fukui repos.
- Regenerates even if README files already exist
- Uses AWS Bedrock Claude Haiku
- Writes locally only, never pushes
"""

import base64
import io
import json
import logging
import os
import random
import re
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3

REPOS_DIR = Path.home() / "code4fukui"
MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
REGION = "us-east-1"
MAX_WORKERS = int(os.getenv("README_MAX_WORKERS", "3"))
SLEEP_BETWEEN = float(os.getenv("README_SLEEP_BETWEEN", "1.0"))
THROTTLE_JITTER = float(os.getenv("README_THROTTLE_JITTER", "1.0"))
LOG_FILE = Path.home() / "generate_readmes_full.log"

MAX_TOTAL_BYTES = 80000

SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".woff", ".ttf", ".eot",
    ".mp3", ".mp4", ".wav",
    ".zip", ".tar", ".gz",
    ".bin", ".wasm", ".lock", ".pdf",
}
SKIP_DIRS = {"node_modules", "dist", ".git", ".vscode", "__pycache__"}

# Vision support
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".avi", ".mkv"}
MAX_IMAGES_PER_REPO = 3
_SKIP_IMAGE_NAME = re.compile(r"favicon|\bicon\b|\blogo\b|badge|banner", re.IGNORECASE)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger(__name__)
bedrock = boto3.client("bedrock-runtime", region_name=REGION)


def _encode_image(fpath: Path) -> str | None:
    """Return base64-encoded image resized to max 1024px, or None on failure."""
    try:
        from PIL import Image
        img = Image.open(fpath).convert("RGB")
        img.thumbnail((1024, 1024))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=75)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


def _extract_video_frame(fpath: Path) -> str | None:
    """Extract a single keyframe from a video using ffmpeg."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        subprocess.run(
            ["ffmpeg", "-i", str(fpath), "-ss", "00:00:03", "-frames:v", "1",
             str(tmp_path), "-y"],
            capture_output=True, timeout=15,
        )
        data = tmp_path.read_bytes()
        tmp_path.unlink(missing_ok=True)
        return base64.b64encode(data).decode() if data else None
    except Exception:
        return None


def collect_repo_images(repo_path: Path) -> list[dict]:
    """Find up to MAX_IMAGES_PER_REPO representative screenshots/frames."""
    # Priority: known screenshot dirs first, then root, then anywhere
    priority_dirs = ["screenshots", "screenshot", "docs", "assets", "images", "img"]

    candidates = []
    for fpath in repo_path.rglob("*"):
        if not fpath.is_file():
            continue
        rel_parts = fpath.parts[len(repo_path.parts):]
        if any(p in SKIP_DIRS for p in rel_parts):
            continue
        ext = fpath.suffix.lower()
        if ext not in IMAGE_EXTENSIONS and ext not in VIDEO_EXTENSIONS:
            continue
        if _SKIP_IMAGE_NAME.search(fpath.stem):
            continue
        try:
            size = fpath.stat().st_size
        except Exception:
            continue
        if ext in IMAGE_EXTENSIONS and size < 5000:
            continue  # skip tiny decorative images
        rel_dir = str(fpath.parent.relative_to(repo_path)).lower()
        score = next((i for i, d in enumerate(priority_dirs) if rel_dir == d or rel_dir.startswith(d)), len(priority_dirs))
        candidates.append((score, -size, fpath, ext))

    candidates.sort()
    blocks = []
    for _, _, fpath, ext in candidates:
        if len(blocks) >= MAX_IMAGES_PER_REPO:
            break
        if ext in VIDEO_EXTENSIONS:
            data = _extract_video_frame(fpath)
            media = "image/jpeg"
        else:
            data = _encode_image(fpath)
            media = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                     "gif": "image/gif", "webp": "image/webp"}.get(ext.lstrip("."), "image/jpeg")
        if data:
            blocks.append({"type": "image", "source": {"type": "base64", "media_type": media, "data": data}})
    return blocks


def read_repo_context(repo_path: Path) -> str:
    def priority(p: Path) -> int:
        name = p.name.lower()
        ext = p.suffix.lower()
        if "readme" in name:
            return 0
        if name in ("package.json", "deno.json", "deno.jsonc", ".gitignore"):
            return 1
        if ext in (".yml", ".yaml"):
            return 2
        if ext in (".js", ".ts", ".py", ".rb", ".go", ".rs", ".sh"):
            return 3
        if ext in (".html", ".css", ".vue", ".svelte"):
            return 4
        if ext in (".csv", ".tsv"):
            return 9
        return 5

    def is_skipped(p: Path) -> bool:
        rel_parts = p.parts[len(repo_path.parts):]
        if any(part in SKIP_DIRS for part in rel_parts):
            return True
        if p.suffix.lower() in SKIP_EXTENSIONS:
            return True
        # Skip LICENSE files — the model should never copy the full license body
        if p.name.upper() in ("LICENSE", "LICENSE.MD", "LICENSE.TXT", "COPYING"):
            return True
        return False

    all_files = sorted(
        [p for p in repo_path.rglob("*") if p.is_file() and not is_skipped(p)],
        key=priority,
    )

    seen_csv_dirs = set()
    parts = []
    total = 0

    for fpath in all_files:
        ext = fpath.suffix.lower()
        if ext in (".csv", ".tsv"):
            parent = fpath.parent
            if parent in seen_csv_dirs:
                continue
            seen_csv_dirs.add(parent)
            max_bytes = 500
        else:
            max_bytes = 8000

        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")[:max_bytes]
            chunk = f"\n--- {fpath.relative_to(repo_path)} ---\n{content}"
            parts.append(chunk)
            total += len(chunk)
            if total >= MAX_TOTAL_BYTES:
                break
        except Exception:
            continue

    return "\n".join(parts)


def call_bedrock(prompt: str, images: list[dict] | None = None) -> str:
    # Build content: images first (visual context), then text prompt
    content: list[dict] = list(images) if images else []
    content.append({"type": "text", "text": prompt})
    for attempt in range(6):
        try:
            response = bedrock.invoke_model(
                modelId=MODEL_ID,
                body=json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 2200,
                        "messages": [{"role": "user", "content": content}],
                    }
                ),
            )
            return json.loads(response["body"].read())["content"][0]["text"].strip()
        except Exception as e:
            if "ThrottlingException" in str(e) and attempt < 5:
                wait = 2 ** attempt + 2 + random.random() * THROTTLE_JITTER
                log.warning("Throttled, retrying in %ss (attempt %s/6)", wait, attempt + 1)
                time.sleep(wait)
            else:
                raise


def build_prompt_english(repo_name: str, context: str, has_images: bool = False) -> str:
    img_note = "\nScreenshots of the project are included above — use them to describe the UI or output accurately." if has_images else ""
    return f"""You are a technical writer creating an English README.md for a Japanese open source project on GitHub.{img_note}

Repository name: {repo_name}

Repository context (file snippets):
{context}

Write a clean, accurate English README.md.

Hard rules:
- Use only facts grounded in the repository context.
- Never invent demo URLs, APIs, features, or file names.
- Never output placeholder text such as [Project Name] or template instructions.
- If no real demo URL is present, omit the Demo section.
- For the License section: write one short line only (e.g. "MIT License — see [LICENSE](LICENSE)."). Never paste the full license text.
- Output markdown only.

Preferred structure (use only relevant sections):
# <Project Name>
One or two sentence description.

## Demo
## Features
## Requirements
## Usage
## Data / API
## License
"""


def build_prompt_japanese(repo_name: str, context: str, has_images: bool = False) -> str:
    img_note = "\nリポジトリのスクリーンショットが上に添付されています。UIや出力結果を正確に説明するために活用してください。" if has_images else ""
    return f"""あなたは日本語のREADME.ja.mdを作成する技術ライターです。{img_note}

リポジトリ名: {repo_name}

リポジトリの内容（抜粋）:
{context}

正確で簡潔なREADME.ja.mdを作成してください。

必須ルール:
- リポジトリ内容に基づく事実のみを書く
- URLや機能を捏造しない
- [プロジェクト名] のようなテンプレート文言を出力しない
- デモURLが確認できない場合は「デモ」セクションを省略
- タイトル（#）は自然な日本語を優先（固有技術名は英語可）
- マークダウンのみ出力

推奨構成（該当するもののみ）:
# <プロジェクト名>
1〜2文の説明

## デモ
## 機能
## 必要環境
## 使い方
## データ・API
## ライセンス
"""


def has_template_artifact(text: str) -> bool:
    if re.search(r"\[Project Name\]|One or two sentence description|\[プロジェクト名\]", text):
        return True
    # Catch full inlined license body (model copied LICENSE file verbatim)
    if re.search(r"Permission is hereby granted, free of charge", text, re.IGNORECASE):
        return True
    return False


def generate_with_validation(prompt: str, lang: str, images: list[dict] | None = None) -> str:
    text = call_bedrock(prompt, images)
    if not has_template_artifact(text):
        return text

    # One correction retry if template artifacts leaked.
    repair_prompt = (
        prompt
        + "\n\nThe previous output contained template placeholders. Regenerate with concrete content only,"
        + " using facts from repository context."
    )
    fixed = call_bedrock(repair_prompt, images)
    if has_template_artifact(fixed):
        log.warning("Template artifact still present after retry (%s)", lang)
    return fixed


def normalize_en_link(text: str) -> str:
    line = "> 日本語のREADMEはこちらです: [README.ja.md](README.ja.md)"
    if "README.ja.md" in text:
        text = re.sub(r"^>\s*.*README\.ja\.md.*$", line, text, flags=re.MULTILINE)
        return text

    if text.startswith("#"):
        nl = text.find("\n")
        if nl == -1:
            return text + "\n\n" + line + "\n"
        head = text[: nl + 1]
        rest = text[nl + 1 :]
        if rest.startswith("\n"):
            rest = rest[1:]
        return head + "\n" + line + "\n\n" + rest

    return line + "\n\n" + text


def process_repo(repo_path: Path) -> tuple[str, str]:
    name = repo_path.name
    try:
        context = read_repo_context(repo_path)
        if not context.strip():
            return name, "SKIP (empty repo)"

        images = collect_repo_images(repo_path)
        has_img = bool(images)
        if has_img:
            log.info("%s: including %d image(s)", name, len(images))

        time.sleep(SLEEP_BETWEEN)
        en = generate_with_validation(build_prompt_english(name, context, has_img), "en", images)
        en = normalize_en_link(en)
        (repo_path / "README.md").write_text(en, encoding="utf-8")

        time.sleep(SLEEP_BETWEEN)
        ja = generate_with_validation(build_prompt_japanese(name, context, has_img), "ja", images)
        (repo_path / "README.ja.md").write_text(ja, encoding="utf-8")

        return name, "OK"
    except Exception as e:
        return name, f"FAIL: {e}"


def main() -> None:
    repos = sorted([p for p in REPOS_DIR.iterdir() if p.is_dir() and (p / ".git").exists()])
    total = len(repos)
    log.info("Found %s repos", total)

    ok = skip = fail = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(process_repo, r): r for r in repos}
        for i, fut in enumerate(as_completed(futures), 1):
            name, status = fut.result()
            if status == "OK":
                ok += 1
            elif "SKIP" in status:
                skip += 1
            else:
                fail += 1
            log.info("[%s/%s] %s: %s", i, total, status, name)

    log.info("=== Done: OK=%s SKIP=%s FAIL=%s ===", ok, skip, fail)


if __name__ == "__main__":
    main()
