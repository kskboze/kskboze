"""
コマンドラインから操作するための入口です。

  python3 -m app.cli init      … データベースを作る
  python3 -m app.cli run       … 本日の営業指示を作る
  python3 -m app.cli show      … 本日の指示を画面に表示する
  python3 -m app.cli import 種類 ファイル … CSVを取り込む

毎朝自動で動かしたい場合は、`run` をタスクスケジューラ（Windows）や
cron（Mac/Linux）に登録してください。README に手順を書いてあります。
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

from app.db import init_db, session
from app.engine.orchestrator import daily_summary, generate, list_instructions

PRIORITY_MARK = {1: "★最優先", 2: "◎今週中", 3: "○計画的", 4: "・余力"}


def cmd_init() -> None:
    init_db()
    print("データベースを準備しました。")


def cmd_run(args: list[str]) -> None:
    as_of = date.today()
    use_ai = "--no-ai" not in args
    for a in args:
        if a.startswith("--date="):
            as_of = datetime.strptime(a.split("=", 1)[1], "%Y-%m-%d").date()

    init_db()
    print(f"{as_of} の営業指示を作成しています…")
    result = generate(as_of=as_of, use_ai=use_ai)
    print(f"  顧客分析     : {result['profiles']:,} 名")
    print(f"  日別需要判定 : {result['demand_days']:,} 日分")
    print(f"  予算予測     : {result['forecasts']} 件")
    print(f"  営業指示     : {result['instructions']} 件（対象 {result['targets']:,} 名）")
    if result["ai_used"]:
        print(f"  AI文面生成   : {result['ai_used']} 件")
    print("完了しました。 python3 -m app.cli show で内容を確認できます。")


def cmd_show(args: list[str]) -> None:
    run_date = date.today().isoformat()
    for a in args:
        if a.startswith("--date="):
            run_date = a.split("=", 1)[1]
    with session() as conn:
        summary = daily_summary(conn, run_date)
        rows = list_instructions(conn, run_date)

    print("=" * 78)
    print(f" {run_date} の営業指示   {summary['count']}件 / 対象 {summary['targets']:,}名 "
          f"/ 見込み {summary['expected_revenue']:,}円")
    print("=" * 78)
    for r in rows:
        mark = PRIORITY_MARK.get(r["priority"], "")
        print(f"\n[{mark}] {r['title']}")
        print(f"  手段: {r['channel_label']}  対象: {r['target_count']}名  "
              f"見込み: {r['expected_revenue']:,}円  期限: {r['deadline']}")
        print(f"  理由: {r['reason'][:110]}")
        print(f"  行動: {r['action'][:110]}")
    print()


def cmd_import(args: list[str]) -> None:
    if len(args) < 2:
        print("使い方: python3 -m app.cli import <種類> <ファイル>")
        print("  種類: courses / customers / visits / reservations / budgets")
        return
    kind, path = args[0], Path(args[1])
    if not path.exists():
        print(f"ファイルが見つかりません: {path}")
        return
    from app.importer import import_file

    init_db()
    result = import_file(kind, path.read_bytes(), path.name)
    print(result.summary())
    for e in result.errors:
        print("  ! " + e)
    if result.unmapped_columns:
        print("  （読み取らなかった列: " + "、".join(result.unmapped_columns) + "）")


def main() -> None:
    args = sys.argv[1:]
    command = args[0] if args else "help"
    rest = args[1:]

    if command == "init":
        cmd_init()
    elif command == "run":
        cmd_run(rest)
    elif command == "show":
        cmd_show(rest)
    elif command == "import":
        cmd_import(rest)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
