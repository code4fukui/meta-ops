#!/usr/bin/env python3
"""
Commit README.md and README.ja.md changes across all code4fukui repos.
Local commits only. No push.
"""

import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPOS_DIR = Path.home() / "code4fukui"
MAX_WORKERS = 4
LOG_FILE = Path.home() / "commit_readmes_local.log"
COMMIT_MSG = "docs: refresh English and Japanese README for globalization"
ASSISTED_BY = [
    "Claude (AWS Bedrock anthropic.claude-3-haiku-20240307-v1:0)",
    "GitHub Copilot (GPT-5.3-Codex)",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger(__name__)


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True, check=False)


def commit_body() -> str:
    return "\n".join([f"Assisted-by: {x}" for x in ASSISTED_BY])


def process_repo(repo: Path) -> tuple[str, str]:
    name = repo.name
    try:
        en = repo / "README.md"
        ja = repo / "README.ja.md"
        if not en.exists() or not ja.exists():
            return name, "SKIP_MISSING"

        add = run_git(repo, "add", "--", "README.md", "README.ja.md")
        if add.returncode != 0:
            return name, f"FAIL_ADD: {(add.stderr or add.stdout).strip()}"

        # Ensure only target files are staged.
        staged = run_git(repo, "diff", "--cached", "--name-only")
        staged_files = [x.strip() for x in staged.stdout.splitlines() if x.strip()]
        bad = [x for x in staged_files if x not in ("README.md", "README.ja.md")]
        if bad:
            run_git(repo, "reset", "--", *bad)
            return name, f"FAIL_STAGED_NON_TARGET: {', '.join(bad)}"

        diff = run_git(repo, "diff", "--cached", "--quiet")
        if diff.returncode == 0:
            return name, "SKIP"

        commit = run_git(repo, "commit", "-m", COMMIT_MSG, "-m", commit_body())
        if commit.returncode != 0:
            return name, f"FAIL_COMMIT: {(commit.stderr or commit.stdout).strip()}"

        return name, "OK"
    except Exception as e:
        return name, f"FAIL: {e}"


def main() -> None:
    repos = sorted([p for p in REPOS_DIR.iterdir() if p.is_dir() and (p / ".git").exists()])
    total = len(repos)
    log.info("Found %s repos", total)

    counts = {"OK": 0, "SKIP": 0, "SKIP_MISSING": 0, "FAIL": 0}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(process_repo, r): r for r in repos}
        for i, fut in enumerate(as_completed(futures), 1):
            name, status = fut.result()
            if status in counts:
                counts[status] += 1
            elif status.startswith("FAIL"):
                counts["FAIL"] += 1
            else:
                counts["FAIL"] += 1
            log.info("[%s/%s] %s: %s", i, total, status, name)

    log.info(
        "=== Done: OK=%s SKIP=%s SKIP_MISSING=%s FAIL=%s ===",
        counts["OK"],
        counts["SKIP"],
        counts["SKIP_MISSING"],
        counts["FAIL"],
    )


if __name__ == "__main__":
    main()
