"""
予算分析：今月・来月の着地を予測し、予算とのギャップを人数に換算します。

【考え方】
   着地予測 = ①確定実績 ＋ ②オンブック（既に入っている予約） ＋ ③これから入る見込み

③が肝心です。「予約はまだ入っていないが、例年どおりならこれくらい入る」分を
需要分析（demand.py）の最終着地予測から拾ってきます。
そして、

   不足額 = 予算 − 着地予測
   必要人数 = 不足額 ÷ 平均単価

まで落とすことで、「あと何人送客すればよいか」という行動できる数字になります。
部長がおっしゃる「月初に達成予測100％にしておく」運用は、この数字を毎朝見て、
不足していれば施策を打つ、という形で実現します。
"""

from __future__ import annotations

import calendar
import sqlite3
from datetime import date, datetime, timedelta

from app.db import get_settings


def month_range(year_month: str) -> tuple[date, date]:
    """'2026-10' → (2026-10-01, 2026-10-31) を返します。"""
    year, month = (int(x) for x in year_month.split("-"))
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def shift_month(year_month: str, delta: int) -> str:
    year, month = (int(x) for x in year_month.split("-"))
    total = year * 12 + (month - 1) + delta
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def average_spend(conn: sqlite3.Connection, course_id: str, as_of: date) -> int:
    """そのコースの1人あたり平均単価（直近1年の実績から）。"""
    since = (as_of - timedelta(days=365)).isoformat()
    row = conn.execute(
        "SELECT SUM(revenue) AS rev, SUM(players) AS ppl FROM visits "
        "WHERE course_id = ? AND play_date >= ? AND play_date <= ?",
        (course_id, since, as_of.isoformat()),
    ).fetchone()
    if row and row["ppl"]:
        return int((row["rev"] or 0) / row["ppl"])
    # 実績が無ければ、入っている予約の単価を使います
    row = conn.execute(
        "SELECT SUM(amount) AS amt, SUM(players) AS ppl FROM reservations WHERE course_id = ?",
        (course_id,),
    ).fetchone()
    if row and row["ppl"]:
        return int((row["amt"] or 0) / row["ppl"])
    return 12000  # それも無ければ暫定値


def forecast_month(
    conn: sqlite3.Connection, course_id: str, year_month: str, as_of: date
) -> dict:
    """1コース・1ヶ月分の着地予測を作ります。"""
    start, end = month_range(year_month)
    spend = average_spend(conn, course_id, as_of)

    target_row = conn.execute(
        "SELECT target_revenue, target_players FROM budgets WHERE course_id = ? AND year_month = ?",
        (course_id, year_month),
    ).fetchone()
    target_revenue = int(target_row["target_revenue"]) if target_row else 0
    target_players = int(target_row["target_players"] or 0) if target_row else 0

    # ① 確定実績（今日より前にプレーが終わった分）
    actual = conn.execute(
        "SELECT COALESCE(SUM(revenue),0) AS rev, COALESCE(SUM(players),0) AS ppl FROM visits "
        "WHERE course_id = ? AND play_date BETWEEN ? AND ?",
        (course_id, start.isoformat(), min(end, as_of - timedelta(days=1)).isoformat()),
    ).fetchone()
    actual_revenue, actual_players = int(actual["rev"]), int(actual["ppl"])

    # ② オンブック（今日以降のプレー日に、すでに入っている予約）
    onbook_start = max(start, as_of)
    onbook = conn.execute(
        "SELECT COALESCE(SUM(amount),0) AS amt, COALESCE(SUM(players),0) AS ppl FROM reservations "
        "WHERE course_id = ? AND play_date BETWEEN ? AND ? "
        "AND COALESCE(status,'confirmed') <> 'cancelled'",
        (course_id, onbook_start.isoformat(), end.isoformat()),
    ).fetchone()
    onbook_revenue, onbook_players = int(onbook["amt"]), int(onbook["ppl"])
    if onbook_revenue == 0 and onbook_players > 0:
        onbook_revenue = onbook_players * spend

    # ③ これから入る見込み（需要予測の「最終着地 − 今のオンブック」）
    pickup_players = 0
    if onbook_start <= end:
        rows = conn.execute(
            "SELECT forecast_players, onbook_players FROM demand_days "
            "WHERE course_id = ? AND play_date BETWEEN ? AND ?",
            (course_id, onbook_start.isoformat(), end.isoformat()),
        ).fetchall()
        pickup_players = sum(
            max(int(r["forecast_players"] or 0) - int(r["onbook_players"] or 0), 0) for r in rows
        )
    pickup_revenue = pickup_players * spend

    forecast_revenue = actual_revenue + onbook_revenue + pickup_revenue
    forecast_players = actual_players + onbook_players + pickup_players
    ratio = (forecast_revenue / target_revenue) if target_revenue else 0.0
    gap_revenue = target_revenue - forecast_revenue
    gap_players = int(round(gap_revenue / spend)) if spend and gap_revenue > 0 else 0

    days_left = (end - as_of).days + 1 if end >= as_of else 0

    return {
        "course_id": course_id,
        "year_month": year_month,
        "as_of": as_of.isoformat(),
        "target_revenue": target_revenue,
        "target_players": target_players,
        "actual_revenue": actual_revenue,
        "actual_players": actual_players,
        "onbook_revenue": onbook_revenue,
        "onbook_players": onbook_players,
        "pickup_revenue": pickup_revenue,
        "pickup_players": pickup_players,
        "forecast_revenue": forecast_revenue,
        "forecast_players": forecast_players,
        "achievement_ratio": round(ratio, 4),
        "achievement_pct": round(ratio * 100, 1),
        "gap_revenue": gap_revenue,
        "gap_players": gap_players,
        "avg_spend": spend,
        "days_left": max(days_left, 0),
        # 予算が未達のとき、残り日数で1日あたり何人必要か
        "needed_per_day": int(round(gap_players / days_left)) if days_left and gap_players > 0 else 0,
    }


