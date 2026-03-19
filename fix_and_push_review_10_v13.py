import re
import subprocess
from pathlib import Path

BASE = Path('/home/ubuntu/code4fukui')
BRANCH = 'review-readme-20260316-13'
# Prioritize corrective repos first.
PRIORITY = ['mp3-tag-editor', 'fukui-kanko-trend-data']
EXCLUDE = {
    'ASN1','chart-line','dinosaur-opendata','echizen-coast-kanko-reservation','EDINET',
    'find47','fukui-kanko-survey','fukui-kanko-trend-report','mikatagoko-kanko-reservation','moyo',
    'ar-vr360-viewer','fukui-kanko-reservation','fukui-kanko-trend-data','fukui-station-kanko-reservation','i18n',
    'ishikawa-kanko-survey','mp3-recorder','mp3-tag-editor','mp4player','mpy-cross-v6',
    'muno3','music-api-js','music-brainstorming-bgm','music-fnct-sabae','music-future-with-you','music-kanko-dx','music-new-shoshinge'
}
md_link = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')


def run(repo: Path, *args: str, timeout: int = 120):
    return subprocess.run(['git', '-C', str(repo), *args], text=True, capture_output=True, timeout=timeout)


def out(repo: Path, *args: str, timeout: int = 120) -> str:
    p = run(repo, *args, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip())
    return p.stdout


def out_or_empty(repo: Path, *args: str, timeout: int = 120) -> str:
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
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        ai = a[i]
        row = dp[i]
        next_row = dp[i + 1]
        for j in range(m - 1, -1, -1):
            if ai == b[j]:
                row[j] = 1 + next_row[j + 1]
            else:
                row[j] = row[j + 1] if row[j + 1] >= next_row[j] else next_row[j]
    i = j = 0
    seq = []
    while i < n and j < m:
        if a[i] == b[j]:
            seq.append(a[i])
            i += 1
            j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return seq


def shortest_common_supersequence(a, b):
    common = lcs(a, b)
    i = j = k = 0
    out_lines = []
    while k < len(common):
        c = common[k]
        while i < len(a) and a[i] != c:
            out_lines.append(a[i])
            i += 1
        while j < len(b) and b[j] != c:
            out_lines.append(b[j])
            j += 1
        out_lines.append(c)
        i += 1
        j += 1
        k += 1
    out_lines.extend(a[i:])
    out_lines.extend(b[j:])
    return out_lines


def cleanup_lines(lines):
    # Keep content intact; only trim repeated blank lines.
    out_l = []
    prev_blank = False
    for ln in lines:
        blank = (ln.strip() == '')
        if blank and prev_blank:
            continue
        out_l.append(ln)
        prev_blank = blank
    while out_l and out_l[-1].strip() == '':
        out_l.pop()
    return out_l


def find_license_index(lines):
    for i, ln in enumerate(lines):
        t = ln.strip().lower()
        if t in ('## license', '## ライセンス'):
            return i
    return len(lines)


def ensure_license_tail(lines, ja=False):
    lines = cleanup_lines(lines)
    lic_i = find_license_index(lines)
    body = lines[:lic_i]
    if body and body[-1].strip() != '':
        body.append('')
    if ja:
        body.append('## ライセンス')
        body.append('このプロジェクトは [MIT License](LICENSE) のもとで公開されています。')
    else:
        body.append('## License')
        body.append('This project is licensed under the [MIT License](LICENSE).')
    return cleanup_lines(body)


def extract_repo_links(lines):
    links = []
    seen = set()
    for ln in lines:
        m = md_link.search(ln)
        if not m:
            continue
        text, url = m.group(1).strip(), m.group(2).strip()
        if 'github.com/code4fukui/' not in url:
            continue
        key = (text, url)
        if key in seen:
            continue
        seen.add(key)
        links.append((text, url))
    return links


