import re
import subprocess
from pathlib import Path

BASE = Path('/home/ubuntu/code4fukui')
BRANCH = 'review-readme-20260316-15'
EXCLUDE = {
    'ASN1','chart-line','dinosaur-opendata','echizen-coast-kanko-reservation','EDINET','find47','fukui-kanko-survey','fukui-kanko-trend-report','mikatagoko-kanko-reservation','moyo',
    'ar-vr360-viewer','fukui-kanko-reservation','fukui-kanko-trend-data','fukui-station-kanko-reservation','i18n','ishikawa-kanko-survey','mp3-recorder','mp3-tag-editor','mp4player','mpy-cross-v6',
    'muno3','music-api-js','music-brainstorming-bgm','music-fnct-sabae','music-future-with-you','music-kanko-dx','music-new-shoshinge',
    'music-opendata-fukui','music-pioneerpork','music-player','mykkrec','name2pic','nanoevents','nanoid','natural-earth-geojson'
}
md_link = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')

def run(repo: Path, *args: str, timeout: int = 180):
    return subprocess.run(['git', '-C', str(repo), *args], text=True, capture_output=True, timeout=timeout)

def out(repo: Path, *args: str, timeout: int = 180) -> str:
    p = run(repo, *args, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip())
    return p.stdout

def out_or_empty(repo: Path, *args: str, timeout: int = 180) -> str:
    p = run(repo, *args, timeout=timeout)
    if p.returncode != 0:
        return ''
    return p.stdout

def norm(s: str) -> str:
    return s.replace('\r\n', '\n').replace('\r', '\n')

def split_lines(s: str):
    return norm(s).split('\n')

def lcs(a, b):
    n, m = len(a), len(b)
    dp = [[0]*(m+1) for _ in range(n+1)]
    for i in range(n-1, -1, -1):
        for j in range(m-1, -1, -1):
            if a[i] == b[j]:
                dp[i][j] = 1 + dp[i+1][j+1]
            else:
                dp[i][j] = dp[i+1][j] if dp[i+1][j] >= dp[i][j+1] else dp[i][j+1]
    i = j = 0
    seq = []
    while i < n and j < m:
        if a[i] == b[j]:
            seq.append(a[i]); i += 1; j += 1
        elif dp[i+1][j] >= dp[i][j+1]:
            i += 1
        else:
            j += 1
    return seq

def scs(a, b):
    common = lcs(a, b)
    i = j = k = 0
    outl = []
    while k < len(common):
        c = common[k]
        while i < len(a) and a[i] != c:
            outl.append(a[i]); i += 1
        while j < len(b) and b[j] != c:
            outl.append(b[j]); j += 1
        outl.append(c); i += 1; j += 1; k += 1
    outl.extend(a[i:]); outl.extend(b[j:])
    return outl

def cleanup(lines):
    outl = []
    prev_blank = False
    for ln in lines:
        blank = ln.strip() == ''
        if blank and prev_blank:
            continue
        outl.append(ln)
        prev_blank = blank
    while outl and outl[-1].strip() == '':
        outl.pop()
    return outl

def find_lic_idx(lines):
    for i, ln in enumerate(lines):
        t = ln.strip().lower()
        if t in ('## license', '## ライセンス'):
            return i
    return len(lines)

def ensure_license_tail(lines, ja=False):
    body = cleanup(lines[:find_lic_idx(lines)])
    if body and body[-1].strip() != '':
        body.append('')
    if ja:
        body.append('## ライセンス')
        body.append('このプロジェクトは [MIT License](LICENSE) のもとで公開されています。')
    else:
        body.append('## License')
        body.append('This project is licensed under the [MIT License](LICENSE).')
    return cleanup(body)

def extract_links(lines):
    res = []
    seen = set()
    for ln in lines:
        for m in md_link.finditer(ln):
            txt, url = m.group(1).strip(), m.group(2).strip()
            if 'github.com/code4fukui/' not in url:
                continue
            k = (txt, url)
            if k in seen:
                continue
            seen.add(k)
            res.append((txt, url))
    return res

