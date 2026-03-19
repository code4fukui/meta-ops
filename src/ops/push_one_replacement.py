import re, subprocess
from pathlib import Path

base = Path('/home/ubuntu/code4fukui')
branch = 'review-readme-20260316-10'
used = {
    'ASN1','chart-line','dinosaur-opendata','echizen-coast-kanko-reservation','EDINET',
    'find47','fukui-kanko-survey','fukui-kanko-trend-report','mikatagoko-kanko-reservation','moyo'
}
license_re = re.compile(r'(license|licence|mit|copyright|ライセンス|著作権)', re.IGNORECASE)
link_only_re = re.compile(r'(README\\.ja\\.md|日本語のREADMEはこちらです)', re.IGNORECASE)

def sh(repo: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True, stderr=subprocess.DEVNULL)

def is_license_only(repo: Path) -> bool:
    try:
        patch = sh(repo, 'show', '--format=', '-U0', 'HEAD', '--', 'README.md', 'README.ja.md')
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

for rp in sorted([p for p in base.iterdir() if p.is_dir() and (p / '.git').exists()], key=lambda p: p.name.lower()):
    if rp.name in used:
        continue
    try:
        ahead = int(sh(rp, 'rev-list', '--count', '@{u}..HEAD').strip())
        behind = int(sh(rp, 'rev-list', '--count', 'HEAD..@{u}').strip())
        if ahead <= 0 or behind != 0:
            continue
        if sh(rp, 'log', '-1', '--pretty=%an').strip() != 'Amil Khanzada':
            continue
        files = [x.strip() for x in sh(rp, 'show', '--name-only', '--pretty=', 'HEAD').splitlines() if x.strip()]
        if any(f not in ('README.md', 'README.ja.md') for f in files):
            continue
        add = delete = 0
        for ln in sh(rp, 'show', '--numstat', '--pretty=', 'HEAD').splitlines():
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
        if total <= 4 or is_license_only(rp):
            continue
        head = sh(rp, 'rev-parse', '--short', 'HEAD').strip()
        p = subprocess.run(['git', '-C', str(rp), 'push', 'origin', f'HEAD:refs/heads/{branch}'], text=True, capture_output=True, timeout=60)
        if p.returncode == 0:
            print(f'OK|{rp.name}|{head}|total={total}')
        else:
            print(f'FAIL|{rp.name}|{head}|{(p.stderr or p.stdout).strip()}')
        break
    except Exception:
        continue
