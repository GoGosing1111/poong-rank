@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo CNINE_UPDATE_ALL_START
echo CURRENT_FOLDER=%cd%

echo CNINE_UPDATE_ALL_START > update_all_log.txt
echo CURRENT_FOLDER=%cd% >> update_all_log.txt
echo DATE=%date% %time% >> update_all_log.txt

echo.
echo STEP_1_UPDATE_LIVE_STATUS
python update_live_status.py
echo LIVE_EXIT=%errorlevel% >> update_all_log.txt
if errorlevel 1 goto ERROR_END

echo.
echo STEP_2_UPDATE_CNINE_NOTICE
python update_cnine_notice.py
echo NOTICE_EXIT=%errorlevel% >> update_all_log.txt
if errorlevel 1 goto ERROR_END

echo.
echo ALL_DONE
echo ALL_DONE >> update_all_log.txt
echo.
echo GitHub upload files:
echo - index.html
echo - live_status.json
echo - notice_status.json
echo - notice_history.json
echo.
pause
exit /b 0

:ERROR_END
echo.
echo ERROR_STOPPED
echo ERROR_STOPPED >> update_all_log.txt
echo Check update_all_log.txt
echo Check notice_debug.txt / live_status_debug.txt
echo.
pause
exit /b 1