def ensure_parity(en_lines, ja_lines):
    en = extract_links(en_lines)
    ja = extract_links(ja_lines)
    en_urls = {u for _, u in en}
    ja_urls = {u for _, u in ja}
    miss_ja = [(t, u) for t, u in en if u not in ja_urls]
    miss_en = [(t, u) for t, u in ja if u not in en_urls]

    def insert(lines, items):
        if not items:
            return lines
        idx = find_lic_idx(lines)
        head, tail = lines[:idx], lines[idx:]
        if head and head[-1].strip() != '':
            head.append('')
        for t, u in items:
            b = f'- [{t}]({u})'
            if b not in head:
                head.append(b)
        if tail and tail[0].strip() != '':
            head.append('')
        return cleanup(head + tail)

    return insert(en_lines, miss_en), insert(ja_lines, miss_ja)

def eligible(repo: Path):
    try:
        if out(repo, 'status', '--porcelain').strip() != '':
            return False
        ahead = int(out(repo, 'rev-list', '--count', '@{u}..HEAD').strip() or '0')
        behind = int(out(repo, 'rev-list', '--count', 'HEAD..@{u}').strip() or '0')
        if ahead <= 0 or behind != 0:
            return False
        if out(repo, 'log', '-1', '--pretty=%an').strip() != 'Amil Khanzada':
            return False
        files = [x.strip() for x in out(repo, 'show', '--name-only', '--pretty=', 'HEAD').splitlines() if x.strip()]
        return all(f in ('README.md', 'README.ja.md') for f in files)
    except Exception:
        return False

def fix_and_push(repo: Path):
    name = repo.name
    p_en = repo / 'README.md'
    p_ja = repo / 'README.ja.md'
    if not p_en.exists() or not p_ja.exists():
        return ('SKIP', name, 'missing-readme-pair')

    head_en = norm(p_en.read_text(encoding='utf-8'))
    head_ja = norm(p_ja.read_text(encoding='utf-8'))
    up_en = norm(out_or_empty(repo, 'show', '@{u}:README.md')) or head_en
    up_ja = norm(out_or_empty(repo, 'show', '@{u}:README.ja.md')) or head_ja

    en_lines = scs(split_lines(up_en), split_lines(head_en))
    ja_lines = scs(split_lines(up_ja), split_lines(head_ja))
    en_lines, ja_lines = ensure_parity(en_lines, ja_lines)
    en_lines = ensure_license_tail(en_lines, ja=False)
    ja_lines = ensure_license_tail(ja_lines, ja=True)

    new_en = '\n'.join(cleanup(en_lines)) + '\n'
    new_ja = '\n'.join(cleanup(ja_lines)) + '\n'

    changed = False
    if new_en != head_en:
        p_en.write_text(new_en, encoding='utf-8'); changed = True
    if new_ja != head_ja:
        p_ja.write_text(new_ja, encoding='utf-8'); changed = True

    if changed:
        if run(repo, 'add', 'README.md', 'README.ja.md').returncode != 0:
            return ('ERR', name, 'git-add-failed')
        if run(repo, 'commit', '--amend', '--no-edit').returncode != 0:
            return ('ERR', name, 'amend-failed')

    head = out(repo, 'rev-parse', '--short', 'HEAD').strip()
    p = run(repo, 'push', 'origin', f'HEAD:refs/heads/{BRANCH}', timeout=300)
    if p.returncode != 0:
        return ('ERR', name, (p.stderr or p.stdout).strip().replace('\n', ' '))
    return ('OK', name, head)

repos = sorted([p for p in BASE.iterdir() if p.is_dir() and (p / '.git').exists()], key=lambda p: p.name.lower())
results = []
for repo in repos:
    if repo.name in EXCLUDE:
        continue
    if not eligible(repo):
        continue
    r = fix_and_push(repo)
    if r[0] == 'OK':
        results.append(r)
        print(f'OK|{r[1]}|{r[2]}')
    else:
        print(f'{r[0]}|{r[1]}|{r[2]}')
    if len(results) >= 10:
        break

print(f'SUMMARY|ok={len(results)}|branch={BRANCH}')
for _, name, head in results:
    print(f'COMMIT|{name}|https://github.com/code4fukui/{name}/commit/{head}')
