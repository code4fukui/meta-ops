import re
import subprocess
from pathlib import Path

BASE = Path('/home/ubuntu/code4fukui')
BRANCH = 'review-readme-20260316-12'
EXCLUDE = {
    'ASN1','chart-line','dinosaur-opendata','echizen-coast-kanko-reservation','EDINET',
    'find47','fukui-kanko-survey','fukui-kanko-trend-report','mikatagoko-kanko-reservation','moyo',
    'ar-vr360-viewer','fukui-kanko-reservation','fukui-kanko-trend-data','fukui-station-kanko-reservation','i18n',
    'ishikawa-kanko-survey','mp3-recorder','mp3-tag-editor','mp4player','mpy-cross-v6'
}
license_re = re.compile(r'\[LICENSE\]\(LICENSE\)|\[MIT License\]\(LICENSE\)|ライセンス|License', re.IGNORECASE)
md_link_re = re.compile(r'\[[^\]]+\]\([^\)]+\)')


def run(repo: Path, *args: str, timeout: int = 60):
    return subprocess.run(['git', '-C', str(repo), *args], text=True, capture_output=True, timeout=timeout)


def out(repo: Path, *args: str, timeout: int = 60) -> str:
    p = run(repo, *args, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip())
    return p.stdout


def clean_status(repo: Path) -> bool:
    return out(repo, 'status', '--porcelain').strip() == ''


def read_head_file(repo: Path, file_name: str) -> str:
    p = run(repo, 'show', f'HEAD:{file_name}')
    if p.returncode != 0:
        return ''
    return p.stdout


def read_upstream_file(repo: Path, file_name: str) -> str:
    p = run(repo, 'show', f'@{{u}}:{file_name}')
    if p.returncode != 0:
        return ''
    return p.stdout


def write_file(path: Path, content: str):
    path.write_text(content, encoding='utf-8')


def normalize_newlines(s: str) -> str:
    return s.replace('\r\n', '\n').replace('\r', '\n')


def ensure_license_tail_en(lines):
    content = '\n'.join(lines).strip('\n')
    if '[LICENSE](LICENSE)' in content:
        # Make sure a license section sits at the end.
        pass
    # Remove trailing blank lines.
    while lines and lines[-1].strip() == '':
        lines.pop()
    # Append canonical end section if end does not already include LICENSE link.
    tail = '\n'.join(lines[-6:])
    if '[LICENSE](LICENSE)' not in tail:
        if lines and lines[-1].strip() != '':
            lines.append('')
        lines.append('## License')
        lines.append('This project is licensed under the [MIT License](LICENSE).')
    return lines


def ensure_license_tail_ja(lines):
    while lines and lines[-1].strip() == '':
        lines.pop()
    tail = '\n'.join(lines[-6:])
    if '[LICENSE](LICENSE)' not in tail:
        if lines and lines[-1].strip() != '':
            lines.append('')
        lines.append('## ライセンス')
        lines.append('このプロジェクトは [MIT License](LICENSE) のもとで公開されています。')
    return lines


def restore_important_removed_lines(upstream_text: str, head_text: str, file_kind: str):
    up_lines = normalize_newlines(upstream_text).split('\n')
    hd_lines = normalize_newlines(head_text).split('\n')
    hd_set = set(hd_lines)

    # Lines that existed upstream but are now gone and likely important project info.
    restore = []
    for ln in up_lines:
        t = ln.strip()
        if not t:
            continue
        if t in hd_set:
            continue
        if license_re.search(t):
            continue
        is_info_line = (
            t.startswith('- ') or
            t.startswith('* ') or
            t.startswith('## ') or
            md_link_re.search(t) is not None or
            'http://' in t or 'https://' in t
        )
        if not is_info_line:
            continue
        # Avoid restoring translation-pointer boilerplate that can duplicate.
        if 'README.ja.md' in t and '日本語' in t:
            continue
        restore.append(ln)

    if not restore:
        return hd_lines

    # Add restored lines in a dedicated preserved section near end.
    marker = '## Preserved Notes' if file_kind == 'en' else '## 補足情報'
    if marker not in hd_lines:
        if hd_lines and hd_lines[-1].strip() != '':
            hd_lines.append('')
        hd_lines.append(marker)
    for ln in restore:
        if ln not in hd_set and ln not in hd_lines:
            hd_lines.append(ln)
    return hd_lines


