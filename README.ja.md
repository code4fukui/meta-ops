# meta-ops

Code for FUKUI 全体の README 整備を行う運用スクリプト集です。

このリポジトリはシンプル構成に整理済みで、再利用する主要スクリプトのみを保持します。

## 現在の構成

- `safe_first_candidates.txt`: 低リスク候補リポジトリ一覧
- `src/ops/`: Python 運用スクリプト
- `CLAUDE.md`: 品質・安全ルール
- `REPOSITORY_GUIDE.md`: 全体マップ

## スクリプト (`src/ops`)

- `generate_readmes_from_codebase.py`
  - 実コード/設定を解析して英語 `README.md` を生成
- `generate_readmes_full_refresh.py`
  - Bedrock を使った EN+JA のフル再生成
- `readme_quality_audit.py`
  - README 品質監査とレポート出力
- `commit_readmes_local.py`
  - README のみをローカルコミット
- `push_readmes.py`
  - レビュー済みコミットをバッチ push
- `delete_non_main_branches_all.py`
  - 非デフォルトブランチ一括整理
- `regen_all_bulk.py`
  - 一括 no-push 再生成の参照スクリプト

## クイックスタート

```bash
cd ~/meta-ops
python3 src/ops/generate_readmes_from_codebase.py --help
```

基本フロー:

1. README 生成/更新
2. 品質監査
3. ローカルコミット
4. サンプルレビュー
5. バッチ push

## 要件

- Linux
- Python 3.11+
- Git
- （必要時）`boto3` / `ffmpeg` / Pillow
- 対象 repo を `~/code4fukui` 配下に配置

## 安全ルール

- 明示承認なしで default ブランチに push しない
- 既存の重要説明と attribution を保持
- ライセンスは `LICENSE` へのリンクで統一
