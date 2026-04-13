import os
import io
import json
import anthropic
import requests
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from pathlib import Path
from bs4 import BeautifulSoup
from database import init_db, get_all_companies, get_company, create_company, update_company, delete_company

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "nknarts-aps-navi-secret")

# DB初期化（gunicorn起動時にも必ず実行）
init_db()

# システムプロンプトを読み込む
SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "aps-advisor-ai" / "knowledge" / "system_prompt.md"
try:
    with open(SYSTEM_PROMPT_PATH, encoding="utf-8") as f:
        BASE_SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    BASE_SYSTEM_PROMPT = "あなたはAPS観点で営業アドバイスをするAIアドバイザーです。"

# PPTXテンプレートパス
TEMPLATE_PATH = Path(__file__).parent / "アカウントプラン_テンプレート_260226.pptx"

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MAX_HISTORY = 20


# ─────────────────────────────────────────
# ヘルパー関数
# ─────────────────────────────────────────

def build_system_prompt(company):
    systems = company.get("systems", [])
    key_persons = company.get("key_persons", [])

    systems_text = "\n".join([
        f"  - {s.get('name','')}（{s.get('type','')}）導入：{s.get('installed','')} / リプレース見込み：{s.get('replace','')}"
        for s in systems
    ]) or "  （未入力）"

    key_persons_text = "\n".join([
        f"  - {p.get('name','')}（{p.get('title','')}）意思決定権：{p.get('decision','')} / {p.get('note','')}"
        for p in key_persons
    ]) or "  （未入力）"

    company_info = f"""
【調査対象会社】{company.get('company_name', '')}
【業種】{company.get('industry', '')}
【従業員数】{company.get('employees', '')}
【売上規模】{company.get('revenue', '')}
【担当営業】{company.get('sales_person', '')}

【会社概要】{company.get('overview', '（未入力）')}
【中期経営計画】{company.get('mid_term_plan', '（未入力）')}
【MVV】{company.get('mvv', '（未入力）')}
【競合状況】{company.get('competitors', '（未入力）')}
【エンドユーザーの課題】{company.get('end_user_issues', '（未入力）')}
【潜在ニーズ】{company.get('latent_needs', '（未入力）')}
【ビッグプレー候補】{company.get('big_play', '（未入力）')}
【パイプライン状況】{company.get('pipeline', '（未入力）')}
【キーパーソン】{key_persons_text}
【システム一覧】{systems_text}

上記の情報をもとに、APS観点でアドバイスをしてください。
"""
    return BASE_SYSTEM_PROMPT + "\n\n---\n" + company_info


def fetch_url_text(url):
    """URLのHTMLテキストを取得"""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; APSNavi/1.0)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    # 長すぎる場合は先頭8000字に絞る
    return text[:8000]


def set_slide_text(slide, placeholder_text, new_text):
    """スライド内の指定テキストを置換"""
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                if placeholder_text in run.text:
                    run.text = run.text.replace(placeholder_text, new_text)


def fill_text_box(slide, search_keyword, new_text, max_chars=500):
    """キーワードを含むテキストボックスの内容を置き換える"""
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        full_text = shape.text_frame.text
        if search_keyword in full_text:
            tf = shape.text_frame
            # 全段落をクリアして最初の段落に書き込む
            for i, para in enumerate(tf.paragraphs):
                for run in para.runs:
                    run.text = ""
            if tf.paragraphs:
                run = tf.paragraphs[0].runs
                if run:
                    run[0].text = new_text[:max_chars]
                else:
                    from pptx.util import Pt
                    tf.paragraphs[0].text = new_text[:max_chars]
            break


# ─────────────────────────────────────────
# ルート
# ─────────────────────────────────────────

@app.route("/")
def index():
    companies = get_all_companies()
    return render_template("index.html", companies=companies)


@app.route("/company/new", methods=["GET", "POST"])
def company_new():
    if request.method == "POST":
        data = _parse_form(request.form)
        company_id = create_company(data)
        return redirect(url_for("company_advisor", company_id=company_id))
    return render_template("company_form.html", company=None, mode="new")


@app.route("/company/<int:company_id>/edit", methods=["GET", "POST"])
def company_edit(company_id):
    company = get_company(company_id)
    if not company:
        return redirect(url_for("index"))
    if request.method == "POST":
        data = _parse_form(request.form)
        update_company(company_id, data)
        return redirect(url_for("company_advisor", company_id=company_id))
    return render_template("company_form.html", company=company, mode="edit")