def fix_repo(repo: Path):
    name = repo.name
    if not clean_status(repo):
        return ('SKIP', name, 'dirty-worktree')

    ahead = int(out(repo, 'rev-list', '--count', '@{u}..HEAD').strip() or '0')
    behind = int(out(repo, 'rev-list', '--count', 'HEAD..@{u}').strip() or '0')
    if ahead <= 0 or behind != 0:
        return ('SKIP', name, f'ahead={ahead},behind={behind}')

    author = out(repo, 'log', '-1', '--pretty=%an').strip()
    if author != 'Amil Khanzada':
        return ('SKIP', name, f'author={author}')

    files = [x.strip() for x in out(repo, 'show', '--name-only', '--pretty=', 'HEAD').splitlines() if x.strip()]
    if any(f not in ('README.md', 'README.ja.md') for f in files):
        return ('SKIP', name, 'non-readme-change')

    readme = repo / 'README.md'
    readme_ja = repo / 'README.ja.md'
    if not readme.exists() or not readme_ja.exists():
        return ('SKIP', name, 'missing-readme-pair')

    head_en = normalize_newlines(readme.read_text(encoding='utf-8'))
    head_ja = normalize_newlines(readme_ja.read_text(encoding='utf-8'))
    up_en = normalize_newlines(read_upstream_file(repo, 'README.md'))
    up_ja = normalize_newlines(read_upstream_file(repo, 'README.ja.md'))

    new_en_lines = restore_important_removed_lines(up_en, head_en, 'en')
    new_ja_lines = restore_important_removed_lines(up_ja, head_ja, 'ja')
    new_en_lines = ensure_license_tail_en(new_en_lines)
    new_ja_lines = ensure_license_tail_ja(new_ja_lines)

    new_en = '\n'.join(new_en_lines).rstrip() + '\n'
    new_ja = '\n'.join(new_ja_lines).rstrip() + '\n'

    changed = False
    if new_en != head_en:
        write_file(readme, new_en)
        changed = True
    if new_ja != head_ja:
        write_file(readme_ja, new_ja)
        changed = True

    if changed:
        p = run(repo, 'add', 'README.md', 'README.ja.md')
        if p.returncode != 0:
            return ('ERR', name, (p.stderr or p.stdout).strip())
        p = run(repo, 'commit', '--amend', '--no-edit')
        if p.returncode != 0:
            return ('ERR', name, (p.stderr or p.stdout).strip())

    head = out(repo, 'rev-parse', '--short', 'HEAD').strip()
    p = run(repo, 'push', 'origin', f'HEAD:refs/heads/{BRANCH}')
    if p.returncode != 0:
        return ('ERR', name, (p.stderr or p.stdout).strip())

    return ('OK', name, head)


repos = sorted([p for p in BASE.iterdir() if p.is_dir() and (p / '.git').exists()], key=lambda p: p.name.lower())
results = []
for rp in repos:
    if rp.name in EXCLUDE:
        continue
    try:
        r = fix_repo(rp)
    except Exception as e:
        r = ('ERR', rp.name, str(e))
    if r[0] == 'OK':
        results.append(r)
        print(f'OK|{r[1]}|{r[2]}')
    elif r[0] == 'ERR':
        print(f'ERR|{r[1]}|{r[2].replace(chr(10), " ")}')
    if len(results) >= 10:
        break

print(f'SUMMARY|ok={len(results)}|branch={BRANCH}')
for _, name, head in results:
    print(f'LINK|{name}|https://github.com/code4fukui/{name}/tree/{BRANCH}|https://github.com/code4fukui/{name}/commit/{head}')
