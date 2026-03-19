import random
import re
import subprocess
from pathlib import Path

base = Path('/home/ubuntu/code4fukui')
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
        if ln.startswith('+++') or ln.startswith('---') or ln.startswith('@@'):
            continue
        if ln.startswith('+') or ln.startswith('-'):
            text = ln[1:].strip()
            if text:
                changed.append(text)

    if not changed:
        return False

    has_license_marker = any(license_re.search(x) for x in changed)
    all_allowed = all(license_re.search(x) or link_only_re.search(x) for x in changed)
    return has_license_marker and all_allowed

rows = []
tiny_filtered = []

for rp in sorted([p for p in base.iterdir() if p.is_dir() and (p / '.git').exists()], key=lambda p: p.name.lower()):
    name = rp.name
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

        branch = sh(rp, 'rev-parse', '--abbrev-ref', 'HEAD').strip()
        commit = sh(rp, 'rev-parse', '--short', 'HEAD').strip()
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

        license_only = is_license_only(rp)
        tiny = total <= 4 or license_only

        item = {
            'name': name,
            'branch': branch,
            'commit': commit,
            'files': ','.join(files),
            'add': add,
            'del': delete,
            'total': total,
            'license_only': license_only,
        }

        if tiny:
            tiny_filtered.append(item)
        else:
            rows.append(item)
    except Exception:
        continue

next50 = rows[:50]
print(f'ORDER=alphabetical_case_insensitive')
print(f'PENDING_NON_TINY_TOTAL={len(rows)}')
print(f'PENDING_TINY_FILTERED_TOTAL={len(tiny_filtered)}')
print(f'NEXT50_COUNT={len(next50)}')
print('')
print('NEXT50')
for i, r in enumerate(next50, 1):
    print(f"{i:02d}|{r['name']}|{r['branch']}|{r['commit']}|{r['files']}|+{r['add']}/-{r['del']}|total={r['total']}")

print('')
print('RANDOM_SAMPLE_DIFF_PREVIEW')
random.seed(42)
sample = random.sample(next50, min(8, len(next50)))
for s in sample:
    repo = base / s['name']
    patch = sh(repo, 'show', '--format=', '-U0', 'HEAD', '--', 'README.md', 'README.ja.md')
    changed = []
    for ln in patch.splitlines():
        if ln.startswith('+++') or ln.startswith('---') or ln.startswith('@@'):
            continue
        if ln.startswith('+') or ln.startswith('-'):
            text = ln[1:].strip()
            if text:
                changed.append((ln[0], text))
    print(f"- {s['name']} ({s['commit']}) +{s['add']}/-{s['del']} total={s['total']}")
    for sign, text in changed[:6]:
        t = text if len(text) <= 120 else text[:117] + '...'
        print(f"  {sign} {t}")
    if len(changed) > 6:
        print(f"  ... ({len(changed)-6} more changed lines)")

print('')
print('TINY_FILTERED_FIRST20')
for t in tiny_filtered[:20]:
    reason = 'license-only' if t['license_only'] else 'small-diff'
    print(f"- {t['name']} ({t['commit']}) +{t['add']}/-{t['del']} total={t['total']} [{reason}]")
