@echo off
rem ===================================================
rem   ゴルフ場 営業指示エージェント  起動スクリプト（Windows）
rem   使い方：このファイルをダブルクリックしてください
rem ===================================================
chcp 65001 >nul
cd /d "%~dp0"

rem --- Pythonの呼び名は環境によって python / py / python3 と異なるため、順に探します ---
set "PY="
python --version >nul 2>&1 && set "PY=python"
if not defined PY py --version >nul 2>&1 && set "PY=py"
if not defined PY python3 --version >nul 2>&1 && set "PY=python3"

if not defined PY (
  echo.
  echo [エラー] Python が見つかりませんでした。
  echo   https://www.python.org/downloads/ からインストールしてください。
  echo   インストール時に「Add Python to PATH」に必ずチェックを入れてください。
  echo.
  pause
  exit /b 1
)
echo ■ 使用する Python: %PY%
%PY% --version

echo.
echo ■ 必要なライブラリを確認しています...
%PY% -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo.
  echo [エラー] ライブラリのインストールに失敗しました。
  echo   インターネット接続をご確認のうえ、もう一度お試しください。
  echo.
  pause
  exit /b 1
)

echo ■ データベースを準備しています...
%PY% -m app.cli init
if errorlevel 1 ( pause & exit /b 1 )

echo ■ 本日の営業指示を作成しています...
%PY% -m app.cli run
rem  データがまだ無い場合はここで指示が0件になりますが、問題ありません。
rem  起動後の画面「データ取込」から取り込んでください。

echo.
echo ======================================================
echo   ブラウザで次のアドレスを開いてください
echo       http://127.0.0.1:8000
echo   終了するときは、この画面で Ctrl + C を押してください
echo ======================================================
echo.
%PY% -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
