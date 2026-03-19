import subprocess
from pathlib import Path

BASE = Path('/home/ubuntu/code4fukui')


def run(repo: Path, *args: str):
    return subprocess.run(['git', '-C', str(repo), *args], text=True, capture_output=True)


def out(repo: Path, *args: str) -> str:
    p = run(repo, *args)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip())
    return p.stdout

repos = sorted([p for p in BASE.iterdir() if p.is_dir() and (p / '.git').exists()], key=lambda p: p.name.lower())

deleted = 0
skipped = 0
errors = 0

for repo in repos:
    name = repo.name
    try:
        head_ref = out(repo, 'symbolic-ref', 'refs/remotes/origin/HEAD').strip()
        default = head_ref.split('/')[-1] if head_ref else 'main'

        heads = out(repo, 'for-each-ref', '--format=%(refname:short)', 'refs/remotes/origin').splitlines()
        branches = []
        for h in heads:
            if not h.startswith('origin/'):
                continue
            b = h[len('origin/'):]
            if b == 'HEAD':
                continue
            branches.append(b)

        targets = [b for b in branches if b != default]
        if not targets:
            skipped += 1
            continue

        for b in targets:
            p = run(repo, 'push', 'origin', '--delete', b)
            if p.returncode == 0:
                deleted += 1
                print(f'DEL|{name}|{b}')
            else:
                msg = (p.stderr or p.stdout).strip().replace('\n', ' ')
                print(f'ERR|{name}|{b}|{msg}')
                errors += 1

    except Exception as e:
        print(f'ERR|{name}|meta|{str(e).replace(chr(10), " ")}')
        errors += 1

print(f'SUMMARY|deleted={deleted}|repos_no_extra={skipped}|errors={errors}')
