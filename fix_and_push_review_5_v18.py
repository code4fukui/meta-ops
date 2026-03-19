import re
import subprocess
from pathlib import Path

BASE = Path('/home/ubuntu/code4fukui')
BRANCH = 'review-readme-20260317-18'
EXCLUDE = {
    'ASN1','chart-line','dinosaur-opendata','echizen-coast-kanko-reservation','EDINET','find47','fukui-kanko-survey','fukui-kanko-trend-report','mikatagoko-kanko-reservation','moyo',
    'ar-vr360-viewer','fukui-kanko-reservation','fukui-kanko-trend-data','fukui-station-kanko-reservation','i18n','ishikawa-kanko-survey','mp3-recorder','mp3-tag-editor','mp4player','mpy-cross-v6',
    'muno3','music-api-js','music-brainstorming-bgm','music-fnct-sabae','music-future-with-you','music-kanko-dx','music-new-shoshinge',
    'music-opendata-fukui','music-pioneerpork','music-player','mykkrec','name2pic','nanoevents','nanoid','natural-earth-geojson',
    'ndarray','ndarray-ops','ndb-dashboard','ndb-opendata','nearornot','nekocam','neomo.css','nesly-assembler','next-course-of-study','niid_go_jp'
}
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
    out_lines=[]; prev=False
    for ln in lines:
        b=ln.strip()==''
        if b and prev: continue
        out_lines.append(ln); prev=b
    while out_lines and out_lines[-1].strip()=='': out_lines.pop()
    return out_lines

def find_first_h1(lines):
    for i,ln in enumerate(lines):
        if ln.strip().startswith('# '): return i
    return -1

def ensure_top_link(lines, line):
    lines=[ln for ln in lines if ln.strip() not in (line, f'> {line}')]
    i=find_first_h1(lines)
    if i<0:
        return cleanup_blank([line,'']+lines)
    pos=i+1
    if pos < len(lines) and lines[pos].strip()!='':
        lines.insert(pos,''); pos+=1
    lines.insert(pos,line)
    if pos+1 < len(lines) and lines[pos+1].strip()!='':
        lines.insert(pos+1,'')
    return cleanup_blank(lines)

def dedupe_h1(lines):
    seen=set(); out_lines=[]
    for ln in lines:
        s=ln.strip()
        if s.startswith('# '):
            key=' '.join(s[2:].lower().split())
            if key in seen: continue
            seen.add(key)
        out_lines.append(ln)
    return out_lines

def remove_setext_title_if_h1_exists(lines):
    has_h1=any(ln.strip().startswith('# ') for ln in lines)
    if has_h1 and len(lines)>=2 and lines[0].strip() and re.fullmatch(r'[=-]{3,}', lines[1].strip()):
        return lines[2:]
    return lines

def find_license_idx(lines):
    for i,ln in enumerate(lines):
        if ln.strip().lower() in ('## license','## ライセンス'): return i
    return len(lines)

def ensure_license_tail(lines, ja=False):
    body=cleanup_blank(lines[:find_license_idx(lines)])
    if body and body[-1].strip()!='': body.append('')
    if ja:
        body += ['## ライセンス','このプロジェクトは [MIT License](LICENSE) のもとで公開されています。']
    else:
        body += ['## License','This project is licensed under the [MIT License](LICENSE).']
    return cleanup_blank(body)

def extract_code4fukui_links(lines):
    links=[]; seen=set()
    for ln in lines:
        for m in md_link_re.finditer(ln):
            t,u=m.group(1).strip(),m.group(2).strip()
            if 'github.com/code4fukui/' not in u: continue
            k=(t,u)
            if k in seen: continue
            seen.add(k); links.append((t,u))
    return links

