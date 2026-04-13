import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "companies.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            -- 基本情報
            company_name TEXT NOT NULL,
            industry TEXT,
            employees TEXT,
            revenue TEXT,
            hp_url TEXT,
            sales_person TEXT,
            -- Work6: お客様概要（AI自動取得）
            founded TEXT,
            established TEXT,
            headquarters TEXT,
            capital TEXT,
            operating_profit TEXT,
            branches TEXT,
            group_companies TEXT,
            company_detail TEXT,
            overview TEXT,
            president_profile TEXT,
            mvv TEXT,
            -- Work7: 経営方針（AI自動取得）
            mid_term_plan TEXT,
            ir_info TEXT,
            investment_areas TEXT,
            -- 業界分析（AI自動生成）
            pest TEXT,
            five_forces TEXT,
            swot TEXT,
            cross_swot TEXT,
            positioning TEXT,
            -- 営業調査項目（手入力）
            systems TEXT DEFAULT '[]',
            key_persons TEXT DEFAULT '[]',
            competitors TEXT,
            end_user_issues TEXT,
            latent_needs TEXT,
            big_play TEXT,
            pipeline TEXT,
            -- Work8: これまでの活動（手入力）
            activity_history TEXT,
            -- Work9: 中長期売上プラン（手入力）
            mid_long_term_plan TEXT,
            -- Work10: 組織図（手入力）
            org_chart TEXT,
            -- Work11: 今年のForecast（手入力）
            forecast TEXT,
            -- Work12: 主要案件（手入力）
            key_cases TEXT,
            -- Work13: カバレッジマップ（手入力）
            coverage_map TEXT,
            -- アクションプラン・リクエスト（手入力）
            action_plan TEXT,
            company_requests TEXT,
            -- メタ
            created_at TEXT,
            updated_at TEXT
        )
    """)
    # 既存テーブルへのカラム追加（マイグレーション）
    existing = [row[1] for row in conn.execute("PRAGMA table_info(companies)").fetchall()]
    new_columns = [
        ("founded", "TEXT"),
        ("established", "TEXT"),
        ("headquarters", "TEXT"),
        ("capital", "TEXT"),
        ("operating_profit", "TEXT"),
        ("branches", "TEXT"),
        ("group_companies", "TEXT"),
        ("company_detail", "TEXT"),
        ("overview", "TEXT"),
        ("president_profile", "TEXT"),
        ("mvv", "TEXT"),
        ("mid_term_plan", "TEXT"),
        ("ir_info", "TEXT"),
        ("investment_areas", "TEXT"),
        ("pest", "TEXT"),
        ("five_forces", "TEXT"),
        ("swot", "TEXT"),
        ("cross_swot", "TEXT"),
        ("positioning", "TEXT"),
        ("activity_history", "TEXT"),
        ("mid_long_term_plan", "TEXT"),
        ("org_chart", "TEXT"),
        ("forecast", "TEXT"),
        ("key_cases", "TEXT"),
        ("coverage_map", "TEXT"),
        ("action_plan", "TEXT"),
        ("company_requests", "TEXT"),
    ]
    for col, col_type in new_columns:
        if col not in existing:
            conn.execute(f"ALTER TABLE companies ADD COLUMN {col} {col_type}")
    conn.commit()
    conn.close()


def get_all_companies():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM companies ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_company(company_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM companies WHERE id = ?", (company_id,)
    ).fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["systems"] = json.loads(d["systems"] or "[]")
        d["key_persons"] = json.loads(d["key_persons"] or "[]")
        return d
    return None


def create_company(data):
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute("""
        INSERT INTO companies (
            company_name, industry, employees, revenue, hp_url, sales_person,
            founded, established, headquarters, capital, operating_profit,
            branches, group_companies, company_detail, overview, president_profile, mvv,
            mid_term_plan, ir_info, investment_areas,
            pest, five_forces, swot, cross_swot, positioning,
            systems, key_persons,
            competitors, end_user_issues, latent_needs, big_play, pipeline,
            activity_history, mid_long_term_plan, org_chart, forecast,
            key_cases, coverage_map, action_plan, company_requests,
            created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        data.get("company_name", ""),
        data.get("industry", ""),
        data.get("employees", ""),
        data.get("revenue", ""),
        data.get("hp_url", ""),
        data.get("sales_person", ""),
        data.get("founded", ""),
        data.get("established", ""),
        data.get("headquarters", ""),
        data.get("capital", ""),
        data.get("operating_profit", ""),
        data.get("branches", ""),
        data.get("group_companies", ""),
        data.get("company_detail", ""),
        data.get("overview", ""),
        data.get("president_profile", ""),
        data.get("mvv", ""),
        data.get("mid_term_plan", ""),
        data.get("ir_info", ""),
        data.get("investment_areas", ""),
        data.get("pest", ""),
        data.get("five_forces", ""),
        data.get("swot", ""),
        data.get("cross_swot", ""),
        data.get("positioning", ""),
        json.dumps(data.get("systems", []), ensure_ascii=False),
        json.dumps(data.get("key_persons", []), ensure_ascii=False),
        data.get("competitors", ""),
        data.get("end_user_issues", ""),
        data.get("latent_needs", ""),
        data.get("big_play", ""),
        data.get("pipeline", ""),
        data.get("activity_history", ""),
        data.get("mid_long_term_plan", ""),
        data.get("org_chart", ""),
        data.get("forecast", ""),
        data.get("key_cases", ""),
        data.get("coverage_map", ""),
        data.get("action_plan", ""),
        data.get("company_requests", ""),
        now, now
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_company(company_id, data):
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        UPDATE companies SET
            company_name=?, industry=?, employees=?, revenue=?, hp_url=?, sales_person=?,
            founded=?, established=?, headquarters=?, capital=?, operating_profit=?,
            branches=?, group_companies=?, company_detail=?, overview=?, president_profile=?, mvv=?,
            mid_term_plan=?, ir_info=?, investment_areas=?,
            pest=?, five_forces=?, swot=?, cross_swot=?, positioning=?,
            systems=?, key_persons=?,
            competitors=?, end_user_issues=?, latent_needs=?, big_play=?, pipeline=?,
            activity_history=?, mid_long_term_plan=?, org_chart=?, forecast=?,
            key_cases=?, coverage_map=?, action_plan=?, company_requests=?,
            updated_at=?
        WHERE id=?
    """, (
        data.get("company_name", ""),
        data.get("industry", ""),
        data.get("employees", ""),
        data.get("revenue", ""),
        data.get("hp_url", ""),
        data.get("sales_person", ""),
        data.get("founded", ""),
        data.get("established", ""),
        data.get("headquarters", ""),
        data.get("capital", ""),
        data.get("operating_profit", ""),
        data.get("branches", ""),
        data.get("group_companies", ""),
        data.get("company_detail", ""),
        data.get("overview", ""),
        data.get("president_profile", ""),
        data.get("mvv", ""),
        data.get("mid_term_plan", ""),
        data.get("ir_info", ""),
        data.get("investment_areas", ""),
        data.get("pest", ""),
        data.get("five_forces", ""),
        data.get("swot", ""),
        data.get("cross_swot", ""),
        data.get("positioning", ""),
        json.dumps(data.get("systems", []), ensure_ascii=False),
        json.dumps(data.get("key_persons", []), ensure_ascii=False),
        data.get("competitors", ""),
        data.get("end_user_issues", ""),
        data.get("latent_needs", ""),
        data.get("big_play", ""),
        data.get("pipeline", ""),
        data.get("activity_history", ""),
        data.get("mid_long_term_plan", ""),
        data.get("org_chart", ""),
        data.get("forecast", ""),
        data.get("key_cases", ""),
        data.get("coverage_map", ""),
        data.get("action_plan", ""),
        data.get("company_requests", ""),
        now,
        company_id
    ))
    conn.commit()
    conn.close()


def delete_company(company_id):
    conn = get_db()
    conn.execute("DELETE FROM companies WHERE id = ?", (company_id,))
    conn.commit()
    conn.close()
