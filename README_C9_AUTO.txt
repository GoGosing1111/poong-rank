CNINE 와이고수 자동화 패키지

덮어쓰기/추가 파일:
- auto_edit_ygosu_c9_dashboard.py
- make_ygosu_c9_dashboard.py
- run_make_ygosu_c9_dashboard.bat
- run_cnine_full_auto.bat
- run_cnine_full_auto_scheduler.bat

실행 순서:
1) GitHub 폴더 최상단에 전부 복사
2) 수동 테스트: run_cnine_full_auto.bat
3) 작업 스케줄러에는 run_cnine_full_auto_scheduler.bat 등록

자동 흐름:
run_update_and_push_fixed.bat
-> GitHub JSON 최신화
-> run_make_ygosu_c9_dashboard.bat
-> ygosu_paste.txt 생성
-> auto_edit_ygosu_c9_dashboard.py
-> https://ygosu.com/board/soop/1648434 글 자동 수정