def ensure_link_parity(en_lines, ja_lines):
    en=extract_code4fukui_links(en_lines)
    ja=extract_code4fukui_links(ja_lines)
    en_u={u for _,u in en}; ja_u={u for _,u in ja}
    miss_ja=[(t,u) for t,u in en if u not in ja_u]
    miss_en=[(t,u) for t,u in ja if u not in en_u]
    def inject(lines, items):
        if not items: return lines
        idx=find_license_idx(lines)
        head,tail=lines[:idx],lines[idx:]
        if head and head[-1].strip()!='': head.append('')
        for t,u in items:
            b=f'- [{t}]({u})'
            if b not in head: head.append(b)
        if tail and tail[0].strip()!='': head.append('')
        return cleanup_blank(head+tail)
    return inject(en_lines, miss_en), inject(ja_lines, miss_ja)

def eligible(repo: Path):
    try:
        if out(repo,'status','--porcelain').strip()!='': return False
        ahead=int(out(repo,'rev-list','--count','@{u}..HEAD').strip() or '0')
        behind=int(out(repo,'rev-list','--count','HEAD..@{u}').strip() or '0')
        if ahead<=0 or behind!=0: return False
        if out(repo,'log','-1','--pretty=%an').strip()!='Amil Khanzada': return False
        files=[x.strip() for x in out(repo,'show','--name-only','--pretty=','HEAD').splitlines() if x.strip()]
        return all(f in ('README.md','README.ja.md') for f in files)
    except Exception:
        return False

def process(repo: Path):
    p_en=repo/'README.md'; p_ja=repo/'README.ja.md'
    if not p_en.exists() or not p_ja.exists():
        return ('ERR', repo.name, 'missing-readme-pair')

    cur_en=norm(p_en.read_text(encoding='utf-8'))
    cur_ja=norm(p_ja.read_text(encoding='utf-8'))
    up_en=norm(out_or_empty(repo,'show','@{u}:README.md')) or cur_en
    up_ja=norm(out_or_empty(repo,'show','@{u}:README.ja.md')) or cur_ja

    en_lines=up_en.split('\n')
    ja_lines=up_ja.split('\n')
    en_lines=remove_setext_title_if_h1_exists(en_lines)
    ja_lines=remove_setext_title_if_h1_exists(ja_lines)
    en_lines=dedupe_h1(en_lines)
    ja_lines=dedupe_h1(ja_lines)
    en_lines=ensure_top_link(en_lines, JA_LINK_LINE)
    ja_lines=ensure_top_link(ja_lines, EN_LINK_LINE)
    en_lines,ja_lines=ensure_link_parity(en_lines,ja_lines)
    en_lines=ensure_license_tail(en_lines,ja=False)
    ja_lines=ensure_license_tail(ja_lines,ja=True)

    new_en='\n'.join(cleanup_blank(en_lines))+'\n'
    new_ja='\n'.join(cleanup_blank(ja_lines))+'\n'

    changed=False
    if new_en!=cur_en:
        p_en.write_text(new_en,encoding='utf-8'); changed=True
    if new_ja!=cur_ja:
        p_ja.write_text(new_ja,encoding='utf-8'); changed=True

    if changed:
        if run(repo,'add','README.md','README.ja.md').returncode!=0:
            return ('ERR', repo.name, 'git-add-failed')
        if run(repo,'commit','--amend','--no-edit').returncode!=0:
            return ('ERR', repo.name, 'amend-failed')

    head=out(repo,'rev-parse','--short','HEAD').strip()
    p=run(repo,'push','origin',f'HEAD:refs/heads/{BRANCH}',timeout=360)
    if p.returncode!=0:
        return ('ERR', repo.name, (p.stderr or p.stdout).strip().replace('\n',' '))
    return ('OK', repo.name, head)

ok=[]
for repo in sorted([p for p in BASE.iterdir() if p.is_dir() and (p/'.git').exists()], key=lambda p:p.name.lower()):
    if repo.name in EXCLUDE: continue
    if not eligible(repo): continue
    r=process(repo)
    if r[0]=='OK':
        ok.append(r)
        print(f'OK|{r[1]}|{r[2]}')
        print(f'COMMIT|{r[1]}|https://github.com/code4fukui/{r[1]}/commit/{r[2]}')
    else:
        print(f'ERR|{r[1]}|{r[2]}')
    if len(ok)>=5: break

print(f'SUMMARY|ok={len(ok)}|branch={BRANCH}')
