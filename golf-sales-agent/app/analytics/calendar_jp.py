"""
日本の祝日カレンダー（外部ライブラリなしで判定します）。

ゴルフ場では平日と土日祝で単価も需要もまったく違うため、
「この日は土日祝か」を正しく判定することがとても大切です。
"""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

WEEKDAY_NAMES = ["月", "火", "水", "木", "金", "土", "日"]

# 毎年日付が決まっている祝日
_FIXED = {
    (1, 1): "元日",
    (2, 11): "建国記念の日",
    (2, 23): "天皇誕生日",
    (4, 29): "昭和の日",
    (5, 3): "憲法記念日",
    (5, 4): "みどりの日",
    (5, 5): "こどもの日",
    (8, 11): "山の日",
    (11, 3): "文化の日",
    (11, 23): "勤労感謝の日",
}

# 「◯月の第◯月曜日」が祝日になるもの（ハッピーマンデー）
_HAPPY_MONDAY = {
    (1, 2): "成人の日",
    (7, 3): "海の日",
    (9, 3): "敬老の日",
    (10, 2): "スポーツの日",
}


def _nth_monday(year: int, month: int, nth: int) -> date:
    d = date(year, month, 1)
    d += timedelta(days=(7 - d.weekday()) % 7)  # その月の最初の月曜
    return d + timedelta(days=7 * (nth - 1))


def _vernal_equinox(year: int) -> date:
    """春分の日（天文学的な近似式。1900〜2099年で実用上一致します）。"""
    day = int(20.8431 + 0.242194 * (year - 1980) - (year - 1980) // 4)
    return date(year, 3, day)


def _autumnal_equinox(year: int) -> date:
    """秋分の日（同上）。"""
    day = int(23.2488 + 0.242194 * (year - 1980) - (year - 1980) // 4)
    return date(year, 9, day)


@lru_cache(maxsize=32)
def holidays_of_year(year: int) -> dict[date, str]:
    """その年の祝日（振替休日を含む）を {日付: 名前} で返します。"""
    result: dict[date, str] = {}
    for (month, day), name in _FIXED.items():
        try:
            result[date(year, month, day)] = name
        except ValueError:
            pass
    for (month, nth), name in _HAPPY_MONDAY.items():
        result[_nth_monday(year, month, nth)] = name
    result[_vernal_equinox(year)] = "春分の日"
    result[_autumnal_equinox(year)] = "秋分の日"

    # 振替休日：祝日が日曜と重なったら、次の平日が休みになります
    for d in sorted(list(result.keys())):
        if d.weekday() == 6:
            nxt = d + timedelta(days=1)
            while nxt in result:
                nxt += timedelta(days=1)
            result[nxt] = "振替休日"
    return result


def holiday_name(d: date) -> str | None:
    return holidays_of_year(d.year).get(d)


def is_holiday(d: date) -> bool:
    return d in holidays_of_year(d.year)


def is_weekend(d: date) -> bool:
    """土日または祝日なら True（ゴルフ場でいう「土日祝」）。"""
    return d.weekday() >= 5 or is_holiday(d)


def day_label(d: date) -> str:
    """「10/12(日・祝)」のような表示用の文字列を作ります。"""
    name = holiday_name(d)
    mark = WEEKDAY_NAMES[d.weekday()]
    if name:
        return f"{d.month}/{d.day}({mark}・祝)"
    return f"{d.month}/{d.day}({mark})"
