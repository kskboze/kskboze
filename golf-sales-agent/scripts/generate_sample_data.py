"""
動作確認用のサンプルデータを作ります（実在のデータではありません）。

    python3 scripts/generate_sample_data.py

8コース分の、実際の営業規模に近いデータを作ります。
  ・約1年2ヶ月分の来場実績（1日あたり100〜200名規模）
  ・繰り返しお越しになる「固定客」約3,000名と、1〜2回で終わる「一見客」多数
  ・先々75日分の予約（一部の曜日をわざと弱くしてあります）
  ・今月・来月・再来月の予算（前年実績の103〜112%）

実データを入れる前に、まずこれで画面の動きを確かめてください。
作り直したいときは data/golf.db を削除してから、もう一度実行します。
"""

from __future__ import annotations

import random
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.analytics.calendar_jp import is_weekend      # noqa: E402
from app.analytics.demand import DEFAULT_BOOKING_CURVE, curve_fraction   # noqa: E402
from app.db import init_db, session                    # noqa: E402

random.seed(20260917)   # 毎回同じデータになるよう固定します

TODAY = date.today()
HISTORY_DAYS = 430        # 過去約1年2ヶ月（前年同月の予算比較ができる長さ）
FUTURE_DAYS = 75          # 先々2ヶ月半
CORE_CUSTOMERS = 3000     # 繰り返しお越しになる固定客
GUEST_POOL = 52000        # 1〜2回で終わる一見客の母数

COURSES = [
    # (ID, コース名, 略称, エリア, 平日定員, 土日定員, 平日単価, 土日単価, 勢い)
    ("C01", "霞ヶ浦カントリークラブ", "霞ヶ浦", "茨城県", 160, 200, 9800, 17500, 1.00),
    ("C02", "那須高原ゴルフ倶楽部", "那須高原", "栃木県", 140, 180, 11200, 19800, 0.92),
    ("C03", "房総グリーンカントリー", "房総", "千葉県", 180, 220, 8600, 16200, 1.05),
    ("C04", "秩父さくらゴルフクラブ", "秩父", "埼玉県", 150, 190, 9200, 16800, 0.86),
    ("C05", "湘南シーサイドゴルフ", "湘南", "神奈川県", 130, 170, 13500, 23000, 1.10),
    ("C06", "赤城高原カントリー倶楽部", "赤城", "群馬県", 145, 185, 8900, 15600, 0.84),
    ("C07", "富士見野ゴルフ倶楽部", "富士見野", "山梨県", 155, 195, 10400, 18200, 0.97),
    ("C08", "東京ベイサイドゴルフ", "東京ベイ", "千葉県", 120, 160, 15800, 26500, 1.15),
]
COURSE_MAP = {c[0]: c for c in COURSES}

PREFECTURES = ["東京都", "神奈川県", "埼玉県", "千葉県", "茨城県", "栃木県", "群馬県", "山梨県"]
CHANNELS = ["自社WEB", "楽天GORA", "GDO", "じゃらんゴルフ", "電話", "一休"]
CHANNEL_W = [30, 22, 18, 14, 10, 6]
PLANS = ["セルフ・昼食付", "キャディ付・昼食付", "セルフ・食事別", "平日限定お得プラン",
         "早朝スループレー", "コンペパック"]
FAMILY = ["佐藤", "鈴木", "高橋", "田中", "伊藤", "渡辺", "山本", "中村", "小林", "加藤",
          "吉田", "山田", "佐々木", "山口", "松本", "井上", "木村", "林", "斎藤", "清水",
          "山崎", "森", "池田", "橋本", "阿部", "石川", "前田", "藤田", "後藤", "岡田"]
GIVEN = ["健一", "誠", "浩二", "隆", "博之", "和彦", "正男", "徹", "洋一", "秀樹",
         "大輔", "健太", "拓也", "修", "康弘", "光男", "一郎", "俊介",
         "美咲", "由美", "恵子", "陽子", "直子", "真理", "智子", "久美子"]

PLAYER_CHOICES = [1, 2, 3, 4]
PLAYER_WEIGHTS = [0.08, 0.20, 0.20, 0.52]


def season_factor(d: date) -> float:
    """ゴルフの季節変動。春と秋が繁忙、真夏と真冬が閑散。"""
    return {1: 0.62, 2: 0.70, 3: 0.92, 4: 1.15, 5: 1.20, 6: 0.98,
            7: 0.80, 8: 0.74, 9: 1.05, 10: 1.22, 11: 1.18, 12: 0.85}[d.month]


