CNINE 대시보드 공지 자동화 통합본

사용 순서
1. 이 폴더를 GitHub poong-rank 저장소 폴더에 덮어쓰기
2. cnine.kr/board/an 이 회원 전용이면 cnine_cookies.txt를 같은 폴더에 생성
3. run_update_all.bat 실행
4. 생성된 live_status.json / notice_status.json / index.html을 GitHub Commit/Push

파일 설명
- update_live_status.py : 기존 LIVE 상태 수집
- update_cnine_notice.py : https://www.cnine.kr/board/an 공지 수집
- notice_status.json : 대시보드가 읽는 공지 데이터
- notice_debug.html : 공지 수집 실패 시 실제 받아온 HTML
- notice_debug.txt : 수집 로그

주의
- 로그인 쿠키가 없거나 만료되면 공지 수집이 실패할 수 있음
- cnine 사이트 HTML 구조가 바뀌면 notice_debug.html을 보고 파서만 조정하면 됨