@app.route("/company/<int:company_id>/advisor")
def company_advisor(company_id):
    company = get_company(company_id)
    if not company:
        return redirect(url_for("index"))
    session_key = f"history_{company_id}"
    session[session_key] = []
    return render_template("advisor.html", company=company)


@app.route("/company/<int:company_id>/chat", methods=["POST"])
def company_chat(company_id):
    company = get_company(company_id)
    if not company:
        return jsonify({"error": "会社情報が見つかりません"}), 404

    data = request.get_json()
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "メッセージを入力してください"}), 400

    session_key = f"history_{company_id}"
    history = session.get(session_key, [])
    history.append({"role": "user", "content": user_message})
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=build_system_prompt(company),
            messages=history,
        )
        assistant_message = response.content[0].text
        history.append({"role": "assistant", "content": assistant_message})
        session[session_key] = history
        return jsonify({"reply": assistant_message})
    except Exception as e:
        return jsonify({"error": f"エラーが発生しました: {str(e)}"}), 500


@app.route("/company/<int:company_id>/analyze", methods=["POST"])
def company_analyze(company_id):
    company = get_company(company_id)
    if not company:
        return jsonify({"error": "会社情報が見つかりません"}), 404

    first_message = f"{company.get('company_name', '')}についてAPS観点で総合的にアドバイスしてください。特に「ビッグプレー候補」「潜在ニーズの深掘り」「パイプラインの充実度」の観点でお願いします。"
    history = [{"role": "user", "content": first_message}]

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=build_system_prompt(company),
            messages=history,
        )
        assistant_message = response.content[0].text
        history.append({"role": "assistant", "content": assistant_message})
        session[f"history_{company_id}"] = history
        return jsonify({"reply": assistant_message})
    except Exception as e:
        return jsonify({"error": f"エラーが発生しました: {str(e)}"}), 500


@app.route("/company/<int:company_id>/delete", methods=["POST"])
def company_delete(company_id):
    delete_company(company_id)
    return redirect(url_for("index"))


# ─────────────────────────────────────────
# URL自動取得API
# ─────────────────────────────────────────

@app.route("/api/fetch_url", methods=["POST"])
def api_fetch_url():
    """HPのURLを読み込んでAIで会社情報を自動抽出"""
    data = request.get_json()
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "URLを入力してください"}), 400

    try:
        hp_text = fetch_url_text(url)
    except Exception as e:
        return jsonify({"error": f"URLの取得に失敗しました: {str(e)}"}), 400

    prompt = f"""以下は企業のHPから取得したテキストです。
このテキストをもとに、下記の情報をJSON形式で抽出してください。
情報がない項目は空文字列にしてください。架空の情報は絶対に作らないでください。

抽出する項目：
- company_name: 会社名（正式名称）
- industry: 業種（例：製造業、IT・SIer、旅行業など）
- employees: 従業員数
- revenue: 売上規模（概算）
- overview: 会社概要・事業内容（300字程度）
- mid_term_plan: 中期経営計画・会社方針（200字程度）
- mvv: ミッション・ビジョン・バリュー（MVV）
- president_profile: 代表者名・プロフィール（100字程度）

HPテキスト：
{hp_text}

JSON形式のみで返してください（説明文不要）："""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        # JSON部分だけ抽出
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        return jsonify({"success": True, "data": result})
    except json.JSONDecodeError:
        return jsonify({"error": "AIの返答をパースできませんでした。もう一度試してください。"}), 500
    except Exception as e:
        return jsonify({"error": f"エラーが発生しました: {str(e)}"}), 500


# ─────────────────────────────────────────
# APS業界分析 自動生成API
# ─────────────────────────────────────────

@app.route("/company/<int:company_id>/generate_analysis", methods=["POST"])
def generate_analysis(company_id):
    """PEST・5Forces・SWOT・クロスSWOT・ポジショニングを自動生成してDBに保存"""
    company = get_company(company_id)
    if not company:
        return jsonify({"error": "会社情報が見つかりません"}), 404

    company_name = company.get("company_name", "")
    industry = company.get("industry", "")
    overview = company.get("overview", "")

    prompt = f"""以下の企業について、APS観点での業界分析を行ってください。
架空の情報は作らず、一般的な業界知識と提供された情報をもとに分析してください。

企業名：{company_name}
業種：{industry}
会社概要：{overview}

以下の分析を日本語で、各200〜400字程度で行いJSON形式で返してください：

{{
  "pest": "PEST分析（政治・経済・社会・技術の4観点で業界への影響を分析）",
  "five_forces": "5Forces分析（新規参入・売り手・買い手・代替品・既存競合の5観点で分析）",
  "swot": "SWOT分析（強み・弱み・機会・脅威を箇条書きで）",
  "cross_swot": "クロスSWOT分析（強み×機会、強み×脅威、弱み×機会、弱み×脅威の戦略を提示）",
  "positioning": "ポジショニング（業界内での差別化ポイントと競合との比較）",
  "investment_areas": "投資エリア（公開情報から投資可能性がある領域と想定されるソリューション）"
}}

JSONのみ返してください（説明文不要）："""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)

        # DBに保存
        update_data = dict(company)
        update_data.update(result)
        update_company(company_id, update_data)

        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"error": f"分析生成に失敗しました: {str(e)}"}), 500


