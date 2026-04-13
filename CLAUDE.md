# APSナビ — AI開発ガイド（Cursor & Claude Code 共通リファレンス）

> **このファイルはCursorとClaude Codeが常に参照する唯一の真実（Single Source of Truth）。**
> コードを変更したら、このファイルの該当箇所も必ず更新すること。

---

## ① プロジェクト概要

**APSナビ**（旧称：アカマネ）  
N.K.ナーツ株式会社の営業チーム向け「APS（アカウントプランニングセッション）作成サポートツール」。

| 項目 | 内容 |
|------|------|
| 目的 | 営業がAPS（アカウントプラン）を効率的に作成できるようにする |
| 対象ユーザー | N.K.ナーツの営業（将来的に100名規模） |
| 現フェーズ | MVP（ログインなし・テンプレート1種類・100社保存） |
| 本番URL | https://aps-navi.onrender.com |
| GitHubリポジトリ | https://github.com/natsumi0358/aps-navi |
| デプロイ | Render（GitHub push で自動デプロイ） |

---

## ② 役割分担（Cursor vs Claude Code）

### Cursorが担当する作業

```
✅ 日常的な小修正・バグ修正（1〜3ファイル程度の変更）
✅ HTMLテンプレートのデザイン調整・CSS修正
✅ 既存関数のリファクタリング
✅ コードの補完・提案の受け入れ
✅ ローカルでの動作確認・デバッグ
✅ git add / git commit（小さな変更）
```

### Claude Codeが担当する作業

```
✅ 新機能の設計・実装（複数ファイルにまたがる変更）
✅ DBスキーマの変更（database.py + マイグレーション）
✅ 新APIエンドポイントの追加（app.py）
✅ このCLAUDE.mdの更新・SPEC.mdの更新
✅ GitHub push & Renderデプロイ確認
✅ 大規模リファクタリング
✅ 要件定義・設計相談
```

### 共同作業のルール

1. **どちらが作業しても、変更後に `CLAUDE.md` の「⑦ 最新の実装状態」を更新する**
2. **DBスキーマを変更したら `database.py` の `init_db()` と `new_columns` リストを必ず両方更新する**
3. **新しいフォームフィールドを追加したら `_parse_form()` にも必ず追加する**
4. **Renderへのデプロイは `git push origin main` のみ（自動）**

---

## ③ 技術スタック

| 技術 | バージョン | 用途 |
|------|-----------|------|
| Python | 3.x | バックエンド言語 |
| Flask | >=3.0.0 | Webフレームワーク |
| SQLite | 標準 | データベース（companies.db） |
| Anthropic SDK | >=0.28.0 | Claude API |
| python-pptx | >=0.6.21 | PPTXテンプレート流し込み |
| BeautifulSoup4 | >=4.12.0 | HPスクレイピング |
| requests | >=2.31.0 | HTTP取得 |
| gunicorn | >=21.2.0 | 本番サーバー |
| Marked.js | CDN | フロントのMarkdownレンダリング |

---

## ④ ファイル構成

```
akamane/
├── CLAUDE.md                              ← ★このファイル（常時参照）
├── SPEC.md                                ← 詳細仕様書
├── README.md                              ← GitHub用概要
├── app.py                                 ← Flaskアプリ本体（全ルート定義）
├── database.py                            ← DB初期化・CRUD操作
├── requirements.txt                       ← 依存ライブラリ
├── render.yaml                            ← Renderデプロイ設定
├── companies.db                           ← SQLiteデータ（本番はRenderの永続ストレージ不使用）
├── アカウントプラン_テンプレート_260226.pptx  ← PPTXテンプレート
└── templates/
    ├── base.html                          ← 共通レイアウト（ヘッダー・フッター）
    ├── index.html                         ← 会社一覧（カードグリッド）
    ├── company_form.html                  ← 会社情報入力フォーム（Work6〜13）
    └── advisor.html                       ← AIアドバイス・チャット画面
```

---

## ⑤ データベース設計（最新）

### companies テーブル