def sample_lead_days() -> int:
    """
    予約日〜プレー日の日数を、標準的な予約曲線に沿って抽選します。

    過去実績のリードタイムと、先々の予約の入り方がちぐはぐだと、
    「過去の同時点と比べる」という需要判定が正しく働きません。
    そのため、どちらも同じ曲線から作るようにしています。

    curve_fraction(d) は「d日前までに入っている予約の割合」です。
    言い換えると「リードタイムが d 日以上になる確率」なので、
    0〜1の乱数 u に対して curve_fraction(d) = u となる d を探せば、
    曲線どおりのリードタイムが得られます。
    """
    u = random.random()
    points = sorted(DEFAULT_BOOKING_CURVE)          # 日数の小さい順
    previous_day, previous_value = 0, 1.0
    for day, value in points:
        if value <= u:
            if previous_value <= value:
                return day
            ratio = (previous_value - u) / (previous_value - value)
            return max(0, int(round(previous_day + (day - previous_day) * ratio)))
        previous_day, previous_value = day, value
    # 曲線の外（かなり早い時期の予約）はここに来ます
    return random.randint(90, 150)


def person_name() -> str:
    return f"{random.choice(FAMILY)} {random.choice(GIVEN)}"


def contact_info(index: int, prefix: str, generous: bool) -> dict:
    """連絡先と配信許諾。固定客ほど連絡先が揃っている、という前提にしています。"""
    mail_p, line_p, sms_p = (0.78, 0.42, 0.55) if generous else (0.45, 0.14, 0.30)
    return {
        "email": f"{prefix}{index:06d}@example.com" if random.random() < mail_p else None,
        "phone": (f"090-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"
                  if random.random() < 0.90 else None),
        "line_id": f"U{prefix}{index:06d}" if random.random() < line_p else None,
        "prefecture": random.choice(PREFECTURES),
        "birth_year": random.randint(1948, 1998),
        "gender": random.choices(["男性", "女性"], weights=[0.83, 0.17])[0],
        "member_type": random.choices(["会員", "ビジター"],
                                      weights=[0.30, 0.70] if generous else [0.03, 0.97])[0],
        "allow_mail": 1 if random.random() < (0.92 if generous else 0.70) else 0,
        "allow_dm": 1 if random.random() < (0.85 if generous else 0.55) else 0,
        "allow_line": 1 if random.random() < 0.88 else 0,
        "allow_sms": 1 if random.random() < (0.50 if generous else 0.30) else 0,
    }


def make_core_customers() -> list[dict]:
    """繰り返しお越しになる固定客。来場周期を1人ずつ持たせます。"""
    customers = []
    for i in range(1, CORE_CUSTOMERS + 1):
        kind = random.choices(["heavy", "middle", "light"], weights=[0.18, 0.42, 0.40])[0]
        cycle = {"heavy": random.randint(21, 45),
                 "middle": random.randint(46, 100),
                 "light": random.randint(101, 220)}[kind]
        info = contact_info(i, "core", generous=True)
        customers.append({
            "customer_id": f"K{i:06d}",
            "name": person_name(),
            "home_course_id": random.choice(COURSES)[0],
            "_kind": kind,
            "_cycle": cycle,
            **info,
        })
    return customers


def make_guest_customers() -> list[dict]:
    """1〜2回で終わることが多い一見客。ここを2回目につなげるのが営業課題です。"""
    customers = []
    for i in range(1, GUEST_POOL + 1):
        info = contact_info(i, "g", generous=False)
        customers.append({
            "customer_id": f"G{i:06d}",
            "name": person_name(),
            "home_course_id": None,
            **info,
        })
    return customers


def core_visit_plan(core: list[dict]) -> dict[tuple[str, str], list[dict]]:
    """
    固定客の来場予定を、周期にしたがって先に決めます。
    キーは (コースID, 日付) で、後から1日ごとの人数を埋めるときに使います。
    """
    plan: dict[tuple[str, str], list[dict]] = defaultdict(list)
    start_limit = TODAY - timedelta(days=HISTORY_DAYS)

    for cust in core:
        cycle = cust["_cycle"]
        current = start_limit + timedelta(days=random.randint(0, min(cycle * 2, 200)))
        # 3割の方は途中で来なくなります（離反を再現）
        churn_at = (TODAY - timedelta(days=random.randint(40, 400))
                    if random.random() < 0.30 else None)

        while current < TODAY:
            if churn_at and current > churn_at:
                break
            course_id = (cust["home_course_id"] if random.random() < 0.80
                         else random.choice(COURSES)[0])
            plan[(course_id, current.isoformat())].append(cust)
            current += timedelta(days=max(7, int(random.gauss(cycle, cycle * 0.35))))
    return plan


