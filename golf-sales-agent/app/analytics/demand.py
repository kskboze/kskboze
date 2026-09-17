"""
需要分析：先々の各日が「弱日」か「強日」かを判定します。

【考え方】
単に「予約が少ない日＝弱日」とすると、判断を誤ります。
2ヶ月先の日はどこも予約が少ないのが当たり前だからです。
そこで「同じ曜日・同じ時期の過去の日が、同じ“◯日前”の時点でどれくらい埋まっていたか」
と比べます。これを業界では「ペース比較（ブッキングペース）」と呼びます。

  ペース比 = 今の充足率 ÷ 過去の同時点の充足率
  1.0 なら例年並み / 1.2 なら好調 / 0.7 なら苦戦

さらに、過去の「ここから最終的にどれだけ積み上がったか」（ピックアップ）を掛けて、
最終着地人数を予測します。
"""

from __future__ import annotations

import sqlite3
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta

from app.analytics.calendar_jp import day_label, holiday_name, is_weekend
from app.config import as_float, as_int
from app.db import get_settings

GRADE_LABELS = {
    "S": "強日",
    "A": "やや強",
    "B": "標準",
    "C": "弱日",
    "D": "最弱日",
}
GRADE_ORDER = {"D": 0, "C": 1, "B": 2, "A": 3, "S": 4}

# 過去データが足りないときに使う「標準的な予約の入り方」。
# 例: 30日前の時点では、最終予約数の約40%が入っているのが普通、という意味です。
DEFAULT_BOOKING_CURVE = [
    (90, 0.08), (60, 0.15), (45, 0.24), (30, 0.40),
    (21, 0.53), (14, 0.66), (7, 0.82), (3, 0.92), (1, 0.97), (0, 1.00),
]


def curve_fraction(days_out: int) -> float:
    """◯日前の時点で、最終予約数の何割が入っているのが標準かを返します。"""
    days_out = max(0, days_out)
    points = DEFAULT_BOOKING_CURVE
    if days_out >= points[0][0]:
        return points[0][1]
    for i in range(len(points) - 1):
        hi_d, hi_v = points[i]
        lo_d, lo_v = points[i + 1]
        if lo_d <= days_out <= hi_d:
            if hi_d == lo_d:
                return hi_v
            ratio = (days_out - lo_d) / (hi_d - lo_d)
            return lo_v + (hi_v - lo_v) * ratio
    return 1.0


