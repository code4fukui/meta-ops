# meta-ops

Automation and QA scripts for repository-wide README internationalization across the Code for FUKUI organization.

This repo is the cleaned public subset of the internal operations workspace. It keeps the reusable generation, audit, commit, and push tooling while excluding one-off recovery scripts and local review artifacts.

## Files

- [src/generate_readmes_full_refresh.py](src/generate_readmes_full_refresh.py): regenerate `README.md` and `README.ja.md` across repos using Bedrock, including screenshot and video-frame context when available
- [src/commit_readmes_local.py](src/commit_readmes_local.py): create local README-only commits across repos
- [src/push_readmes.py](src/push_readmes.py): push README-only commits safely with resumable behavior
- [src/readme_quality_audit.py](src/readme_quality_audit.py): audit generated READMEs and produce a quality report
- [REPOSITORY_GUIDE.md](REPOSITORY_GUIDE.md): high-level map of the repository ecosystem

## Notes

- Temporary local artifacts can live under `tmp/`; that path is ignored.
- Logs, PID files, and Python cache files are ignored.