def guest_tickets(guests: list[dict]) -> list[str]:
    """
    一見客の「来場券」を作ります。
    6割の方は1回だけ、2.5割が2回、1.5割が3〜4回という配分にし、
    それをよく混ぜてから使うことで、来場時期の偏りを無くします。
    """
    tickets: list[str] = []
    for guest in guests:
        times = random.choices([1, 2, 3, 4], weights=[0.60, 0.25, 0.10, 0.05])[0]
        tickets.extend([guest["customer_id"]] * times)
    random.shuffle(tickets)
    return tickets


def build_history(core: list[dict], guests: list[dict]) -> list[tuple]:
    """
    1日ずつ「その日の来場人数」を決め、固定客で足りない分を一見客で埋めます。
    これにより、実際のゴルフ場に近い1日あたりの来場ボリュームになります。
    """
    plan = core_visit_plan(core)
    tickets = guest_tickets(guests)
    ticket_index = 0
    visits: list[tuple] = []
    visit_no = 0

    for course in COURSES:
        course_id, _, _, _, cap_wd, cap_we, price_wd, price_we, momentum = course
        for offset in range(HISTORY_DAYS, 0, -1):
            play = TODAY - timedelta(days=offset)
            weekend = is_weekend(play)
            capacity = cap_we if weekend else cap_wd
            unit = price_we if weekend else price_wd

            fill = (0.86 if weekend else 0.54) * momentum * (season_factor(play) / 1.05)
            fill *= random.uniform(0.85, 1.12)
            target_players = int(capacity * min(max(fill, 0.08), 1.0))

            booked = 0
            # ① まず固定客の来場を置きます
            for cust in plan.get((course_id, play.isoformat()), []):
                players = random.choices(PLAYER_CHOICES, weights=PLAYER_WEIGHTS)[0]
                visit_no += 1
                lead = max(1, sample_lead_days())
                visits.append((
                    f"V{visit_no:07d}", cust["customer_id"], course_id, play.isoformat(),
                    (play - timedelta(days=lead)).isoformat(), players,
                    int(unit * random.uniform(0.88, 1.15)) * players,
                    random.choice(PLANS), random.choices(CHANNELS, weights=CHANNEL_W)[0],
                ))
                booked += players

            # ② 残りを一見客で埋めます
            while booked < target_players and ticket_index < len(tickets):
                players = random.choices(PLAYER_CHOICES, weights=PLAYER_WEIGHTS)[0]
                players = min(players, target_players - booked)
                if players <= 0:
                    break
                guest_id = tickets[ticket_index]
                ticket_index += 1
                visit_no += 1
                lead = max(1, sample_lead_days())
                visits.append((
                    f"V{visit_no:07d}", guest_id, course_id, play.isoformat(),
                    (play - timedelta(days=lead)).isoformat(), players,
                    int(unit * random.uniform(0.85, 1.12)) * players,
                    random.choice(PLANS), random.choices(CHANNELS, weights=CHANNEL_W)[0],
                ))
                booked += players
    return visits


