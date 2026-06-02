@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo MAKE_YGOSU_C9_DASHBOARD_START
python make_ygosu_c9_dashboard.py
if errorlevel 1 exit /b 1

echo.
echo GENERATED_FILES:
echo - ygosu_c9_dashboard_full.html
echo - ygosu_paste.txt

exit /b 0