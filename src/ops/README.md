# Operations Scripts

This directory contains the consolidated Python operations scripts for `meta-ops`.

## Core Scripts

- `generate_readmes_from_codebase.py`: generate practical English READMEs from real code/config analysis.
- `generate_readmes_full_refresh.py`: full EN+JA README regeneration pipeline (Bedrock-based).
- `readme_quality_audit.py`: audit generated README quality.
- `commit_readmes_local.py`: create local README-only commits.
- `push_readmes.py`: push reviewed README commits in controlled batches.
- `delete_non_main_branches_all.py`: remove non-default branches across repos.
- `regen_all_bulk.py`: bulk no-push refresh reference script.

## Typical Usage

```bash
cd ~/meta-ops
python3 src/ops/generate_readmes_from_codebase.py --help
```

Use scripts in this order for large operations:

1. Generate/update README files.
2. Audit output quality.
3. Commit locally.
4. Push only after review/approval.
