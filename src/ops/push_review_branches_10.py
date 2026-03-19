import re
import subprocess
from pathlib import Path

base = Path('/home/ubuntu/code4fukui')
branch = 'review-readme-20260316-10'
subjects = {
    'docs: add English and Japanese README via AI internationalization',
    'docs: refresh English and Japanese README for globalization',
    'docs: remove unsupported README.en.md',
}
license_re = re.compile(r'(license|licence|mit|copyright|ライセンス|著作権)', re.IGNORECASE)
link_only_re = re.compile(r'(README\.ja\.md|日本語のREADMEはこちらです)', re.IGNORECASE)

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

candidates = []
for rp in sorted([p for p in base.iterdir() if p.is_dir() and (p / '.git').exists()], key=lambda p: p.name.lower()):
    try:
        subj = sh(rp, 'log', '-1', '--pretty=%s', '@{u}').strip()
        if subj not in subjects:
            continue
        ahead = int(sh(rp, 'rev-list', '--count', '@{u}..HEAD').strip())
        behind = int(sh(rp, 'rev-list', '--count', 'HEAD..@{u}').strip())
        if ahead <= 0 or behind != 0:
            continue
        author = sh(rp, 'log', '-1', '--pretty=%an').strip()
        if author != 'Amil Khanzada':
            continue
        files = [x.strip() for x in sh(rp, 'show', '--name-only', '--pretty=', 'HEAD').splitlines() if x.strip()]
        if any(f not in ('README.md', 'README.ja.md') for f in files):
            continue
        numstat = sh(rp, 'show', '--numstat', '--pretty=', 'HEAD').splitlines()
        add = delete = 0
        for ln in numstat:
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
        candidates.append((rp.name, rp, total))
    except Exception:
        continue

selected = candidates[:10]
print(f'SELECTED={len(selected)}')
results = []
for name, rp, total in selected:
    head = sh(rp, 'rev-parse', '--short', 'HEAD').strip()
    # Push HEAD to a review branch on origin without touching default branch.
    p = subprocess.run(['git', '-C', str(rp), 'push', 'origin', f'HEAD:refs/heads/{branch}'], text=True, capture_output=True)
    if p.returncode == 0:
        results.append((name, head, total, 'OK'))
    else:
        results.append((name, head, total, 'FAIL', (p.stderr or p.stdout).strip()))

for r in results:
    if r[3] == 'OK':
        print(f"OK|{r[0]}|{r[1]}|total={r[2]}")
    else:
        print(f"FAIL|{r[0]}|{r[1]}|total={r[2]}|{r[4]}")
print(f'BRANCH={branch}')
