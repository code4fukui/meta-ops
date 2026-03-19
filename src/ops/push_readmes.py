#!/usr/bin/env python3
"""
Commit and push README.md + README.ja.md across code4fukui repos.
Safe behavior:
- only stages README.md and README.ja.md
- no force push
- skips unchanged repos
- resumable by git state (and handles ahead-of-origin case)
"""

import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPOS_DIR = Path.home() / "code4fukui"
MAX_WORKERS = 3
LOG_FILE = Path.home() / "push.log"
COMMIT_MSG = "docs: add English and Japanese README via AI internationalization"
COMMIT_ASSISTED_BY = [
    "Claude (AWS Bedrock anthropic.claude-3-haiku-20240307-v1:0)",
    "GitHub Copilot (GPT-5.3-Codex)",
]

# Repos with clearly questionable placeholder demo links; defer until corrected.
EXCLUDE_REPOS = {
    "webrtc-test",
    "i18n",
    "chart-line",
    "airphoto_cityhall_echizen",
    "SECD.js",
    "ar-vr360-viewer",
    "sabaego",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger(__name__)


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def ahead_count(repo: Path) -> int:
    res = run_git(repo, "rev-list", "--count", "@{u}..HEAD")
    if res.returncode != 0:
        return -1  # no upstream or unknown
    try:
        return int((res.stdout or "0").strip() or 0)
    except ValueError:
        return -1


def commit_trailer_block() -> str:
    lines = [f"Assisted-by: {entry}" for entry in COMMIT_ASSISTED_BY]
    return "\n".join(lines)


def process_repo(repo: Path) -> tuple[str, str]:
    name = repo.name
    try:
        if name in EXCLUDE_REPOS:
            return name, "SKIP_QUALITY"

        en = repo / "README.md"
        ja = repo / "README.ja.md"
        if not en.exists() or not ja.exists():
            return name, "SKIP_MISSING"

        add = run_git(repo, "add", "--", "README.md", "README.ja.md")
        if add.returncode != 0:
            return name, f"FAIL_ADD: {(add.stderr or add.stdout).strip()}"

        diff = run_git(repo, "diff", "--cached", "--quiet")
        staged_changes = diff.returncode == 1

        committed_now = False
        if staged_changes:
            commit = run_git(repo, "commit", "-m", COMMIT_MSG, "-m", commit_trailer_block())
            if commit.returncode != 0:
                msg = (commit.stderr or commit.stdout).strip()
                return name, f"FAIL_COMMIT: {msg}"
            committed_now = True

        ahead = ahead_count(repo)
        should_push = committed_now or ahead > 0 or ahead == -1

        if not should_push:
            return name, "SKIP"

        push = run_git(repo, "push", "origin", "HEAD")
        if push.returncode != 0:
            msg = (push.stderr or push.stdout).strip()
            return name, f"FAIL_PUSH: {msg}"

        if committed_now:
            return name, "OK"
        return name, "PUSHED_PENDING"

    except Exception as e:
        return name, f"FAIL: {e}"


def main() -> None:
    repos = sorted([p for p in REPOS_DIR.iterdir() if p.is_dir() and (p / ".git").exists()])
    log.info(f"Found {len(repos)} repos")

    counts = {
        "OK": 0,
        "SKIP": 0,
        "SKIP_MISSING": 0,
        "SKIP_QUALITY": 0,
        "PUSHED_PENDING": 0,
        "FAIL": 0,
    }

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(process_repo, repo): repo for repo in repos}
        for i, fut in enumerate(as_completed(futures), 1):
            name, status = fut.result()
            if status in counts:
                counts[status] += 1
            elif status.startswith("FAIL"):
                counts["FAIL"] += 1
            else:
                counts["FAIL"] += 1
            log.info(f"[{i}/{len(repos)}] {status}: {name}")

    log.info(
        "=== Done: "
        f"OK={counts['OK']} SKIP={counts['SKIP']} SKIP_MISSING={counts['SKIP_MISSING']} "
        f"SKIP_QUALITY={counts['SKIP_QUALITY']} PUSHED_PENDING={counts['PUSHED_PENDING']} FAIL={counts['FAIL']} ==="
    )


if __name__ == "__main__":
    main()
