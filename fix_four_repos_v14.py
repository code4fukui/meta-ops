import re
import subprocess
from pathlib import Path

BASE = Path('/home/ubuntu/code4fukui')
BRANCH = 'review-readme-20260316-14'
TARGETS = ['music-pioneerpork', 'music-player', 'nanoevents', 'nanoid']

BAD_EN_LINE = 'The songs and metadata are sourced from the [music-opendata-fukui](https://github.com/code4fukui/music-opendata-fukui) project.'

md_link_re = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')

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

def key(line: str) -> str:
    return ' '.join(line.strip().split()).lower()

def merge_upstream_first(up_lines, head_lines):
    merged = []
    seen = set()
    for ln in up_lines + head_lines:
        k = key(ln)
        # Keep intentional blank lines but squash runs later.
        if ln.strip() != '' and k in seen:
            continue
        if ln.strip() != '':
            seen.add(k)
        merged.append(ln)
    return merged

def squash_blank_runs(lines):
    out_lines = []
    prev_blank = False
    for ln in lines:
        is_blank = (ln.strip() == '')
        if is_blank and prev_blank:
            continue
        out_lines.append(ln)
        prev_blank = is_blank
    while out_lines and out_lines[-1].strip() == '':
        out_lines.pop()
    return out_lines

def drop_known_bad(lines):
    out_lines = []
    for ln in lines:
        if ln.strip() == BAD_EN_LINE:
            continue
        out_lines.append(ln)
    return out_lines

def dedupe_nanoid_titles(lines):
    # Keep first heading variant only.
    out_lines = []
    seen_h1 = set()
    for ln in lines:
        t = ln.strip().lower()
        if t in ('# nano id', '# nanoid'):
            if 'nanoid-title' in seen_h1:
                continue
            seen_h1.add('nanoid-title')
            out_lines.append('# Nano ID')
            continue
        out_lines.append(ln)
    return out_lines

def ensure_license_tail(lines, ja=False):
    # Remove existing trailing license section headers if any; re-append canonical tail.
    idx = len(lines)
    for i, ln in enumerate(lines):
        t = ln.strip().lower()
        if t in ('## license', '## ライセンス'):
            idx = i
            break
    body = squash_blank_runs(lines[:idx])
    if body and body[-1].strip() != '':
        body.append('')
    if ja:
        body.append('## ライセンス')
        body.append('このプロジェクトは [MIT License](LICENSE) のもとで公開されています。')
    else:
        body.append('## License')
        body.append('This project is licensed under the [MIT License](LICENSE).')
    return squash_blank_runs(body)

def extract_links(lines):
    links = []
    seen = set()
    for ln in lines:
        for m in md_link_re.finditer(ln):
            txt, url = m.group(1).strip(), m.group(2).strip()
            k = (txt, url)
            if k in seen:
                continue
            seen.add(k)
            links.append((txt, url))
    return links

def ensure_link_parity(en_lines, ja_lines):
    en_links = extract_links(en_lines)
    ja_links = extract_links(ja_lines)
    en_urls = {u for _, u in en_links}
    ja_urls = {u for _, u in ja_links}

    missing_ja = [(t, u) for t, u in en_links if u not in ja_urls]
    missing_en = [(t, u) for t, u in ja_links if u not in en_urls]

    def insert_before_license(lines, items):
        if not items:
            return lines
        idx = len(lines)
        for i, ln in enumerate(lines):
            if ln.strip().lower() in ('## license', '## ライセンス'):
                idx = i
                break
        head, tail = lines[:idx], lines[idx:]
        if head and head[-1].strip() != '':
            head.append('')
        for t, u in items:
            bullet = f'- [{t}]({u})'
            if bullet not in head:
                head.append(bullet)
        if tail and tail[0].strip() != '':
            head.append('')
        return squash_blank_runs(head + tail)

    ja_lines = insert_before_license(ja_lines, missing_ja)
    en_lines = insert_before_license(en_lines, missing_en)
    return en_lines, ja_lines

