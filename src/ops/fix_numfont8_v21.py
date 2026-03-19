import json
import subprocess
from pathlib import Path
import boto3

repo = Path('/home/ubuntu/code4fukui/numfont8')
branch = 'review-readme-20260317-21'
model_id = 'anthropic.claude-3-haiku-20240307-v1:0'
region = 'us-east-1'
JA_LINK_LINE = '日本語のREADMEはこちらです: [README.ja.md](README.ja.md)'

bedrock = boto3.client('bedrock-runtime', region_name=region)


def run(*args, timeout=240):
    return subprocess.run(['git', '-C', str(repo), *args], text=True, capture_output=True, timeout=timeout)


def out(*args, timeout=240):
    p = run(*args, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip())
    return p.stdout


def norm(s):
    return s.replace('\r\n', '\n').replace('\r', '\n')


def cleanup(lines):
    outl = []
    prev = False
    for ln in lines:
        b = ln.strip() == ''
        if b and prev:
            continue
        outl.append(ln)
        prev = b
    while outl and outl[-1].strip() == '':
        outl.pop()
    return outl


def ensure_top_ja_link(lines):
    lines = [ln for ln in lines if ln.strip() not in (JA_LINK_LINE, f'> {JA_LINK_LINE}')]
    h1 = -1
    for i, ln in enumerate(lines):
        if ln.strip().startswith('# '):
            h1 = i
            break
    if h1 < 0:
        return cleanup([JA_LINK_LINE, ''] + lines)
    pos = h1 + 1
    if pos < len(lines) and lines[pos].strip() != '':
        lines.insert(pos, '')
        pos += 1
    lines.insert(pos, JA_LINK_LINE)
    if pos + 1 < len(lines) and lines[pos + 1].strip() != '':
        lines.insert(pos + 1, '')
    return cleanup(lines)


def ensure_license_tail(lines, ja=False):
    idx = len(lines)
    for i, ln in enumerate(lines):
        if ln.strip().lower() in ('## license', '## ライセンス'):
            idx = i
            break
    body = cleanup(lines[:idx])
    if body and body[-1].strip() != '':
        body.append('')
    if ja:
        body += ['## ライセンス', 'このプロジェクトは [MIT License](LICENSE) のもとで公開されています。']
    else:
        body += ['## License', 'This project is licensed under the [MIT License](LICENSE).']
    return cleanup(body)


def call_bedrock(prompt, max_tokens=1600):
    resp = bedrock.invoke_model(
        modelId=model_id,
        body=json.dumps({
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': max_tokens,
            'messages': [{'role': 'user', 'content': prompt}],
        }),
    )
    return json.loads(resp['body'].read())['content'][0]['text'].strip()


def split_sections(md):
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


def translate_full(en_md):
    out_chunks = []
    for chunk in split_sections(en_md):
        prompt = f'''Translate the following README markdown chunk from English to Japanese.
Rules:
- Preserve markdown structure, heading levels, section order, lists, and links.
- Preserve URLs exactly.
- Preserve code blocks exactly.
- Do not omit any content.
- Output markdown only.

English markdown chunk:
{chunk}
'''
        out_chunks.append(call_bedrock(prompt))
    return '\n\n'.join(out_chunks).strip() + '\n'


if out('status', '--porcelain').strip() != '':
    raise SystemExit('ERR|numfont8|dirty-worktree')

# Build EN from upstream to recover dropped content (including ISO link).
up_en = norm(out('show', '@{u}:README.md'))
en_lines = up_en.split('\n')
en_lines = ensure_top_ja_link(en_lines)
en_lines = ensure_license_tail(en_lines, ja=False)
en_final = '\n'.join(cleanup(en_lines)) + '\n'

# Full JA translation from finalized EN.
ja_final = translate_full(en_final)
ja_lines = norm(ja_final).split('\n')
# Remove any injected English-pointer line from JA, as requested.
ja_lines = [ln for ln in ja_lines if ln.strip() != 'English README is here: [README.md](README.md)']
ja_lines = ensure_license_tail(ja_lines, ja=True)
ja_final = '\n'.join(cleanup(ja_lines)) + '\n'

(repo / 'README.md').write_text(en_final, encoding='utf-8')
(repo / 'README.ja.md').write_text(ja_final, encoding='utf-8')

if run('add', 'README.md', 'README.ja.md').returncode != 0:
    raise SystemExit('ERR|numfont8|git-add-failed')
if run('commit', '--amend', '--no-edit').returncode != 0:
    raise SystemExit('ERR|numfont8|amend-failed')

head = out('rev-parse', '--short', 'HEAD').strip()
p = run('push', 'origin', f'HEAD:refs/heads/{branch}', timeout=360)
if p.returncode != 0:
    raise SystemExit('ERR|numfont8|' + (p.stderr or p.stdout).strip().replace('\n', ' '))

print(f'OK|numfont8|{head}')
print(f'COMMIT|numfont8|https://github.com/code4fukui/numfont8/commit/{head}')