def ensure_link_parity(en_lines, ja_lines):
    en_links = extract_repo_links(en_lines)
    ja_links = extract_repo_links(ja_lines)
    en_set = {u for _, u in en_links}
    ja_set = {u for _, u in ja_links}

    missing_in_ja = [(t, u) for t, u in en_links if u not in ja_set]
    missing_in_en = [(t, u) for t, u in ja_links if u not in en_set]

    def insert_before_license(lines, items):
        if not items:
            return lines
        idx = find_license_index(lines)
        head = lines[:idx]
        tail = lines[idx:]
        if head and head[-1].strip() != '':
            head.append('')
        for t, u in items:
            head.append(f'- [{t}]({u})')
        if tail and tail[0].strip() != '':
            head.append('')
        return cleanup_lines(head + tail)

    ja_lines = insert_before_license(ja_lines, missing_in_ja)
    en_lines = insert_before_license(en_lines, missing_in_en)
    return en_lines, ja_lines


def candidate_order(all_repos):
    by_name = {p.name: p for p in all_repos}
    ordered = []
    for n in PRIORITY:
        if n in by_name:
            ordered.append(by_name[n])
    for p in all_repos:
        if p.name not in PRIORITY:
            ordered.append(p)
    return ordered


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
        if any(f not in ('README.md', 'README.ja.md') for f in files):
            return False
        return True
    except Exception:
        return False


def fix_and_push(repo: Path):
    name = repo.name
    readme = repo / 'README.md'
    readme_ja = repo / 'README.ja.md'
    if not readme.exists() or not readme_ja.exists():
        return ('SKIP', name, 'missing-readme-pair')

    head_en = norm(readme.read_text(encoding='utf-8'))
    head_ja = norm(readme_ja.read_text(encoding='utf-8'))
    up_en = norm(out_or_empty(repo, 'show', '@{u}:README.md')) or head_en
    up_ja = norm(out_or_empty(repo, 'show', '@{u}:README.ja.md')) or head_ja

    merged_en = shortest_common_supersequence(split_lines(up_en), split_lines(head_en))
    merged_ja = shortest_common_supersequence(split_lines(up_ja), split_lines(head_ja))

    merged_en = ensure_license_tail(merged_en, ja=False)
    merged_ja = ensure_license_tail(merged_ja, ja=True)
    merged_en, merged_ja = ensure_link_parity(merged_en, merged_ja)
    merged_en = ensure_license_tail(merged_en, ja=False)
    merged_ja = ensure_license_tail(merged_ja, ja=True)

    new_en = '\n'.join(cleanup_lines(merged_en)) + '\n'
    new_ja = '\n'.join(cleanup_lines(merged_ja)) + '\n'

    changed = False
    if new_en != head_en:
        readme.write_text(new_en, encoding='utf-8')
        changed = True
    if new_ja != head_ja:
        readme_ja.write_text(new_ja, encoding='utf-8')
        changed = True

    if changed:
        if run(repo, 'add', 'README.md', 'README.ja.md').returncode != 0:
            return ('ERR', name, 'git-add-failed')
        if run(repo, 'commit', '--amend', '--no-edit').returncode != 0:
            return ('ERR', name, 'amend-failed')

    head = out(repo, 'rev-parse', '--short', 'HEAD').strip()
    p = run(repo, 'push', 'origin', f'HEAD:refs/heads/{BRANCH}', timeout=240)
    if p.returncode != 0:
        return ('ERR', name, (p.stderr or p.stdout).strip().replace('\n', ' '))
    return ('OK', name, head)


repos = sorted([p for p in BASE.iterdir() if p.is_dir() and (p / '.git').exists()], key=lambda p: p.name.lower())
ordered = candidate_order(repos)
results = []
for rp in ordered:
    if rp.name in EXCLUDE and rp.name not in PRIORITY:
        continue
    if not eligible(rp):
        continue
    r = fix_and_push(rp)
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
