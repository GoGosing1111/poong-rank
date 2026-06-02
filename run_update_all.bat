@echo off
chcp 65001 >nul
cd /d "%~dp0"

set ERR=0

echo CNINE_UPDATE_ALL_START
echo CURRENT_FOLDER=%cd%

echo CNINE_UPDATE_ALL_START > update_all_log.txt
echo CURRENT_FOLDER=%cd% >> update_all_log.txt
echo DATE=%date% %time% >> update_all_log.txt

echo.
echo STEP_1_UPDATE_LIVE_STATUS
if exist update_live_status.py (
  python update_live_status.py
  echo LIVE_EXIT=%errorlevel% >> update_all_log.txt
  if errorlevel 1 goto ERROR_END
) else (
  echo SKIP_LIVE_NO_FILE
  echo SKIP_LIVE_NO_FILE >> update_all_log.txt
)

echo.
echo STEP_2_UPDATE_CNINE_NOTICE
if exist update_cnine_notice.py (
  python update_cnine_notice.py
  echo NOTICE_EXIT=%errorlevel% >> update_all_log.txt
  if errorlevel 1 goto ERROR_END
) else (
  echo SKIP_NOTICE_NO_FILE
  echo SKIP_NOTICE_NO_FILE >> update_all_log.txt
)

echo.
echo STEP_3_UPDATE_RANK_TABLE
python update_rank_table.py
echo RANK_EXIT=%errorlevel% >> update_all_log.txt
if errorlevel 1 goto ERROR_END

echo.
echo STEP_4_UPDATE_SCHEDULE
if exist update_schedule_status.py (
  python update_schedule_status.py
  echo SCHEDULE_EXIT=%errorlevel% >> update_all_log.txt
  if errorlevel 1 goto ERROR_END
) else (
  echo SKIP_SCHEDULE_NO_FILE
  echo SKIP_SCHEDULE_NO_FILE >> update_all_log.txt
)

echo.
echo STEP_5_GIT_PUSH
git add live_status.json notice_status.json ranking_data.json schedule_status.json

git diff --cached --quiet
if errorlevel 1 (
  git commit -m "auto update"
  echo COMMIT_EXIT=%errorlevel% >> update_all_log.txt
  if errorlevel 1 goto ERROR_END

  git push origin main
  echo PUSH_EXIT=%errorlevel% >> update_all_log.txt
  if errorlevel 1 goto ERROR_END
) else (
  echo NO_CHANGES_TO_COMMIT
  echo NO_CHANGES_TO_COMMIT >> update_all_log.txt
)

echo.
echo ALL_DONE
echo ALL_DONE >> update_all_log.txt
echo.
echo Generated files:
echo - live_status.json
echo - notice_status.json
echo - ranking_data.json
echo - schedule_status.json

exit /b 0

:ERROR_END
set ERR=%errorlevel%
echo.
echo ERROR_STOPPED
echo ERRORLEVEL=%ERR%
echo ERROR_STOPPED >> update_all_log.txt
echo ERRORLEVEL=%ERR% >> update_all_log.txt
echo Check update_all_log.txt / ranking_debug.txt / schedule_debug_body.txt
exit /b %ERR%
