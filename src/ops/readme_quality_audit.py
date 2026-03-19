#!/usr/bin/env python3
"""
Audit generated README files across all code4fukui repos.
Produces:
- deterministic issue counters
- sample-based AI quality review using Bedrock
- Markdown report suitable for meta-ops
"""

import json
import logging
import random
import re
from pathlib import Path

import boto3

REPOS_DIR = Path.home() / "code4fukui"
REGION = "us-east-1"
MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
LOG_FILE = Path.home() / "readme_quality_audit.log"
OUT_FILE = Path.home() / "README_QUALITY_REPORT.md"
SAMPLE_SIZE = 60
SEED = 42

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger(__name__)
bedrock = boto3.client("bedrock-runtime", region_name=REGION)


def call_bedrock(prompt: str, max_tokens: int = 1600) -> str:
    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }
        ),
    )
    return json.loads(response["body"].read())["content"][0]["text"].strip()


def repo_dirs() -> list[Path]:
    return sorted([p for p in REPOS_DIR.iterdir() if p.is_dir() and (p / ".git").exists()])


def collect_metrics(repos: list[Path]) -> tuple[dict[str, int], list[str]]:
    metrics = {
        "repos_total": 0,
        "missing_en": 0,
        "missing_ja": 0,
        "en_missing_ja_link": 0,
        "template_artifacts": 0,
        "localhost_or_example": 0,
        "short_en": 0,
        "short_ja": 0,
    }
    flagged = []

    for repo in repos:
        metrics["repos_total"] += 1
        en = repo / "README.md"
        ja = repo / "README.ja.md"

        if not en.exists():
            metrics["missing_en"] += 1
            flagged.append(f"{repo.name}: missing README.md")
            continue
        if not ja.exists():
            metrics["missing_ja"] += 1
            flagged.append(f"{repo.name}: missing README.ja.md")

        en_text = en.read_text(encoding="utf-8", errors="ignore") if en.exists() else ""
        ja_text = ja.read_text(encoding="utf-8", errors="ignore") if ja.exists() else ""

        if "README.ja.md" not in en_text:
            metrics["en_missing_ja_link"] += 1
            flagged.append(f"{repo.name}: English README missing JA link")

        if re.search(r"\[Project Name\]|One or two sentence description|\[プロジェクト名\]", en_text + "\n" + ja_text):
            metrics["template_artifacts"] += 1
            flagged.append(f"{repo.name}: template artifact")

        if re.search(r"localhost|example\.com", en_text + "\n" + ja_text, re.I):
            metrics["localhost_or_example"] += 1

        if len(en_text.split()) < 30:
            metrics["short_en"] += 1
        if len(ja_text.split()) < 15:
            metrics["short_ja"] += 1

    return metrics, flagged


def build_sample(repos: list[Path]) -> list[Path]:
    random.seed(SEED)
    selected = []

    preferred = [
        "fukui-kanko-survey",
        "fukui-kanko-advice",
        "fukui-kanko-people-flow-data",
        "fukui-kanko-people-flow-visualization",
        "fukui-kanko-trend-report",
        "capture_monitor",
        "aeon",
        "sabaego",
        "webrtc-test",
        "i18n",
    ]
    repo_map = {r.name: r for r in repos}
    for name in preferred:
        if name in repo_map:
            selected.append(repo_map[name])

    remaining = [r for r in repos if r not in selected]
    selected.extend(random.sample(remaining, max(0, min(SAMPLE_SIZE - len(selected), len(remaining)))))
    return selected


def render_sample_context(sample: list[Path]) -> str:
    chunks = []
    for repo in sample:
        en = (repo / "README.md").read_text(encoding="utf-8", errors="ignore")[:1800]
        ja = (repo / "README.ja.md").read_text(encoding="utf-8", errors="ignore")[:1200]
        chunks.append(f"## {repo.name}\n\n[EN]\n{en}\n\n[JA]\n{ja}")
    return "\n\n---\n\n".join(chunks)


def ai_review(sample_context: str, metrics: dict[str, int]) -> str:
    prompt = f"""You are reviewing a large batch of generated GitHub READMEs for technical quality.

Deterministic metrics:
{json.dumps(metrics, indent=2)}

Here is a representative sample of generated English and Japanese READMEs:

{sample_context}

Write a concise markdown report with these sections:

# README Quality Report
## Executive Summary
## What Looks Strong
## Quality Risks
## Specific Patterns To Review Later
## Verdict

Rules:
- Focus on readability, factuality, consistency, and obvious hallucination risk.
- Be honest and specific.
- Do not claim you verified facts beyond the provided sample and metrics.
- Output markdown only.
"""
    return call_bedrock(prompt)


def main() -> None:
    repos = repo_dirs()
    metrics, flagged = collect_metrics(repos)
    sample = build_sample(repos)
    sample_context = render_sample_context(sample)
    review = ai_review(sample_context, metrics)

    appendix = "\n".join(f"- {item}" for item in flagged[:200])
    report = review + "\n\n## Deterministic Metrics\n\n```json\n" + json.dumps(metrics, indent=2) + "\n```\n"
    if appendix:
        report += "\n## Flagged Items\n\n" + appendix + "\n"

    OUT_FILE.write_text(report, encoding="utf-8")
    log.info("Saved quality report to %s", OUT_FILE)


if __name__ == "__main__":
    main()