def rebuild_forecasts(conn: sqlite3.Connection, as_of: date) -> int:
    """今月と来月の予測を全コース分つくり、保存します。"""
    this_month = as_of.strftime("%Y-%m")
    months = [this_month, shift_month(this_month, 1)]
    courses = [r[0] for r in conn.execute("SELECT course_id FROM courses ORDER BY course_id")]

    saved = 0
    for course_id in courses:
        for ym in months:
            f = forecast_month(conn, course_id, ym, as_of)
            conn.execute(
                "INSERT INTO budget_forecasts (course_id, year_month, as_of, target_revenue,"
                " actual_revenue, onbook_revenue, pickup_revenue, forecast_revenue,"
                " achievement_ratio, gap_revenue, avg_spend, gap_players)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
                " ON CONFLICT(course_id, year_month) DO UPDATE SET"
                "  as_of=excluded.as_of, target_revenue=excluded.target_revenue,"
                "  actual_revenue=excluded.actual_revenue, onbook_revenue=excluded.onbook_revenue,"
                "  pickup_revenue=excluded.pickup_revenue, forecast_revenue=excluded.forecast_revenue,"
                "  achievement_ratio=excluded.achievement_ratio, gap_revenue=excluded.gap_revenue,"
                "  avg_spend=excluded.avg_spend, gap_players=excluded.gap_players",
                (
                    f["course_id"], f["year_month"], f["as_of"], f["target_revenue"],
                    f["actual_revenue"], f["onbook_revenue"], f["pickup_revenue"],
                    f["forecast_revenue"], f["achievement_ratio"], f["gap_revenue"],
                    f["avg_spend"], f["gap_players"],
                ),
            )
            saved += 1
    return saved


def get_forecast(conn: sqlite3.Connection, course_id: str, year_month: str, as_of: date) -> dict:
    """保存済みがあればそれを、無ければその場で計算して返します。"""
    row = conn.execute(
        "SELECT * FROM budget_forecasts WHERE course_id = ? AND year_month = ?",
        (course_id, year_month),
    ).fetchone()
    if not row:
        return forecast_month(conn, course_id, year_month, as_of)
    data = dict(row)
    start, end = month_range(year_month)
    days_left = max((end - as_of).days + 1, 0)
    data["achievement_pct"] = round((data.get("achievement_ratio") or 0) * 100, 1)
    data["days_left"] = days_left
    data["needed_per_day"] = (
        int(round((data.get("gap_players") or 0) / days_left))
        if days_left and (data.get("gap_players") or 0) > 0 else 0
    )
    return data


def all_forecasts(conn: sqlite3.Connection, year_month: str, as_of: date) -> list[dict]:
    """全コース分をまとめて返します（ダッシュボード用）。"""
    courses = conn.execute("SELECT course_id, name, short_name FROM courses ORDER BY course_id").fetchall()
    out = []
    for c in courses:
        f = get_forecast(conn, c["course_id"], year_month, as_of)
        f["course_name"] = c["name"]
        f["short_name"] = c["short_name"] or c["name"]
        out.append(f)
    return out
