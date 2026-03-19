import subprocess
from pathlib import Path

repos = ['imgaddlines', 'imgcrop', 'imgtools', 'IMI2', 'indexed-mp3player']
base = Path('/home/ubuntu/code4fukui')

ok_to_push = []
for r in repos:
    rp = base / r
    try:
        ahead = int(subprocess.check_output(['git','-C',str(rp),'rev-list','--count','@{u}..HEAD'], text=True).strip())
        behind = int(subprocess.check_output(['git','-C',str(rp),'rev-list','--count','HEAD..@{u}'], text=True).strip())
        author = subprocess.check_output(['git','-C',str(rp),'log','-1','--pretty=%an <%ae>'], text=True).strip()
        files = [x.strip() for x in subprocess.check_output(['git','-C',str(rp),'show','--name-only','--pretty=','HEAD'], text=True).splitlines() if x.strip()]
        safe_files = all(f in ('README.md','README.ja.md') for f in files)
        print(f'CHECK {r} ahead={ahead} behind={behind} author={author} files={files}')
        if ahead > 0 and behind == 0 and safe_files:
            ok_to_push.append(r)
    except Exception as e:
        print(f'CHECK_FAIL {r}: {e}')

print(f'PUSH_PLAN count={len(ok_to_push)} repos={ok_to_push}')

for r in ok_to_push:
    rp = base / r
    p = subprocess.run(['git','-C',str(rp),'push','origin','HEAD'], text=True, capture_output=True)
    if p.returncode == 0:
        print(f'PUSH_OK {r}')
    else:
        print(f'PUSH_FAIL {r}')
        print((p.stderr or p.stdout).strip())
