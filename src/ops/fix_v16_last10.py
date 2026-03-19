import re
import subprocess
from pathlib import Path

BASE = Path('/home/ubuntu/code4fukui')
BRANCH = 'review-readme-20260317-16'
TARGETS = [
    'ndarray', 'ndarray-ops', 'ndb-dashboard', 'ndb-opendata', 'nearornot',
    'nekocam', 'neomo.css', 'nesly-assembler', 'next-course-of-study', 'niid_go_jp'
]
JA_LINK_LINE = '日本語のREADMEはこちらです: [README.ja.md](README.ja.md)'
EN_LINK_LINE = 'English README is here: [README.md](README.md)'
md_link_re = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')


def run(repo: Path, *args: str, timeout: int = 240):
    return subprocess.run(['git', '-C', str(repo), *args], text=True, capture_output=True, timeout=timeout)


def out(repo: Path, *args: str, timeout: int = 240) -> str:
    p = run(repo, *args, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip())
    return p.stdout


def norm(s: str) -> str:
    return s.replace('\r\n', '\n').replace('\r', '\n')


def cleanup_blank(lines):
    out_lines = []
    prev_blank = False
    for ln in lines:
        blank = ln.strip() == ''
        if blank and prev_blank:
            continue
        out_lines.append(ln)
        prev_blank = blank
    while out_lines and out_lines[-1].strip() == '':
        out_lines.pop()
    return out_lines


def heading_key(line: str):
    t = line.strip()
    if not t.startswith('#'):
        return None
    # Normalize heading text for dedupe (case-insensitive, ignore punctuation and extra spaces)
    h = re.sub(r'^#+\s*', '', t)
    h = re.sub(r'[^a-zA-Z0-9\u3040-\u30ff\u3400-\u9fff]+', ' ', h).strip().lower()
    return h


def dedupe_headings(lines):
    seen = set()
    out_lines = []
    for ln in lines:
        hk = heading_key(ln)
        if hk is not None:
            if hk in seen:
                continue
            seen.add(hk)
        out_lines.append(ln)
    return out_lines


def find_first_h1(lines):
    for i, ln in enumerate(lines):
        if ln.strip().startswith('# '):
            return i
    return -1


def ensure_line_near_top(lines, line):
    # Remove all existing duplicates and insert exactly once near top (after first H1).
    lines = [ln for ln in lines if ln.strip() != line]
    i = find_first_h1(lines)
    if i < 0:
        return [line, ''] + lines
    insert_at = i + 1
    # Keep one blank between heading and link line if possible.
    if insert_at < len(lines) and lines[insert_at].strip() != '':
        lines.insert(insert_at, '')
        insert_at += 1
    lines.insert(insert_at, line)
    # Ensure blank after link line unless next line already blank/end.
    if insert_at + 1 < len(lines) and lines[insert_at + 1].strip() != '':
        lines.insert(insert_at + 1, '')
    return lines


def extract_code4fukui_links(lines):
    links = []
    seen = set()
    for ln in lines:
        for m in md_link_re.finditer(ln):
            txt, url = m.group(1).strip(), m.group(2).strip()
            if 'github.com/code4fukui/' not in url:
                continue
            k = (txt, url)
            if k in seen:
                continue
            seen.add(k)
            links.append((txt, url))
    return links


def find_license_idx(lines):
    for i, ln in enumerate(lines):
        if ln.strip().lower() in ('## license', '## ライセンス'):
            return i
    return len(lines)


def ensure_link_parity(en_lines, ja_lines):
    en_links = extract_code4fukui_links(en_lines)
    ja_links = extract_code4fukui_links(ja_lines)
    en_urls = {u for _, u in en_links}
    ja_urls = {u for _, u in ja_links}

    miss_ja = [(t, u) for t, u in en_links if u not in ja_urls]
    miss_en = [(t, u) for t, u in ja_links if u not in en_urls]

    def inject(lines, items):
        if not items:
            return lines
        idx = find_license_idx(lines)
        head, tail = lines[:idx], lines[idx:]
        if head and head[-1].strip() != '':
            head.append('')
        for t, u in items:
            bullet = f'- [{t}]({u})'
            if bullet not in head:
                head.append(bullet)
        if tail and tail[0].strip() != '':
            head.append('')
        return head + tail

    en_lines = inject(en_lines, miss_en)
    ja_lines = inject(ja_lines, miss_ja)
    return en_lines, ja_lines


