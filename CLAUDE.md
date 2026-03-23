# CLAUDE.md

## Why this file exists
This file records repeated mistakes from the README globalization rollout and the exact guardrails to prevent them.

## Mistakes we made
1. Dropped important existing README content (project-specific links, demo sections, data references).
2. Created EN/JA mismatch by generating Japanese from partial context instead of finalized English.
3. Inserted unwanted helper text into README output:
- `English README is here: [README.md](README.md)` in Japanese files.
- `以下のREADMEのマークダウンの部分を英語から日本語に翻訳します。`
4. Placed the Japanese-link line inconsistently or duplicated it:
- `日本語のREADMEはこちらです: [README.ja.md](README.ja.md)`
5. Duplicated headings (for example `# Nano ID` and `# nanoid`).
6. Added duplicate paragraphs/sentences during merge.
7. Changed equivalent license wording unnecessarily.
8. Introduced formatting regressions (extra spaces, blank-line noise, trailer spacing issues).

## Non-negotiable rules
1. Build canonical English README first.
2. Translate Japanese from that finalized English README only (full translation, not partial merge translation).
3. Preserve all existing project-specific content unless explicitly instructed to remove it.
4. In `README.md`, include exactly one Japanese-link line near the top.
5. Do not add `English README is here: [README.md](README.md)` to Japanese README.
6. Strip any leaked translation prompt/instruction text.
7. Keep EN/JA section coverage aligned (no major omissions).
8. Keep one canonical license section at the end linking to `LICENSE`.
9. Never push rollout commits unless user explicitly approves push.
10. If local ahead commits are multiple, squash locally without requiring force-push.
11. Do not replace a well-prepared `README.ja.md` wholesale; preserve existing high-value technical sections and only add/normalize missing essentials.
12. Preserve existing attribution and data-source lines (for example: `Data source: CC BY Fukui Tourism Association`) if they already exist.
13. Avoid technical downscoping in `README.md`; keep critical data caveats and link clearly to full technical EN/JA docs.

## Required validation before reporting "done"
1. Search for leaked line:
- `grep -Rsn "以下のREADMEのマークダウンの部分を英語から日本語に翻訳します。" -- */README*`
2. Search for unwanted JA pointer in JA files:
- `grep -Rsn "English README is here: \[README.md\](README.md)" -- */README.ja.md`
3. Verify Japanese-link line exists once in English README and appears near top.
4. Check for obvious duplicate H1 headings.
5. Spot-check EN/JA line counts for large gaps.
6. Confirm no non-README file changes were introduced unintentionally.
7. If `README.ja.md` existed before, verify core sections were not removed.
8. Search diff for attribution removals:
- `git diff -- README* | grep -n "^-.*Data source: CC BY Fukui Tourism Association"`

## Commit message hygiene
1. No extra blank line between trailers.
2. Use stable doc-refresh subject/body style agreed in this project.
3. Do not add unnecessary wording churn in README license text.

## If any check fails
Stop, amend locally, re-run validations, and only then present commit links.

## Handoff Context Dump (2026-03-23)

### Scope and intent
- This repository (`meta-ops`) orchestrates large-scale README operations across Code for FUKUI repositories.
- Current operating mode is conservative and quality-first.
- Default branch pushes require explicit user approval.
- The next agent/prompt has direct access to this folder and should read files directly before making assumptions.

### Current repository state
- Branch: `master`
- HEAD: `5b42825f30e92077f629ec61a27b37ccf3960099`
- Local branch status: `master` is ahead of `origin/master` by 2 commits.
- Most recent commits:
	1. `5b42825` chore(meta-ops): consolidate ops scripts and remove one-off artifacts
	2. `0d7ea79` chore: move operation scripts to src/ops and simplify candidate lists
	3. `cd9bef2` chore: centralize automation scripts and add short README repo list
	4. `d1cf17d` docs: add CLAUDE.md mistake prevention guide

### Consolidated script inventory (single operations location)
- `src/ops/generate_readmes_from_codebase.py`
	- English README generation from actual codebase analysis (package files, project structure, scripts).
- `src/ops/generate_readmes_full_refresh.py`
	- Full EN/JA regeneration pipeline with Bedrock + context assets.
- `src/ops/readme_quality_audit.py`
	- README quality checks/reporting.
- `src/ops/commit_readmes_local.py`
	- README-only local commit creation.
- `src/ops/push_readmes.py`
	- Controlled push workflow.
- `src/ops/delete_non_main_branches_all.py`
	- Non-default branch cleanup.
- `src/ops/regen_all_bulk.py`
	- Bulk no-push refresh reference script.
- `src/ops/README.md`
	- Script index and usage order.

### Candidate list baseline
- Canonical list file: `safe_first_candidates.txt`
- Current size: 144 repos.
- Meaning: conservative first-pass targets selected to minimize README regression risk.

### What was done recently (important)
1. Large cleanup/consolidation completed in `meta-ops`:
	 - Removed many one-off/versioned scripts from previous rollout experiments.
	 - Consolidated maintained scripts under `src/ops/`.
2. README docs were simplified to match new layout:
	 - `README.md`
	 - `README.ja.md`
	 - `src/ops/README.md`
3. `generate_readmes_from_codebase.py` received an install-instructions bug fix:
	 - function signature/context fix so repo name/path handling is valid.

### Quality and safety constraints (must preserve)
- EN-first canonical generation.
- JA translation only from finalized EN README.
- Preserve existing high-value README content unless removal is explicitly requested.
- Preserve attribution/data-source lines if already present.
- Keep exactly one canonical license section linking to `LICENSE`.
- Never push rollout changes to default branches without explicit user approval.

### Operational history summary (for continuity)
- A previous safe-first batch process targeted 144 repos and pushed review-branch updates.
- User feedback required replacing short baseline text with codebase-derived README content.
- Direction then shifted to simplify `meta-ops` itself before continuing rollout.

### Open work likely expected next
1. Validate `generate_readmes_from_codebase.py` quality on a sample set (5-10 repos) by manual spot-check.
2. Improve template richness where outputs are still too generic:
	 - purpose extraction from code/config
	 - setup/run commands by detected scripts
	 - clearer architecture/structure sections
3. Run controlled batch generation for additional repos (EN only unless user requests JA).
4. Produce review links and commit SHAs in small batches for approval.
5. Only after approval, plan promotion strategy from review branches to default branches.

### Suggested verification commands for the next agent
- Repo status:
	- `git status --short`
	- `git branch -vv`
	- `git log --oneline -n 10`
- Script health:
	- `python3 -m py_compile src/ops/*.py`
- Candidate baseline checks:
	- `wc -l safe_first_candidates.txt`
- README policy checks (in target repo roots):
	- `grep -Rsn "以下のREADMEのマークダウンの部分を英語から日本語に翻訳します。" -- */README*`
	- `grep -Rsn "English README is here: \[README.md\](README.md)" -- */README.ja.md`

### Prompting guidance for successor agents
- Assume filesystem access and read current scripts/docs first.
- Do not re-introduce deleted one-off scripts unless user explicitly asks.
- Keep changes minimal, auditable, and batch-based.
- Prefer deterministic scripted operations over manual ad hoc edits.
