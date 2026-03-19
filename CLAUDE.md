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
