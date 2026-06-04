@echo off
cd /d "%~dp0"
echo MAKE_BEOBBANG_DASHBOARD_START
python make_beobbang_dashboard.py
echo.
echo DONE
pause
