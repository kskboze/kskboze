"""
司令塔：毎朝の処理をこの順番で実行します。

  1. 顧客分析をやり直す   （来場周期・ランク・ステータス）
  2. 需要分析をやり直す   （弱日・強日の判定）
  3. 予算の着地予測を作る （今月・来月）
  4. すべてのルールを動かして、指示の候補を集める
  5. 重複を整理する       （同じお客様に同じ日に何通も送らない）
  6. 案内文を作る         （テンプレート、設定があればAIで推敲）
  7. データベースに保存する

「本日の指示を作成」ボタンを押すと、この関数が動きます。
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import date, datetime, timedelta

from app.analytics.budget import rebuild_forecasts
from app.analytics.customers import rebuild_profiles
from app.analytics.demand import rebuild_demand
from app.config import as_int
from app.db import get_settings, session
from app.engine import ai as ai_mod
from app.engine import messages as msg_mod
from app.engine.rules import RULES, Instruction, build_context, estimate, spread


def refresh_analytics(conn: sqlite3.Connection, as_of: date) -> dict:
    """分析だけをやり直します（データ取り込み直後にも呼びます）。"""
    profiles = rebuild_profiles(conn, as_of)
    days = rebuild_demand(conn, as_of)
    forecasts = rebuild_forecasts(conn, as_of)
    return {"profiles": profiles, "demand_days": days, "forecasts": forecasts}


def generate(as_of: date | None = None, use_ai: bool = True) -> dict:
    """本日の営業指示をひととおり作ります。"""
    as_of = as_of or date.today()
    with session() as conn:
        stats = refresh_analytics(conn, as_of)
        ctx = build_context(conn, as_of)
        settings = get_settings(conn)

        # --- 4. ルールを実行して候補を集める ---
        candidates: list[Instruction] = []
        for rule in RULES:
            try:
                candidates.extend(rule(ctx))
            except Exception as exc:   # 1つのルールの失敗で全体を止めない
                print(f"[警告] ルール {rule.__name__} でエラー: {exc}")

        # --- 5. 重複の整理 ---
        cooldown = as_int(settings.get("contact_cooldown_days"), 14)
        max_targets = as_int(settings.get("max_targets_per_instruction"), 500)
        recent_cutoff = (as_of - timedelta(days=cooldown)).isoformat()
        recently_contacted = {
            r[0] for r in conn.execute(
                "SELECT DISTINCT customer_id FROM contact_log WHERE sent_date >= ?",
                (recent_cutoff,),
            )
        }

        # 対象者の取り合いになったときの優先順位です。
        #   ①優先度が高いもの ②個別対応の施策 ③売上インパクトが大きいもの
        # ②を入れているのは、一斉配信の施策が先に大量の顧客を確保してしまい、
        # 本来はお電話すべき常連様まで一斉メールに回ってしまうのを防ぐためです。
        candidates.sort(key=lambda i: (i.priority, i.precision, -i.expected_revenue))
        assigned: set[str] = set()
        final: list[Instruction] = []
        for inst in candidates:
            if inst.channel == "ops":
                final.append(inst)
                continue
            kept = [
                (cid, score) for cid, score in inst.targets
                if cid not in assigned and cid not in recently_contacted
            ]
            if not kept:
                continue
            kept.sort(key=lambda t: t[1], reverse=True)
            kept = kept[:max_targets]
            inst.targets = kept
            assigned.update(cid for cid, _ in kept)
            # 重複を除いて対象者が減ったので、見込みを実際の人数で計算し直します
            inst.expected_players, inst.expected_revenue = estimate(
                inst.rule_id, len(kept), spread(ctx, inst.course_id or ""),
                inst.cap_players,
            )
            final.append(inst)

        # --- 6〜7. 文面を作って保存 ---
        conn.execute("DELETE FROM instruction_targets WHERE instruction_id IN "
                     "(SELECT instruction_id FROM instructions WHERE run_date = ?)",
                     (as_of.isoformat(),))
        conn.execute("DELETE FROM instructions WHERE run_date = ?", (as_of.isoformat(),))

        ai_used = 0
        for inst in final:
            instruction_id = uuid.uuid4().hex[:12]
            subject, body = "", ""
            used_ai = False
            if inst.channel != "ops":
                subject, body = msg_mod.render(inst.message_key, inst.channel, inst.message_vars)
                if use_ai and ai_mod.is_available():
                    subject, body, used_ai = ai_mod.refine_message(
                        instruction_title=inst.title,
                        reason=inst.reason,
                        action=inst.action,
                        channel=inst.channel,
                        course_name=ctx.course_name(inst.course_id),
                        target_summary=f"{len(inst.targets)}名（{inst.category}）",
                        base_subject=subject,
                        base_body=body,
                    )
                    ai_used += int(used_ai)

            conn.execute(
                "INSERT INTO instructions (instruction_id, run_date, course_id, rule_id, priority,"
                " category, title, reason, action, channel, target_count, target_dates,"
                " expected_players, expected_revenue, response_rate, message_subject,"
                " message_body, ai_generated, deadline, status, created_at)"
                " VALUES (" + ",".join("?" * 21) + ")",
                (
                    instruction_id, as_of.isoformat(), inst.course_id, inst.rule_id,
                    inst.priority, inst.category, inst.title, inst.reason, inst.action,
                    inst.channel, len(inst.targets), inst.target_dates,
                    inst.expected_players, inst.expected_revenue, inst.response_rate,
                    subject, body,
                    int(used_ai), inst.deadline, "open",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            if inst.targets:
                conn.executemany(
                    "INSERT OR IGNORE INTO instruction_targets(instruction_id, customer_id, score)"
                    " VALUES (?,?,?)",
                    [(instruction_id, cid, score) for cid, score in inst.targets],
                )

        return {
            **stats,
            "instructions": len(final),
            "targets": len(assigned),
            "ai_used": ai_used,
            "as_of": as_of.isoformat(),
        }


def list_instructions(conn: sqlite3.Connection, run_date: str, course_id: str | None = None) -> list[dict]:
    """保存済みの指示を読み出します。"""
    sql = "SELECT i.*, c.name AS course_name FROM instructions i " \
          "LEFT JOIN courses c ON c.course_id = i.course_id WHERE i.run_date = ?"
    params: list = [run_date]
    if course_id:
        sql += " AND i.course_id = ?"
        params.append(course_id)
    sql += " ORDER BY i.priority ASC, i.expected_revenue DESC"
    rows = conn.execute(sql, params).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["channel_label"] = {
            "line": "LINE", "mail": "メール", "sms": "SMS",
            "dm": "DM（ハガキ）", "tel": "お電話", "ops": "運営指示",
        }.get(d["channel"], d["channel"])
        d["sms_warning"] = (
            msg_mod.sms_length_warning(d["message_body"] or "") if d["channel"] == "sms" else None
        )
        out.append(d)
    return out


def instruction_detail(conn: sqlite3.Connection, instruction_id: str) -> dict | None:
    row = conn.execute(
        "SELECT i.*, c.name AS course_name FROM instructions i "
        "LEFT JOIN courses c ON c.course_id = i.course_id WHERE i.instruction_id = ?",
        (instruction_id,),
    ).fetchone()
    if not row:
        return None
    data = dict(row)
    data["targets"] = [dict(r) for r in conn.execute(
        "SELECT t.customer_id, t.score, c.name, c.email, c.phone, c.line_id, "
        "       c.prefecture, p.rank_code, p.status_code, p.total_visits, p.last_visit, "
        "       p.cycle_days, p.avg_spend, p.next_expected_date "
        "FROM instruction_targets t "
        "JOIN customers c USING(customer_id) "
        "LEFT JOIN customer_profiles p USING(customer_id) "
        "WHERE t.instruction_id = ? ORDER BY t.score DESC",
        (instruction_id,),
    )]
    data["channel_label"] = {
        "line": "LINE", "mail": "メール", "sms": "SMS",
        "dm": "DM（ハガキ）", "tel": "お電話", "ops": "運営指示",
    }.get(data["channel"], data["channel"])
    data["sms_warning"] = (
        msg_mod.sms_length_warning(data["message_body"] or "") if data["channel"] == "sms" else None
    )
    return data


def mark_status(conn: sqlite3.Connection, instruction_id: str, status: str) -> None:
    """
    指示に「完了」「見送り」の印をつけます。
    完了にしたときだけ接触履歴に記録し、同じ方への送りすぎを防ぎます。
    """
    conn.execute(
        "UPDATE instructions SET status = ? WHERE instruction_id = ?", (status, instruction_id)
    )
    if status != "done":
        return
    row = conn.execute(
        "SELECT run_date, course_id, rule_id, channel FROM instructions WHERE instruction_id = ?",
        (instruction_id,),
    ).fetchone()
    if not row:
        return
    targets = conn.execute(
        "SELECT customer_id FROM instruction_targets WHERE instruction_id = ?", (instruction_id,)
    ).fetchall()
    conn.executemany(
        "INSERT INTO contact_log(customer_id, course_id, rule_id, channel, sent_date, instruction_id)"
        " VALUES (?,?,?,?,?,?)",
        [(t[0], row["course_id"], row["rule_id"], row["channel"], row["run_date"], instruction_id)
         for t in targets],
    )


def daily_summary(conn: sqlite3.Connection, run_date: str) -> dict:
    """本日の指示の全体像（画面上部のまとめ）。"""
    row = conn.execute(
        "SELECT COUNT(*) AS cnt, COALESCE(SUM(target_count),0) AS targets, "
        "COALESCE(SUM(expected_revenue),0) AS revenue, "
        "SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) AS done, "
        "SUM(CASE WHEN priority=1 THEN 1 ELSE 0 END) AS urgent "
        "FROM instructions WHERE run_date = ?",
        (run_date,),
    ).fetchone()
    return {
        "count": row["cnt"] or 0,
        "targets": row["targets"] or 0,
        "expected_revenue": row["revenue"] or 0,
        "done": row["done"] or 0,
        "urgent": row["urgent"] or 0,
    }