| カラム | 型 | 説明 | 入力方式 |
|--------|-----|------|---------|
| id | INTEGER PK | 主キー | 自動 |
| company_name | TEXT | 会社名 | 手入力 |
| industry | TEXT | 業種 | AI自動取得 |
| sales_person | TEXT | 担当営業名 | 手入力 |
| hp_url | TEXT | 会社HP URL | 手入力 |
| **Work6（お客様概要）** | | | |
| founded | TEXT | 創業年 | AI自動取得 |
| established | TEXT | 設立年 | AI自動取得 |
| headquarters | TEXT | 本社所在地 | AI自動取得 |
| capital | TEXT | 資本金 | AI自動取得 |
| revenue | TEXT | 売上高 | AI自動取得 |
| operating_profit | TEXT | 経常利益 | AI自動取得 |
| employees | TEXT | 従業員数 | AI自動取得 |
| branches | TEXT | 事業所・店舗 | AI自動取得 |
| group_companies | TEXT | グループ会社 | AI自動取得 |
| overview | TEXT | 事業内容・会社概要 | AI自動取得 |
| president_profile | TEXT | 代表者プロフィール | AI自動取得 |
| mvv | TEXT | MVV（ミッション・ビジョン・バリュー） | AI自動取得 |
| company_detail | TEXT | 補足詳細 | 手入力 |
| **Work7（経営方針）** | | | |
| mid_term_plan | TEXT | 中期経営計画・経営方針 | 手入力 |
| ir_info | TEXT | IR情報・業績トレンド | 手入力 |
| investment_areas | TEXT | 投資エリア・想定ソリューション | AI自動生成 |
| **業界分析（Work2〜5）** | | | |
| pest | TEXT | PEST分析 | AI自動生成 |
| five_forces | TEXT | 5Forces分析 | AI自動生成 |
| swot | TEXT | SWOT分析 | AI自動生成 |
| cross_swot | TEXT | クロスSWOT分析 | AI自動生成 |
| positioning | TEXT | ポジショニング | AI自動生成 |
| **営業調査** | | | |
| systems | TEXT (JSON) | システム一覧 | 手入力 |
| key_persons | TEXT (JSON) | キーパーソン一覧 | 手入力 |
| competitors | TEXT | 競合状況 | 手入力 |
| end_user_issues | TEXT | エンドユーザーの課題 | 手入力 |
| latent_needs | TEXT | 潜在ニーズ・本音 | 手入力 |
| big_play | TEXT | ビッグプレー候補 | 手入力 |
| pipeline | TEXT | 現在の案件・パイプライン | 手入力 |
| **Work8〜13** | | | |
| activity_history | TEXT | これまでの活動（時系列） | 手入力 |
| mid_long_term_plan | TEXT | 中長期3〜5ヵ年プラン | 手入力 |
| org_chart | TEXT | 組織図・意思決定ルート | 手入力 |
| forecast | TEXT | 今期Forecast | 手入力 |
| key_cases | TEXT | 主要案件概要書 | 手入力 |
| coverage_map | TEXT | カバレッジマップ | 手入力 |
| action_plan | TEXT | アクションプラン（90日） | 手入力 |
| company_requests | TEXT | お客様リクエスト・懸案 | 手入力 |
| created_at | TEXT | 作成日時 | 自動 |
| updated_at | TEXT | 更新日時 | 自動 |

> **⚠️ DBスキーマを変更するときは必ず `database.py` の `init_db()` の CREATE TABLE と `new_columns` リストの両方を更新する。**

---

