# meta-ops

Code for FUKUI 全体に対して、README の国際化をリポジトリ横断で実行するための自動化・品質確認スクリプト集です。

このリポジトリは、README グローバル化ワークフローのうち再利用可能な公開サブセットを収録しています。
- AWS Bedrock を使って `README.md` / `README.ja.md` を生成
- コード、設定、スクリーンショット、動画フレームを生成コンテキストに利用
- 生成結果の品質監査
- README 変更のみをローカルでコミット
- レビュー後に安全なバッチで push

元の運用ワークスペースにあった、非公開インフラ設定、単発の復旧スクリプト、ローカル検証用成果物は含みません。

## リポジトリ構成

- [src/generate_readmes_full_refresh.py](src/generate_readmes_full_refresh.py): Bedrock を使って各 repo の `README.md` / `README.ja.md` を再生成（スクリーンショット・動画フレーム対応）
- [src/commit_readmes_local.py](src/commit_readmes_local.py): README 変更のみを各 repo でローカルコミット
- [src/push_readmes.py](src/push_readmes.py): README 変更のみを安全に push（再開可能）
- [src/readme_quality_audit.py](src/readme_quality_audit.py): 生成 README を監査して品質レポートを出力
- [src/ops/](src/ops): 段階的ロールアウトや復旧作業で使う補助運用スクリプト群
- [safe_first_candidates.txt](safe_first_candidates.txt): まず着手する低リスク候補 repo の一覧
- [REPOSITORY_GUIDE.md](REPOSITORY_GUIDE.md): リポジトリエコシステムの俯瞰ガイド

## 必要要件

- Ubuntu などの Linux ホスト
- Python 3.11+
- Git
- 動画フレーム抽出用の `ffmpeg`
- 画像リサイズ用の Pillow
- Bedrock 接続用の `boto3`
- `us-east-1` で Bedrock を呼び出せる AWS アイデンティティ
- `~/code4fukui` 配下に対象リポジトリ一式が配置されていること

スクリプトは以下の配置を前提にしています。

```text
~/meta-ops/
~/code4fukui/<repo-1>/
~/code4fukui/<repo-2>/
...
```

## AWS / Bedrock セットアップ

生成スクリプトは Bedrock Runtime API を直接利用します。デフォルト値は以下です。

- region: `us-east-1`
- model: `anthropic.claude-3-haiku-20240307-v1:0`

EC2 では、モデル呼び出し権限を持つインスタンスプロファイル / IAM ロールを使う構成が最もシンプルです。最低限、`us-east-1` で Bedrock invoke 権限が必要です。

IAM ポリシー例:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    }
  ]
}
```

インスタンスロールを使わない場合でも、標準の AWS 認証情報読み込みは利用できます。ただし、認証情報をこの repo に保存しないでください。

## 再現可能な EC2 セットアップ

1. Ubuntu EC2 インスタンスを起動
2. `us-east-1` で Bedrock Runtime を呼べる IAM ロールをアタッチ
3. インスタンスへ SSH 接続
4. システムパッケージをインストール
5. 本 repo と対象組織の repo 群を clone
6. Python 依存をインストール
7. ロールアウトで使う Git 署名情報を設定

セットアップ例:

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-pip python3-venv python3-pil ffmpeg rsync

cd ~
git clone https://github.com/code4fukui/meta-ops.git
mkdir -p ~/code4fukui
cd ~/code4fukui

# 対象 repo は運用方針に合わせた方法で clone してください。
# 自動化は、各 repo が ~/code4fukui 直下にある前提です。
```

Git 署名設定（任意）:

```bash
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"
```

大規模実行前の Bedrock 接続確認:

```bash
python3 - <<'PY'
import boto3
boto3.client('bedrock-runtime', region_name='us-east-1')
print('bedrock ok')
PY
```

## 生成ワークフロー

標準的な流れは次の通りです。

1. 全 repo に対して README をローカル生成
2. 生成結果を監査
3. README 変更のみをローカルコミット
4. サンプルを目視レビュー
5. 制御されたバッチで push

### 1. README 生成

EC2 上で実行:

```bash
cd ~/meta-ops
python3 src/generate_readmes_full_refresh.py
```

生成時に使う主なコンテキスト:
- README とコード / 設定ファイル
- CSV/TSV の小さなサンプル
- スクリーンショット
- 動画から抽出した 1 フレーム

生成時に避けるもの:
- ドキュメントに不要なバイナリアセット
- `LICENSE` 本文の丸写し
- 装飾用アイコンや極小画像

### 2. README 品質監査

```bash
cd ~/meta-ops
python3 src/readme_quality_audit.py
```

決定論的メトリクスと、サンプルに基づく AI 品質レビューを出力します。

### 3. ローカルのみコミット

```bash
cd ~/meta-ops
python3 src/commit_readmes_local.py
```

このスクリプトは各 repo で `README.md` / `README.ja.md` のみを stage し、push せずローカルコミットを作成します。

### 4. レビュー後に push

```bash
cd ~/meta-ops
python3 src/push_readmes.py
```

push スクリプトは保守的な設計です。
- README ファイルのみ stage
- 欠損 repo はスキップ
- force-push しない
- git 状態から再開可能
- 手動レビューが必要な repo を除外可能

## 長時間ジョブを安全に実行する

大規模実行は時間がかかるため、EC2 上では `nohup` / `screen` / `tmux` の利用を推奨します。

例:

```bash
cd ~/meta-ops
nohup env README_MAX_WORKERS=2 README_SLEEP_BETWEEN=1.5 README_THROTTLE_JITTER=2.0 \
  python3 src/generate_readmes_full_refresh.py > ~/regen_vision.log 2>&1 < /dev/null &
```