def ensure_license_tail(lines, ja=False):
    idx = find_license_idx(lines)
    body = cleanup_blank(lines[:idx])
    if body and body[-1].strip() != '':
        body.append('')
    if ja:
        body += ['## ライセンス', 'このプロジェクトは [MIT License](LICENSE) のもとで公開されています。']
    else:
        body += ['## License', 'This project is licensed under the [MIT License](LICENSE).']
    return cleanup_blank(body)


def process_repo(name: str):
    repo = BASE / name
    if not repo.exists():
        return ('ERR', name, 'repo-not-found')
    try:
        if out(repo, 'status', '--porcelain').strip() != '':
            return ('ERR', name, 'dirty-worktree')
        ahead = int(out(repo, 'rev-list', '--count', '@{u}..HEAD').strip() or '0')
        behind = int(out(repo, 'rev-list', '--count', 'HEAD..@{u}').strip() or '0')
        if ahead <= 0 or behind != 0:
            return ('ERR', name, f'ahead={ahead},behind={behind}')

        files = [x.strip() for x in out(repo, 'show', '--name-only', '--pretty=', 'HEAD').splitlines() if x.strip()]
        if any(f not in ('README.md', 'README.ja.md') for f in files):
            return ('ERR', name, 'non-readme-change')

        p_en = repo / 'README.md'
        p_ja = repo / 'README.ja.md'
        if not p_en.exists() or not p_ja.exists():
            return ('ERR', name, 'missing-readme-pair')

        en_lines = norm(p_en.read_text(encoding='utf-8')).split('\n')
        ja_lines = norm(p_ja.read_text(encoding='utf-8')).split('\n')

        en_lines = dedupe_headings(en_lines)
        ja_lines = dedupe_headings(ja_lines)

        en_lines = ensure_line_near_top(en_lines, JA_LINK_LINE)
        ja_lines = ensure_line_near_top(ja_lines, EN_LINK_LINE)

        en_lines, ja_lines = ensure_link_parity(en_lines, ja_lines)
        en_lines = ensure_license_tail(en_lines, ja=False)
        ja_lines = ensure_license_tail(ja_lines, ja=True)

        new_en = '\n'.join(cleanup_blank(en_lines)) + '\n'
        new_ja = '\n'.join(cleanup_blank(ja_lines)) + '\n'

        changed = False
        if new_en != norm(p_en.read_text(encoding='utf-8')):
            p_en.write_text(new_en, encoding='utf-8')
            changed = True
        if new_ja != norm(p_ja.read_text(encoding='utf-8')):
            p_ja.write_text(new_ja, encoding='utf-8')
            changed = True

        if changed:
            if run(repo, 'add', 'README.md', 'README.ja.md').returncode != 0:
                return ('ERR', name, 'git-add-failed')
            if run(repo, 'commit', '--amend', '--no-edit').returncode != 0:
                return ('ERR', name, 'amend-failed')

        head = out(repo, 'rev-parse', '--short', 'HEAD').strip()
        p = run(repo, 'push', 'origin', f'HEAD:refs/heads/{BRANCH}', timeout=360)
        if p.returncode != 0:
            return ('ERR', name, (p.stderr or p.stdout).strip().replace('\n', ' '))
        return ('OK', name, head)
    except Exception as e:
        return ('ERR', name, str(e).replace('\n', ' '))


ok = []
for n in TARGETS:
    r = process_repo(n)
    if r[0] == 'OK':
        ok.append(r)
        print(f'OK|{r[1]}|{r[2]}')
        print(f'COMMIT|{r[1]}|https://github.com/code4fukui/{r[1]}/commit/{r[2]}')
    else:
        print(f'ERR|{r[1]}|{r[2]}')

print(f'SUMMARY|ok={len(ok)}|branch={BRANCH}')
