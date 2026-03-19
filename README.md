# meta-ops

Operational scripts for large-scale README maintenance across Code for FUKUI repositories.

This repo is intentionally small. It keeps only reusable scripts and one canonical candidate list.

## Current Layout

- `safe_first_candidates.txt`: conservative target repos list
- `src/ops/`: all Python operations scripts
- `CLAUDE.md`: quality and safety guardrails
- `REPOSITORY_GUIDE.md`: ecosystem map

## Scripts (`src/ops`)

- `generate_readmes_from_codebase.py`
  - Scans each target repo and generates a practical English `README.md` from actual code/config structure.
- `generate_readmes_full_refresh.py`
  - Full EN+JA regeneration pipeline using Bedrock and richer context.
- `readme_quality_audit.py`
  - Quality checks and report generation for README outputs.
- `commit_readmes_local.py`
  - Stages and commits README-only changes locally.
- `push_readmes.py`
  - Pushes reviewed README commits in controlled batches.
- `delete_non_main_branches_all.py`
  - Cleanup utility for non-default branches across repos.
- `regen_all_bulk.py`
  - Bulk no-push refresh workflow reference script.

## Quick Start

```bash
cd ~/meta-ops
python3 src/ops/generate_readmes_from_codebase.py --help
```

Typical flow:

1. Generate or refresh READMEs.
2. Run audit.
3. Commit locally.
4. Review sample repos.
5. Push in batches.

## Requirements

- Linux host
- Python 3.11+
- Git
- Optional: `boto3`, `ffmpeg`, Pillow (for Bedrock/vision workflows)
- Target repos checked out under `~/code4fukui`

## Safety Rules

- Do not push to default branches without explicit approval.
- Preserve important existing project content and attribution lines.
- Keep license sections linked to `LICENSE`.
