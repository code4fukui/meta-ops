import subprocess
from pathlib import Path

base = Path('/home/ubuntu/code4fukui')
subjects = {
    'docs: add English and Japanese README via AI internationalization',
    'docs: refresh English and Japanese README for globalization',
    'docs: remove unsupported README.en.md',
}

rows = []
for rp in sorted([p for p in base.iterdir() if p.is_dir() and (p / '.git').exists()], key=lambda p: p.name.lower()):
    r = rp.name
    try:
        subj = subprocess.check_output(['git','-C',str(rp),'log','-1','--pretty=%s','@{u}'], text=True, stderr=subprocess.DEVNULL).strip()
        if subj not in subjects:
            continue
        ahead = int(subprocess.check_output(['git','-C',str(rp),'rev-list','--count','@{u}..HEAD'], text=True).strip())
        behind = int(subprocess.check_output(['git','-C',str(rp),'rev-list','--count','HEAD..@{u}'], text=True).strip())
        if ahead <= 0 or behind != 0:
            continue
        author = subprocess.check_output(['git','-C',str(rp),'log','-1','--pretty=%an'], text=True).strip()
        if author != 'Amil Khanzada':
            continue
        commit = subprocess.check_output(['git','-C',str(rp),'rev-parse','--short','HEAD'], text=True).strip()
        branch = subprocess.check_output(['git','-C',str(rp),'rev-parse','--abbrev-ref','HEAD'], text=True).strip()
        files = [x.strip() for x in subprocess.check_output(['git','-C',str(rp),'show','--name-only','--pretty=','HEAD'], text=True).splitlines() if x.strip()]
        if any(f not in ('README.md','README.ja.md') for f in files):
            continue
        stat = subprocess.check_output(['git','-C',str(rp),'show','--shortstat','--pretty=','HEAD'], text=True).strip()
        rows.append((r, branch, commit, ','.join(files), stat))
    except Exception:
        pass

rows = rows[:50]
for i, (r,b,c,f,s) in enumerate(rows,1):
    print(f"{i:02d}|{r}|{b}|{c}|{f}|{s}")
print(f"TOTAL_NEXT_50={len(rows)}")
