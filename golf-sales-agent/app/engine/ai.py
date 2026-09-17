"""
AI（Claude）で案内文を作る部分です。

【設計方針】
数字の計算（誰が対象か、何人必要か）は、すべてプログラム側で確定させます。
AIには「その結果をどう伝えるか」＝文章だけを任せます。
こうすることで、
  ・毎日同じ条件なら同じ対象者が出る（結果がぶれない）
  ・AIが数字を作り話すことがない
という、業務で使ううえで大切な安定性が保てます。

APIキーが未設定の場合は、テンプレート文面がそのまま使われます。
つまり、キーが無くてもシステムは完全に動きます。
"""

from __future__ import annotations

from app.config import AI_ENABLED, AI_MODEL, ANTHROPIC_API_KEY

SYSTEM_PROMPT = """あなたは日本のゴルフ場の営業担当者です。
既存のお客様へお送りする案内文を作成します。

必ず守ること:
- 丁寧語で、品位のある落ち着いた日本語。過度な煽りや絵文字の多用はしない
- 誇大な表現、断定的な効果の約束、根拠のない「限定」表現は使わない
- お客様のお名前は {お名前} というプレースホルダーのままにする（差し込みで置換するため）
- 予約URLは（URL）と書く。勝手にURLを作らない
- 与えられた事実（対象日、特典内容）以外の数字・事実を足さない
- 出力は案内文の本文のみ。前置きや解説は書かない
"""

CHANNEL_GUIDE = {
    "mail": "メール本文。件名は含めず本文のみ。250〜400文字程度。",
    "line": "LINEメッセージ。150文字以内。読みやすく改行する。絵文字は多くて1つ。",
    "sms": "SMS。全角70文字以内に必ず収める。用件と（URL）のみ。",
    "dm": "ハガキDMの文面。180〜260文字程度。手紙らしい落ち着いた文体。",
    "tel": "電話で話す際のトークスクリプト。話す順番を箇条書きで5項目以内。",
}


def is_available() -> bool:
    """AIが使える状態かどうか。"""
    if not AI_ENABLED:
        return False
    try:
        import anthropic  # noqa: F401
        return True
    except ImportError:
        return False


def status_message() -> str:
    """設定画面に出す、AIの状態説明。"""
    if not ANTHROPIC_API_KEY:
        return "未設定（テンプレート文面で動作中）。.env に ANTHROPIC_API_KEY を設定すると有効になります。"
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return "APIキーはありますが anthropic ライブラリが未インストールです（pip install anthropic）。"
    return f"有効（モデル: {AI_MODEL}）"


def refine_message(
    *, instruction_title: str, reason: str, action: str, channel: str,
    course_name: str, target_summary: str, base_subject: str, base_body: str,
) -> tuple[str, str, bool]:
    """
    テンプレート文面をAIに整えてもらいます。
    戻り値は (件名, 本文, AIを使ったかどうか) です。
    失敗した場合はテンプレートをそのまま返すので、業務は止まりません。
    """
    if channel == "ops" or not is_available():
        return base_subject, base_body, False

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, timeout=30.0)
        guide = CHANNEL_GUIDE.get(channel, "案内文")
        prompt = f"""次の営業施策に使う案内文を作成してください。

【ゴルフ場】{course_name}
【施策】{instruction_title}
【この施策を行う理由】{reason}
【営業担当への指示】{action}
【送付対象】{target_summary}
【送付手段】{guide}

【たたき台（この趣旨を保ったまま、より自然で心に届く文章にしてください）】
{base_body}

案内文の本文のみを出力してください。"""

        response = client.messages.create(
            model=AI_MODEL,
            max_tokens=1200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        body = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ).strip()
        if not body:
            return base_subject, base_body, False

        subject = base_subject
        if channel == "mail":
            subject = _make_subject(client, course_name, instruction_title, body) or base_subject
        return subject, body, True

    except Exception:
        # 通信エラーや残高不足でも業務が止まらないよう、テンプレートに戻します
        return base_subject, base_body, False


def _make_subject(client, course_name: str, title: str, body: str) -> str | None:
    """メールの件名だけを作ります（開封率を左右する一番大事な部分です）。"""
    try:
        response = client.messages.create(
            model=AI_MODEL,
            max_tokens=120,
            system="日本のゴルフ場のメール件名を作ります。全角30文字以内、煽らず、"
                   "誰からの何の連絡か一目で分かるように。件名のみ出力。",
            messages=[{
                "role": "user",
                "content": f"ゴルフ場名: {course_name}\n施策: {title}\n本文:\n{body[:600]}",
            }],
        )
        subject = "".join(
            b.text for b in response.content if getattr(b, "type", "") == "text"
        ).strip().strip("「」\"'")
        return subject or None
    except Exception:
        return None
