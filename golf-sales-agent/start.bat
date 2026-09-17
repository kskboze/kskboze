@echo off
rem ===================================================
rem   ゴルフ場 営業指示エージェント  起動スクリプト（Windows）
rem   使い方：このファイルをダブルクリックしてください
rem ===================================================
cd /d "%~dp0"

echo ■ 必要なライブラリを確認しています...
python -m pip install -q -r requirements.txt

echo ■ データベースを準備しています...
python -m app.cli init

echo ■ 本日の営業指示を作成しています...
python -m app.cli run

echo.
echo ======================================================
echo   ブラウザで次のアドレスを開いてください
echo       http://127.0.0.1:8000
echo   終了するときは、この画面で Ctrl + C を押してください
echo ======================================================
echo.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
