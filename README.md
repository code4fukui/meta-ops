# meta-ops

> 日本語のREADMEはこちらです: [README.ja.md](README.ja.md)

Operational toolkit for large-scale README maintenance and internationalization across the 1200+ [Code for FUKUI](https://github.com/code4fukui) repositories.

This repository contains the scripts and configuration used to generate, audit, and deploy high-quality, bilingual READMEs, ensuring consistency and clarity across a diverse open-source ecosystem.

## Core Workflow
The scripts are designed to be run in a sequence for safe, large-scale updates:
1.  **Generate:** Create or refresh READMEs using one of the generation scripts.
2.  **Audit:** Run the quality audit script to generate a report and identify potential issues.
3.  **Commit:** Use `commit_readmes_local.py` to create local, README-only commits.
4.  **Review:** Manually inspect a sample of the local commits for quality and accuracy.
5.  **Push:** Push the reviewed changes to origin in controlled, safe batches.

## Scripts (`src/ops/`)
| Script | Description |
| --- | --- |
| `generate_readmes_from_codebase.py` | Generates a practical English README by analyzing code structure, dependencies (`package.json`), and key files. |
| `generate_readmes_full_refresh.py` | Performs a full EN+JA regeneration using AWS Bedrock (Claude 3 Haiku), with vision support for screenshots. |
| `readme_quality_audit.py` | Runs deterministic checks and uses AI to generate a quality report on generated READMEs. |

| `push_readmes.py` | Pushes reviewed, locally-committed README changes to origin in controlled, resumable batches. |
| `delete_non_main_branches_all.py` | A utility script to clean up non-default branches across all repositories. |
| `regen_all_bulk.py` | Reference script for a bulk, no-push regeneration and translation workflow. |

## Repository Structure
- `safe_first_candidates.txt`: A conservative list of repositories targeted for initial, low-risk updates.
- `src/ops/`: All Python operations scripts.
- `CLAUDE.md`: Quality and safety guardrails for AI-assisted content generation.
- `REPOSITORY_GUIDE.md`: A map of the Code for FUKUI ecosystem for international developers.

## Quick Start
```bash
# Navigate to the meta-ops directory
cd ~/meta-ops

# View options for a script
python3 src/ops/generate_readmes_from_codebase.py --help
```

## Requirements
- A Linux host
- Python 3.11+
- Git
- Target repositories checked out under `~/code4fukui`
- **Optional:** `boto3`, `ffmpeg`, `Pillow` for workflows involving AWS Bedrock and vision support.

## Safety Guardrails
- ✅ **No Direct Pushes:** Do not push to default branches without an explicit, reviewed workflow.
- ✅ **Preserve Content:** Retain important existing project descriptions and attribution lines.
- ✅ **Consistent Licensing:** Ensure license sections link directly to the `LICENSE` file.
- 🚫 **No Force Pushing:** Scripts are designed to avoid force pushes and overwriting history.