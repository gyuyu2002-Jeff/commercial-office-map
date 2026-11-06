@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在建置【全台商辦＆企業地圖 - 官方營業登記資料】...
python build_commercial_html.py
if errorlevel 1 (
  pause
  exit /b 1
)
python serve_local.py