def to_date(text) -> date | None:
    if not text:
        return None
    try:
        return datetime.strptime(str(text)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _capacity(course: sqlite3.Row, target: date) -> int:
    return int(
        course["capacity_weekend"] if is_weekend(target) else course["capacity_weekday"]
    ) or 1


MAX_LEAD = 120   # 予約リードタイムをさかのぼって見る上限（日）


class CoursePastDays:
    """
    1コース分の過去実績を、需要比較にすぐ使える形へ整理したものです。

    ポイントは「◯日前の時点で何人入っていたか」を先に数え上げておくことです。
    毎回 全実績を数え直すと8コース×60日分で非常に遅くなるため、
    ここで1度だけ集計しておきます。
    """

    def __init__(self, visits: list[sqlite3.Row]) -> None:
        # 日付 -> 最終来場人数
        self.final: dict[date, int] = defaultdict(int)
        # 日付 -> 「◯日前時点の累計人数」の配列（添字が days_out）
        histogram: dict[date, list[int]] = {}

        for v in visits:
            play = to_date(v["play_date"])
            if not play:
                continue
            players = int(v["players"] or 1)
            self.final[play] += players
            booked = to_date(v["booked_at"])
            lead = (play - booked).days if booked else 0
            lead = max(0, min(lead, MAX_LEAD))
            bucket = histogram.setdefault(play, [0] * (MAX_LEAD + 1))
            bucket[lead] += players

        # 後ろから足し込むと「◯日前までに入っていた人数」になります
        self.at_point: dict[date, list[int]] = {}
        for play, bucket in histogram.items():
            cumulative = [0] * (MAX_LEAD + 1)
            running = 0
            for lead in range(MAX_LEAD, -1, -1):
                running += bucket[lead]
                cumulative[lead] = running
            self.at_point[play] = cumulative

        self.dates = sorted(self.final.keys())

    def comparable(self, target: date) -> list[date]:
        """比較対象にする過去の日（同じ曜日の性格・近い時期）を選びます。"""
        same_weekend = is_weekend(target)
        target_yday = target.timetuple().tm_yday
        out = []
        for d in self.dates:
            if d >= target or is_weekend(d) != same_weekend:
                continue
            diff = abs(d.timetuple().tm_yday - target_yday)
            if min(diff, 365 - diff) > 45:
                continue
            # 平日は曜日ごとの差が大きいので、曜日も揃えます
            if not same_weekend and d.weekday() != target.weekday():
                continue
            out.append(d)
        return out

    def pace(
        self, target: date, days_out: int, capacity: int
    ) -> tuple[float | None, float | None, int]:
        """
        (過去の同時点での充足率の中央値, 最終着地までの伸び率の中央値, 参考日数)
        を返します。参考にできる日が3日未満のときは None を返します。
        """
        index = max(0, min(days_out, MAX_LEAD))
        fills: list[float] = []
        pickups: list[float] = []
        for d in self.comparable(target):
            final_players = self.final.get(d, 0)
            if final_players <= 0:
                continue
            at_point = self.at_point[d][index]
            fills.append(at_point / capacity)
            pickups.append(final_players / max(at_point, 1))
        if len(fills) < 3:
            return None, None, len(fills)
        return statistics.median(fills), statistics.median(pickups), len(fills)

    def typical_final_fill(self, target: date, capacity: int) -> float:
        """過去の同種の日が、最終的にどれくらい埋まっていたか。"""
        same_weekend = is_weekend(target)
        values = [
            players for d, players in self.final.items()
            if d < target and is_weekend(d) == same_weekend
        ]
        if not values:
            return 0.55 if same_weekend else 0.35
        return min(statistics.mean(values) / capacity, 1.0)


MIN_BENCHMARK_FILL = 0.03   # これ未満だと「過去の同時点」が参考にならないと判断します
MAX_PACE_RATIO = 3.0        # 比率が極端に振れないよう上限を置きます


def _grade(pace_ratio: float, fill_rate: float, s: dict) -> str:
    """ペース比と充足率から、その日の強弱を5段階で判定します。"""
    if fill_rate >= as_float(s.get("grade_s_fill"), 0.85):
        return "S"
    if pace_ratio >= as_float(s.get("grade_s_pace"), 1.10):
        return "S"
    if pace_ratio >= as_float(s.get("grade_a_pace"), 1.00):
        return "A"
    if pace_ratio >= as_float(s.get("grade_c_pace"), 0.90):
        return "B"
    if pace_ratio >= as_float(s.get("grade_d_pace"), 0.75):
        return "C"
    return "D"


def rebuild_demand(conn: sqlite3.Connection, as_of: date) -> int:
    """
    今日から先の各日について、弱日・強日を判定して demand_days に保存します。
    """
    s = get_settings(conn)
    horizon = as_int(s.get("demand_horizon_days"), 60)

    courses = conn.execute("SELECT * FROM courses ORDER BY course_id").fetchall()
    # 比較用の過去データ（直近2年分あれば十分です）
    since = (as_of - timedelta(days=730)).isoformat()
    all_visits = conn.execute(
        "SELECT course_id, play_date, booked_at, players FROM visits WHERE play_date >= ?",
        (since,),
    ).fetchall()
    visits_by_course: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for v in all_visits:
        visits_by_course[v["course_id"]].append(v)

    onbook = conn.execute(
        "SELECT course_id, play_date, SUM(players) AS players, SUM(amount) AS amount "
        "FROM reservations WHERE play_date >= ? AND COALESCE(status,'confirmed') <> 'cancelled' "
        "GROUP BY course_id, play_date",
        (as_of.isoformat(),),
    ).fetchall()
    onbook_map = {(r["course_id"], r["play_date"]): r for r in onbook}

    records: list[tuple] = []
    for course in courses:
        past = CoursePastDays(visits_by_course.get(course["course_id"], []))
        for offset in range(0, horizon + 1):
            target = as_of + timedelta(days=offset)
            capacity = _capacity(course, target)
            row = onbook_map.get((course["course_id"], target.isoformat()))
            players = int(row["players"] or 0) if row else 0
            fill_rate = players / capacity

            bench, pickup, _ = past.pace(target, offset, capacity)
            typical_final = past.typical_final_fill(target, capacity)
            if bench is None:
                # 過去データが足りない場合は「標準的な予約の入り方」で代用します
                fraction = curve_fraction(offset)
                bench = typical_final * fraction
                pickup = 1 / max(fraction, 0.05)

            forecast_players = int(round(players * (pickup or 1.0)))
            # 満口を超える予測は出しません
            forecast_players = min(forecast_players, capacity)
            forecast_fill = forecast_players / capacity

            if bench >= MIN_BENCHMARK_FILL:
                # 通常はこちら：今の充足率を、過去の同時点と比べます
                pace_ratio = fill_rate / bench
            else:
                # まだ予約が動き出さない時期（例：2ヶ月先）は、同時点比較が
                # わずかな差で何倍にも振れてしまいます。
                # そこで「最終着地の予測」と「例年の最終着地」を比べます。
                pace_ratio = (
                    forecast_fill / typical_final if typical_final > 0.01 else 1.0
                )
            pace_ratio = min(pace_ratio, MAX_PACE_RATIO)
            gap_players = max(capacity - forecast_players, 0)
            grade = _grade(pace_ratio, fill_rate, s)

            records.append((
                course["course_id"], target.isoformat(), as_of.isoformat(),
                target.weekday(), 1 if is_weekend(target) else 0, offset,
                capacity, players, round(fill_rate, 4), round(bench, 4),
                round(pace_ratio, 4), forecast_players, round(forecast_fill, 4),
                gap_players, grade,
            ))

    conn.execute("DELETE FROM demand_days")
    conn.executemany(
        "INSERT INTO demand_days (course_id, play_date, as_of, dow, is_weekend, days_out,"
        " capacity, onbook_players, fill_rate, benchmark_fill, pace_ratio,"
        " forecast_players, forecast_fill, gap_players, grade)"
        " VALUES (" + ",".join("?" * 15) + ")",
        records,
    )
    return len(records)


def weak_days(
    conn: sqlite3.Connection, course_id: str, grades: tuple[str, ...] = ("C", "D"),
    within_days: int | None = None, limit: int = 30,
) -> list[dict]:
    """弱日の一覧を取り出します（送客施策の対象日になります）。"""
    sql = "SELECT * FROM demand_days WHERE course_id = ? AND grade IN ({})".format(
        ",".join("?" * len(grades))
    )
    params: list = [course_id, *grades]
    if within_days is not None:
        sql += " AND days_out <= ?"
        params.append(within_days)
    sql += " ORDER BY gap_players DESC, play_date ASC LIMIT ?"
    params.append(limit)
    return [decorate(dict(r)) for r in conn.execute(sql, params).fetchall()]


def strong_days(conn: sqlite3.Connection, course_id: str, limit: int = 30) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM demand_days WHERE course_id = ? AND grade IN ('S','A') "
        "ORDER BY play_date ASC LIMIT ?",
        (course_id, limit),
    ).fetchall()
    return [decorate(dict(r)) for r in rows]


def calendar_days(conn: sqlite3.Connection, course_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM demand_days WHERE course_id = ? ORDER BY play_date", (course_id,)
    ).fetchall()
    return [decorate(dict(r)) for r in rows]


def decorate(row: dict) -> dict:
    """画面表示に使いやすいよう、ラベルを足します。"""
    d = to_date(row["play_date"])
    row["label"] = day_label(d) if d else row["play_date"]
    row["holiday"] = holiday_name(d) if d else None
    row["grade_label"] = GRADE_LABELS.get(row["grade"], row["grade"])
    row["fill_pct"] = round((row.get("fill_rate") or 0) * 100)
    row["forecast_pct"] = round((row.get("forecast_fill") or 0) * 100)
    row["pace_pct"] = round((row.get("pace_ratio") or 0) * 100)
    return row
