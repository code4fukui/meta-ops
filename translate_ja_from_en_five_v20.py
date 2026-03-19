import json
import re
import subprocess
from pathlib import Path
import boto3

BASE = Path('/home/ubuntu/code4fukui')
BRANCH = 'review-readme-20260317-20'
MODEL_ID = 'anthropic.claude-3-haiku-20240307-v1:0'
REGION = 'us-east-1'
EXCLUDE = {
    'ASN1','chart-line','dinosaur-opendata','echizen-coast-kanko-reservation','EDINET','find47','fukui-kanko-survey','fukui-kanko-trend-report','mikatagoko-kanko-reservation','moyo',
    'ar-vr360-viewer','fukui-kanko-reservation','fukui-kanko-trend-data','fukui-station-kanko-reservation','i18n','ishikawa-kanko-survey','mp3-recorder','mp3-tag-editor','mp4player','mpy-cross-v6',
    'muno3','music-api-js','music-brainstorming-bgm','music-fnct-sabae','music-future-with-you','music-kanko-dx','music-new-shoshinge',
    'music-opendata-fukui','music-pioneerpork','music-player','mykkrec','name2pic','nanoevents','nanoid','natural-earth-geojson',
    'ndarray','ndarray-ops','ndb-dashboard','ndb-opendata','nearornot','nekocam','neomo.css','nesly-assembler','next-course-of-study','niid_go_jp',
    'node-ecdsa-sig-formatter','node-html-parser','node-jws','node-mailchecker','node-red-contrib-togglebutton'
}
JA_LINK_LINE = '日本語のREADMEはこちらです: [README.ja.md](README.ja.md)'
EN_LINK_LINE = 'English README is here: [README.md](README.md)'

bedrock = boto3.client('bedrock-runtime', region_name=REGION)


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
    prev = False
    for ln in lines:
        b = ln.strip() == ''
        if b and prev:
            continue
        out_lines.append(ln)
        prev = b
    while out_lines and out_lines[-1].strip() == '':
        out_lines.pop()
    return out_lines


def find_first_h1(lines):
    for i, ln in enumerate(lines):
        if ln.strip().startswith('# '):
            return i
    return -1


def ensure_top_link(lines, link_line):
    lines = [ln for ln in lines if ln.strip() not in (link_line, f'> {link_line}')]
    i = find_first_h1(lines)
    if i < 0:
        return cleanup_blank([link_line, ''] + lines)
    pos = i + 1
    if pos < len(lines) and lines[pos].strip() != '':
        lines.insert(pos, '')
        pos += 1
    lines.insert(pos, link_line)
    if pos + 1 < len(lines) and lines[pos + 1].strip() != '':
        lines.insert(pos + 1, '')
    return cleanup_blank(lines)


def find_license_idx(lines):
    for i, ln in enumerate(lines):
        if ln.strip().lower() in ('## license', '## ライセンス'):
            return i
    return len(lines)


def ensure_license_tail(lines, ja=False):
    body = cleanup_blank(lines[:find_license_idx(lines)])
    if body and body[-1].strip() != '':
        body.append('')
    if ja:
        body += ['## ライセンス', 'このプロジェクトは [MIT License](LICENSE) のもとで公開されています。']
    else:
        body += ['## License', 'This project is licensed under the [MIT License](LICENSE).']
    return cleanup_blank(body)


def split_by_sections(md: str):
    lines = norm(md).split('\n')
    chunks = []
    cur = []
    for ln in lines:
        if ln.startswith('## ') and cur:
            chunks.append('\n'.join(cur).strip('\n'))
            cur = [ln]
        else:
            cur.append(ln)
    if cur:
        chunks.append('\n'.join(cur).strip('\n'))
    return [c for c in chunks if c.strip()]


def call_bedrock(prompt: str, max_tokens: int = 1400):
    resp = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps({
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': max_tokens,
            'messages': [{'role': 'user', 'content': prompt}],
        }),
    )
    return json.loads(resp['body'].read())['content'][0]['text'].strip()


def translate_chunk(chunk: str):
    prompt = f'''Translate the following README markdown chunk from English to Japanese.
Rules:
- Preserve the same markdown structure, heading levels, lists, and section order.
- Preserve all links and URLs exactly.
- Preserve code blocks exactly (do not translate code).
- Do not drop any sentences.
- Output markdown only.

English markdown chunk:
{chunk}
'''
    return call_bedrock(prompt)


def translate_full_en_to_ja(en_md: str):
    chunks = split_by_sections(en_md)
    ja_chunks = []
    for c in chunks:
        ja_chunks.append(translate_chunk(c))
    return '\n\n'.join(ja_chunks).strip() + '\n'


def eligible(repo: Path):
    try:
        if repo.name in EXCLUDE:
            return False
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


def process_repo(repo: Path):
    name = repo.name
    p_en = repo / 'README.md'
    p_ja = repo / 'README.ja.md'
    if not p_en.exists():
        return ('ERR', name, 'missing-readme-md')

    en_md = norm(p_en.read_text(encoding='utf-8'))

    en_lines = en_md.split('\n')
    en_lines = ensure_top_link(en_lines, JA_LINK_LINE)
    en_lines = ensure_license_tail(en_lines, ja=False)
    en_final = '\n'.join(cleanup_blank(en_lines)) + '\n'

    ja_md = translate_full_en_to_ja(en_final)
    ja_lines = norm(ja_md).split('\n')
    ja_lines = ensure_top_link(ja_lines, EN_LINK_LINE)
    ja_lines = ensure_license_tail(ja_lines, ja=True)
    ja_final = '\n'.join(cleanup_blank(ja_lines)) + '\n'

    if len(ja_final.splitlines()) < int(len(en_final.splitlines()) * 0.75):
        return ('ERR', name, 'ja-too-short-after-translation')

    changed = False
    if en_final != en_md:
        p_en.write_text(en_final, encoding='utf-8')
        changed = True
    old_ja = norm(p_ja.read_text(encoding='utf-8')) if p_ja.exists() else ''
    if ja_final != old_ja:
        p_ja.write_text(ja_final, encoding='utf-8')
        changed = True

    if not changed:
        head = out(repo, 'rev-parse', '--short', 'HEAD').strip()
        return ('OK', name, head)

    if run(repo, 'add', 'README.md', 'README.ja.md').returncode != 0:
        return ('ERR', name, 'git-add-failed')
    if run(repo, 'commit', '--amend', '--no-edit').returncode != 0:
        return ('ERR', name, 'amend-failed')

    head = out(repo, 'rev-parse', '--short', 'HEAD').strip()
    p = run(repo, 'push', 'origin', f'HEAD:refs/heads/{BRANCH}', timeout=480)
    if p.returncode != 0:
        return ('ERR', name, (p.stderr or p.stdout).strip().replace('\n', ' '))
    return ('OK', name, head)


repos = sorted([p for p in BASE.iterdir() if p.is_dir() and (p / '.git').exists()], key=lambda p: p.name.lower())
count = 0
for repo in repos:
    if not eligible(repo):
        continue
    r = process_repo(repo)
    if r[0] == 'OK':
        print(f'OK|{r[1]}|{r[2]}')
        print(f'COMMIT|{r[1]}|https://github.com/code4fukui/{r[1]}/commit/{r[2]}')
        count += 1
    else:
        print(f'ERR|{r[1]}|{r[2]}')
    if count >= 5:
        break

print(f'SUMMARY|ok={count}|branch={BRANCH}')
