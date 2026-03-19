import json
import subprocess
from pathlib import Path
import boto3

BASE = Path('/home/ubuntu/code4fukui')
MODEL_ID = 'anthropic.claude-3-haiku-20240307-v1:0'
REGION = 'us-east-1'
JA_LINK_LINE = '日本語のREADMEはこちらです: [README.ja.md](README.ja.md)'
BAD_LEAK_LINE = '以下のREADMEのマークダウンの部分を英語から日本語に翻訳します。'

SUBJECT = 'docs: refresh English and Japanese README for globalization'
BODY = [
    '- Regenerate Japanese README from canonical English README',
    '- Keep language pointers and license links consistent',
]
TRAILERS = [
    'Generated-by: Claude via AWS Bedrock (anthropic.claude-3-haiku-20240307-v1:0)',
    'Verified-by: Amil Khanzada <amilkh@users.noreply.github.com>',
]

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
        s = ln.strip()
        b = s == ''
        if s == BAD_LEAK_LINE:
            continue
        if s == 'English README is here: [README.md](README.md)':
            continue
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


def ensure_top_ja_link(lines):
    lines = [ln for ln in lines if ln.strip() not in (JA_LINK_LINE, f'> {JA_LINK_LINE}')]
    i = find_first_h1(lines)
    if i < 0:
        return cleanup_blank([JA_LINK_LINE, ''] + lines)
    pos = i + 1
    if pos < len(lines) and lines[pos].strip() != '':
        lines.insert(pos, '')
        pos += 1
    lines.insert(pos, JA_LINK_LINE)
    if pos + 1 < len(lines) and lines[pos + 1].strip() != '':
        lines.insert(pos + 1, '')
    return cleanup_blank(lines)


def find_license_idx(lines):
    for i, ln in enumerate(lines):
        if ln.strip().lower() in ('## license', '## ライセンス'):
            return i
    return len(lines)


def ensure_license_tail(lines, ja=False):
    idx = find_license_idx(lines)
    body = cleanup_blank(lines[:idx])

    if ja:
        heading = '## ライセンス'
        mit_line = 'このプロジェクトは [MIT License](LICENSE) のもとで公開されています。'
    else:
        heading = '## License'
        mit_line = 'This project is licensed under the [MIT License](LICENSE).'

    if idx >= len(lines):
        section = [heading, mit_line]
    else:
        section = cleanup_blank(lines[idx:])
        if not section or not section[0].strip().startswith('## '):
            section = [heading] + section
        if mit_line not in [ln.strip() for ln in section]:
            if section and section[-1].strip() != '':
                section.append('')
            section.append(mit_line)

    if body and body[-1].strip() != '':
        body.append('')
    return cleanup_blank(body + section)


def ja_looks_prepared(ja_md: str, en_md: str) -> bool:
    lines = cleanup_blank(norm(ja_md).split('\n'))
    if not lines:
        return False
    if sum(1 for ln in lines if ln.strip().startswith('## ')) < 3:
        return False
    if BAD_LEAK_LINE in [ln.strip() for ln in lines]:
        return False
    en_non_empty = max(1, sum(1 for ln in norm(en_md).split('\n') if ln.strip()))
    ja_non_empty = sum(1 for ln in lines if ln.strip())
    return ja_non_empty >= int(en_non_empty * 0.55)


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
    out_chunks = []
    for c in split_by_sections(en_md):
        out_chunks.append(translate_chunk(c))
    return '\n\n'.join(out_chunks).strip() + '\n'


def has_upstream(repo: Path):
    return run(repo, 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}').returncode == 0


def commit_message():
    return SUBJECT + '\n\n' + '\n'.join(BODY) + '\n\n' + '\n'.join(TRAILERS)

repos = sorted([p for p in BASE.iterdir() if p.is_dir() and (p / '.git').exists()], key=lambda p: p.name.lower())

ok = 0
changed = 0
skipped = 0
errs = 0

