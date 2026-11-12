@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在建置【全台商辦大樓地圖 - 商辦樓內企業名錄】...
python build_commercial_html.py
if errorlevel 1 (
  pause
  exit /b 1
)
python serve_local.py
