"""
アプリ全体の設定をまとめた場所です。

「しきい値」（例: 何日来ていなければ離反とみなすか）は、ここに集めてあります。
運用しながら数字を調整したくなったら、まずこのファイルを見てください。
画面の「設定」ページから変更した値は、データベースに保存され、
ここの初期値より優先されます。
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------
# 1. ファイルの置き場所
# ---------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent   # golf-sales-agent/ のこと
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
EXPORT_DIR = DATA_DIR / "exports"
SAMPLE_DIR = DATA_DIR / "sample"

for _d in (DATA_DIR, UPLOAD_DIR, EXPORT_DIR, SAMPLE_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def _load_dotenv() -> None:
    """.env ファイルがあれば読み込みます（無くてもエラーにしません）。"""
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

DATABASE_PATH = Path(os.environ.get("DATABASE_PATH") or (DATA_DIR / "golf.db"))
if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = BASE_DIR / DATABASE_PATH

# ---------------------------------------------------------------
# 2. AI（Claude）の設定 — キーが無い場合はテンプレート文面で動きます
# ---------------------------------------------------------------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
AI_MODEL = os.environ.get("AI_MODEL", "claude-sonnet-5").strip() or "claude-sonnet-5"
AI_ENABLED = bool(ANTHROPIC_API_KEY)

# ---------------------------------------------------------------
# 3. 営業ロジックのしきい値（初期値）
# ---------------------------------------------------------------
DEFAULT_SETTINGS: dict[str, float | int | str] = {
    # --- 顧客ランク：通算来場回数で分けます ---
    "rank_f2_min": 2,          # 2回来場でF2
    "rank_f3_min": 3,          # 3〜5回でF3（育成層）
    "rank_f4_min": 6,          # 6〜11回でF4（常連）
    "rank_f5_min": 12,         # 12回以上でF5（ロイヤル）

    # --- 顧客ステータス：最終来場からの日数を「来場周期」の何倍で見るか ---
    "status_active_ratio": 1.2,    # 周期の1.2倍以内なら「順調」
    "status_at_risk_ratio": 2.0,   # 2.0倍以内なら「離反予備軍」
    "status_dormant_days": 540,    # 540日を超えたら「離脱」
    # --- 1回だけご来場の方は「周期」が無いので、固定日数で判定します ---
    "first_timer_active_days": 90,   # 初回から90日以内 → まだ2回目を狙える
    "first_timer_risk_days": 210,    # 210日以内 → 引き戻しの余地あり

    # --- 来場周期が計算できない人（1回だけの人）に使う既定値 ---
    "default_cycle_days": 90,
    # --- 予約リードタイム（予約日〜プレー日）の既定値 ---
    "default_lead_days": 14,

    # --- アプローチ日の許容幅：推奨日の前後何日までを「今日の対象」にするか ---
    "approach_window_days": 3,

    # --- 需要判定（弱日/強日）---
    "demand_horizon_days": 60,     # 何日先まで見るか
    "grade_s_pace": 1.10,          # 過去同時点比 +10%以上 → 強日S
    "grade_a_pace": 1.00,
    "grade_c_pace": 0.90,          # -10%を下回ると 弱日C
    "grade_d_pace": 0.75,          # -25%を下回ると 最弱日D
    "grade_s_fill": 0.85,          # 充足率85%以上は無条件で強日
    "urgent_days": 14,             # 14日以内の最弱日は「緊急」扱い

    # --- 接触疲労の管理 ---
    "contact_cooldown_days": 14,   # 同じお客様への再アプローチは14日空ける
    "max_targets_per_instruction": 500,  # 1指示あたりの上限人数

    # --- 予算 ---
    "budget_alert_ratio": 1.00,    # 予測達成率がこれ未満なら対策指示を出す
    "next_month_lead_days": 10,    # 月末何日前から翌月の予算対策を始めるか
}


def as_float(value, fallback: float) -> float:
    """設定値を安全に小数へ変換します。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def as_int(value, fallback: int) -> int:
    """設定値を安全に整数へ変換します。"""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return fallback