# ─────────────────────────────────────────
# PPTXダウンロード
# ─────────────────────────────────────────

@app.route("/company/<int:company_id>/download_ppt", methods=["GET"])
def download_ppt(company_id):
    """テンプレートに会社情報を流し込んでPPTXをダウンロード"""
    from pptx import Presentation
    from pptx.util import Pt
    import copy

    company = get_company(company_id)
    if not company:
        return jsonify({"error": "会社情報が見つかりません"}), 404

    if not TEMPLATE_PATH.exists():
        return jsonify({"error": "テンプレートファイルが見つかりません"}), 500

    prs = Presentation(str(TEMPLATE_PATH))

    company_name = company.get("company_name", "")
    sales_person = company.get("sales_person", "")

    def replace_in_shape(shape, old, new):
        if not shape.has_text_frame:
            return
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                if old in run.text:
                    run.text = run.text.replace(old, new)

    def write_to_shape_by_index(slide, shape_idx, text, max_chars=600):
        """スライド内のshape_idx番目のテキストボックスに書き込む"""
        text_shapes = [s for s in slide.shapes if s.has_text_frame]
        if shape_idx < len(text_shapes):
            tf = text_shapes[shape_idx].text_frame
            tf.word_wrap = True
            # 既存テキストをクリア
            for para in tf.paragraphs:
                for run in para.runs:
                    run.text = ""
            if tf.paragraphs and tf.paragraphs[0].runs:
                tf.paragraphs[0].runs[0].text = str(text)[:max_chars]
            else:
                tf.paragraphs[0].text = str(text)[:max_chars]

    # スライドごとに情報を流し込む
    slides = prs.slides

    # P6: PEST分析（例の文字列を差し替え）
    if len(slides) > 5 and company.get("pest"):
        slide = slides[5]
        for shape in slide.shapes:
            if shape.has_text_frame and "家具・インテリア業界" in shape.text_frame.text:
                for para in shape.text_frame.paragraphs:
                    for run in para.runs:
                        run.text = run.text.replace("家具・インテリア業界", f"{company.get('industry', company_name)}業界")

    # P13: 会社概要（Work6）- テキスト全体をタイトルと内容で構成
    if len(slides) > 12:
        slide = slides[12]
        overview_text = f"""■ {company_name}

業種：{company.get('industry', '')}
従業員数：{company.get('employees', '')}
売上規模：{company.get('revenue', '')}
HP：{company.get('hp_url', '')}

【事業内容】
{company.get('overview', '')}

【代表者】
{company.get('president_profile', '')}"""
        # 最初の大きなテキストボックスに書き込む
        for shape in slide.shapes:
            if shape.has_text_frame and ("社名" in shape.text_frame.text or "創業" in shape.text_frame.text):
                tf = shape.text_frame
                tf.word_wrap = True
                for para in tf.paragraphs:
                    for run in para.runs:
                        run.text = ""
                if tf.paragraphs:
                    if tf.paragraphs[0].runs:
                        tf.paragraphs[0].runs[0].text = overview_text[:800]
                    else:
                        tf.paragraphs[0].text = overview_text[:800]
                break

    # P18: MVV
    if len(slides) > 17 and company.get("mvv"):
        slide = slides[17]
        for shape in slide.shapes:
            if shape.has_text_frame and "MVV" in shape.text_frame.text:
                tf = shape.text_frame
                for para in tf.paragraphs:
                    for run in para.runs:
                        run.text = ""
                if tf.paragraphs:
                    if tf.paragraphs[0].runs:
                        tf.paragraphs[0].runs[0].text = company.get("mvv", "")[:600]
                    else:
                        tf.paragraphs[0].text = company.get("mvv", "")[:600]
                break

    # P20: 経営方針・中期計画
    if len(slides) > 19 and company.get("mid_term_plan"):
        slide = slides[19]
        for shape in slide.shapes:
            if shape.has_text_frame and ("経営方針" in shape.text_frame.text or "中期" in shape.text_frame.text):
                tf = shape.text_frame
                for para in tf.paragraphs:
                    for run in para.runs:
                        run.text = ""
                if tf.paragraphs:
                    if tf.paragraphs[0].runs:
                        tf.paragraphs[0].runs[0].text = company.get("mid_term_plan", "")[:600]
                    else:
                        tf.paragraphs[0].text = company.get("mid_term_plan", "")[:600]
                break

    # P22: 投資エリア
    if len(slides) > 21 and company.get("investment_areas"):
        slide = slides[21]
        for shape in slide.shapes:
            if shape.has_text_frame and len(shape.text_frame.text) > 100:
                tf = shape.text_frame
                for para in tf.paragraphs:
                    for run in para.runs:
                        run.text = ""
                if tf.paragraphs:
                    if tf.paragraphs[0].runs:
                        tf.paragraphs[0].runs[0].text = company.get("investment_areas", "")[:800]
                    else:
                        tf.paragraphs[0].text = company.get("investment_areas", "")[:800]
                break

    # タイトルスライド（P1）に会社名と担当営業を追加
    if len(slides) > 0:
        slide = slides[0]
        for shape in slide.shapes:
            if shape.has_text_frame:
                replace_in_shape(shape, "N.K.ナーツ株式会社", f"{company_name}\n担当：{sales_person}")

    # バイナリとして書き出し
    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)

    filename = f"APS_{company_name}_{company.get('sales_person', '')}.pptx"
    filename = filename.replace("/", "_").replace(" ", "_")

    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )


