@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo CNINE_SCHEDULER_AUTO_START > cnine_full_auto_log.txt
echo DATE=%date% %time% >> cnine_full_auto_log.txt

call run_update_and_push_fixed.bat >> cnine_full_auto_log.txt 2>&1
if errorlevel 1 exit /b 1

call run_make_ygosu_c9_dashboard.bat >> cnine_full_auto_log.txt 2>&1
if errorlevel 1 exit /b 1

python auto_edit_ygosu_c9_dashboard.py >> cnine_full_auto_log.txt 2>&1
if errorlevel 1 exit /b 1

echo ALL_DONE >> cnine_full_auto_log.txt
exit /b 0
