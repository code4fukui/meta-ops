# meta-ops

Automation and QA scripts for repository-wide README internationalization across the Code for FUKUI organization.

This repository contains the reusable public subset of the README globalization workflow:
- generate bilingual `README.md` and `README.ja.md` files with AWS Bedrock
- use code, config, screenshots, and video frames as generation context
- audit generated output for quality risks
- commit README-only changes locally
- push reviewed changes safely in batches

It does not include private infrastructure config, one-off recovery scripts, or local review artifacts from the original internal operations workspace.

## Repository Layout

- [src/generate_readmes_full_refresh.py](src/generate_readmes_full_refresh.py): regenerate `README.md` and `README.ja.md` across repos using Bedrock, with screenshot and video-frame context when available
- [src/commit_readmes_local.py](src/commit_readmes_local.py): create local README-only commits across repos
- [src/push_readmes.py](src/push_readmes.py): push README-only commits safely with resumable behavior
- [src/readme_quality_audit.py](src/readme_quality_audit.py): audit generated READMEs and produce a quality report
- [REPOSITORY_GUIDE.md](REPOSITORY_GUIDE.md): high-level map of the repository ecosystem

## Requirements

- Ubuntu or another Linux host
- Python 3.11+
- Git
- `ffmpeg` for extracting video frames
- Pillow for image resizing
- `boto3` for Bedrock access
- an AWS identity that can call Bedrock in `us-east-1`
- a checkout of the target repositories under `~/code4fukui`

The scripts assume this layout:

```text
~/meta-ops/
~/code4fukui/<repo-1>/
~/code4fukui/<repo-2>/
...
```

## AWS / Bedrock Setup

The generator uses the Bedrock runtime API directly. By default it calls:

- region: `us-east-1`
- model: `anthropic.claude-3-haiku-20240307-v1:0`

The cleanest setup on EC2 is an instance profile / IAM role with permission to invoke the model. At minimum, the runtime needs Bedrock invoke access in `us-east-1`.

Example IAM policy scope:

```json
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Effect": "Allow",
			"Action": [
				"bedrock:InvokeModel",
				"bedrock:InvokeModelWithResponseStream"
			],
			"Resource": "*"
		}
	]
}
```

If you do not want to use an instance role, standard AWS credential loading also works, but do not store credentials in this repo.

## Reproducible EC2 Setup

1. Launch an Ubuntu EC2 instance.
2. Attach an IAM role with Bedrock runtime access in `us-east-1`.
3. SSH into the instance.
4. Install system packages.
5. Clone this repo and the target organization repos.
6. Install Python dependencies.
7. Set git identity for the commits you want the rollout to use.

Example bootstrap:

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-pip python3-venv python3-pil ffmpeg rsync

cd ~
git clone https://github.com/code4fukui/meta-ops.git
mkdir -p ~/code4fukui
cd ~/code4fukui

# Clone the target repos here by whatever method fits your organization.
# The automation expects each target repo to live directly under ~/code4fukui.
```

Optional git identity setup:

```bash
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"
```

Verify Bedrock access before running a large batch:

```bash
python3 - <<'PY'
import boto3
boto3.client('bedrock-runtime', region_name='us-east-1')
print('bedrock ok')
PY
```

## Generation Workflow

The typical workflow is:

1. Generate bilingual READMEs locally across the repo set.
2. Audit the generated output.
3. Commit README-only changes locally.
4. Review a sample.
5. Push in controlled batches.

### 1. Generate READMEs

From the EC2 instance:

```bash
cd ~/meta-ops
python3 src/generate_readmes_full_refresh.py
```

What the generator uses as context:
- README and code/config files from the repo
- small CSV/TSV samples when present
- screenshots when present
- one extracted frame from a video when present

What it avoids:
- binary assets that do not help documentation
- full license-body copy-through from `LICENSE` files
- decorative icons and tiny images

### 2. Audit README quality

```bash
cd ~/meta-ops
python3 src/readme_quality_audit.py
```

This produces a deterministic metric summary plus a sample-based AI review.

### 3. Commit locally only

```bash
cd ~/meta-ops
python3 src/commit_readmes_local.py
```

This script stages only `README.md` and `README.ja.md` in each repo and creates local commits without pushing.

### 4. Push reviewed changes

```bash
cd ~/meta-ops
python3 src/push_readmes.py
```

The push script is conservative:
- it only stages README files
- it skips missing repos
- it avoids force-push
- it can resume from git state
- it allows hard-coded exclusions for repos that need manual review

## Running Long Jobs Safely

Large runs can take a long time. Use `nohup`, `screen`, or `tmux` on the EC2 instance.

Example:

```bash
cd ~/meta-ops
nohup env README_MAX_WORKERS=2 README_SLEEP_BETWEEN=1.5 README_THROTTLE_JITTER=2.0 \
	python3 src/generate_readmes_full_refresh.py > ~/regen_vision.log 2>&1 < /dev/null &
```

Useful knobs:
- `README_MAX_WORKERS`: concurrent repo workers
- `README_SLEEP_BETWEEN`: spacing between generation calls
- `README_THROTTLE_JITTER`: random extra backoff to reduce synchronized retries

These are useful when Bedrock starts returning `ThrottlingException`.

## Vision Support

The generator can improve README quality for UI-heavy repos by passing screenshots into the Bedrock prompt. For repos with videos, it extracts a single frame with `ffmpeg` and sends that frame as image context.

This is especially useful for:
- web apps
- dashboards
- maps
- AR / XR demos
- visualization repos with meaningful screenshots

## Safety Notes

- Do not store AWS credentials, SSH config, or private repo lists in this repository.
- Keep one-off recovery scripts outside the public repo or under `tmp/` if they are strictly local and untracked.
- Review a sample of generated READMEs before any bulk push.
- Prefer controlled batches over all-repo pushes.

## Temporary Files

- `tmp/` is ignored and can be used for local scratch files.
- Logs, PID files, and Python cache files are ignored.
