"""
Web画面の入口です（FastAPI という仕組みを使っています）。

起動方法:
    python3 -m uvicorn app.main:app --reload
    → ブラウザで http://127.0.0.1:8000 を開いてください

「どのURLにアクセスしたら、どの画面を出すか」をここでまとめて決めています。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from urllib.parse import quote

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.analytics import customers as customer_mod
from app.analytics import demand as demand_mod
from app.analytics.budget import all_forecasts, get_forecast, shift_month
from app.analytics.calendar_jp import day_label
from app.config import BASE_DIR
from app.db import get_settings, init_db, session, set_setting
from app.engine import ai as ai_mod
from app.engine.orchestrator import (
    daily_summary, generate, instruction_detail, list_instructions, mark_status,
    refresh_analytics,
)
from app.engine.rules import RULE_INFO
from app.exporter import instructions_csv, save_to_disk, targets_csv, to_bytes
from app.importer import COLUMN_ALIASES, import_file

app = FastAPI(title="ゴルフ場 営業指示エージェント")

WEB_DIR = BASE_DIR / "app" / "web"
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))

PRIORITY_LABELS = {1: "最優先", 2: "今週中", 3: "計画的", 4: "余力があれば"}
IMPORT_KINDS = {
    "courses": "コースマスタ",
    "customers": "顧客マスタ",
    "visits": "来場実績",
    "reservations": "予約データ",
    "budgets": "月次予算",
}


@app.on_event("startup")
def startup() -> None:
    init_db()


# ---------- テンプレートから使える小さな道具 ----------
def yen(value) -> str:
    """金額を「1,234万円」のような読みやすい形にします。"""
    try:
        value = int(value or 0)
    except (TypeError, ValueError):
        return "0円"
    if abs(value) >= 100_000_000:
        return f"{value / 100_000_000:.2f}億円"
    if abs(value) >= 10_000:
        return f"{value / 10_000:,.0f}万円"
    return f"{value:,}円"


templates.env.filters["yen"] = yen
templates.env.filters["comma"] = lambda v: f"{int(v or 0):,}"
templates.env.globals["PRIORITY_LABELS"] = PRIORITY_LABELS
templates.env.globals["RULE_INFO"] = RULE_INFO
templates.env.globals["RANK_LABELS"] = customer_mod.RANK_LABELS
templates.env.globals["STATUS_LABELS"] = customer_mod.STATUS_LABELS
templates.env.globals["GRADE_LABELS"] = demand_mod.GRADE_LABELS


def today_str() -> str:
    return date.today().isoformat()


def page(request: Request, name: str, status_code: int = 200, **context) -> HTMLResponse:
    context.setdefault("today", today_str())
    context.setdefault("nav", "")
    return templates.TemplateResponse(request, name, context, status_code=status_code)


# ---------------------------------------------------------------
# ダッシュボード
# ---------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    run_date = today_str()
    this_month = run_date[:7]
    next_month = shift_month(this_month, 1)
    as_of = date.today()

    with session() as conn:
        has_data = conn.execute("SELECT COUNT(*) FROM visits").fetchone()[0] > 0
        summary = daily_summary(conn, run_date)
        this_forecasts = all_forecasts(conn, this_month, as_of)
        next_forecasts = all_forecasts(conn, next_month, as_of)
        top = list_instructions(conn, run_date)[:8]
        weak_total = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(gap_players),0) FROM demand_days "
            "WHERE grade IN ('C','D') AND days_out <= 30"
        ).fetchone()
        ranks = customer_mod.rank_totals(conn)

    totals = {
        "target": sum(f["target_revenue"] for f in this_forecasts),
        "forecast": sum(f["forecast_revenue"] for f in this_forecasts),
    }
    totals["ratio"] = (totals["forecast"] / totals["target"] * 100) if totals["target"] else 0
    next_totals = {
        "target": sum(f["target_revenue"] for f in next_forecasts),
        "forecast": sum(f["forecast_revenue"] for f in next_forecasts),
    }
    next_totals["ratio"] = (
        next_totals["forecast"] / next_totals["target"] * 100 if next_totals["target"] else 0
    )

    return page(
        request, "dashboard.html", nav="dashboard", has_data=has_data,
        summary=summary, this_forecasts=this_forecasts, next_forecasts=next_forecasts,
        totals=totals, next_totals=next_totals, top=top,
        this_month=this_month, next_month=next_month,
        weak_days=weak_total[0], weak_gap=weak_total[1], ranks=ranks,
        today_label=day_label(as_of),
    )


@app.post("/generate")
def do_generate(use_ai: str = Form("on")):
    generate(as_of=date.today(), use_ai=(use_ai == "on"))
    return RedirectResponse("/instructions", status_code=303)


# ---------------------------------------------------------------
# 営業指示
# ---------------------------------------------------------------
@app.get("/instructions", response_class=HTMLResponse)
def instructions(request: Request, course: str = "", priority: str = "", rule: str = ""):
    run_date = today_str()
    with session() as conn:
        rows = list_instructions(conn, run_date)
        summary = daily_summary(conn, run_date)
        courses = [dict(r) for r in conn.execute(
            "SELECT course_id, name, short_name FROM courses ORDER BY course_id")]

    filtered = rows
    if course:
        filtered = [r for r in filtered if r["course_id"] == course]
    if priority:
        filtered = [r for r in filtered if str(r["priority"]) == priority]
    if rule:
        filtered = [r for r in filtered if r["rule_id"] == rule]

    grouped: dict[int, list[dict]] = {}
    for r in filtered:
        grouped.setdefault(r["priority"], []).append(r)

    rule_counts: dict[str, int] = {}
    for r in rows:
        rule_counts[r["rule_id"]] = rule_counts.get(r["rule_id"], 0) + 1

    # コースごとの件数をまとめます。8コースの全体像を一目で掴んでいただくためです。
    course_summary = []
    for c in courses:
        mine = [r for r in rows if r["course_id"] == c["course_id"]]
        course_summary.append({
            "course_id": c["course_id"],
            "name": c["name"],
            "count": len(mine),
            "urgent": sum(1 for r in mine if r["priority"] == 1),
            "targets": sum(r["target_count"] or 0 for r in mine),
            "revenue": sum(r["expected_revenue"] or 0 for r in mine),
            "done": sum(1 for r in mine if r["status"] == "done"),
        })

    return page(
        request, "instructions.html", nav="instructions", grouped=grouped,
        summary=summary, courses=courses, run_date=run_date,
        selected_course=course, selected_priority=priority, selected_rule=rule,
        total=len(rows), shown=len(filtered), rule_counts=rule_counts,
        course_summary=course_summary,
    )


@app.get("/instructions/{instruction_id}", response_class=HTMLResponse)
def instruction_page(request: Request, instruction_id: str):
    with session() as conn:
        data = instruction_detail(conn, instruction_id)
    if not data:
        return page(request, "not_found.html", status_code=404, nav="instructions")
    # 画面には先頭50名だけを表示します。全員分はCSVでお渡しします
    # （数千名を1ページに並べると、表示が非常に重くなるためです）。
    return page(request, "instruction_detail.html", nav="instructions", inst=data,
                targets=data["targets"][:50], target_total=len(data["targets"]))


@app.post("/instructions/{instruction_id}/status")
def update_status(instruction_id: str, status: str = Form(...)):
    with session() as conn:
        mark_status(conn, instruction_id, status)
    return RedirectResponse(f"/instructions/{instruction_id}", status_code=303)


@app.get("/instructions/{instruction_id}/targets.csv")
def download_targets(instruction_id: str):
    with session() as conn:
        filename, text = targets_csv(conn, instruction_id)
    save_to_disk(filename, text)
    return Response(
        content=to_bytes(text),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": _disposition(filename)},
    )


@app.get("/instructions.csv")
def download_instructions():
    run_date = today_str()
    with session() as conn:
        filename, text = instructions_csv(conn, run_date)
    save_to_disk(filename, text)
    return Response(
        content=to_bytes(text),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": _disposition(filename)},
    )


def _disposition(filename: str) -> str:
    """
    日本語のファイル名でも正しくダウンロードできるようにします。

    古いブラウザ向けに英数字の名前も併記し（filename=）、
    対応ブラウザには日本語の名前を渡します（filename*=）。
    これは RFC 5987 という決まりに沿った書き方です。
    """
    stem = filename.rsplit(".", 1)[0]
    ascii_name = "".join(
        ch if ch.isascii() and (ch.isalnum() or ch in "-_") else "" for ch in stem
    ) or "download"
    encoded = quote(filename, safe="")
    return f"attachment; filename=\"{ascii_name}.csv\"; filename*=UTF-8\'\'{encoded}"


# ---------------------------------------------------------------
# コース詳細
# ---------------------------------------------------------------
@app.get("/courses/{course_id}", response_class=HTMLResponse)
def course_page(request: Request, course_id: str):
    as_of = date.today()
    this_month = as_of.strftime("%Y-%m")
    next_month = shift_month(this_month, 1)
    with session() as conn:
        course = conn.execute(
            "SELECT * FROM courses WHERE course_id = ?", (course_id,)).fetchone()
        if not course:
            return page(request, "not_found.html", status_code=404)
        course = dict(course)
        calendar = demand_mod.calendar_days(conn, course_id)
        this_f = get_forecast(conn, course_id, this_month, as_of)
        next_f = get_forecast(conn, course_id, next_month, as_of)
        instructions_here = list_instructions(conn, today_str(), course_id)
        channel_mix = [dict(r) for r in conn.execute(
            "SELECT channel, SUM(players) AS players, SUM(revenue) AS revenue "
            "FROM visits WHERE course_id = ? AND play_date >= ? "
            "GROUP BY channel ORDER BY revenue DESC",
            (course_id, (as_of - timedelta(days=365)).isoformat()),
        )]

    weeks: list[list[dict | None]] = []
    if calendar:
        first = datetime.strptime(calendar[0]["play_date"], "%Y-%m-%d").date()
        week: list[dict | None] = [None] * first.weekday()
        for day in calendar:
            week.append(day)
            if len(week) == 7:
                weeks.append(week)
                week = []
        if week:
            weeks.append(week + [None] * (7 - len(week)))

    total_revenue = sum(c["revenue"] or 0 for c in channel_mix) or 1
    for c in channel_mix:
        c["share"] = round((c["revenue"] or 0) / total_revenue * 100, 1)

    return page(request, "course.html", nav="dashboard", course=course, weeks=weeks,
                this_f=this_f, next_f=next_f, this_month=this_month, next_month=next_month,
                instructions=instructions_here, channel_mix=channel_mix)


# ---------------------------------------------------------------
# 顧客分析
# ---------------------------------------------------------------
@app.get("/customers", response_class=HTMLResponse)
def customers_page(request: Request, rank: str = "", status: str = "", q: str = ""):
    with session() as conn:
        ranks = customer_mod.rank_totals(conn)
        segments = customer_mod.segment_summary(conn)
        cycle_rows = [dict(r) for r in conn.execute(
            "SELECT CASE WHEN cycle_days <= 30 THEN 'a:30日以内' "
            "            WHEN cycle_days <= 60 THEN 'b:31〜60日' "
            "            WHEN cycle_days <= 90 THEN 'c:61〜90日' "
            "            WHEN cycle_days <= 180 THEN 'd:91〜180日' "
            "            ELSE 'e:181日以上' END AS bucket, "
            "       COUNT(*) AS cnt, AVG(avg_spend) AS spend "
            "FROM customer_profiles WHERE total_visits >= 2 AND cycle_is_estimated = 0 "
            "GROUP BY bucket ORDER BY bucket")]
        upcoming = [dict(r) for r in conn.execute(
            "SELECT approach_date, COUNT(*) AS cnt FROM customer_profiles "
            "WHERE approach_date >= ? AND approach_date <= ? "
            "GROUP BY approach_date ORDER BY approach_date",
            (today_str(), (date.today() + timedelta(days=14)).isoformat()))]

        where, params = ["1=1"], []
        if rank:
            where.append("p.rank_code = ?")
            params.append(rank)
        if status:
            where.append("p.status_code = ?")
            params.append(status)
        if q:
            where.append("(c.name LIKE ? OR c.customer_id LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])
        people = [dict(r) for r in conn.execute(
            "SELECT p.*, c.name, c.email, c.phone, c.line_id FROM customer_profiles p "
            "JOIN customers c USING(customer_id) WHERE " + " AND ".join(where) +
            " ORDER BY p.total_revenue DESC LIMIT 100", params)]
        matched = conn.execute(
            "SELECT COUNT(*) FROM customer_profiles p JOIN customers c USING(customer_id) "
            "WHERE " + " AND ".join(where), params).fetchone()[0]

    return page(request, "customers.html", nav="customers", ranks=ranks, segments=segments,
                cycle_rows=cycle_rows, upcoming=upcoming, people=people, matched=matched,
                selected_rank=rank, selected_status=status, q=q)


# ---------------------------------------------------------------
# データ取り込み
# ---------------------------------------------------------------
@app.get("/import", response_class=HTMLResponse)
def import_page(request: Request, done: str = ""):
    with session() as conn:
        logs = [dict(r) for r in conn.execute(
            "SELECT * FROM import_log ORDER BY id DESC LIMIT 15")]
        counts = {
            "courses": conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0],
            "customers": conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0],
            "visits": conn.execute("SELECT COUNT(*) FROM visits").fetchone()[0],
            "reservations": conn.execute("SELECT COUNT(*) FROM reservations").fetchone()[0],
            "budgets": conn.execute("SELECT COUNT(*) FROM budgets").fetchone()[0],
        }
    return page(request, "import.html", nav="import", logs=logs, counts=counts,
                kinds=IMPORT_KINDS, aliases=COLUMN_ALIASES, result=None, done=done)


@app.post("/import", response_class=HTMLResponse)
async def do_import(request: Request, kind: str = Form(...), file: UploadFile = File(...)):
    content = await file.read()
    result = import_file(kind, content, file.filename or "uploaded.csv")
    if result.ok:
        with session() as conn:
            refresh_analytics(conn, date.today())
    with session() as conn:
        logs = [dict(r) for r in conn.execute(
            "SELECT * FROM import_log ORDER BY id DESC LIMIT 15")]
        counts = {
            "courses": conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0],
            "customers": conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0],
            "visits": conn.execute("SELECT COUNT(*) FROM visits").fetchone()[0],
            "reservations": conn.execute("SELECT COUNT(*) FROM reservations").fetchone()[0],
            "budgets": conn.execute("SELECT COUNT(*) FROM budgets").fetchone()[0],
        }
    return page(request, "import.html", nav="import", logs=logs, counts=counts,
                kinds=IMPORT_KINDS, aliases=COLUMN_ALIASES, result=result, done="")


# ---------------------------------------------------------------
# 設定
# ---------------------------------------------------------------
@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, saved: str = ""):
    with session() as conn:
        values = get_settings(conn)
    return page(request, "settings.html", nav="settings", values=values,
                ai_status=ai_mod.status_message(), saved=saved,
                groups=SETTING_GROUPS)


@app.post("/settings")
async def save_settings(request: Request):
    form = await request.form()
    with session() as conn:
        for key in form:
            if key in {k for group in SETTING_GROUPS for k, _, _ in group["items"]}:
                set_setting(conn, key, form[key])
    return RedirectResponse("/settings?saved=1", status_code=303)


SETTING_GROUPS = [
    {
        "title": "顧客ランクの区切り（通算来場回数）",
        "note": "何回お越しいただいた方をどのランクに入れるかの設定です。",
        "items": [
            ("rank_f3_min", "F3（育成層）の下限回数", "この回数以上でF3になります"),
            ("rank_f4_min", "F4（常連）の下限回数", "この回数以上でF4になります"),
            ("rank_f5_min", "F5（ロイヤル）の下限回数", "この回数以上でF5になります"),
        ],
    },
    {
        "title": "離反の判定",
        "note": "「その方の来場周期の何倍空いたら離れかけと見るか」を決めます。",
        "items": [
            ("status_active_ratio", "順調とみなす倍率", "例: 1.2 なら周期の1.2倍まで順調"),
            ("status_at_risk_ratio", "離反予備軍とみなす倍率", "例: 2.0 なら周期の2倍まで"),
            ("status_dormant_days", "離脱とみなす日数", "この日数を超えたら離脱扱い"),
            ("first_timer_active_days", "初回客が「熱い」期間（日）", "1回のみの方の判定に使います"),
            ("first_timer_risk_days", "初回客の引き戻し期限（日）", "これを超えると休眠扱い"),
        ],
    },
    {
        "title": "アプローチのタイミング",
        "items": [
            ("approach_window_days", "推奨日の前後何日を対象にするか", "3なら前後3日を今日の対象に"),
            ("default_cycle_days", "来場周期の既定値（日）", "計算できない方に使う値"),
            ("default_lead_days", "予約リードタイムの既定値（日）", "予約はプレーの何日前に入るか"),
        ],
    },
    {
        "title": "弱日・強日の判定",
        "note": "過去の同時点と比べた予約の入り具合（ペース比）で判定します。",
        "items": [
            ("demand_horizon_days", "何日先まで見るか", "既定60日"),
            ("grade_s_pace", "強日Sとするペース比", "例: 1.10 で例年比+10%以上"),
            ("grade_c_pace", "弱日Cとするペース比", "例: 0.90 で例年比-10%以下"),
            ("grade_d_pace", "最弱日Dとするペース比", "例: 0.75 で例年比-25%以下"),
            ("grade_s_fill", "無条件で強日とする充足率", "例: 0.85 で85%以上埋まっていれば強日"),
            ("urgent_days", "緊急扱いにする日数", "この日数以内の最弱日は緊急指示に"),
        ],
    },
    {
        "title": "お客様への配慮",
        "note": "送りすぎを防ぐための設定です。長い目で見た開封率を守ります。",
        "items": [
            ("contact_cooldown_days", "同じ方への再連絡を空ける日数", "既定14日"),
            ("max_targets_per_instruction", "1指示あたりの上限人数", "既定500名"),
        ],
    },
    {
        "title": "予算対策",
        "items": [
            ("next_month_lead_days", "翌月対策を強調し始める日数", "月末の何日前から「今月中に着手」と表示するか"),
        ],
    },
]
