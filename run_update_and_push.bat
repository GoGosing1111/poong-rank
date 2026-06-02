@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo CNINE_UPDATE_AND_PUSH_START
echo CURRENT_FOLDER=%cd%

echo CNINE_UPDATE_AND_PUSH_START > update_push_log.txt
echo DATE=%date% %time% >> update_push_log.txt

call run_update_all.bat
echo RETURNED_FROM_RUN_UPDATE_ALL ERRORLEVEL=%errorlevel%
echo RETURNED_FROM_RUN_UPDATE_ALL ERRORLEVEL=%errorlevel% >> update_push_log.txt
if errorlevel 1 goto ERROR_END

echo.
echo ALL_DONE_PUSH
echo ALL_DONE_PUSH >> update_push_log.txt
exit /b 0

:ERROR_END
echo.
echo ERROR_STOPPED_PUSH
echo ERROR_STOPPED_PUSH >> update_push_log.txt
echo Check update_push_log.txt
exit /b 1