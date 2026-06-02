@echo off
chcp 65001 >nul
cd /d "%~dp0"

set LOG=cnine_full_auto_log.txt

echo CNINE_FULL_AUTO_START
echo CNINE_FULL_AUTO_START > "%LOG%"
echo DATE=%date% %time% >> "%LOG%"
echo FOLDER=%cd% >> "%LOG%"

echo.
echo STEP_1_RUN_UPDATE_AND_PUSH
call run_update_and_push.bat
echo STEP_1_RETURN=%errorlevel%
echo STEP_1_RETURN=%errorlevel% >> "%LOG%"
if errorlevel 1 goto ERROR_END

echo.
echo STEP_2_MAKE_YGOSU_C9_DASHBOARD
call run_make_ygosu_c9_dashboard.bat
echo STEP_2_RETURN=%errorlevel%
echo STEP_2_RETURN=%errorlevel% >> "%LOG%"
if errorlevel 1 goto ERROR_END

echo.
echo STEP_3_AUTO_EDIT_YGOSU
python auto_edit_ygosu_c9_dashboard.py
echo STEP_3_RETURN=%errorlevel%
echo STEP_3_RETURN=%errorlevel% >> "%LOG%"
if errorlevel 1 goto ERROR_END

echo.
echo ALL_DONE
echo ALL_DONE >> "%LOG%"
exit /b 0

:ERROR_END
echo.
echo ERROR_STOPPED
echo ERROR_STOPPED >> "%LOG%"
echo Check %LOG%
exit /b 1
