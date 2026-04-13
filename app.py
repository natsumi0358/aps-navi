import os
import json
import anthropic
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from pathlib import Path
from database import init_db, get_all_companies, get_company, create_company, update_company, delete_company

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "nknarts-akamane-secret")

# システムプロンプトを読み込む（①と同じ）
SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "aps-advisor-ai" / "knowledge" / "system_prompt.md"
try:
    with open(SYSTEM_PROMPT_PATH, encoding="utf-8") as f:
        BASE_SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    BASE_SYSTEM_PROMPT = "あなたはAPS観点で営業アドバイスをするAIアドバイザーです。"

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

MAX_HISTORY = 20


def build_system_prompt(company):
    """会社情報をシステムプロンプトに組み込む"""
    systems = company.get("systems", [])
    key_persons = company.get("key_persons", [])

    systems_text = ""
    if systems:
        for s in systems:
            systems_text += f"  - {s.get('name', '')}（{s.get('type', '')}）導入：{s.get('installed', '')} / リプレース見込み：{s.get('replace', '')}\n"
    else:
        systems_text = "  （未入力）"

    key_persons_text = ""
    if key_persons:
        for p in key_persons:
            key_persons_text += f"  - {p.get('name', '')}（{p.get('title', '')}）意思決定権：{p.get('decision', '')} / {p.get('note', '')}\n"
    else:
        key_persons_text = "  （未入力）"

    company_info = f"""
【調査対象会社】{company.get('company_name', '')}
【業種】{company.get('industry', '')}
【従業員数】{company.get('employees', '')}
【売上規模】{company.get('revenue', '')}
【担当営業】{company.get('sales_person', '')}

【会社概要】
{company.get('overview', '（未入力）')}

【中期経営計画・会社の方針】
{company.get('mid_term_plan', '（未入力）')}

【キーパーソン一覧】
{key_persons_text}

【現在使っているシステム一覧】
{systems_text}

【競合状況】
{company.get('competitors', '（未入力）')}

【顧客の顧客（エンドユーザー）の課題】
{company.get('end_user_issues', '（未入力）')}

【潜在ニーズ・本音（ヒアリングメモ）】
{company.get('latent_needs', '（未入力）')}

【ビッグプレー候補】
{company.get('big_play', '（未入力）')}

【現在の案件・パイプライン状況】
{company.get('pipeline', '（未入力）')}

上記の情報をもとに、APS観点でアドバイスをしてください。
"""
    return BASE_SYSTEM_PROMPT + "\n\n---\n" + company_info


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
    # チャット履歴をリセット
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

    system_prompt = build_system_prompt(company)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system_prompt,
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
    """初回アドバイス（ワンショット分析）"""
    company = get_company(company_id)
    if not company:
        return jsonify({"error": "会社情報が見つかりません"}), 404

    system_prompt = build_system_prompt(company)
    first_message = f"{company.get('company_name', '')}についてAPS観点で総合的にアドバイスしてください。特に「ビッグプレー候補」「潜在ニーズの深掘り」「パイプラインの充実度」の観点でお願いします。"

    session_key = f"history_{company_id}"
    history = [{"role": "user", "content": first_message}]

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system_prompt,
            messages=history,
        )
        assistant_message = response.content[0].text
        history.append({"role": "assistant", "content": assistant_message})
        session[session_key] = history
        return jsonify({"reply": assistant_message})
    except Exception as e:
        return jsonify({"error": f"エラーが発生しました: {str(e)}"}), 500


@app.route("/company/<int:company_id>/delete", methods=["POST"])
def company_delete(company_id):
    delete_company(company_id)
    return redirect(url_for("index"))


def _parse_form(form):
    """フォームデータをパースしてdict形式に変換"""
    # システム一覧（複数行）
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

    # キーパーソン（複数行）
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
        "overview": form.get("overview", "").strip(),
        "mid_term_plan": form.get("mid_term_plan", "").strip(),
        "systems": systems,
        "key_persons": key_persons,
        "competitors": form.get("competitors", "").strip(),
        "end_user_issues": form.get("end_user_issues", "").strip(),
        "latent_needs": form.get("latent_needs", "").strip(),
        "big_play": form.get("big_play", "").strip(),
        "pipeline": form.get("pipeline", "").strip(),
    }


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5002))
    app.run(debug=False, host="0.0.0.0", port=port)
