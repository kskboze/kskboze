"""
CSV出力：指示の対象者リストを、配信ツールに取り込める形で書き出します。

メール配信サービスやLINE公式アカウント、SMS配信サービスは、
だいたい「1行1名・先頭行が見出し」のCSVを受け付けます。
Excelで開いたときに文字化けしないよう、BOM付きUTF-8で書き出しています。
"""

from __future__ import annotations

import csv
import io
import sqlite3
from datetime import datetime

from app.analytics.customers import RANK_LABELS, STATUS_LABELS
from app.config import EXPORT_DIR

TARGET_HEADERS = [
    "顧客ID", "氏名", "メールアドレス", "電話番号", "LINEID", "都道府県",
    "ランク", "状態", "通算来場回数", "最終来場日", "来場周期(日)",
    "次回来場予測日", "平均単価", "送付手段", "件名", "本文",
]


def targets_csv(conn: sqlite3.Connection, instruction_id: str) -> tuple[str, str]:
    """指示1件分の対象者CSVを作り、(ファイル名, 中身) を返します。"""
    inst = conn.execute(
        "SELECT i.*, c.name AS course_name FROM instructions i "
        "LEFT JOIN courses c ON c.course_id = i.course_id WHERE i.instruction_id = ?",
        (instruction_id,),
    ).fetchone()
    if not inst:
        raise ValueError("指示が見つかりません")

    rows = conn.execute(
        "SELECT c.customer_id, c.name, c.email, c.phone, c.line_id, c.prefecture, "
        "       p.rank_code, p.status_code, p.total_visits, p.last_visit, p.cycle_days, "
        "       p.next_expected_date, p.avg_spend "
        "FROM instruction_targets t JOIN customers c USING(customer_id) "
        "LEFT JOIN customer_profiles p USING(customer_id) "
        "WHERE t.instruction_id = ? ORDER BY t.score DESC",
        (instruction_id,),
    ).fetchall()

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(TARGET_HEADERS)
    channel_label = {
        "line": "LINE", "mail": "メール", "sms": "SMS",
        "dm": "DM（ハガキ）", "tel": "お電話", "ops": "運営指示",
    }.get(inst["channel"], inst["channel"])

    for r in rows:
        writer.writerow([
            r["customer_id"], r["name"] or "", r["email"] or "", r["phone"] or "",
            r["line_id"] or "", r["prefecture"] or "",
            RANK_LABELS.get(r["rank_code"], r["rank_code"] or ""),
            STATUS_LABELS.get(r["status_code"], r["status_code"] or ""),
            r["total_visits"] or 0, r["last_visit"] or "", r["cycle_days"] or "",
            r["next_expected_date"] or "", r["avg_spend"] or 0,
            channel_label, inst["message_subject"] or "", inst["message_body"] or "",
        ])

    course = (inst["course_name"] or "全体").replace("/", "_")
    filename = f"{inst['run_date']}_{course}_{inst['rule_id']}_{inst['channel']}.csv"
    return filename, buffer.getvalue()


def instructions_csv(conn: sqlite3.Connection, run_date: str) -> tuple[str, str]:
    """その日の指示一覧をCSVにします（朝礼資料などにお使いください）。"""
    rows = conn.execute(
        "SELECT i.*, c.name AS course_name FROM instructions i "
        "LEFT JOIN courses c ON c.course_id = i.course_id "
        "WHERE i.run_date = ? ORDER BY i.priority, i.expected_revenue DESC",
        (run_date,),
    ).fetchall()

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow([
        "優先度", "コース", "分類", "指示内容", "理由", "具体的な行動",
        "送付手段", "対象人数", "対象日", "見込み人数", "見込み売上", "期限", "状態",
    ])
    for r in rows:
        writer.writerow([
            r["priority"], r["course_name"] or "", r["category"], r["title"],
            (r["reason"] or "").replace("\n", " "), (r["action"] or "").replace("\n", " "),
            r["channel"], r["target_count"], r["target_dates"],
            r["expected_players"], r["expected_revenue"], r["deadline"], r["status"],
        ])
    return f"{run_date}_営業指示一覧.csv", buffer.getvalue()


def to_bytes(text: str) -> bytes:
    """ExcelでもGoogleスプレッドシートでも文字化けしない形にします。"""
    return text.encode("utf-8-sig")


def save_to_disk(filename: str, text: str) -> str:
    """出力フォルダにも控えを残します。"""
    safe = filename.replace("/", "_")
    path = EXPORT_DIR / safe
    path.write_bytes(to_bytes(text))
    return str(path)


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M")
