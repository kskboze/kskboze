"""
営業施策ルール集：分析結果から「誰に・いつ・何を・どの手段で」を決めます。

1つのルールが1種類の営業指示を作ります。ルールを足したい／やめたいときは
このファイルの RULES 一覧をいじるだけで済むようにしてあります。

【優先度】
  1 = 今日必ずやる（売上インパクト大・時間的猶予なし）
  2 = 今週中にやる
  3 = 計画的にやる
  4 = 余力があればやる
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.analytics import demand as demand_mod
from app.analytics.budget import get_forecast, month_range, shift_month
from app.analytics.calendar_jp import day_label
from app.analytics.customers import RANK_LABELS
from app.config import as_int
from app.db import get_settings

CHANNEL_LABELS = {
    "line": "LINE",
    "mail": "メール",
    "sms": "SMS",
    "dm": "DM（ハガキ）",
    "tel": "お電話",
    "ops": "運営指示（送信なし）",
}


# 1組あたりの平均人数。お一人が予約すると、だいたいこの人数でお越しになります。
AVG_PARTY_SIZE = 3.2

# 施策ごとの想定反応率（案内を送ったうち、実際にご予約くださる割合）。
# 業界の一般的な水準を初期値にしています。
# 運用しながら実績が溜まったら、この数字を実測値に置き換えてください。
RESPONSE_RATES = {
    "R01": 0.15,   # 周期アプローチ：ちょうど検討中の時期なので高い
    "R02": 0.30,   # 常連へのお電話：直接お話しするため最も高い
    "R10": 0.04,   # 初回→2回目：関係が薄いので低め
    "R11": 0.05,   # 2回目→3回目
    "R12": 0.08,   # 育成層への回数券案内
    "R20": 0.02,   # 休眠復活：最も反応が取りにくい
    "R30": 0.04,   # 弱日への送客
    "R31": 0.03,   # 緊急送客：日程が限られるため低め
    "R50": 0.06,   # 翌月の先行予約
    "R60": 0.10,   # ロイヤル顧客
}


def estimate(rule_id: str, target_count: int, avg_spend: int,
             cap_players: int | None = None) -> tuple[int, int]:
    """
    対象人数から、見込み来場人数と見込み売上を試算します。

      見込み人数 = 対象人数 × 想定反応率 × 1組あたりの平均人数

    「全員が来てくださる」前提の数字は現場の信頼を失いますので、
    必ず反応率を掛けた控えめな数字を出すようにしています。
    """
    rate = RESPONSE_RATES.get(rule_id, 0.05)
    players = int(round(target_count * rate * AVG_PARTY_SIZE))
    if cap_players is not None:
        players = min(players, cap_players)   # 空き枠以上には埋まりません
    return players, players * avg_spend


@dataclass
class Instruction:
    """1件の営業指示。画面のカード1枚に対応します。"""
    rule_id: str
    priority: int
    category: str
    title: str
    reason: str
    action: str
    channel: str
    course_id: str | None = None
    targets: list[tuple[str, float]] = field(default_factory=list)
    target_dates: str = ""
    expected_players: int = 0
    expected_revenue: int = 0
    message_key: str = ""
    message_vars: dict = field(default_factory=dict)
    deadline: str = ""
    # 1 = 個別対応（お一人ずつ狙う施策） / 2 = 一斉配信（まとめて送る施策）
    # 同じお客様が複数の施策に該当したときは、1 の施策を優先します。
    # 一斉配信が優良顧客を先取りしてしまうのを防ぐためです。
    precision: int = 2
    # 想定反応率（画面に「この数字は反応率◯%で試算」と表示するために保持します）
    response_rate: float = 0.05
    # 空き枠の上限（弱日対策など、これ以上は埋まらないという制約）
    cap_players: int | None = None


@dataclass
class Context:
    """ルールが参照する材料一式。毎朝1回だけ作って使い回します。"""
    conn: sqlite3.Connection
    as_of: date
    settings: dict
    courses: list[sqlite3.Row]
    course_names: dict[str, str]

    def course_name(self, course_id: str | None) -> str:
        return self.course_names.get(course_id or "", "全コース")


def build_context(conn: sqlite3.Connection, as_of: date) -> Context:
    courses = conn.execute("SELECT * FROM courses ORDER BY course_id").fetchall()
    return Context(
        conn=conn,
        as_of=as_of,
        settings=get_settings(conn),
        courses=courses,
        course_names={c["course_id"]: c["name"] for c in courses},
    )


# ---------------------------------------------------------------
# 共通の小道具
# ---------------------------------------------------------------
def fetch_profiles(ctx: Context, where: str, params: tuple = ()) -> list[sqlite3.Row]:
    """条件に合う顧客プロファイルを取り出します（連絡先も一緒に）。"""
    sql = (
        "SELECT p.*, c.name, c.email, c.phone, c.line_id, "
        "       c.allow_mail, c.allow_dm, c.allow_line, c.allow_sms, c.prefecture "
        "FROM customer_profiles p JOIN customers c USING(customer_id) "
        f"WHERE {where}"
    )
    return ctx.conn.execute(sql, params).fetchall()


def pick_channel(row: sqlite3.Row, preference: list[str]) -> str | None:
    """
    そのお客様に実際に届く手段を、優先順に1つだけ選びます。
    許諾が無い手段は絶対に選びません（特定電子メール法などの遵守のため）。
    """
    for channel in preference:
        if channel == "line" and row["allow_line"] and row["line_id"]:
            return "line"
        if channel == "mail" and row["allow_mail"] and row["email"]:
            return "mail"
        if channel == "sms" and row["allow_sms"] and row["phone"]:
            return "sms"
        if channel == "dm" and row["allow_dm"]:
            return "dm"
        if channel == "tel" and row["phone"]:
            return "tel"
    return None


def group_by_channel(
    rows: list[sqlite3.Row], preference: list[str], score_fn=None
) -> dict[str, list[tuple[str, float]]]:
    """お客様を「届く手段」ごとに振り分けます。"""
    groups: dict[str, list[tuple[str, float]]] = {}
    for row in rows:
        channel = pick_channel(row, preference)
        if not channel:
            continue   # どの手段でも連絡できない方は対象外
        score = score_fn(row) if score_fn else 0.0
        groups.setdefault(channel, []).append((row["customer_id"], score))
    return groups


def spread(ctx: Context, course_id: str) -> int:
    row = ctx.conn.execute(
        "SELECT avg_spend FROM budget_forecasts WHERE course_id = ? ORDER BY year_month LIMIT 1",
        (course_id,),
    ).fetchone()
    return int(row["avg_spend"]) if row and row["avg_spend"] else 12000


def cap_targets(rows: list, needed_players: int, score_key, minimum: int = 80) -> list:
    """
    送る人数を、必要な人数に見合う範囲に絞ります。

    100名分の空きを埋めるために8,000名へ一斉送信すると、
    お客様の受信疲れを招き、長い目で見て開封率が下がります。
    経験的に「必要人数の5〜6倍」に案内すれば十分埋まるため、その範囲に抑えます。
    """
    limit = max(minimum, needed_players * 6)
    if len(rows) <= limit:
        return rows
    return sorted(rows, key=score_key, reverse=True)[:limit]


def dates_text(days: list[dict], limit: int = 6) -> str:
    """対象日を「10/2(金)、10/9(金)…」の形にまとめます。"""
    labels = [d["label"] for d in days[:limit]]
    if len(days) > limit:
        labels.append(f"ほか{len(days) - limit}日")
    return "、".join(labels)


# ===============================================================
# ルール本体
# ===============================================================
def rule_cycle_approach(ctx: Context) -> list[Instruction]:
    """
    R01 予約周期アプローチ（このシステムの目玉）
    「次回来場予測日 − 予約リードタイム」が今日にあたる方へご案内します。
    例：来場周期30日・リードタイム14日の方 → 前回来場から16日目にご案内。
    """
    window = as_int(ctx.settings.get("approach_window_days"), 3)
    lo = (ctx.as_of - timedelta(days=window)).isoformat()
    hi = (ctx.as_of + timedelta(days=window)).isoformat()
    # 来場周期が「実測できた方」だけを対象にします。
    # 1回しかお越しでない方の周期は推定値にすぎず、その日にご案内する根拠が弱いためです。
    # （1回のみの方は R10「初回→2回目」が担当します）
    rows = fetch_profiles(
        ctx,
        "p.approach_date BETWEEN ? AND ? AND p.status_code IN ('ACTIVE','AT_RISK') "
        "AND p.total_visits >= 2 AND p.cycle_is_estimated = 0",
        (lo, hi),
    )
    out: list[Instruction] = []
    by_course: dict[str, list[sqlite3.Row]] = {}
    for r in rows:
        by_course.setdefault(r["main_course_id"] or ctx.courses[0]["course_id"], []).append(r)

    for course_id, members in by_course.items():
        groups = group_by_channel(
            members, ["line", "mail", "sms", "dm"], score_fn=lambda r: r["avg_spend"] or 0
        )
        for channel, targets in groups.items():
            sample = next(m for m in members if m["customer_id"] == targets[0][0])
            out.append(Instruction(
                rule_id="R01",
                priority=1,
                precision=1,
                category="周期アプローチ",
                title=f"{ctx.course_name(course_id)}｜来場サイクルが来た{len(targets)}名へ予約のご案内",
                reason=(
                    f"この{len(targets)}名は、来場周期から見て"
                    f"「そろそろ次の予約を入れる時期」に入りました。"
                    f"（平均周期 約{sample['cycle_days']}日／予約は平均{sample['lead_days']}日前）"
                    "この直前のタイミングでお声がけすると、他コースに流れる前に押さえられます。"
                ),
                action="次回プレー日の候補を2〜3日提示し、予約ページへ直接誘導してください。",
                channel=channel,
                course_id=course_id,
                targets=targets,
                response_rate=RESPONSE_RATES["R01"],
                message_key="cycle_approach",
                message_vars={"course_name": ctx.course_name(course_id)},
                deadline=(ctx.as_of + timedelta(days=2)).isoformat(),
            ))
    return out


def rule_vip_at_risk(ctx: Context) -> list[Instruction]:
    """R02 常連の離反予備軍。ここを止めるのが売上防衛では最優先です。"""
    rows = fetch_profiles(
        ctx,
        "p.rank_code IN ('F4','F5') AND p.status_code = 'AT_RISK'",
    )
    out: list[Instruction] = []
    by_course: dict[str, list[sqlite3.Row]] = {}
    for r in rows:
        by_course.setdefault(r["main_course_id"] or ctx.courses[0]["course_id"], []).append(r)

    for course_id, members in by_course.items():
        groups = group_by_channel(
            members, ["tel", "line", "mail", "dm"], score_fn=lambda r: r["total_revenue"] or 0
        )
        for channel, targets in groups.items():
            out.append(Instruction(
                rule_id="R02",
                priority=1,
                precision=1,
                category="離反防止",
                title=f"{ctx.course_name(course_id)}｜常連{len(targets)}名が来場間隔を空けています",
                reason=(
                    "通算6回以上ご来場の常連様が、ご自身のいつもの来場周期の2倍近く"
                    "お見えになっていません。常連1名の離反は年間で数十万円規模の損失に相当します。"
                    "値引きよりも『気にかけている』という姿勢が効く層です。"
                ),
                action=(
                    "割引の提示は不要です。支配人名でのご挨拶と、"
                    "希望日を伺って枠を確保する形でお声がけしてください。"
                ),
                channel=channel,
                course_id=course_id,
                targets=targets,
                response_rate=RESPONSE_RATES["R02"],
                message_key="vip_at_risk",
                message_vars={"course_name": ctx.course_name(course_id)},
                deadline=(ctx.as_of + timedelta(days=3)).isoformat(),
            ))
    return out


def _repeat_rule(
    ctx: Context, rule_id: str, visits_count: int, max_recency: int,
    title_suffix: str, reason: str, action: str, message_key: str, priority: int,
) -> list[Instruction]:
    """「◯回しか来ていない方」向けルールの共通処理。"""
    rows = fetch_profiles(
        ctx,
        "p.total_visits = ? AND p.recency_days IS NOT NULL AND p.recency_days <= ? "
        "AND p.status_code <> 'LOST'",
        (visits_count, max_recency),
    )
    out: list[Instruction] = []
    by_course: dict[str, list[sqlite3.Row]] = {}
    for r in rows:
        by_course.setdefault(r["main_course_id"] or ctx.courses[0]["course_id"], []).append(r)

    for course_id, members in by_course.items():
        groups = group_by_channel(
            members, ["line", "mail", "sms", "dm"],
            score_fn=lambda r: -(r["recency_days"] or 999),
        )
        for channel, targets in groups.items():
            out.append(Instruction(
                rule_id=rule_id,
                priority=priority,
                precision=1,
                category="リピート育成",
                title=f"{ctx.course_name(course_id)}｜{title_suffix}（{len(targets)}名）",
                reason=reason,
                action=action,
                channel=channel,
                course_id=course_id,
                targets=targets,
                response_rate=RESPONSE_RATES.get(rule_id, 0.05),
                message_key=message_key,
                message_vars={"course_name": ctx.course_name(course_id)},
                deadline=(ctx.as_of + timedelta(days=5)).isoformat(),
            ))
    return out


def rule_first_to_second(ctx: Context) -> list[Instruction]:
    """R10 1回だけの方を2回目へ。リピーター対策の入口です。"""
    return _repeat_rule(
        ctx, "R10", 1, 150, "初回ご来場のみの方を2回目へ",
        reason=(
            "ご来場が1回だけの方です。ゴルフ場では『2回目に来ていただけるか』が"
            "最大の分岐点で、2回目を越えた方の定着率は大きく跳ね上がります。"
            "初回から日が浅いうちほど効果が高いため、優先的に着手してください。"
        ),
        action=(
            "『またお会いしたい』というメッセージを主役にし、"
            "2回目限定の平日ご優待（昼食付など、値引きではなく付加価値）を1つ添えてください。"
        ),
        message_key="first_to_second", priority=2,
    )


def rule_second_to_third(ctx: Context) -> list[Instruction]:
    """R11 2回来場の方を3回目へ。いわゆる「3回の壁」の突破です。"""
    return _repeat_rule(
        ctx, "R11", 2, 180, "2回ご来場の方に3回目のきっかけを",
        reason=(
            "2回ご来場いただいた方です。3回目を越えると『行きつけのコース』として"
            "定着しやすくなります。ここに手を打つかどうかで年間のリピート率が変わります。"
        ),
        action=(
            "コースの特徴（グリーン・名物ホール・食事）を1つ具体的に伝え、"
            "前回と違う季節の楽しみ方を提案してください。同伴者紹介特典も有効です。"
        ),
        message_key="second_to_third", priority=2,
    )


def rule_third_wall(ctx: Context) -> list[Instruction]:
    """R12 3〜5回の育成層を常連化。回数券・会員制度のご案内が効きます。"""
    rows = fetch_profiles(
        ctx, "p.rank_code = 'F3' AND p.status_code = 'ACTIVE'",
    )
    out: list[Instruction] = []
    by_course: dict[str, list[sqlite3.Row]] = {}
    for r in rows:
        by_course.setdefault(r["main_course_id"] or ctx.courses[0]["course_id"], []).append(r)
    for course_id, members in by_course.items():
        groups = group_by_channel(members, ["mail", "line", "dm"],
                                  score_fn=lambda r: r["visits_12m"] or 0)
        for channel, targets in groups.items():
            out.append(Instruction(
                rule_id="R12", priority=3, precision=1, category="リピート育成",
                title=f"{ctx.course_name(course_id)}｜育成層{len(targets)}名を常連へ（回数券・優待会員）",
                reason=(
                    "3〜5回ご来場で、現在も順調にお越しの方です。"
                    "この層に回数券や年間優待をご案内すると、来場頻度と単価が同時に上がります。"
                    "1回ごとの割引より、まとめてのご購入の方が結果的に単価は維持されます。"
                ),
                action="回数券・年間優待のご案内。先に枠を押さえていただく形が有効です。",
                channel=channel, course_id=course_id, targets=targets,
                response_rate=RESPONSE_RATES["R12"],
                message_key="third_wall",
                message_vars={"course_name": ctx.course_name(course_id)},
                deadline=(ctx.as_of + timedelta(days=7)).isoformat(),
            ))
    return out


def rule_winback(ctx: Context) -> list[Instruction]:
    """R20 休眠のお客様を呼び戻します。"""
    rows = fetch_profiles(ctx, "p.status_code = 'DORMANT' AND p.total_visits >= 2")
    out: list[Instruction] = []
    by_course: dict[str, list[sqlite3.Row]] = {}
    for r in rows:
        by_course.setdefault(r["main_course_id"] or ctx.courses[0]["course_id"], []).append(r)
    for course_id, members in by_course.items():
        groups = group_by_channel(members, ["dm", "mail", "line"],
                                  score_fn=lambda r: r["total_revenue"] or 0)
        for channel, targets in groups.items():
            out.append(Instruction(
                rule_id="R20", priority=3, precision=1, category="休眠復活",
                title=f"{ctx.course_name(course_id)}｜休眠中の{len(targets)}名へ復活のご案内",
                reason=(
                    "以前は複数回お越しいただいていたのに、ご自身の来場周期を大きく超えて"
                    "お見えになっていない方です。他コースへ移られている可能性があります。"
                    "コース改修・レストラン刷新など『変化』を伝えると戻ってきていただけます。"
                ),
                action=(
                    "『お久しぶりです』から入り、この間に変わった点を具体的に1つ伝えてください。"
                    "復活限定のご優待は弱日に限定して設定すると、単価を落とさずに済みます。"
                ),
                channel=channel, course_id=course_id, targets=targets,
                response_rate=RESPONSE_RATES["R20"],
                message_key="winback",
                message_vars={"course_name": ctx.course_name(course_id)},
                deadline=(ctx.as_of + timedelta(days=10)).isoformat(),
            ))
    return out


def rule_weak_day_fill(ctx: Context) -> list[Instruction]:
    """R30 弱日への送客。曜日の相性が良いお客様に絞って狙い撃ちします。"""
    out: list[Instruction] = []
    urgent = as_int(ctx.settings.get("urgent_days"), 14)
    for course in ctx.courses:
        course_id = course["course_id"]
        days = demand_mod.weak_days(ctx.conn, course_id, ("C", "D"), limit=40)
        days = [d for d in days if d["days_out"] > urgent]
        if not days:
            continue
        gap = sum(d["gap_players"] for d in days)
        dows = {d["dow"] for d in days}
        weekend_target = any(d["is_weekend"] for d in days)

        rows = fetch_profiles(
            ctx,
            "p.main_course_id = ? AND p.status_code IN ('ACTIVE','AT_RISK') "
            "AND (p.main_dow IN ({}) OR p.weekday_ratio >= ?)".format(",".join("?" * len(dows))),
            (course_id, *sorted(dows), 0.7 if not weekend_target else 0.0),
        )
        if not rows:
            continue
        rows = cap_targets(rows, gap, lambda r: r["visits_12m"] or 0)
        groups = group_by_channel(rows, ["line", "mail", "sms", "dm"],
                                  score_fn=lambda r: r["visits_12m"] or 0)
        for channel, targets in groups.items():
            out.append(Instruction(
                rule_id="R30", priority=2, category="弱日対策",
                title=f"{ctx.course_name(course_id)}｜弱日{len(days)}日への送客（対象{len(targets)}名）",
                reason=(
                    f"これらの日は、例年の同じ時期・同じ曜日と比べて予約の入りが遅れています。"
                    f"合計で約{gap}名分の空きが見込まれます。"
                    "対象は、この曜日によくお越しになる方に絞っているため反応が取りやすい層です。"
                ),
                action=(
                    "対象日を明示してご案内してください。"
                    "値引きに頼らず、キャディ付き・昼食グレードアップなど付加価値型の特典を優先します。"
                ),
                channel=channel, course_id=course_id, targets=targets,
                target_dates=dates_text(days),
                response_rate=RESPONSE_RATES["R30"], cap_players=gap,
                message_key="weak_day",
                message_vars={
                    "course_name": ctx.course_name(course_id),
                    "dates": dates_text(days, 4),
                },
                deadline=(ctx.as_of + timedelta(days=3)).isoformat(),
            ))
    return out


def rule_urgent_weak_day(ctx: Context) -> list[Instruction]:
    """R31 直近2週間の最弱日。時間が無いので即日動きます。"""
    out: list[Instruction] = []
    urgent = as_int(ctx.settings.get("urgent_days"), 14)
    for course in ctx.courses:
        course_id = course["course_id"]
        days = demand_mod.weak_days(ctx.conn, course_id, ("D",), within_days=urgent, limit=20)
        days = [d for d in days if d["days_out"] >= 1 and d["gap_players"] > 0]
        if not days:
            continue
        gap = sum(d["gap_players"] for d in days)
        rows = fetch_profiles(
            ctx,
            "p.main_course_id = ? AND p.status_code IN ('ACTIVE','AT_RISK') AND p.total_visits >= 2",
            (course_id,),
        )
        rows = cap_targets(rows, gap, lambda r: -(r["recency_days"] or 999))
        groups = group_by_channel(rows, ["sms", "line", "mail"],
                                  score_fn=lambda r: -(r["recency_days"] or 999))
        for channel, targets in groups.items():
            out.append(Instruction(
                rule_id="R31", priority=1, category="緊急送客",
                title=f"【緊急】{ctx.course_name(course_id)}｜{urgent}日以内の最弱日 {len(days)}日・約{gap}名分の空き",
                reason=(
                    f"直近{urgent}日以内に、予約の入りが大きく遅れている日が{len(days)}日あります。"
                    "この期間の空き枠は、当日を過ぎると売上ゼロで確定してしまいます。"
                    "直前でも動く層（SMS・LINEが届く既存顧客）に絞って一気に埋めます。"
                ),
                action=(
                    "即時配信してください。ポータルサイトの在庫開放と価格見直しも同時に行い、"
                    "自社サイト経由のご予約には現地での特典を付けて誘導します。"
                ),
                channel=channel, course_id=course_id, targets=targets,
                target_dates=dates_text(days),
                response_rate=RESPONSE_RATES["R31"], cap_players=gap,
                message_key="urgent_weak_day",
                message_vars={
                    "course_name": ctx.course_name(course_id),
                    "dates": dates_text(days, 3),
                },
                deadline=ctx.as_of.isoformat(),
            ))
    return out


def rule_strong_day_upsell(ctx: Context) -> list[Instruction]:
    """R40 強日は単価を上げる。送信作業ではなく運営側の指示です。"""
    out: list[Instruction] = []
    for course in ctx.courses:
        course_id = course["course_id"]
        days = [
            d for d in demand_mod.strong_days(ctx.conn, course_id, limit=40)
            if d["days_out"] <= 45 and d["fill_rate"] >= 0.6
        ]
        if not days:
            continue
        out.append(Instruction(
            rule_id="R40", priority=2, category="単価アップ",
            title=f"{ctx.course_name(course_id)}｜好調日{len(days)}日は値引き停止・単価を上げる",
            reason=(
                "これらの日は例年より予約の入りが早く、放っておいても埋まる見込みです。"
                "ここで安いプランを残すことは、本来いただけるはずの単価を捨てているのと同じです。"
                "弱日に使う原資は、強日の単価から生み出します。"
            ),
            action=(
                "①ポータルサイトの割引プランを停止または締切、"
                "②キャディ付き・プレミアム昼食などの上位プランを前面に、"
                "③残枠は自社サイト限定で通常単価にて販売してください。"
            ),
            channel="ops", course_id=course_id, targets=[],
            target_dates=dates_text(days, 8),
            expected_players=0,
            expected_revenue=int(sum(d["onbook_players"] for d in days) * spread(ctx, course_id) * 0.05),
            message_key="",
            deadline=(ctx.as_of + timedelta(days=2)).isoformat(),
        ))
    return out


def rule_next_month_budget(ctx: Context) -> list[Instruction]:
    """
    R50 翌月予算の先行対策（部長のご要望の中心）。
    「月初の時点で達成予測100％」にするため、前月のうちに不足分を埋めにいきます。
    """
    this_month = ctx.as_of.strftime("%Y-%m")
    next_month = shift_month(this_month, 1)
    _, month_end = month_range(this_month)
    days_to_month_end = (month_end - ctx.as_of).days
    lead = as_int(ctx.settings.get("next_month_lead_days"), 10)

    out: list[Instruction] = []
    for course in ctx.courses:
        course_id = course["course_id"]
        f = get_forecast(ctx.conn, course_id, next_month, ctx.as_of)
        if not f["target_revenue"] or f["achievement_ratio"] >= 1.0:
            continue
        gap_players = f["gap_players"]
        if gap_players <= 0:
            continue

        start, end = month_range(next_month)
        days = [
            d for d in demand_mod.calendar_days(ctx.conn, course_id)
            if start.isoformat() <= d["play_date"] <= end.isoformat()
            and d["grade"] in ("B", "C", "D")
        ]
        days.sort(key=lambda d: d["gap_players"], reverse=True)

        rows = fetch_profiles(
            ctx,
            "p.main_course_id = ? AND p.status_code IN ('ACTIVE','AT_RISK') "
            "AND p.rank_code IN ('F3','F4','F5')",
            (course_id,),
        )
        rows = cap_targets(rows, gap_players, lambda r: r["avg_spend"] or 0)
        groups = group_by_channel(rows, ["line", "mail", "dm", "sms"],
                                  score_fn=lambda r: r["avg_spend"] or 0)
        urgency = "【今月中に着手】" if days_to_month_end <= lead else ""
        for channel, targets in groups.items():
            out.append(Instruction(
                rule_id="R50", priority=1, category="予算対策（翌月）",
                title=(
                    f"{urgency}{ctx.course_name(course_id)}｜{next_month}の予算に"
                    f"{gap_players}名不足（予測{f['achievement_pct']}%）"
                ),
                reason=(
                    f"{next_month}の着地予測は予算の{f['achievement_pct']}%、"
                    f"不足額は{f['gap_revenue']:,}円（約{gap_players}名分）です。"
                    f"来月に入ってから動くと直前値引きになり単価が崩れます。"
                    f"今月のうちに前受けで埋めておけば、通常単価のまま達成できます。"
                ),
                action=(
                    f"来月の空きが目立つ日（{dates_text(days, 5)}）を提示し、"
                    "今月中のご予約で特典が付く形で先行予約を獲得してください。"
                ),
                channel=channel, course_id=course_id, targets=targets,
                target_dates=dates_text(days, 8),
                response_rate=RESPONSE_RATES["R50"], cap_players=gap_players,
                message_key="next_month_budget",
                message_vars={
                    "course_name": ctx.course_name(course_id),
                    "month": f"{int(next_month[5:7])}月",
                    "dates": dates_text(days, 4),
                },
                deadline=month_end.isoformat(),
            ))
    return out


def rule_this_month_sprint(ctx: Context) -> list[Instruction]:
    """R51 当月の予算未達。残り日数から逆算して必要人数を出します。"""
    this_month = ctx.as_of.strftime("%Y-%m")
    out: list[Instruction] = []
    for course in ctx.courses:
        course_id = course["course_id"]
        f = get_forecast(ctx.conn, course_id, this_month, ctx.as_of)
        if not f["target_revenue"] or f["achievement_ratio"] >= 1.0:
            continue
        if f["gap_players"] <= 0:
            continue
        days = [
            d for d in demand_mod.weak_days(ctx.conn, course_id, ("B", "C", "D"), limit=40)
            if d["play_date"][:7] == this_month
        ]
        out.append(Instruction(
            rule_id="R51", priority=1, category="予算対策（当月）",
            title=(
                f"{ctx.course_name(course_id)}｜今月の予算にあと{f['gap_players']}名"
                f"（予測{f['achievement_pct']}%・残り{f['days_left']}日）"
            ),
            reason=(
                f"今月の着地予測は{f['forecast_revenue']:,}円、予算に対し{f['achievement_pct']}%です。"
                f"不足は{f['gap_revenue']:,}円（約{f['gap_players']}名）。"
                f"残り{f['days_left']}日なので、1日あたり{f['needed_per_day']}名の上乗せが必要です。"
            ),
            action=(
                f"空きの大きい日（{dates_text(days, 5)}）に既存顧客を集中的に送客してください。"
                "同時に、当月の強日は値引きを止めて単価で補います。"
            ),
            channel="ops", course_id=course_id, targets=[],
            target_dates=dates_text(days, 8),
            # ここは「不足額」であって「この指示で見込める額」ではないので、
            # 見込み欄には計上しません（指示文と理由の中に明記しています）。
            expected_players=0,
            expected_revenue=0,
            message_key="",
            deadline=month_range(this_month)[1].isoformat(),
        ))
    return out


def rule_vip_thanks(ctx: Context) -> list[Instruction]:
    """R60 ロイヤル顧客への感謝。守りの施策で、単価維持に効きます。"""
    rows = fetch_profiles(ctx, "p.rank_code = 'F5' AND p.status_code = 'ACTIVE'")
    if not rows:
        return []
    out: list[Instruction] = []
    by_course: dict[str, list[sqlite3.Row]] = {}
    for r in rows:
        by_course.setdefault(r["main_course_id"] or ctx.courses[0]["course_id"], []).append(r)
    for course_id, members in by_course.items():
        groups = group_by_channel(members, ["dm", "mail", "line"],
                                  score_fn=lambda r: r["total_revenue"] or 0)
        for channel, targets in groups.items():
            out.append(Instruction(
                rule_id="R60", priority=4, precision=1, category="ロイヤル維持",
                title=f"{ctx.course_name(course_id)}｜ロイヤル顧客{len(targets)}名へ感謝のご連絡",
                reason=(
                    "年12回以上お越しいただいている最上位のお客様です。"
                    "この層は売上構成比が高い一方、離反すると取り返しがつきません。"
                    "販売ではなく感謝を伝える接点を定期的に作ることが、結果的に最も効きます。"
                ),
                action="優先予約枠のご案内や、コンペ幹事のご相談など、特別扱いを形にしてください。",
                channel=channel, course_id=course_id, targets=targets,
                response_rate=RESPONSE_RATES["R60"],
                message_key="vip_thanks",
                message_vars={"course_name": ctx.course_name(course_id)},
                deadline=(ctx.as_of + timedelta(days=14)).isoformat(),
            ))
    return out


# 実行するルールの一覧（上から順に評価されます）
RULES = [
    rule_this_month_sprint,
    rule_next_month_budget,
    rule_urgent_weak_day,
    rule_cycle_approach,
    rule_vip_at_risk,
    rule_weak_day_fill,
    rule_first_to_second,
    rule_second_to_third,
    rule_strong_day_upsell,
    rule_third_wall,
    rule_winback,
    rule_vip_thanks,
]

RULE_INFO = {
    "R01": "予約周期アプローチ",
    "R02": "常連の離反防止",
    "R10": "初回→2回目",
    "R11": "2回目→3回目",
    "R12": "育成層の常連化",
    "R20": "休眠復活",
    "R30": "弱日への送客",
    "R31": "緊急送客（直近の最弱日）",
    "R40": "強日の単価アップ",
    "R50": "翌月予算の先行対策",
    "R51": "当月予算のラストスパート",
    "R60": "ロイヤル顧客の維持",
}