def build_reservations(core: list[dict], guests: list[dict]) -> list[tuple]:
    """
    先々の予約。日ごとに最終着地を決め、予約曲線から今の予約数を逆算します。
    一部の曜日をわざと弱くして、弱日判定の動きを確認できるようにしています。
    """
    reservations: list[tuple] = []
    res_no = 0
    pool = core + guests[: GUEST_POOL // 2]

    for course in COURSES:
        course_id, _, _, _, cap_wd, cap_we, price_wd, price_we, momentum = course
        weak_dows = random.sample([0, 1, 2, 3, 4], 2)   # 弱くする平日を2つ

        for offset in range(0, FUTURE_DAYS + 1):
            target = TODAY + timedelta(days=offset)
            weekend = is_weekend(target)
            capacity = cap_we if weekend else cap_wd
            unit = price_we if weekend else price_wd

            fill = (0.86 if weekend else 0.54) * momentum * (season_factor(target) / 1.05)
            if not weekend and target.weekday() in weak_dows:
                fill *= 0.60                            # 構造的に弱い曜日
            if random.random() < 0.12:
                fill *= random.uniform(0.5, 0.75)       # 突発的な弱日
            fill = min(max(fill, 0.08), 1.0)

            final_players = int(capacity * fill)
            now_players = int(final_players * curve_fraction(offset) * random.uniform(0.85, 1.12))
            now_players = max(0, min(now_players, capacity))

            booked = 0
            guard = 0
            while booked < now_players and guard < 120:
                guard += 1
                players = random.choices(PLAYER_CHOICES, weights=PLAYER_WEIGHTS)[0]
                players = min(players, now_players - booked)
                if players <= 0:
                    break
                cust = random.choice(pool) if random.random() < 0.65 else None
                res_no += 1
                reservations.append((
                    f"R{res_no:07d}", cust["customer_id"] if cust else None, course_id,
                    target.isoformat(),
                    (TODAY - timedelta(days=random.randint(0, 50))).isoformat(),
                    players, int(unit * random.uniform(0.88, 1.12)) * players,
                    random.choice(PLANS), random.choices(CHANNELS, weights=CHANNEL_W)[0],
                    "confirmed",
                ))
                booked += players
    return reservations


def build_budgets(visits: list[tuple]) -> list[tuple]:
    """前年同月の実績をもとに、今月・来月・再来月の予算を置きます。"""
    actual: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    for v in visits:
        key = (v[2], v[3][:7])
        actual[key][0] += v[6]      # 売上
        actual[key][1] += v[5]      # 人数

    months = []
    cursor = date(TODAY.year, TODAY.month, 1)
    for _ in range(3):
        months.append(cursor.strftime("%Y-%m"))
        cursor = date(cursor.year + (cursor.month // 12), cursor.month % 12 + 1, 1)

    budgets = []
    for course in COURSES:
        course_id = course[0]
        for ym in months:
            year, month = (int(x) for x in ym.split("-"))
            rev, ppl = actual.get((course_id, f"{year-1:04d}-{month:02d}"), [0, 0])
            if rev == 0:
                # 前年実績が無い月は、直近3ヶ月の平均から置きます
                recent = [v for k, v in actual.items() if k[0] == course_id]
                rev = int(sum(x[0] for x in recent) / max(len(recent), 1))
                ppl = int(sum(x[1] for x in recent) / max(len(recent), 1))
            growth = random.uniform(1.03, 1.12)   # 前年比103〜112%を目標に
            budgets.append((course_id, ym, int(rev * growth / 10000) * 10000, int(ppl * growth)))
    return budgets


def main() -> None:
    init_db()
    print("サンプルデータを作成しています…（1分ほどかかります）")

    core = make_core_customers()
    guests = make_guest_customers()
    print("  顧客を作成しました。来場実績を作成しています…")
    visits = build_history(core, guests)
    print(f"  来場実績 {len(visits):,} 件。予約を作成しています…")
    reservations = build_reservations(core, guests)
    budgets = build_budgets(visits)

    # 実際に来場のあった顧客だけを登録します（使われない顧客を大量に残さないため）
    used = {v[1] for v in visits} | {r[1] for r in reservations if r[1]}
    customers = [c for c in core + guests if c["customer_id"] in used]

    print(f"  データベースに書き込んでいます…（顧客 {len(customers):,} 名）")
    with session() as conn:
        for table in ("visits", "reservations", "budgets", "customers", "courses", "contact_log",
                      "instructions", "instruction_targets", "customer_profiles",
                      "demand_days", "budget_forecasts"):
            conn.execute(f"DELETE FROM {table}")

        conn.executemany(
            "INSERT INTO courses(course_id, name, short_name, area, capacity_weekday,"
            " capacity_weekend, note) VALUES (?,?,?,?,?,?,?)",
            [(c[0], c[1], c[2], c[3], c[4], c[5], f"平日{c[6]:,}円／土日{c[7]:,}円")
             for c in COURSES],
        )
        conn.executemany(
            "INSERT INTO customers(customer_id, name, email, phone, line_id, prefecture,"
            " birth_year, gender, member_type, home_course_id, allow_mail, allow_dm,"
            " allow_line, allow_sms) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(c["customer_id"], c["name"], c["email"], c["phone"], c["line_id"],
              c["prefecture"], c["birth_year"], c["gender"], c["member_type"],
              c["home_course_id"], c["allow_mail"], c["allow_dm"], c["allow_line"],
              c["allow_sms"]) for c in customers],
        )
        conn.executemany(
            "INSERT INTO visits(visit_id, customer_id, course_id, play_date, booked_at,"
            " players, revenue, plan_name, channel) VALUES (?,?,?,?,?,?,?,?,?)", visits,
        )
        conn.executemany(
            "INSERT INTO reservations(reservation_id, customer_id, course_id, play_date,"
            " booked_at, players, amount, plan_name, channel, status)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)", reservations,
        )
        conn.executemany(
            "INSERT INTO budgets(course_id, year_month, target_revenue, target_players)"
            " VALUES (?,?,?,?)", budgets,
        )

    print()
    print(f"  コース      : {len(COURSES):>8,} 件")
    print(f"  顧客        : {len(customers):>8,} 名")
    print(f"  来場実績    : {len(visits):>8,} 件")
    print(f"  先々の予約  : {len(reservations):>8,} 件")
    print(f"  月次予算    : {len(budgets):>8,} 件")
    print("完了しました。次は  python3 -m app.cli run  で本日の指示を作成してください。")


if __name__ == "__main__":
    main()
