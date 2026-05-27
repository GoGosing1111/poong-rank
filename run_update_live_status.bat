@echo off
cd /d "%~dp0"

echo C9_DASHBOARD_LIVE_UPDATE
echo.

python update_live_status.py

echo.
echo DONE
pause