主な調整パラメータ:
- `README_MAX_WORKERS`: 並列ワーカー数
- `README_SLEEP_BETWEEN`: 生成呼び出し間隔
- `README_THROTTLE_JITTER`: 再試行時のランダム待機

Bedrock の `ThrottlingException` が出る場合に有効です。

## Vision 対応

UI が重要な repo では、スクリーンショットを Bedrock プロンプトに渡すことで README の精度を改善できます。動画を含む repo では、`ffmpeg` で 1 フレーム抽出して画像コンテキストとして利用します。

特に効果が高い領域:
- Web アプリ
- ダッシュボード
- 地図系アプリ
- AR / XR デモ
- 可視化系 repo

## 安全運用メモ

- AWS 認証情報、SSH 設定、非公開 repo リストを本 repo に保存しない
- 単発の復旧スクリプトは公開 repo 外で管理するか、`tmp/` 配下で未追跡のまま扱う
- 一括 push 前に必ずサンプルレビューを行う
- 全 repo 一括 push より、制御されたバッチ配信を優先する

## 一時ファイル

- `tmp/` は無視対象で、ローカル作業用に利用できます
- ログ、PID、Python キャッシュは無視対象です

## エンドツーエンド実行手順

このセクションは、組織規模で README 国際化を再現するための具体的な実行手順です。

### 1. EC2 を起動して準備

大規模バッチ向け推奨:
- Ubuntu 24.04 LTS
- 4 vCPU / 16 GB RAM クラス以上
- 全 repo を clone できる十分なディスク（組織規模により 100GB+）

依存パッケージをインストール:

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-pip python3-venv python3-pil ffmpeg rsync curl
```

### 2. AWS Bedrock 権限を設定

EC2 に、`us-east-1` で Bedrock Runtime を呼べる IAM ロールをアタッチします。

クイック確認:

```bash
python3 - <<'PY'
import boto3
boto3.client('bedrock-runtime', region_name='us-east-1')
print('bedrock ok')
PY
```

### 3. EC2 上で GitHub 接続設定

サーバ専用 SSH キーを作成し、GitHub アカウントへ公開鍵を登録します。

```bash
ssh-keygen -t ed25519 -C "ec2-readme-ops" -f ~/.ssh/ec2_readme_ops
cat ~/.ssh/ec2_readme_ops.pub
```

SSH 設定:

```bash
cat >> ~/.ssh/config << 'EOF'
Host github.com
  IdentityFile ~/.ssh/ec2_readme_ops
  User git
EOF
chmod 600 ~/.ssh/config
ssh -T git@github.com
```

注意: バックグラウンド実行前に、SSH ホスト鍵受諾を一度対話で済ませてください。

### 4. repo を clone

まず本 repo を clone:

```bash
cd ~
git clone https://github.com/code4fukui/meta-ops.git
mkdir -p ~/code4fukui
```

続いて対象組織 repo を `~/code4fukui` へ展開します。再現しやすい方法として GitHub API ページング例:

```bash
cat > ~/clone_all.sh << 'BASH'
#!/usr/bin/env bash
set -euo pipefail

ORG="code4fukui"
OUT="$HOME/code4fukui"
LOG="$HOME/clone.log"
mkdir -p "$OUT"
cd "$OUT"

echo "=== clone start $(date -Iseconds) ===" | tee -a "$LOG"
page=1
while true; do
  urls=$(curl -fsSL "https://api.github.com/orgs/$ORG/repos?type=public&per_page=100&page=$page" \
    | python3 -c "import sys, json; d=json.load(sys.stdin); [print(x['ssh_url']) for x in d]")

  [[ -z "$urls" ]] && break

  while IFS= read -r url; do
    [[ -z "$url" ]] && continue
    name=$(basename "$url" .git)
    if [[ -d "$name/.git" ]]; then
      echo "SKIP $name" | tee -a "$LOG"
    else
      if git clone --depth=1 "$url"; then
        echo "OK   $name" | tee -a "$LOG"
      else
        echo "FAIL $name" | tee -a "$LOG"
      fi
    fi
  done <<< "$urls"

  page=$((page + 1))
done
echo "=== clone done $(date -Iseconds) ===" | tee -a "$LOG"
BASH

chmod +x ~/clone_all.sh
bash ~/clone_all.sh
```

### 5. 生成実行（Vision 有効）

前景実行:

```bash
cd ~/meta-ops
python3 src/generate_readmes_full_refresh.py
```

安全なバックグラウンド実行:

```bash
cd ~/meta-ops
nohup env README_MAX_WORKERS=2 README_SLEEP_BETWEEN=1.5 README_THROTTLE_JITTER=2.0 \
  python3 src/generate_readmes_full_refresh.py > ~/regen_vision.log 2>&1 < /dev/null &
echo $! > ~/regen_vision.pid
```

進捗確認:

```bash
tail -f ~/regen_vision.log
```

### 6. 品質監査

```bash
cd ~/meta-ops
python3 src/readme_quality_audit.py
```

### 7. ローカルコミット（push なし）

```bash
cd ~/meta-ops
python3 src/commit_readmes_local.py
```

### 8. 制御バッチで push

```bash
cd ~/meta-ops
python3 src/push_readmes.py
```

推奨運用:
- まず小バッチで push
- 代表 repo を手動レビュー
- 問題なければ段階的に拡大

### 9. 検証と再開

長時間ジョブが中断された場合:
- 生成は同じスクリプトで再実行可能
- commit/push は git 状態を使って再開可能

便利な確認コマンド:

```bash
pgrep -af 'generate_readmes_full_refresh.py|commit_readmes_local.py|push_readmes.py'
tail -n 50 ~/regen_vision.log
tail -n 50 ~/commit_readmes_local.log
tail -n 50 ~/push.log
```