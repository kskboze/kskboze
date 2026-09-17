"""
自動テスト：計算ロジックが正しいことを確認します。

    python3 -m unittest discover -s tests -v

数字の計算を人手で毎回確かめるのは大変なので、
「この条件ならこの答えになるはず」をプログラムで書き残しておきます。
ルールを変更したときに、うっかり壊していないかをすぐ確認できます。
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# テスト用に、専用の空データベースを使います（本番データを壊さないため）
_TMP = tempfile.mkdtemp(prefix="golf-test-")
os.environ["DATABASE_PATH"] = str(Path(_TMP) / "test.db")

from app import db                                  # noqa: E402
from app.analytics import customers as cust         # noqa: E402
from app.analytics.budget import forecast_month, month_range, shift_month  # noqa: E402
from app.analytics.calendar_jp import day_label, is_weekend, holiday_name   # noqa: E402
from app.analytics.demand import CoursePastDays, curve_fraction, rebuild_demand  # noqa: E402
from app.engine.messages import render, sms_length_warning   # noqa: E402
from app.engine.rules import AVG_PARTY_SIZE, estimate, pick_channel   # noqa: E402
from app.importer import import_rows, parse_date, parse_int, parse_year_month  # noqa: E402

TODAY = date(2026, 9, 17)


class TestImporter(unittest.TestCase):
    """CSVの読み取りが、表記ゆれを吸収できるかを確認します。"""

    def test_日付のいろいろな書き方を統一できる(self):
        for text in ["2026-10-03", "2026/10/3", "2026年10月3日", "20261003"]:
            self.assertEqual(parse_date(text), "2026-10-03", text)

    def test_日付として読めないものはNoneになる(self):
        self.assertIsNone(parse_date(""))
        self.assertIsNone(parse_date("未定"))

    def test_金額や人数から数字だけを取り出せる(self):
        self.assertEqual(parse_int("12,300円"), 12300)
        self.assertEqual(parse_int("4名"), 4)
        self.assertEqual(parse_int("１２３"), 123)      # 全角でも読めます

    def test_可否の記号を1と0に変換できる(self):
        self.assertEqual(parse_int("○"), 1)
        self.assertEqual(parse_int("×"), 0)

    def test_年月のいろいろな書き方を統一できる(self):
        for text in ["2026-10", "2026/10", "2026年10月", "202610"]:
            self.assertEqual(parse_year_month(text), "2026-10", text)

    def test_日本語の見出しのCSVを取り込める(self):
        db.init_db()
        rows = [{
            "コースID": "T01", "来場日": "2026/9/1", "顧客ID": "C1",
            "人数": "4名", "売上金額": "48,000円", "予約日": "2026年8月20日",
        }]
        result = import_rows("visits", rows, "test.csv")
        self.assertEqual(result.rows_ok, 1)
        with db.session() as conn:
            row = conn.execute("SELECT * FROM visits WHERE customer_id='C1'").fetchone()
        self.assertEqual(row["play_date"], "2026-09-01")
        self.assertEqual(row["players"], 4)
        self.assertEqual(row["revenue"], 48000)

    def test_必須の列が無いときは理由を教えてくれる(self):
        result = import_rows("visits", [{"謎の列": "1"}], "bad.csv")
        self.assertEqual(result.rows_ok, 0)
        self.assertTrue(result.errors)


class TestCalendar(unittest.TestCase):
    """祝日の判定を確認します。"""

    def test_祝日を正しく判定できる(self):
        self.assertEqual(holiday_name(date(2026, 1, 1)), "元日")
        self.assertEqual(holiday_name(date(2026, 10, 12)), "スポーツの日")  # 10月第2月曜
        self.assertEqual(holiday_name(date(2026, 9, 21)), "敬老の日")      # 9月第3月曜

    def test_土日祝は土日祝として扱われる(self):
        self.assertTrue(is_weekend(date(2026, 10, 12)))   # 月曜だが祝日
        self.assertTrue(is_weekend(date(2026, 9, 19)))    # 土曜
        self.assertFalse(is_weekend(date(2026, 9, 17)))   # 平日の木曜

    def test_表示用のラベルが作れる(self):
        self.assertEqual(day_label(date(2026, 10, 12)), "10/12(月・祝)")
        self.assertEqual(day_label(date(2026, 9, 17)), "9/17(木)")


class TestCustomerAnalytics(unittest.TestCase):
    """顧客分析（来場周期・ランク・状態）を確認します。"""

    def test_来場間隔の中央値が周期になる(self):
        # 30日、32日、31日おき → 中央値31日
        self.assertEqual(cust.median_int([30, 32, 31]), 31)

    def test_例外的に長い間隔に引きずられない(self):
        # 平均なら約128日になるが、中央値なら30日のまま
        self.assertEqual(cust.median_int([30, 30, 30, 500]), 30)

    def test_来場回数でランクが決まる(self):
        s = db.DEFAULT_SETTINGS
        self.assertEqual(cust.decide_rank(1, s), "F1")
        self.assertEqual(cust.decide_rank(2, s), "F2")
        self.assertEqual(cust.decide_rank(4, s), "F3")
        self.assertEqual(cust.decide_rank(8, s), "F4")
        self.assertEqual(cust.decide_rank(20, s), "F5")

    def test_同じ日数でも周期によって判定が変わる(self):
        """周期30日の方の90日ぶりは異常、周期180日の方の90日ぶりは正常です。"""
        s = db.DEFAULT_SETTINGS
        self.assertEqual(cust.decide_status(90, 30, s, total_visits=5), "DORMANT")
        self.assertEqual(cust.decide_status(90, 180, s, total_visits=5), "ACTIVE")

    def test_1回だけの方は固定日数で判定される(self):
        s = db.DEFAULT_SETTINGS
        self.assertEqual(cust.decide_status(30, 90, s, total_visits=1), "ACTIVE")
        self.assertEqual(cust.decide_status(150, 90, s, total_visits=1), "AT_RISK")
        self.assertEqual(cust.decide_status(300, 90, s, total_visits=1), "DORMANT")

    def test_アプローチ推奨日が周期とリードタイムから決まる(self):
        """要望の中心：周期30日・リード14日なら、前回来場の16日後にご案内。"""
        db.init_db()
        with db.session() as conn:
            conn.execute("DELETE FROM visits")
            conn.execute("INSERT OR IGNORE INTO courses(course_id, name) VALUES ('T01','テスト')")
            conn.execute("INSERT OR IGNORE INTO customers(customer_id) VALUES ('CYC')")
            # 30日おきに4回来場、直近の予約は14日前に入れている
            for i in range(4):
                play = TODAY - timedelta(days=90 - i * 30)
                conn.execute(
                    "INSERT OR REPLACE INTO visits(visit_id, customer_id, course_id, play_date,"
                    " booked_at, players, revenue) VALUES (?,?,?,?,?,?,?)",
                    (f"CYC{i}", "CYC", "T01", play.isoformat(),
                     (play - timedelta(days=14)).isoformat(), 2, 24000),
                )
            cust.rebuild_profiles(conn, TODAY)
            p = conn.execute(
                "SELECT * FROM customer_profiles WHERE customer_id='CYC'").fetchone()

        self.assertEqual(p["cycle_days"], 30)
        self.assertEqual(p["lead_days"], 14)
        last = TODAY   # 直近の来場が本日
        self.assertEqual(p["next_expected_date"], (last + timedelta(days=30)).isoformat())
        self.assertEqual(p["approach_date"], (last + timedelta(days=16)).isoformat())
        self.assertEqual(p["avg_spend"], 12000)


class TestDemand(unittest.TestCase):
    """需要分析（弱日・強日）を確認します。"""

    def test_予約曲線が滑らかに変化する(self):
        self.assertAlmostEqual(curve_fraction(0), 1.00, places=2)
        self.assertAlmostEqual(curve_fraction(30), 0.40, places=2)
        # 日数が増えるほど「すでに入っている割合」は減ります
        values = [curve_fraction(d) for d in range(0, 91)]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_過去実績から同時点の予約数を数えられる(self):
        rows = [
            {"play_date": "2026-08-06", "booked_at": "2026-07-07", "players": 4},  # 30日前
            {"play_date": "2026-08-06", "booked_at": "2026-08-01", "players": 2},  # 5日前
        ]
        past = CoursePastDays(rows)
        target = date(2026, 8, 6)
        self.assertEqual(past.final[target], 6)
        self.assertEqual(past.at_point[target][30], 4)   # 30日前時点では4名
        self.assertEqual(past.at_point[target][5], 6)    # 5日前時点では6名
        self.assertEqual(past.at_point[target][0], 6)

    def test_弱日と強日が判定される(self):
        db.init_db()
        with db.session() as conn:
            for table in ("visits", "reservations", "courses", "demand_days"):
                conn.execute(f"DELETE FROM {table}")
            conn.execute(
                "INSERT INTO courses(course_id, name, capacity_weekday, capacity_weekend)"
                " VALUES ('D01','需要テスト',100,100)")
            # 過去：毎週金曜に60名（すべて60日前に予約済み）という実績を作ります
            # 60日前に入れておくことで、「◯日前時点」の比較が確実に行えます
            play = TODAY - timedelta(days=364)
            i = 0
            while play < TODAY:
                if play.weekday() == 4:
                    i += 1
                    conn.execute(
                        "INSERT INTO visits(visit_id, customer_id, course_id, play_date,"
                        " booked_at, players, revenue) VALUES (?,?,?,?,?,?,?)",
                        (f"D{i}", "X", "D01", play.isoformat(),
                         (play - timedelta(days=60)).isoformat(), 60, 600000))
                play += timedelta(days=1)
            # 未来：30日後の金曜に「20名しか入っていない」日を作ります
            future = TODAY + timedelta(days=30)
            while future.weekday() != 4:
                future += timedelta(days=1)
            days_out = (future - TODAY).days
            conn.execute(
                "INSERT INTO reservations(reservation_id, course_id, play_date, players, amount)"
                " VALUES ('RR','D01',?,20,200000)", (future.isoformat(),))
            conn.execute("UPDATE settings SET value='90' WHERE key='demand_horizon_days'")
            rebuild_demand(conn, TODAY)
            row = conn.execute(
                "SELECT * FROM demand_days WHERE course_id='D01' AND play_date=?",
                (future.isoformat(),)).fetchone()

        # 例年は同時点で60名(60%)入っているのに、今年は20名(20%)しかない → 最弱日D
        self.assertEqual(row["days_out"], days_out)
        self.assertAlmostEqual(row["fill_rate"], 0.20, places=2)
        self.assertAlmostEqual(row["benchmark_fill"], 0.60, places=2)
        self.assertEqual(row["grade"], "D")


class TestBudget(unittest.TestCase):
    """予算予測を確認します。"""

    def test_月の範囲と翌月の計算(self):
        self.assertEqual(month_range("2026-10"), (date(2026, 10, 1), date(2026, 10, 31)))
        self.assertEqual(month_range("2026-02"), (date(2026, 2, 1), date(2026, 2, 28)))
        self.assertEqual(shift_month("2026-12", 1), "2027-01")
        self.assertEqual(shift_month("2026-09", 1), "2026-10")

    def test_不足額が必要人数に変換される(self):
        db.init_db()
        with db.session() as conn:
            for table in ("visits", "reservations", "budgets", "courses", "demand_days"):
                conn.execute(f"DELETE FROM {table}")
            conn.execute("INSERT INTO courses(course_id, name) VALUES ('B01','予算テスト')")
            # 平均単価が10,000円になるよう、過去の実績を置きます
            conn.execute(
                "INSERT INTO visits(visit_id, customer_id, course_id, play_date, players, revenue)"
                " VALUES ('BV','X','B01',?,100,1000000)",
                ((TODAY - timedelta(days=60)).isoformat(),))
            # 今月の予算1,000万円。実績・予約はゼロ
            conn.execute(
                "INSERT INTO budgets(course_id, year_month, target_revenue) VALUES ('B01',?,?)",
                (TODAY.strftime("%Y-%m"), 10_000_000))
            f = forecast_month(conn, "B01", TODAY.strftime("%Y-%m"), TODAY)

        self.assertEqual(f["avg_spend"], 10000)
        self.assertEqual(f["forecast_revenue"], 0)
        self.assertEqual(f["gap_revenue"], 10_000_000)
        self.assertEqual(f["gap_players"], 1000)          # 1,000万円 ÷ 1万円 = 1,000名


class TestRules(unittest.TestCase):
    """施策ルールの部品を確認します。"""

    def test_許諾の無い手段は選ばれない(self):
        row = {
            "allow_line": 0, "line_id": "U1",
            "allow_mail": 1, "email": "a@example.com",
            "allow_sms": 1, "phone": "090",
            "allow_dm": 1,
        }
        # LINEのIDはあるが許諾が無いので、次の候補のメールが選ばれます
        self.assertEqual(pick_channel(row, ["line", "mail", "sms", "dm"]), "mail")

    def test_連絡先が無ければ何も選ばれない(self):
        row = {"allow_line": 1, "line_id": None, "allow_mail": 1, "email": None,
               "allow_sms": 1, "phone": None, "allow_dm": 0}
        self.assertIsNone(pick_channel(row, ["line", "mail", "sms", "dm"]))

    def test_見込みは反応率をかけた控えめな数字になる(self):
        players, revenue = estimate("R10", 1000, 12000)   # 反応率4%
        self.assertEqual(players, int(round(1000 * 0.04 * AVG_PARTY_SIZE)))
        self.assertEqual(revenue, players * 12000)
        self.assertLess(players, 1000)   # 対象人数より必ず小さくなります

    def test_空き枠を超える見込みは出さない(self):
        players, _ = estimate("R31", 10000, 12000, cap_players=50)
        self.assertEqual(players, 50)


class TestMessages(unittest.TestCase):
    """文面テンプレートを確認します。"""

    def test_差し込みが働く(self):
        subject, body = render("weak_day", "mail",
                               {"course_name": "テストCC", "dates": "10/2(金)"})
        self.assertIn("テストCC", subject)
        self.assertIn("10/2(金)", body)
        self.assertIn("{お名前}", body)   # 宛名は差し込み用に残します

    def test_該当が無くても文面は必ず返る(self):
        subject, body = render("存在しない施策", "line", {"course_name": "テストCC"})
        self.assertTrue(body)

    def test_SMSが長すぎると警告が出る(self):
        self.assertIsNone(sms_length_warning("短い本文です"))
        self.assertIsNotNone(sms_length_warning("あ" * 100))


if __name__ == "__main__":
    unittest.main(verbosity=2)
