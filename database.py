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
            company_name TEXT NOT NULL,
            industry TEXT,
            employees TEXT,
            revenue TEXT,
            hp_url TEXT,
            sales_person TEXT,
            overview TEXT,
            mid_term_plan TEXT,
            systems TEXT DEFAULT '[]',
            key_persons TEXT DEFAULT '[]',
            competitors TEXT,
            end_user_issues TEXT,
            latent_needs TEXT,
            big_play TEXT,
            pipeline TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
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
            overview, mid_term_plan, systems, key_persons,
            competitors, end_user_issues, latent_needs, big_play, pipeline,
            created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        data.get("company_name", ""),
        data.get("industry", ""),
        data.get("employees", ""),
        data.get("revenue", ""),
        data.get("hp_url", ""),
        data.get("sales_person", ""),
        data.get("overview", ""),
        data.get("mid_term_plan", ""),
        json.dumps(data.get("systems", []), ensure_ascii=False),
        json.dumps(data.get("key_persons", []), ensure_ascii=False),
        data.get("competitors", ""),
        data.get("end_user_issues", ""),
        data.get("latent_needs", ""),
        data.get("big_play", ""),
        data.get("pipeline", ""),
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
            overview=?, mid_term_plan=?, systems=?, key_persons=?,
            competitors=?, end_user_issues=?, latent_needs=?, big_play=?, pipeline=?,
            updated_at=?
        WHERE id=?
    """, (
        data.get("company_name", ""),
        data.get("industry", ""),
        data.get("employees", ""),
        data.get("revenue", ""),
        data.get("hp_url", ""),
        data.get("sales_person", ""),
        data.get("overview", ""),
        data.get("mid_term_plan", ""),
        json.dumps(data.get("systems", []), ensure_ascii=False),
        json.dumps(data.get("key_persons", []), ensure_ascii=False),
        data.get("competitors", ""),
        data.get("end_user_issues", ""),
        data.get("latent_needs", ""),
        data.get("big_play", ""),
        data.get("pipeline", ""),
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
