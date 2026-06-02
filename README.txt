CNINE Dashboard Direct API v4

핵심 변경:
- ranking.html -> ranking_data.json 변환 방식 폐기
- update_rank_table.py가 poong.today chart API를 직접 조회
- cnine_members.json의 part/name/match/soop_id 기준 매칭
- 월간 API 0건이면 자동화 중단해서 0 데이터 덮어쓰기 방지

사용법:
1. 이 압축 안 파일들을 GitHub 저장소 poong-rank 폴더 최상단에 덮어쓰기
2. 기존 cnine_members.json은 그대로 유지
3. run_update_all.bat 실행
4. ranking_data.json 생성 확인
5. 문제 없으면 run_update_and_push.bat를 작업 스케줄러에 연결

생성 파일:
- ranking_data.json
- ranking_debug.txt
- api_raw/month.json
- api_raw/day.json
- api_raw/today.json
- schedule_status.json

주의:
- update_schedule_status.py는 Playwright 필요
  pip install playwright beautifulsoup4
  python -m playwright install chromium
- update_cnine_notice.py는 기존 파일이 있으면 실행하고 없으면 스킵
- update_live_status.py도 기존 파일이 있으면 실행하고 없으면 스킵
