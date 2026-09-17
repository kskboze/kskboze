@echo off
rem ===================================================
rem   サンプルデータを作成する（動作確認用）
rem   使い方：このファイルをダブルクリックしてください
rem   ※ 実データを入れる前に、まずこれで動きをご確認ください
rem ===================================================
chcp 65001 >nul
cd /d "%~dp0"

set "PY="
python --version >nul 2>&1 && set "PY=python"
if not defined PY py --version >nul 2>&1 && set "PY=py"
if not defined PY python3 --version >nul 2>&1 && set "PY=python3"

if not defined PY (
  echo [エラー] Python が見つかりませんでした。
  pause
  exit /b 1
)

echo ■ 必要なライブラリを確認しています...
%PY% -m pip install -q -r requirements.txt

echo ■ サンプルデータを作成しています...
%PY% scripts\generate_sample_data.py
if errorlevel 1 ( pause & exit /b 1 )

echo ■ 本日の営業指示を作成しています...
%PY% -m app.cli run

echo.
echo 完了しました。次は start.bat をダブルクリックしてください。
echo.
pause