# ─────────────────────────────────────────
# フォームパース
# ─────────────────────────────────────────

def _parse_form(form):
    system_names = form.getlist("system_name[]")
    system_types = form.getlist("system_type[]")
    system_installed = form.getlist("system_installed[]")
    system_replace = form.getlist("system_replace[]")
    systems = []
    for i in range(len(system_names)):
        if system_names[i].strip():
            systems.append({
                "name": system_names[i].strip(),
                "type": system_types[i].strip() if i < len(system_types) else "",
                "installed": system_installed[i].strip() if i < len(system_installed) else "",
                "replace": system_replace[i].strip() if i < len(system_replace) else "",
            })

    person_names = form.getlist("person_name[]")
    person_titles = form.getlist("person_title[]")
    person_decisions = form.getlist("person_decision[]")
    person_notes = form.getlist("person_note[]")
    key_persons = []
    for i in range(len(person_names)):
        if person_names[i].strip():
            key_persons.append({
                "name": person_names[i].strip(),
                "title": person_titles[i].strip() if i < len(person_titles) else "",
                "decision": person_decisions[i].strip() if i < len(person_decisions) else "不明",
                "note": person_notes[i].strip() if i < len(person_notes) else "",
            })

    return {
        "company_name": form.get("company_name", "").strip(),
        "industry": form.get("industry", "").strip(),
        "employees": form.get("employees", "").strip(),
        "revenue": form.get("revenue", "").strip(),
        "hp_url": form.get("hp_url", "").strip(),
        "sales_person": form.get("sales_person", "").strip(),
        "company_detail": form.get("company_detail", "").strip(),
        "overview": form.get("overview", "").strip(),
        "mid_term_plan": form.get("mid_term_plan", "").strip(),
        "mvv": form.get("mvv", "").strip(),
        "president_profile": form.get("president_profile", "").strip(),
        "ir_info": form.get("ir_info", "").strip(),
        "investment_areas": form.get("investment_areas", "").strip(),
        "pest": form.get("pest", "").strip(),
        "five_forces": form.get("five_forces", "").strip(),
        "swot": form.get("swot", "").strip(),
        "cross_swot": form.get("cross_swot", "").strip(),
        "positioning": form.get("positioning", "").strip(),
        "systems": systems,
        "key_persons": key_persons,
        "competitors": form.get("competitors", "").strip(),
        "end_user_issues": form.get("end_user_issues", "").strip(),
        "latent_needs": form.get("latent_needs", "").strip(),
        "big_play": form.get("big_play", "").strip(),
        "pipeline": form.get("pipeline", "").strip(),
        "activity_history": form.get("activity_history", "").strip(),
        "mid_long_term_plan": form.get("mid_long_term_plan", "").strip(),
        "org_chart": form.get("org_chart", "").strip(),
        "forecast": form.get("forecast", "").strip(),
        "key_cases": form.get("key_cases", "").strip(),
        "action_plan": form.get("action_plan", "").strip(),
        "company_requests": form.get("company_requests", "").strip(),
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(debug=False, host="0.0.0.0", port=port)
