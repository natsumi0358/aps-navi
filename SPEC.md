# ②アカマネ機能 — 開発仕様書

## 概要
初回商談前の会社調査を支援するWebアプリ。
akamane.jp とほぼ同じ機能を Flask + Claude API で実装する。
①逆算提案コーチなつみんと同じ技術スタックで作る。

---

## 画面構成

### 1. トップ画面（会社一覧）
- 過去に作成した会社のカード一覧
- 「+ 新しい会社を追加」ボタン
- 会社名・業種・最終更新日を表示

### 2. 会社情報入力フォーム（新規・編集）
以下の項目を入力できるフォームを作る：

#### 基本情報
- 会社名（必須）
- 業種
- 従業員数
- 売上規模（概算）
- 会社HP URL
- 担当営業名

#### APS調査項目（akamane.jpの項目に準拠）
- **会社概要・事業内容**（テキストエリア）
- **中期経営計画・会社の方針**（テキストエリア）
- **キーパーソン一覧**
  - 名前・役職・意思決定権（あり/なし/不明）・備考
  - 複数人追加できる
- **現在使っているシステム一覧**
  - システム名・自社/他社・導入時期・リプレース見込み時期
  - 複数行追加できる
- **競合状況**（テキストエリア）
- **顧客の顧客（エンドユーザー）の課題**（テキストエリア）
- **潜在ニーズ・本音（ヒアリングメモ）**（テキストエリア）
- **ビッグプレー候補**（テキストエリア）
- **現在の案件・パイプライン状況**（テキストエリア）

### 3. AIアドバイス画面
- 入力した会社情報を①のシステムプロンプトに渡す
- 「AIにアドバイスをもらう」ボタンを押すと加藤夏美AIが分析・アドバイスを返す
- アドバイス結果を画面に表示（マークダウン対応）
- チャット形式で追加質問もできる

---

## 技術スタック
- **言語**：Python 3
- **フレームワーク**：Flask
- **DB**：SQLite（companies.db）
- **AI**：Claude API（claude-sonnet-4-6）
- **フロントエンド**：HTML + CSS + JavaScript（①と同じスタイル）
- **デプロイ**：Render（①と同じ）

---

## データベース設計

### companies テーブル
| カラム | 型 | 説明 |
|---|---|---|
| id | INTEGER | 主キー |
| company_name | TEXT | 会社名 |
| industry | TEXT | 業種 |
| employees | TEXT | 従業員数 |
| revenue | TEXT | 売上規模 |
| hp_url | TEXT | HP URL |
| sales_person | TEXT | 担当営業名 |
| overview | TEXT | 会社概要 |
| mid_term_plan | TEXT | 中期経営計画 |
| systems | TEXT | システム一覧（JSON） |
| key_persons | TEXT | キーパーソン（JSON） |
| competitors | TEXT | 競合状況 |
| end_user_issues | TEXT | エンドユーザーの課題 |
| latent_needs | TEXT | 潜在ニーズ |
| big_play | TEXT | ビッグプレー候補 |
| pipeline | TEXT | 案件・パイプライン状況 |
| created_at | TEXT | 作成日時 |
| updated_at | TEXT | 更新日時 |

---

## ファイル構成
```
akamane/
├── app.py                  # Flask アプリ本体
├── requirements.txt        # 必要ライブラリ
├── .env.example            # 環境変数テンプレート
├── README.md               # 概要
├── SPEC.md                 # この仕様書
├── database.py             # DB初期化・操作
└── templates/
    ├── base.html           # 共通レイアウト
    ├── index.html          # 会社一覧
    ├── company_form.html   # 会社情報入力フォーム
    └── advisor.html        # AIアドバイス画面
```

---

## デザイン方針
- ①と同じ配色（#1a1a2e ダークネイビー）
- スマホでも使えるレスポンシブデザイン
- シンプルで使いやすいUI

---

## 開発手順（しょうさんへの指示）

1. `database.py` を作成してSQLiteのDB初期化コードを書く
2. `app.py` を作成してFlaskルートを実装する
   - GET `/` → 会社一覧
   - GET/POST `/company/new` → 新規会社登録
   - GET/POST `/company/<id>/edit` → 編集
   - GET `/company/<id>/advisor` → AIアドバイス画面
   - POST `/company/<id>/chat` → AIチャットAPI
   - POST `/company/<id>/delete` → 削除
3. `templates/` 以下のHTMLを作成する
4. `requirements.txt` に必要ライブラリを記載する
5. GitHubリポジトリ `akamane` を作成してpushする
6. Renderにデプロイする（①と同じ手順）
7. 環境変数 `ANTHROPIC_API_KEY` を設定する

---

## AIへの渡し方（システムプロンプトの構成）

①のシステムプロンプト（加藤夏美の頭脳）＋以下の会社情報を組み合わせる：

```
【調査対象会社】{company_name}

【会社概要】{overview}
【中期経営計画】{mid_term_plan}
【キーパーソン】{key_persons}
【システム一覧】{systems}
【競合状況】{competitors}
【エンドユーザーの課題】{end_user_issues}
【潜在ニーズ】{latent_needs}
【ビッグプレー候補】{big_play}
【パイプライン状況】{pipeline}

上記の情報をもとに、APS観点でアドバイスをしてください。
```
