"""
データベース（SQLite）の定義と接続をまとめた場所です。

SQLite は「1つのファイルがそのままデータベースになる」仕組みです。
サーバーを別に立てる必要がないので、初めての方でも扱いやすいのが利点です。
実体は data/golf.db というファイル1個です。バックアップはこのファイルをコピーするだけ。
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Any, Iterable, Iterator

from app.config import DATABASE_PATH, DEFAULT_SETTINGS

# ---------------------------------------------------------------
# テーブル定義
# ---------------------------------------------------------------
SCHEMA = """
-- ゴルフ場マスタ（8コース分を登録します）
CREATE TABLE IF NOT EXISTS courses (
    course_id         TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    short_name        TEXT,
    area              TEXT,
    capacity_weekday  INTEGER NOT NULL DEFAULT 160,  -- 平日の販売可能人数（1日）
    capacity_weekend  INTEGER NOT NULL DEFAULT 200,  -- 土日祝の販売可能人数（1日）
    note              TEXT
);

-- 顧客マスタ
CREATE TABLE IF NOT EXISTS customers (
    customer_id     TEXT PRIMARY KEY,
    name            TEXT,
    kana            TEXT,
    email           TEXT,
    phone           TEXT,
    line_id         TEXT,
    postal_code     TEXT,
    prefecture      TEXT,
    city            TEXT,
    birth_year      INTEGER,
    gender          TEXT,
    member_type     TEXT,            -- 会員 / ビジター など
    home_course_id  TEXT,            -- よく使うコース
    allow_mail      INTEGER DEFAULT 1,   -- 1=送ってよい / 0=不可
    allow_dm        INTEGER DEFAULT 1,
    allow_line      INTEGER DEFAULT 0,
    allow_sms       INTEGER DEFAULT 0,
    registered_at   TEXT
);

-- 来場実績（プレーが終わった分）
CREATE TABLE IF NOT EXISTS visits (
    visit_id     TEXT PRIMARY KEY,
    customer_id  TEXT NOT NULL,
    course_id    TEXT NOT NULL,
    play_date    TEXT NOT NULL,       -- YYYY-MM-DD
    booked_at    TEXT,                -- 予約された日 YYYY-MM-DD
    players      INTEGER DEFAULT 1,   -- 同伴者を含む人数
    revenue      INTEGER DEFAULT 0,   -- 売上合計（円）
    plan_name    TEXT,
    channel      TEXT                 -- 自社WEB / 楽天GORA / GDO / じゃらん / 電話 など
);
CREATE INDEX IF NOT EXISTS idx_visits_customer ON visits(customer_id, play_date);
CREATE INDEX IF NOT EXISTS idx_visits_course   ON visits(course_id, play_date);
CREATE INDEX IF NOT EXISTS idx_visits_booked   ON visits(course_id, play_date, booked_at);

-- 未来の予約（オンブック）
CREATE TABLE IF NOT EXISTS reservations (
    reservation_id TEXT PRIMARY KEY,
    customer_id    TEXT,
    course_id      TEXT NOT NULL,
    play_date      TEXT NOT NULL,
    booked_at      TEXT,
    players        INTEGER DEFAULT 1,
    amount         INTEGER DEFAULT 0,
    plan_name      TEXT,
    channel        TEXT,
    status         TEXT DEFAULT 'confirmed'   -- confirmed / cancelled
);
CREATE INDEX IF NOT EXISTS idx_res_course ON reservations(course_id, play_date);

-- 月次予算
CREATE TABLE IF NOT EXISTS budgets (
    course_id      TEXT NOT NULL,
    year_month     TEXT NOT NULL,      -- YYYY-MM
    target_revenue INTEGER NOT NULL,
    target_players INTEGER,
    PRIMARY KEY (course_id, year_month)
);

