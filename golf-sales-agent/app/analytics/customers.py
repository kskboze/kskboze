"""
顧客分析：来場履歴から「この方はどんなお客様か」を数値にします。

ここで出すもの:
  1. 来場周期 (cycle_days)  … 何日おきに来場されるか（来場間隔の中央値）
  2. リードタイム (lead_days) … 予約は来場の何日前に入るか
  3. アプローチ推奨日 (approach_date) … 次回来場予測日 − リードタイム
     → 「予約周期が1ヶ月の方なら、予約を取る2週間前にご案内」を自動化する部分です
  4. ランク (F1〜F5) … 通算来場回数による分類
  5. ステータス … 順調 / 離反予備軍 / 休眠 / 離脱

【なぜ「平均」ではなく「中央値」を使うのか】
たまたま1回だけ3年空いた、という方がいると平均は大きく狂います。
中央値（真ん中の値）は、そうした例外に引っ張られにくく、実態に近い値が出ます。
"""

from __future__ import annotations

import sqlite3
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from app.config import as_float, as_int
from app.db import get_settings

# ランクの表示名（画面やメール文面で使います）
RANK_LABELS = {
    "F0": "予約のみ（未来場）",
    "F1": "初回のみ（1回）",
    "F2": "2回目まで",
    "F3": "育成層（3〜5回）",
    "F4": "常連（6〜11回）",
    "F5": "ロイヤル（12回以上）",
}
STATUS_LABELS = {
    "ACTIVE": "順調",
    "AT_RISK": "離反予備軍",
    "DORMANT": "休眠",
    "LOST": "離脱",
    "UNKNOWN": "判定不能",
}