def fix_one(repo_name: str):
    repo = BASE / repo_name
    if not repo.exists():
        return ('ERR', repo_name, 'repo-not-found')
    if out(repo, 'status', '--porcelain').strip() != '':
        return ('ERR', repo_name, 'dirty-worktree')

    ahead = int(out(repo, 'rev-list', '--count', '@{u}..HEAD').strip() or '0')
    behind = int(out(repo, 'rev-list', '--count', 'HEAD..@{u}').strip() or '0')
    if ahead <= 0 or behind != 0:
        return ('ERR', repo_name, f'ahead={ahead},behind={behind}')

    files = [x.strip() for x in out(repo, 'show', '--name-only', '--pretty=', 'HEAD').splitlines() if x.strip()]
    if any(f not in ('README.md', 'README.ja.md') for f in files):
        return ('ERR', repo_name, 'non-readme-change')

    p_en = repo / 'README.md'
    p_ja = repo / 'README.ja.md'
    if not p_en.exists() or not p_ja.exists():
        return ('ERR', repo_name, 'missing-readme-pair')

    head_en = norm(p_en.read_text(encoding='utf-8')).split('\n')
    head_ja = norm(p_ja.read_text(encoding='utf-8')).split('\n')
    up_en = norm(out_or_empty(repo, 'show', '@{u}:README.md')).split('\n')
    up_ja = norm(out_or_empty(repo, 'show', '@{u}:README.ja.md')).split('\n')
    if up_en == ['']:
        up_en = head_en
    if up_ja == ['']:
        up_ja = head_ja

    new_en = merge_upstream_first(up_en, head_en)
    new_ja = merge_upstream_first(up_ja, head_ja)

    new_en = drop_known_bad(new_en)
    if repo_name == 'nanoid':
        new_en = dedupe_nanoid_titles(new_en)
        new_ja = dedupe_nanoid_titles(new_ja)

    # Ensure specific lines user flagged in music-player are present in both files.
    if repo_name == 'music-player':
        must = [
            '- [opendata-songs](https://github.com/code4fukui/opendata-songs/)',
            '- [MediaSession API](https://developer.mozilla.org/en-US/docs/Web/API/MediaSession)',
        ]
        for m in must:
            if m not in new_en:
                new_en.append(m)
            if m not in new_ja:
                new_ja.append(m)

    new_en, new_ja = ensure_link_parity(new_en, new_ja)
    new_en = ensure_license_tail(new_en, ja=False)
    new_ja = ensure_license_tail(new_ja, ja=True)

    # Deduplicate exact sentence in nanoevents if repeated by merge.
    if repo_name == 'nanoevents':
        sent = 'Because Nano Events API has only just 2 methods, you could just create proxy methods in your class or encapsulate them entirely.'
        seen = False
        dedup = []
        for ln in new_en:
            if ln.strip() == sent:
                if seen:
                    continue
                seen = True
            dedup.append(ln)
        new_en = dedup

    final_en = '\n'.join(squash_blank_runs(new_en)) + '\n'
    final_ja = '\n'.join(squash_blank_runs(new_ja)) + '\n'

    changed = False
    if final_en != norm(p_en.read_text(encoding='utf-8')):
        p_en.write_text(final_en, encoding='utf-8')
        changed = True
    if final_ja != norm(p_ja.read_text(encoding='utf-8')):
        p_ja.write_text(final_ja, encoding='utf-8')
        changed = True

    if changed:
        if run(repo, 'add', 'README.md', 'README.ja.md').returncode != 0:
            return ('ERR', repo_name, 'git-add-failed')
        if run(repo, 'commit', '--amend', '--no-edit').returncode != 0:
            return ('ERR', repo_name, 'amend-failed')

    head = out(repo, 'rev-parse', '--short', 'HEAD').strip()
    p = run(repo, 'push', 'origin', f'HEAD:refs/heads/{BRANCH}', timeout=300)
    if p.returncode != 0:
        return ('ERR', repo_name, (p.stderr or p.stdout).strip().replace('\n', ' '))
    return ('OK', repo_name, head)


for name in TARGETS:
    try:
        r = fix_one(name)
    except Exception as e:
        r = ('ERR', name, str(e).replace('\n', ' '))
    if r[0] == 'OK':
        print(f'OK|{r[1]}|{r[2]}')
        print(f'COMMIT|{r[1]}|https://github.com/code4fukui/{r[1]}/commit/{r[2]}')
    else:
        print(f'ERR|{r[1]}|{r[2]}')
