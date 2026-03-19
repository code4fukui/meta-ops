import subprocess
from pathlib import Path
import re

BASE = Path('/home/ubuntu/code4fukui')
BRANCH = 'review-readme-20260316-12'
EXCLUDE = {
    'ASN1','chart-line','dinosaur-opendata','echizen-coast-kanko-reservation','EDINET',
    'find47','fukui-kanko-survey','fukui-kanko-trend-report','mikatagoko-kanko-reservation','moyo',
    'ar-vr360-viewer','fukui-kanko-reservation','fukui-kanko-trend-data','fukui-station-kanko-reservation','i18n',
    'ishikawa-kanko-survey','mp3-recorder','mp3-tag-editor','mp4player','mpy-cross-v6',
    'muno3','music-api-js','music-brainstorming-bgm','music-fnct-sabae','music-future-with-you','music-kanko-dx','music-new-shoshinge'
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

def normalize_newlines(s: str) -> str:
    return s.replace('\r\n', '\n').replace('\r', '\n')

def ensure_license_tail_en(lines):
    while lines and lines[-1].strip() == '':
        lines.pop()
    if '[LICENSE](LICENSE)' not in '\n'.join(lines[-6:]):
        if lines and lines[-1].strip() != '':
            lines.append('')
        lines.extend(['## License', 'This project is licensed under the [MIT License](LICENSE).'])
    return lines

def ensure_license_tail_ja(lines):
    while lines and lines[-1].strip() == '':
        lines.pop()
    if '[LICENSE](LICENSE)' not in '\n'.join(lines[-6:]):
        if lines and lines[-1].strip() != '':
            lines.append('')
        lines.extend(['## ライセンス', 'このプロジェクトは [MIT License](LICENSE) のもとで公開されています。'])
    return lines

def restore_important_removed_lines(upstream_text: str, head_text: str, file_kind: str):
    up_lines = normalize_newlines(upstream_text).split('\n')
    hd_lines = normalize_newlines(head_text).split('\n')
    hd_set = set(hd_lines)
    restore = []
    for ln in up_lines:
        t = ln.strip()
        if not t or t in hd_set or license_re.search(t):
            continue
        if t.startswith('- ') or t.startswith('* ') or t.startswith('## ') or md_link_re.search(t) is not None or 'http://' in t or 'https://' in t:
            if not ('README.ja.md' in t and '日本語' in t):
                restore.append(ln)
    if restore:
        marker = '## Preserved Notes' if file_kind == 'en' else '## 補足情報'
        if marker not in hd_lines:
            if hd_lines and hd_lines[-1].strip() != '':
                hd_lines.append('')
            hd_lines.append(marker)
        for ln in restore:
            if ln not in hd_lines:
                hd_lines.append(ln)
    return hd_lines

def fix_repo(repo: Path):
    ahead = int(out(repo, 'rev-list', '--count', '@{u}..HEAD').strip() or '0')
    behind = int(out(repo, 'rev-list', '--count', 'HEAD..@{u}').strip() or '0')
    if ahead <= 0 or behind != 0:
        return None
    if out(repo, 'log', '-1', '--pretty=%an').strip() != 'Amil Khanzada':
        return None
    files = [x.strip() for x in out(repo, 'show', '--name-only', '--pretty=', 'HEAD').splitlines() if x.strip()]
    if any(f not in ('README.md', 'README.ja.md') for f in files):
        return None
    if out(repo, 'status', '--porcelain').strip() != '':
        return None

    readme = repo / 'README.md'
    readme_ja = repo / 'README.ja.md'
    if not readme.exists() or not readme_ja.exists():
        return None
    head_en = normalize_newlines(readme.read_text(encoding='utf-8'))
    head_ja = normalize_newlines(readme_ja.read_text(encoding='utf-8'))
    up_en = out(repo, 'show', '@{u}:README.md')
    up_ja = out(repo, 'show', '@{u}:README.ja.md')

    new_en = '\n'.join(ensure_license_tail_en(restore_important_removed_lines(up_en, head_en, 'en'))).rstrip() + '\n'
    new_ja = '\n'.join(ensure_license_tail_ja(restore_important_removed_lines(up_ja, head_ja, 'ja'))).rstrip() + '\n'
    changed = False
    if new_en != head_en:
        readme.write_text(new_en, encoding='utf-8')
        changed = True
    if new_ja != head_ja:
        readme_ja.write_text(new_ja, encoding='utf-8')
        changed = True
    if changed:
        if run(repo, 'add', 'README.md', 'README.ja.md').returncode != 0:
            return None
        if run(repo, 'commit', '--amend', '--no-edit').returncode != 0:
            return None
    head = out(repo, 'rev-parse', '--short', 'HEAD').strip()
    if run(repo, 'push', 'origin', f'HEAD:refs/heads/{BRANCH}').returncode != 0:
        return None
    return head

ok = []
for repo in sorted([p for p in BASE.iterdir() if p.is_dir() and (p / '.git').exists()], key=lambda p: p.name.lower()):
    if repo.name in EXCLUDE:
        continue
    try:
        head = fix_repo(repo)
        if head:
            ok.append((repo.name, head))
            print(f'OK|{repo.name}|{head}')
            if len(ok) >= 3:
                break
    except Exception:
        pass
print(f'SUMMARY|ok={len(ok)}|branch={BRANCH}')
for name, head in ok:
    print(f'LINK|{name}|https://github.com/code4fukui/{name}/tree/{BRANCH}|https://github.com/code4fukui/{name}/commit/{head}')
