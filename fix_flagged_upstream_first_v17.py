import re
import subprocess
from pathlib import Path

BASE = Path('/home/ubuntu/code4fukui')
BRANCH = 'review-readme-20260317-17'
TARGETS = ['ndarray', 'ndb-opendata', 'nearornot', 'nekocam']
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


def out_or_empty(repo: Path, *args: str, timeout: int = 240) -> str:
    p = run(repo, *args, timeout=timeout)
    return p.stdout if p.returncode == 0 else ''


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


def h1_key(line: str):
    t = line.strip()
    if not t.startswith('# '):
        return None
    h = t[2:].strip().lower()
    h = re.sub(r'\s+', ' ', h)
    return h


def dedupe_h1(lines):
    seen = set()
    out_lines = []
    for ln in lines:
        k = h1_key(ln)
        if k is not None:
            if k in seen:
                continue
            seen.add(k)
        out_lines.append(ln)
    return out_lines


def remove_setext_title_if_h1_exists(lines):
    # Remove leading setext title pair if an H1 exists later.
    has_h1 = any(ln.strip().startswith('# ') for ln in lines)
    if not has_h1:
        return lines
    if len(lines) >= 2:
        title = lines[0].strip()
        underline = lines[1].strip()
        if title and re.fullmatch(r'[=-]{3,}', underline):
            return lines[2:]
    return lines


def find_first_h1(lines):
    for i, ln in enumerate(lines):
        if ln.strip().startswith('# '):
            return i
    return -1


def ensure_top_link(lines, link_line):
    # Remove all occurrences including quoted forms.
    stripped = []
    for ln in lines:
        s = ln.strip()
        if s == link_line or s == f'> {link_line}':
            continue
        stripped.append(ln)
    lines = stripped

    i = find_first_h1(lines)
    if i < 0:
        lines = [link_line, ''] + lines
        return cleanup_blank(lines)

    insert_at = i + 1
    if insert_at < len(lines) and lines[insert_at].strip() != '':
        lines.insert(insert_at, '')
        insert_at += 1
    lines.insert(insert_at, link_line)
    if insert_at + 1 < len(lines) and lines[insert_at + 1].strip() != '':
        lines.insert(insert_at + 1, '')
    return cleanup_blank(lines)


def find_license_idx(lines):
    for i, ln in enumerate(lines):
        if ln.strip().lower() in ('## license', '## ライセンス'):
            return i
    return len(lines)


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
            b = f'- [{t}]({u})'
            if b not in head:
                head.append(b)
        if tail and tail[0].strip() != '':
            head.append('')
        return cleanup_blank(head + tail)

    return inject(en_lines, miss_en), inject(ja_lines, miss_ja)


def build_from_upstream(repo: Path, file_path: str, fallback_text: str):
    up = out_or_empty(repo, 'show', f'@{{u}}:{file_path}')
    return norm(up) if up else norm(fallback_text)


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

        cur_en = norm(p_en.read_text(encoding='utf-8'))
        cur_ja = norm(p_ja.read_text(encoding='utf-8'))

        en_lines = build_from_upstream(repo, 'README.md', cur_en).split('\n')
        ja_lines = build_from_upstream(repo, 'README.ja.md', cur_ja).split('\n')

        en_lines = remove_setext_title_if_h1_exists(en_lines)
        ja_lines = remove_setext_title_if_h1_exists(ja_lines)
        en_lines = dedupe_h1(en_lines)
        ja_lines = dedupe_h1(ja_lines)

        en_lines = ensure_top_link(en_lines, JA_LINK_LINE)
        ja_lines = ensure_top_link(ja_lines, EN_LINK_LINE)

        en_lines, ja_lines = ensure_link_parity(en_lines, ja_lines)
        en_lines = ensure_license_tail(en_lines, ja=False)
        ja_lines = ensure_license_tail(ja_lines, ja=True)

        new_en = '\n'.join(cleanup_blank(en_lines)) + '\n'
        new_ja = '\n'.join(cleanup_blank(ja_lines)) + '\n'

        changed = False
        if new_en != cur_en:
            p_en.write_text(new_en, encoding='utf-8')
            changed = True
        if new_ja != cur_ja:
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


for n in TARGETS:
    r = process_repo(n)
    if r[0] == 'OK':
        print(f'OK|{r[1]}|{r[2]}')
        print(f'COMMIT|{r[1]}|https://github.com/code4fukui/{r[1]}/commit/{r[2]}')
    else:
        print(f'ERR|{r[1]}|{r[2]}')
