import json
import subprocess
from pathlib import Path
import boto3

BASE = Path('/home/ubuntu/code4fukui')
REPO = BASE / 'node-html-parser'
BRANCH = 'review-readme-20260317-19'
MODEL_ID = 'anthropic.claude-3-haiku-20240307-v1:0'
REGION = 'us-east-1'
JA_LINK_LINE = '日本語のREADMEはこちらです: [README.ja.md](README.ja.md)'
EN_LINK_LINE = 'English README is here: [README.md](README.md)'

bedrock = boto3.client('bedrock-runtime', region_name=REGION)


def run(*args, timeout=300):
    return subprocess.run(['git', '-C', str(REPO), *args], text=True, capture_output=True, timeout=timeout)


def out(*args, timeout=300):
    p = run(*args, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip())
    return p.stdout


def norm(s):
    return s.replace('\r\n', '\n').replace('\r', '\n')


def cleanup(lines):
    o=[]; prev=False
    for ln in lines:
        b=ln.strip()==''
        if b and prev: continue
        o.append(ln); prev=b
    while o and o[-1].strip()=='': o.pop()
    return o


def find_h1(lines):
    for i,ln in enumerate(lines):
        if ln.strip().startswith('# '): return i
    return -1


def top_link(lines, link):
    lines=[ln for ln in lines if ln.strip() not in (link, f'> {link}')]
    i=find_h1(lines)
    if i<0: return cleanup([link,'']+lines)
    p=i+1
    if p<len(lines) and lines[p].strip()!='': lines.insert(p,''); p+=1
    lines.insert(p,link)
    if p+1<len(lines) and lines[p+1].strip()!='': lines.insert(p+1,'')
    return cleanup(lines)


def lic_idx(lines):
    for i,ln in enumerate(lines):
        if ln.strip().lower() in ('## license','## ライセンス'): return i
    return len(lines)


def license_tail(lines, ja=False):
    body=cleanup(lines[:lic_idx(lines)])
    if body and body[-1].strip()!='': body.append('')
    if ja:
        body += ['## ライセンス','このプロジェクトは [MIT License](LICENSE) のもとで公開されています。']
    else:
        body += ['## License','This project is licensed under the [MIT License](LICENSE).']
    return cleanup(body)


def split_sections(md):
    lines=norm(md).split('\n')
    chunks=[]; cur=[]
    for ln in lines:
        if ln.startswith('## ') and cur:
            chunks.append('\n'.join(cur).strip('\n')); cur=[ln]
        else:
            cur.append(ln)
    if cur: chunks.append('\n'.join(cur).strip('\n'))
    return [c for c in chunks if c.strip()]


def call(prompt, max_tokens=1400):
    resp = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps({
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': max_tokens,
            'messages': [{'role': 'user', 'content': prompt}],
        }),
    )
    return json.loads(resp['body'].read())['content'][0]['text'].strip()


def translate_chunk(chunk):
    prompt=f'''Translate this README markdown chunk from English to Japanese.
Rules:
- Keep exact markdown structure and section order.
- Keep all links and URLs unchanged.
- Keep code blocks unchanged.
- Do not omit any sentence.
- Output markdown only.

{chunk}
'''
    return call(prompt)


def translate_full(en_md):
    chunks=split_sections(en_md)
    out_chunks=[translate_chunk(c) for c in chunks]
    return '\n\n'.join(out_chunks).strip()+'\n'

if out('status','--porcelain').strip()!='':
    print('ERR|node-html-parser|dirty-worktree'); raise SystemExit(0)

ahead=int(out('rev-list','--count','@{u}..HEAD').strip() or '0')
behind=int(out('rev-list','--count','HEAD..@{u}').strip() or '0')
if ahead<=0 or behind!=0:
    print(f'ERR|node-html-parser|ahead={ahead},behind={behind}'); raise SystemExit(0)

p_en=REPO/'README.md'; p_ja=REPO/'README.ja.md'
cur_en=norm(p_en.read_text(encoding='utf-8'))
cur_ja=norm(p_ja.read_text(encoding='utf-8')) if p_ja.exists() else ''

en_lines=top_link(cur_en.split('\n'), JA_LINK_LINE)
en_lines=license_tail(en_lines, ja=False)
en_final='\n'.join(cleanup(en_lines))+'\n'

ja_raw=translate_full(en_final)
ja_lines=top_link(norm(ja_raw).split('\n'), EN_LINK_LINE)
ja_lines=license_tail(ja_lines, ja=True)
ja_final='\n'.join(cleanup(ja_lines))+'\n'

if len(ja_final.splitlines()) < int(len(en_final.splitlines())*0.6):
    print('ERR|node-html-parser|ja-too-short-after-translation'); raise SystemExit(0)

changed=False
if en_final!=cur_en:
    p_en.write_text(en_final,encoding='utf-8'); changed=True
if ja_final!=cur_ja:
    p_ja.write_text(ja_final,encoding='utf-8'); changed=True

if changed:
    if run('add','README.md','README.ja.md').returncode!=0:
        print('ERR|node-html-parser|git-add-failed'); raise SystemExit(0)
    if run('commit','--amend','--no-edit').returncode!=0:
        print('ERR|node-html-parser|amend-failed'); raise SystemExit(0)

sha=out('rev-parse','--short','HEAD').strip()
p=run('push','origin',f'HEAD:refs/heads/{BRANCH}',timeout=600)
if p.returncode!=0:
    print('ERR|node-html-parser|'+((p.stderr or p.stdout).strip().replace('\n',' '))); raise SystemExit(0)

print(f'OK|node-html-parser|{sha}')
print(f'COMMIT|node-html-parser|https://github.com/code4fukui/node-html-parser/commit/{sha}')