def to_date(text: str | None) -> date | None:
    if not text:
        return None
    try:
        return datetime.strptime(str(text)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def median_int(values: list[int]) -> int | None:
    """中央値を整数で返します。値が無ければ None。"""
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return int(round(statistics.median(clean)))


def decide_rank(total_visits: int, s: dict) -> str:
    """通算来場回数からランクを決めます。"""
    if total_visits <= 0:
        return "F0"
    if total_visits >= as_int(s.get("rank_f5_min"), 12):
        return "F5"
    if total_visits >= as_int(s.get("rank_f4_min"), 6):
        return "F4"
    if total_visits >= as_int(s.get("rank_f3_min"), 3):
        return "F3"
    if total_visits >= as_int(s.get("rank_f2_min"), 2):
        return "F2"
    return "F1"


def decide_status(
    recency_days: int | None, cycle_days: int | None, s: dict, total_visits: int = 2
) -> str:
    """
    「その方にとっての普通の間隔」を基準に、来なくなっていないかを判定します。
    周期30日の方の90日ぶりと、周期180日の方の90日ぶりは意味が違うためです。

    ただし1回しかお越しでない方は「その方の周期」が存在しません。
    この場合だけは、初回からの経過日数で判定します
    （初回から90日以内なら、まだ2回目を狙える“熱い”状態、という考え方です）。
    """
    if recency_days is None:
        return "UNKNOWN"
    if recency_days > as_int(s.get("status_dormant_days"), 540):
        return "LOST"
    if total_visits <= 1:
        if recency_days <= as_int(s.get("first_timer_active_days"), 90):
            return "ACTIVE"
        if recency_days <= as_int(s.get("first_timer_risk_days"), 210):
            return "AT_RISK"
        return "DORMANT"
    if cycle_days is None:
        return "UNKNOWN"
    ratio = recency_days / max(cycle_days, 1)
    if ratio <= as_float(s.get("status_active_ratio"), 1.2):
        return "ACTIVE"
    if ratio <= as_float(s.get("status_at_risk_ratio"), 2.0):
        return "AT_RISK"
    return "DORMANT"


def rebuild_profiles(conn: sqlite3.Connection, as_of: date) -> int:
    """
    全顧客の分析をやり直して customer_profiles テーブルに保存します。
    データを取り込んだ後や、毎朝の指示生成前に呼びます。
    """
    s = get_settings(conn)
    default_cycle = as_int(s.get("default_cycle_days"), 90)
    default_lead = as_int(s.get("default_lead_days"), 14)

    rows = conn.execute(
        "SELECT customer_id, course_id, play_date, booked_at, players, revenue "
        "FROM visits ORDER BY customer_id, play_date"
    ).fetchall()

    history: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for r in rows:
        history[r["customer_id"]].append(r)

    # --- ランクごとの周期の代表値を先に出します ---
    # 1回しか来ていない方は自分の周期を計算できないので、
    # 「同じランクの方々の周期の中央値」を仮の値として使います。
    cycles_by_rank: dict[str, list[int]] = defaultdict(list)
    measured: dict[str, int] = {}
    for customer_id, visits in history.items():
        dates = sorted({to_date(v["play_date"]) for v in visits if to_date(v["play_date"])})
        if len(dates) >= 2:
            gaps = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
            gaps = [g for g in gaps if g > 0]
            cycle = median_int(gaps)
            if cycle:
                measured[customer_id] = cycle
                cycles_by_rank[decide_rank(len(dates), s)].append(cycle)

    rank_cycle = {rank: median_int(v) or default_cycle for rank, v in cycles_by_rank.items()}
    all_cycles = [c for v in cycles_by_rank.values() for c in v]
    overall_cycle = median_int(all_cycles) or default_cycle

    # --- リードタイム（予約日〜プレー日）の全体中央値 ---
    all_leads: list[int] = []
    for visits in history.values():
        for v in visits:
            pd_, bd = to_date(v["play_date"]), to_date(v["booked_at"])
            if pd_ and bd and 0 <= (pd_ - bd).days <= 365:
                all_leads.append((pd_ - bd).days)
    overall_lead = median_int(all_leads) or default_lead

    # --- 1人ずつプロファイルを作ります ---
    customer_ids = [r[0] for r in conn.execute("SELECT customer_id FROM customers")]
    # 接触履歴は1回のクエリでまとめて取得します（顧客数が多くても速いように）
    last_contact_map = {
        r[0]: r[1] for r in conn.execute(
            "SELECT customer_id, MAX(sent_date) FROM contact_log GROUP BY customer_id"
        )
    }
    profiles: list[tuple] = []
    twelve_months_ago = as_of - timedelta(days=365)

    for customer_id in customer_ids:
        visits = history.get(customer_id, [])
        dates = sorted([d for d in (to_date(v["play_date"]) for v in visits) if d])
        total_visits = len(dates)
        first_visit = dates[0] if dates else None
        last_visit = dates[-1] if dates else None
        recency = (as_of - last_visit).days if last_visit else None
        visits_12m = sum(1 for d in dates if d >= twelve_months_ago)

        total_revenue = sum(int(v["revenue"] or 0) for v in visits)
        total_players = sum(int(v["players"] or 1) for v in visits)
        avg_spend = int(total_revenue / total_players) if total_players else 0

        rank = decide_rank(total_visits, s)

        # 来場周期：実測できればそれを、できなければ同ランクの代表値を使う
        cycle = measured.get(customer_id)
        estimated = 0
        if cycle is None:
            cycle = rank_cycle.get(rank, overall_cycle)
            estimated = 1

        # リードタイム：その方の実測、無ければ全体の中央値
        leads = []
        for v in visits:
            pd_, bd = to_date(v["play_date"]), to_date(v["booked_at"])
            if pd_ and bd and 0 <= (pd_ - bd).days <= 365:
                leads.append((pd_ - bd).days)
        lead = median_int(leads) or overall_lead

        # ★ここが要：次回来場の予測日と、ご案内を送るべき日
        next_expected = last_visit + timedelta(days=cycle) if last_visit else None
        approach = next_expected - timedelta(days=lead) if next_expected else None

        status = decide_status(recency, cycle, s, total_visits)

        course_counts = Counter(v["course_id"] for v in visits if v["course_id"])
        main_course = course_counts.most_common(1)[0][0] if course_counts else None
        dow_counts = Counter(d.weekday() for d in dates)
        main_dow = dow_counts.most_common(1)[0][0] if dow_counts else None
        weekday_ratio = (
            sum(1 for d in dates if d.weekday() < 5) / total_visits if total_visits else 0.0
        )

        last_contacted = last_contact_map.get(customer_id)

        profiles.append((
            customer_id, as_of.isoformat(), total_visits, visits_12m,
            first_visit.isoformat() if first_visit else None,
            last_visit.isoformat() if last_visit else None,
            recency, total_revenue, avg_spend, cycle, estimated, lead,
            next_expected.isoformat() if next_expected else None,
            approach.isoformat() if approach else None,
            rank, status, main_course, main_dow, round(weekday_ratio, 3), last_contacted,
        ))

    conn.execute("DELETE FROM customer_profiles")
    conn.executemany(
        "INSERT INTO customer_profiles ("
        "customer_id, as_of, total_visits, visits_12m, first_visit, last_visit, recency_days,"
        "total_revenue, avg_spend, cycle_days, cycle_is_estimated, lead_days,"
        "next_expected_date, approach_date, rank_code, status_code, main_course_id,"
        "main_dow, weekday_ratio, last_contacted_at"
        ") VALUES (" + ",".join("?" * 20) + ")",
        profiles,
    )
    return len(profiles)


def segment_summary(conn: sqlite3.Connection) -> list[dict]:
    """ランク×ステータスの人数を集計します（画面の「顧客」ページ用）。"""
    rows = conn.execute(
        "SELECT rank_code, status_code, COUNT(*) AS cnt, "
        "       AVG(avg_spend) AS spend, AVG(cycle_days) AS cycle "
        "FROM customer_profiles GROUP BY rank_code, status_code"
    ).fetchall()
    out = []
    for r in rows:
        out.append({
            "rank_code": r["rank_code"],
            "rank_label": RANK_LABELS.get(r["rank_code"], r["rank_code"]),
            "status_code": r["status_code"],
            "status_label": STATUS_LABELS.get(r["status_code"], r["status_code"]),
            "count": r["cnt"],
            "avg_spend": int(r["spend"] or 0),
            "avg_cycle": int(r["cycle"] or 0),
        })
    out.sort(key=lambda x: (x["rank_code"], x["status_code"]))
    return out


def rank_totals(conn: sqlite3.Connection) -> list[dict]:
    """ランク別の合計（リピーター動向を一目で見るため）。"""
    rows = conn.execute(
        "SELECT rank_code, COUNT(*) AS cnt, "
        "SUM(CASE WHEN status_code='ACTIVE' THEN 1 ELSE 0 END) AS active_cnt, "
        "SUM(CASE WHEN status_code='AT_RISK' THEN 1 ELSE 0 END) AS risk_cnt, "
        "SUM(CASE WHEN status_code IN ('DORMANT','LOST') THEN 1 ELSE 0 END) AS sleep_cnt, "
        "AVG(avg_spend) AS spend "
        "FROM customer_profiles GROUP BY rank_code ORDER BY rank_code"
    ).fetchall()
    return [{
        "rank_code": r["rank_code"],
        "rank_label": RANK_LABELS.get(r["rank_code"], r["rank_code"]),
        "count": r["cnt"],
        "active": r["active_cnt"],
        "at_risk": r["risk_cnt"],
        "sleeping": r["sleep_cnt"],
        "avg_spend": int(r["spend"] or 0),
    } for r in rows]
