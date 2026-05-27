@echo off
cd /d "%~dp0"

echo C9 LIVE STATUS UPDATE V3 - BJAPI
echo.

python --version
echo.

python update_live_status.py

echo.
echo DONE
pause
