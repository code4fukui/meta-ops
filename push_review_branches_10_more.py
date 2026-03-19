import re
import subprocess
from pathlib import Path

BASE = Path('/home/ubuntu/code4fukui')
BRANCH = 'review-readme-20260316-11'
PREV = {
    'ASN1','chart-line','dinosaur-opendata','echizen-coast-kanko-reservation','EDINET',
    'find47','fukui-kanko-survey','fukui-kanko-trend-report','mikatagoko-kanko-reservation','moyo'
}
license_re = re.compile(r'(license|licence|mit|copyright|ライセンス|著作権)', re.IGNORECASE)
link_only_re = re.compile(r'(README\\.ja\\.md|日本語のREADMEはこちらです)', re.IGNORECASE)


def run(repo: Path, *args: str, timeout: int = 30):
    return subprocess.run(['git', '-C', str(repo), *args], text=True, capture_output=True, timeout=timeout)


def out(repo: Path, *args: str, timeout: int = 30) -> str:
    p = run(repo, *args, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip())
    return p.stdout.strip()


def is_license_only(repo: Path) -> bool:
    try:
        patch = out(repo, 'show', '--format=', '-U0', 'HEAD', '--', 'README.md', 'README.ja.md')
    except Exception:
        return False
    changed = []
    for ln in patch.splitlines():
        if ln.startswith(('+++', '---', '@@')):
            continue
        if ln.startswith('+') or ln.startswith('-'):
            t = ln[1:].strip()
            if t:
                changed.append(t)
    if not changed:
        return False
    return any(license_re.search(x) for x in changed) and all(license_re.search(x) or link_only_re.search(x) for x in changed)


ok = []
for repo in sorted([p for p in BASE.iterdir() if p.is_dir() and (p / '.git').exists()], key=lambda p: p.name.lower()):
    name = repo.name
    if name in PREV:
        continue
    try:
        ahead = int(out(repo, 'rev-list', '--count', '@{u}..HEAD'))
        behind = int(out(repo, 'rev-list', '--count', 'HEAD..@{u}'))
        if ahead <= 0 or behind != 0:
            continue
        if out(repo, 'log', '-1', '--pretty=%an') != 'Amil Khanzada':
            continue

        files = [x.strip() for x in out(repo, 'show', '--name-only', '--pretty=', 'HEAD').splitlines() if x.strip()]
        if any(f not in ('README.md', 'README.ja.md') for f in files):
            continue

        add = delete = 0
        for ln in out(repo, 'show', '--numstat', '--pretty=', 'HEAD').splitlines():
            parts = ln.split('\t')
            if len(parts) >= 3:
                try:
                    add += int(parts[0])
                except Exception:
                    pass
                try:
                    delete += int(parts[1])
                except Exception:
                    pass
        total = add + delete
        if total <= 4 or is_license_only(repo):
            continue

        head = out(repo, 'rev-parse', '--short', 'HEAD')
        p = run(repo, 'push', 'origin', f'HEAD:refs/heads/{BRANCH}', timeout=45)
        if p.returncode == 0:
            print(f'OK|{name}|{head}|total={total}')
            ok.append((name, head, total))
        else:
            msg = (p.stderr or p.stdout).strip().replace('\n', ' ')
            print(f'FAIL|{name}|{head}|{msg}')

        if len(ok) >= 10:
            break
    except Exception as e:
        print(f'SKIP|{name}|{str(e).replace(chr(10), " ")}')

print(f'SUMMARY|ok={len(ok)}|branch={BRANCH}')
for name, head, total in ok:
    print(f'LINK|{name}|https://github.com/code4fukui/{name}/tree/{BRANCH}|https://github.com/code4fukui/{name}/commit/{head}|total={total}')
