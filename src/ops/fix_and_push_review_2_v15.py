import re
import subprocess
from pathlib import Path

BASE = Path('/home/ubuntu/code4fukui')
BRANCH = 'review-readme-20260316-15'
EXCLUDE = {
    'ASN1','chart-line','dinosaur-opendata','echizen-coast-kanko-reservation','EDINET','find47','fukui-kanko-survey','fukui-kanko-trend-report','mikatagoko-kanko-reservation','moyo',
    'ar-vr360-viewer','fukui-kanko-reservation','fukui-kanko-trend-data','fukui-station-kanko-reservation','i18n','ishikawa-kanko-survey','mp3-recorder','mp3-tag-editor','mp4player','mpy-cross-v6',
    'muno3','music-api-js','music-brainstorming-bgm','music-fnct-sabae','music-future-with-you','music-kanko-dx','music-new-shoshinge',
    'music-opendata-fukui','music-pioneerpork','music-player','mykkrec','name2pic','nanoevents','nanoid','natural-earth-geojson',
    'ndarray','ndarray-ops','ndb-dashboard','ndb-opendata','nearornot','nekocam','neomo.css','nesly-assembler'
}
md_link = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')

def run(repo: Path, *args: str, timeout: int = 180):
    return subprocess.run(['git', '-C', str(repo), *args], text=True, capture_output=True, timeout=timeout)

def out(repo: Path, *args: str, timeout: int = 180) -> str:
    p = run(repo, *args, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip())
    return p.stdout

def out_or_empty(repo: Path, *args: str, timeout: int = 180) -> str:
    p = run(repo, *args, timeout=timeout)
    return p.stdout if p.returncode == 0 else ''

def norm(s: str) -> str:
    return s.replace('\r\n', '\n').replace('\r', '\n')

def cleanup(lines):
    outl=[]; prev=False
    for ln in lines:
        b=ln.strip()==''
        if b and prev: continue
        outl.append(ln); prev=b
    while outl and outl[-1].strip()=='': outl.pop()
    return outl

def find_lic_idx(lines):
    for i,ln in enumerate(lines):
        if ln.strip().lower() in ('## license','## ライセンス'): return i
    return len(lines)

def ensure_license_tail(lines, ja=False):
    body=cleanup(lines[:find_lic_idx(lines)])
    if body and body[-1].strip()!='': body.append('')
    if ja:
        body += ['## ライセンス','このプロジェクトは [MIT License](LICENSE) のもとで公開されています。']
    else:
        body += ['## License','This project is licensed under the [MIT License](LICENSE).']
    return cleanup(body)

def extract_links(lines):
    outv=[]; seen=set()
    for ln in lines:
        for m in md_link.finditer(ln):
            t,u=m.group(1).strip(),m.group(2).strip()
            if 'github.com/code4fukui/' not in u: continue
            k=(t,u)
            if k in seen: continue
            seen.add(k); outv.append((t,u))
    return outv

def ensure_parity(en_lines, ja_lines):
    en,ja=extract_links(en_lines),extract_links(ja_lines)
    en_u={u for _,u in en}; ja_u={u for _,u in ja}
    miss_ja=[(t,u) for t,u in en if u not in ja_u]
    miss_en=[(t,u) for t,u in ja if u not in en_u]
    def ins(lines,items):
        if not items: return lines
        idx=find_lic_idx(lines); head,tail=lines[:idx],lines[idx:]
        if head and head[-1].strip()!='': head.append('')
        for t,u in items:
            b=f'- [{t}]({u})'
            if b not in head: head.append(b)
        if tail and tail[0].strip()!='': head.append('')
        return cleanup(head+tail)
    return ins(en_lines,miss_en), ins(ja_lines,miss_ja)

def lcs(a,b):
    n,m=len(a),len(b)
    dp=[[0]*(m+1) for _ in range(n+1)]
    for i in range(n-1,-1,-1):
        for j in range(m-1,-1,-1):
            if a[i]==b[j]: dp[i][j]=1+dp[i+1][j+1]
            else: dp[i][j]=dp[i+1][j] if dp[i+1][j]>=dp[i][j+1] else dp[i][j+1]
    i=j=0; seq=[]
    while i<n and j<m:
        if a[i]==b[j]: seq.append(a[i]); i+=1; j+=1
        elif dp[i+1][j]>=dp[i][j+1]: i+=1
        else: j+=1
    return seq

def scs(a,b):
    c=lcs(a,b); i=j=k=0; outl=[]
    while k<len(c):
        x=c[k]
        while i<len(a) and a[i]!=x: outl.append(a[i]); i+=1
        while j<len(b) and b[j]!=x: outl.append(b[j]); j+=1
        outl.append(x); i+=1; j+=1; k+=1
    outl.extend(a[i:]); outl.extend(b[j:]); return outl

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

def fix_push(repo: Path):
    p_en=repo/'README.md'; p_ja=repo/'README.ja.md'
    if not p_en.exists() or not p_ja.exists(): return None
    head_en=norm(p_en.read_text(encoding='utf-8')); head_ja=norm(p_ja.read_text(encoding='utf-8'))
    up_en=norm(out_or_empty(repo,'show','@{u}:README.md')) or head_en
    up_ja=norm(out_or_empty(repo,'show','@{u}:README.ja.md')) or head_ja
    en,ja=scs(up_en.split('\n'),head_en.split('\n')),scs(up_ja.split('\n'),head_ja.split('\n'))
    en,ja=ensure_parity(en,ja)
    en,ja=ensure_license_tail(en,False),ensure_license_tail(ja,True)
    new_en='\n'.join(cleanup(en))+'\n'; new_ja='\n'.join(cleanup(ja))+'\n'
    changed=False
    if new_en!=head_en: p_en.write_text(new_en,encoding='utf-8'); changed=True
    if new_ja!=head_ja: p_ja.write_text(new_ja,encoding='utf-8'); changed=True
    if changed:
        if run(repo,'add','README.md','README.ja.md').returncode!=0: return None
        if run(repo,'commit','--amend','--no-edit').returncode!=0: return None
    head=out(repo,'rev-parse','--short','HEAD').strip()
    if run(repo,'push','origin',f'HEAD:refs/heads/{BRANCH}',timeout=300).returncode!=0: return None
    return head

count=0
for repo in sorted([p for p in BASE.iterdir() if p.is_dir() and (p/'.git').exists()], key=lambda p:p.name.lower()):
    if repo.name in EXCLUDE: continue
    if not eligible(repo): continue
    h=fix_push(repo)
    if h:
        print(f'OK|{repo.name}|{h}')
        print(f'COMMIT|{repo.name}|https://github.com/code4fukui/{repo.name}/commit/{h}')
        count+=1
        if count>=2: break
print(f'SUMMARY|ok={count}|branch={BRANCH}')
