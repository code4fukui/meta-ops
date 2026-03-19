import subprocess
from pathlib import Path

BASE = Path('/home/ubuntu/code4fukui')
SUBJECT = 'docs: refresh English and Japanese README for globalization'
BODY = [
    '- Refresh README.md and README.ja.md for international audiences',
    '- Keep existing project-specific content and structure',
    '- Normalize cross-language metadata and links',
]
TRAILERS = [
    'Generated-by: Claude via AWS Bedrock (anthropic.claude-3-haiku-20240307-v1:0)',
    'Verified-by: Amil Khanzada <amilkh@users.noreply.github.com>',
]


def run(repo: Path, *args: str):
    return subprocess.run(['git', '-C', str(repo), *args], text=True, capture_output=True)


def out(repo: Path, *args: str) -> str:
    p = run(repo, *args)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    return p.stdout.strip()


def has_remote_tracking(repo: Path) -> bool:
    p = run(repo, 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}')
    return p.returncode == 0


def is_clean(repo: Path) -> bool:
    return out(repo, 'status', '--porcelain') == ''


repos = sorted([p for p in BASE.iterdir() if p.is_dir() and (p / '.git').exists()], key=lambda x: x.name.lower())

changed = 0
skipped = 0
errors = 0

for repo in repos:
    name = repo.name
    try:
        if not has_remote_tracking(repo):
            print(f'SKIP|{name}|no-upstream')
            skipped += 1
            continue
        if not is_clean(repo):
            print(f'SKIP|{name}|dirty-worktree')
            skipped += 1
            continue

        ahead = int(out(repo, 'rev-list', '--count', '@{u}..HEAD') or '0')
        behind = int(out(repo, 'rev-list', '--count', 'HEAD..@{u}') or '0')

        if ahead <= 1:
            print(f'SKIP|{name}|ahead={ahead}')
            skipped += 1
            continue
        if behind != 0:
            print(f'SKIP|{name}|behind={behind}')
            skipped += 1
            continue

        author = out(repo, 'log', '-1', '--pretty=%an')
        if author != 'Amil Khanzada':
            print(f'SKIP|{name}|author={author}')
            skipped += 1
            continue

        # Keep commit data staged as one commit relative to upstream branch.
        p = run(repo, 'reset', '--soft', '@{u}')
        if p.returncode != 0:
            raise RuntimeError(f'reset-soft failed: {p.stderr.strip() or p.stdout.strip()}')

        commit_msg = SUBJECT + '\n\n' + '\n'.join(BODY) + '\n\n' + '\n'.join(TRAILERS)
        p = run(repo, 'commit', '-m', commit_msg)
        if p.returncode != 0:
            raise RuntimeError(f'commit failed: {p.stderr.strip() or p.stdout.strip()}')

        head = out(repo, 'rev-parse', '--short', 'HEAD')
        print(f'OK|{name}|ahead={ahead}->1|head={head}')
        changed += 1

    except Exception as e:
        print(f'ERR|{name}|{e}')
        errors += 1

print(f'SUMMARY|changed={changed}|skipped={skipped}|errors={errors}')
