import subprocess
from pathlib import Path

base = Path('/home/ubuntu/code4fukui')
repos = sorted([p for p in base.iterdir() if p.is_dir() and (p / '.git').exists()], key=lambda p: p.name.lower())

deleted = 0
errs = 0
no_temp = 0

for repo in repos:
    name = repo.name
    try:
        refs = subprocess.check_output(
            ['git', '-C', str(repo), 'for-each-ref', '--format=%(refname:short)', 'refs/remotes/origin'],
            text=True,
            stderr=subprocess.DEVNULL,
        ).splitlines()
        temp = []
        for r in refs:
            if r.startswith('origin/review-readme-'):
                temp.append(r[len('origin/'):])
        if not temp:
            no_temp += 1
            continue
        for b in temp:
            p = subprocess.run(['git', '-C', str(repo), 'push', 'origin', '--delete', b], text=True, capture_output=True)
            if p.returncode == 0:
                deleted += 1
                print(f'DEL|{name}|{b}')
            else:
                errs += 1
                msg = (p.stderr or p.stdout).strip().replace('\n', ' ')
                print(f'ERR|{name}|{b}|{msg}')
    except Exception as e:
        errs += 1
        print(f'ERR|{name}|meta|{str(e).replace(chr(10), " ")}')

print(f'SUMMARY|deleted={deleted}|errors={errs}|repos_without_temp={no_temp}|repos_total={len(repos)}')