-- 顧客プロファイル（分析結果の保存先。毎回の計算結果をここに書き込みます）
CREATE TABLE IF NOT EXISTS customer_profiles (
    customer_id        TEXT PRIMARY KEY,
    as_of              TEXT,
    total_visits       INTEGER DEFAULT 0,
    visits_12m         INTEGER DEFAULT 0,
    first_visit        TEXT,
    last_visit         TEXT,
    recency_days       INTEGER,
    total_revenue      INTEGER DEFAULT 0,
    avg_spend          INTEGER DEFAULT 0,   -- 1人あたり平均単価
    cycle_days         INTEGER,             -- 来場周期（来場間隔の中央値）
    cycle_is_estimated INTEGER DEFAULT 0,   -- 1=実測できず推定値を使った
    lead_days          INTEGER,             -- 予約リードタイム（予約日〜プレー日）
    next_expected_date TEXT,                -- 次回来場の予測日
    approach_date      TEXT,                -- 案内を送るべき推奨日
    rank_code          TEXT,                -- F1〜F5
    status_code        TEXT,                -- ACTIVE / AT_RISK / DORMANT / LOST
    main_course_id     TEXT,
    main_dow           INTEGER,             -- よく来る曜日（0=月 ... 6=日）
    weekday_ratio      REAL,                -- 平日来場の割合
    last_contacted_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_prof_rank ON customer_profiles(rank_code, status_code);
CREATE INDEX IF NOT EXISTS idx_prof_appr ON customer_profiles(approach_date);

-- 日別の需要判定（弱日/強日）の保存先
CREATE TABLE IF NOT EXISTS demand_days (
    course_id        TEXT NOT NULL,
    play_date        TEXT NOT NULL,
    as_of            TEXT,
    dow              INTEGER,
    is_weekend       INTEGER,
    days_out         INTEGER,
    capacity         INTEGER,
    onbook_players   INTEGER,
    fill_rate        REAL,
    benchmark_fill   REAL,     -- 過去の同条件・同時点での充足率
    pace_ratio       REAL,     -- 今の充足率 ÷ 過去同時点 （1.0で例年並み）
    forecast_players INTEGER,  -- 最終着地の予測人数
    forecast_fill    REAL,
    gap_players      INTEGER,  -- 満口までの残り人数
    grade            TEXT,     -- S:強日 A:やや強 B:標準 C:弱日 D:最弱日
    PRIMARY KEY (course_id, play_date)
);

-- 予算の着地予測の保存先
CREATE TABLE IF NOT EXISTS budget_forecasts (
    course_id         TEXT NOT NULL,
    year_month        TEXT NOT NULL,
    as_of             TEXT,
    target_revenue    INTEGER,
    actual_revenue    INTEGER,
    onbook_revenue    INTEGER,
    pickup_revenue    INTEGER,   -- これから入るであろう予約の見込み
    forecast_revenue  INTEGER,
    achievement_ratio REAL,
    gap_revenue       INTEGER,
    avg_spend         INTEGER,
    gap_players       INTEGER,   -- 予算達成に必要な追加人数
    PRIMARY KEY (course_id, year_month)
);

-- 生成された営業指示
CREATE TABLE IF NOT EXISTS instructions (
    instruction_id   TEXT PRIMARY KEY,
    run_date         TEXT NOT NULL,
    course_id        TEXT,
    rule_id          TEXT,
    priority         INTEGER,
    category         TEXT,
    title            TEXT,
    reason           TEXT,
    action           TEXT,
    channel          TEXT,
    target_count     INTEGER,
    target_dates     TEXT,
    expected_players INTEGER,
    expected_revenue INTEGER,
    response_rate    REAL DEFAULT 0.05,
    message_subject  TEXT,
    message_body     TEXT,
    ai_generated     INTEGER DEFAULT 0,
    deadline         TEXT,
    status           TEXT DEFAULT 'open',   -- open / done / skipped
    created_at       TEXT
);
CREATE INDEX IF NOT EXISTS idx_inst_run ON instructions(run_date, priority);

-- 指示ごとの対象顧客
CREATE TABLE IF NOT EXISTS instruction_targets (
    instruction_id TEXT NOT NULL,
    customer_id    TEXT NOT NULL,
    score          REAL DEFAULT 0,
    PRIMARY KEY (instruction_id, customer_id)
);

-- 接触履歴（同じ人に送りすぎないための記録）
CREATE TABLE IF NOT EXISTS contact_log (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id    TEXT NOT NULL,
    course_id      TEXT,
    rule_id        TEXT,
    channel        TEXT,
    sent_date      TEXT,
    instruction_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_contact ON contact_log(customer_id, sent_date);

-- 取り込み履歴
CREATE TABLE IF NOT EXISTS import_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    imported_at TEXT,
    kind        TEXT,
    filename    TEXT,
    rows_ok     INTEGER,
    rows_ng     INTEGER,
    message     TEXT
);

-- 画面から変更できる設定値
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def connect() -> sqlite3.Connection:
    """データベースに接続します。結果は列名でも取り出せるようにしておきます。"""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def session() -> Iterator[sqlite3.Connection]:
    """`with session() as conn:` の形で使うと、最後に自動で保存・切断します。"""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# 後から追加した列。既存のデータベースにも自動で足します。
ADDED_COLUMNS = [
    ("instructions", "response_rate", "REAL DEFAULT 0.05"),
]


def init_db() -> None:
    """テーブルを作ります。すでにある場合は何もしません（何度実行しても安全）。"""
    with session() as conn:
        conn.executescript(SCHEMA)
        for table, column, definition in ADDED_COLUMNS:
            existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
            if column not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
                (key, str(value)),
            )


def get_settings(conn: sqlite3.Connection) -> dict[str, str]:
    """設定値をまとめて取り出します。"""
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    merged = {k: str(v) for k, v in DEFAULT_SETTINGS.items()}
    merged.update({r["key"]: r["value"] for r in rows})
    return merged


def set_setting(conn: sqlite3.Connection, key: str, value: Any) -> None:
    conn.execute(
        "INSERT INTO settings(key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )


def upsert(conn: sqlite3.Connection, table: str, rows: Iterable[dict], keys: list[str]) -> int:
    """
    行を追加、すでに同じキーの行があれば上書きします（UPSERT）。
    同じCSVを2回取り込んでも重複しないので安心です。
    """
    rows = list(rows)
    if not rows:
        return 0
    columns = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in columns)
    updates = ", ".join(f"{c} = excluded.{c}" for c in columns if c not in keys)
    sql = (
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) "
        f"ON CONFLICT({', '.join(keys)}) DO UPDATE SET {updates}"
        if updates
        else f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
    )
    conn.executemany(sql, [[r.get(c) for c in columns] for r in rows])
    return len(rows)