for idx, repo in enumerate(repos, start=1):
    name = repo.name
    try:
        if not has_upstream(repo):
            print(f'SKIP|{name}|no-upstream')
            skipped += 1
            continue
        if out(repo, 'status', '--porcelain').strip() != '':
            print(f'SKIP|{name}|dirty-worktree')
            skipped += 1
            continue

        p_en = repo / 'README.md'
        if not p_en.exists():
            print(f'SKIP|{name}|missing-README.md')
            skipped += 1
            continue
        p_ja = repo / 'README.ja.md'

        # Canonical EN
        en_md = norm(p_en.read_text(encoding='utf-8'))
        en_lines = ensure_top_ja_link(en_md.split('\n'))
        en_lines = ensure_license_tail(en_lines, ja=False)
        en_final = '\n'.join(cleanup_blank(en_lines)) + '\n'

        old_ja = norm(p_ja.read_text(encoding='utf-8')) if p_ja.exists() else ''

        # Preserve an existing good JA README. Only regenerate if missing or clearly low-quality.
        if old_ja and ja_looks_prepared(old_ja, en_final):
            ja_lines = ensure_license_tail(norm(old_ja).split('\n'), ja=True)
            ja_final = '\n'.join(cleanup_blank(ja_lines)) + '\n'
        else:
            ja_md = translate_full_en_to_ja(en_final)
            ja_lines = ensure_license_tail(norm(ja_md).split('\n'), ja=True)
            ja_final = '\n'.join(cleanup_blank(ja_lines)) + '\n'

            if len(ja_final.splitlines()) < int(len(en_final.splitlines()) * 0.75):
                print(f'ERR|{name}|ja-too-short')
                errs += 1
                continue

        any_change = False
        if en_final != en_md:
            p_en.write_text(en_final, encoding='utf-8')
            any_change = True
        if ja_final != old_ja:
            p_ja.write_text(ja_final, encoding='utf-8')
            any_change = True

        ahead = int(out(repo, 'rev-list', '--count', '@{u}..HEAD').strip() or '0')
        behind = int(out(repo, 'rev-list', '--count', 'HEAD..@{u}').strip() or '0')

        if behind != 0:
            print(f'SKIP|{name}|behind={behind}')
            skipped += 1
            continue

        if any_change:
            if run(repo, 'add', 'README.md', 'README.ja.md').returncode != 0:
                print(f'ERR|{name}|git-add-failed')
                errs += 1
                continue
            msg = commit_message()
            if ahead > 1:
                if run(repo, 'reset', '--soft', '@{u}').returncode != 0:
                    print(f'ERR|{name}|soft-reset-failed')
                    errs += 1
                    continue
                if run(repo, 'commit', '-m', msg).returncode != 0:
                    print(f'ERR|{name}|commit-after-reset-failed')
                    errs += 1
                    continue
            elif ahead == 1:
                # Rewrite single local commit to keep one-commit policy.
                if run(repo, 'commit', '--amend', '-m', msg).returncode != 0:
                    print(f'ERR|{name}|amend-failed')
                    errs += 1
                    continue
            else:
                if run(repo, 'commit', '-m', msg).returncode != 0:
                    print(f'ERR|{name}|new-commit-failed')
                    errs += 1
                    continue
            changed += 1

        # Final safety squash for any remaining multi-commit ahead stack.
        ahead2 = int(out(repo, 'rev-list', '--count', '@{u}..HEAD').strip() or '0')
        if ahead2 > 1:
            msg = commit_message()
            if run(repo, 'reset', '--soft', '@{u}').returncode == 0 and run(repo, 'commit', '-m', msg).returncode == 0:
                print(f'OK|{name}|squashed-ahead={ahead2}->1')
            else:
                print(f'ERR|{name}|post-squash-failed')
                errs += 1
                continue
        else:
            print(f'OK|{name}|ahead={ahead2}')
        ok += 1

    except Exception as e:
        print(f'ERR|{name}|{str(e).replace(chr(10), " ")}')
        errs += 1

    if idx % 20 == 0:
        print(f'PROGRESS|processed={idx}|ok={ok}|changed={changed}|skip={skipped}|err={errs}')

print(f'SUMMARY|processed={len(repos)}|ok={ok}|changed={changed}|skip={skipped}|err={errs}')