## ⑥ APIエンドポイント一覧（最新）

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/` | 会社一覧ページ |
| GET | `/company/new` | 新規登録フォーム |
| POST | `/company/new` | 会社を保存（action_type=save or save_ppt） |
| GET | `/company/<id>/edit` | 編集フォーム |
| POST | `/company/<id>/edit` | 会社を更新（action_type=save or save_ppt） |
| GET | `/company/<id>/advisor` | AIアドバイス画面 |
| POST | `/company/<id>/chat` | AIチャットAPI（JSON） |
| POST | `/company/<id>/analyze` | AI初回総合分析API（JSON） |
| POST | `/company/<id>/delete` | 会社削除 |
| POST | `/api/fetch_url` | HPからWork6情報をAI自動抽出（JSON） |
| POST | `/company/<id>/generate_analysis` | 業界分析AI自動生成（JSON） |
| GET | `/company/<id>/download_ppt` | PPTXダウンロード |

### action_type の挙動

フォームのhidden input `action_type` の値によって保存後の遷移が変わる：
- `save` → AIアドバイス画面へリダイレクト（デフォルト）
- `save_ppt` → PPTXダウンロードへリダイレクト

---

## ⑦ フォーム構成（company_form.html）

APS講義資料「アカウントプランニングセッション研修_20260206」のWork体系に準拠：

| セクション | Work | 内容 | AI対応 |
|-----------|------|------|--------|
| 基本情報 | - | 会社名・業種・担当・HP URL | - |
| お客様の概要 | Work 6 | 社名/創業/設立/本社/資本金/売上/利益/社員/事業内容/事業所/グループ/代表者 | HPから自動取得 |
| お客様の経営方針 | Work 7 | MVV/中計/IR情報/投資エリア | 一部AI自動取得 |
| 業界分析 | Work 2〜5 | PEST/5Forces/SWOT/クロスSWOT/ポジショニング | AI自動生成ボタン |
| キーパーソン | Work 10・13 | キーパーソン一覧/組織図/カバレッジマップ | 手入力 |
| システム一覧 | - | 現在のシステム | 手入力 |
| 営業調査 | - | 競合/潜在ニーズ/ビッグプレー/パイプライン | 手入力 |
| これまでの活動 | Work 8 | 時系列活動履歴 | 手入力 |
| 中長期プラン | Work 9 | 3〜5ヵ年案件仮説 | 手入力 |
| Forecast | Work 11 | 今期案件・金額・確度 | 手入力 |
| 主要案件 | Work 12 | 概要書 | 手入力 |
| アクションプラン | Work 13他 | 90日アクション/リクエスト | 手入力 |

---

## ⑧ AI自動取得の仕組み

### HP自動取得（`/api/fetch_url`）

1. `fetch_url_text(url)` でトップページを取得
2. BeautifulSoup4で会社概要ページのリンクを自動検索（"会社情報", "corporate", "about" 等のキーワード）
3. 最大2ページ追加取得して結合
4. Claude API（claude-sonnet-4-6）でWork6フィールドをJSON抽出
5. フロントエンドで既入力フィールドを上書きせずに補完

### 業界分析自動生成（`/company/<id>/generate_analysis`）

1. DBから会社名・業種・概要・中計を取得
2. Claude API でPEST/5Forces/SWOT/クロスSWOT/ポジショニング/投資エリアを一括生成
3. 結果をDBに保存（UPDATE）
4. フロントエンドでフォームに反映

---

## ⑨ PPTXテンプレートの構成

ファイル: `アカウントプラン_テンプレート_260226.pptx`（34スライド）

| スライド | 内容 | DBフィールド |
|---------|------|------------|
| P1 | タイトル | company_name, sales_person |
| P13 (index 12) | Work6: お客様概要 | founded/established/capital/revenue/employees/overview/group_companies |
| P18 (index 17) | Work7: MVV | mvv |
| P20 (index 19) | Work7: 経営方針・中計 | mid_term_plan, ir_info |
| P22 (index 21) | Work7: 投資エリア | investment_areas |

> PPTXの流し込みは `download_ppt()` 関数（app.py）で `safe_write()` ヘルパーを使用。
> キーワードマッチングでテキストボックスを特定してから書き込む。

---

## ⑩ 環境変数

| 変数名 | 説明 | 設定場所 |
|--------|------|---------|
| ANTHROPIC_API_KEY | Claude APIキー | Render → Environment |
| FLASK_SECRET_KEY | セッション暗号化 | Renderが自動生成 |

ローカル開発時は `.env` ファイルを作成（`.gitignore` に追加済み）:
```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
```

---

## ⑪ ローカル開発手順

```bash
# 1. リポジトリをクローン（初回のみ）
git clone https://github.com/natsumi0358/aps-navi.git
cd aps-navi

# 2. 仮想環境を作成・有効化
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate  # Windows

# 3. 依存ライブラリをインストール
pip install -r requirements.txt

# 4. 環境変数を設定
cp .env.example .env
# .envにANTHROPIC_API_KEYを記入

# 5. アプリ起動
python app.py
# → http://localhost:5002 でアクセス
```

---

## ⑫ デプロイ手順

```bash
# Renderへは git push するだけで自動デプロイ
git add .
git commit -m "変更内容の説明"
git push origin main

# Renderのダッシュボードでデプロイ状況を確認:
# https://dashboard.render.com
```

---

## ⑬ 未実装・今後の拡張予定

| 優先度 | 機能 | 概要 |
|--------|------|------|
| 高 | PPTXスライド流し込み精度向上 | Work8〜13のスライドにも流し込む |
| 中 | テンプレート切り替え機能 | 複数PPTXテンプレートを選択できる |
| 中 | ログイン機能 | 担当者ごとにデータを管理 |
| 低 | AIによるWork8〜13の下書き生成 | 活動履歴・案件仮説のAI補助 |
| 低 | エクスポート機能 | PDF出力、CSV出力 |

---

## ⑭ よくあるエラーと対処法

| エラー | 原因 | 対処 |
|--------|------|------|
| Internal Server Error | `init_db()` が呼ばれていない | `app = Flask(...)` 直後に `init_db()` があるか確認 |
| URLフェッチ失敗 | タイムアウト or ロボット拒否 | `fetch_page_text()` のtimeoutを調整。robots.txtを確認 |
| JSONパースエラー | Claudeがコードブロック付きで返した | `raw.split("```")` でJSON部分を抽出している箇所を確認 |
| PPTXダウンロード503 | テンプレートファイルが見つからない | `TEMPLATE_PATH.exists()` を確認。ファイル名に日本語文字 |
| Renderでgunicornが起動しない | `render.yaml` の startCommand を確認 | `gunicorn app:app` になっているか確認 |

---

*最終更新: 2026-04-14 / 更新者: Claude Code*
