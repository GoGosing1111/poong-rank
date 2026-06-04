버빵동 베이커리 테마 현황판 사용법

1) 이 폴더 전체를 아래 경로에 넣기
   C:\Users\User\Downloads\upload\poong-rank\beobbang

2) GitHub 업로드
   cd /d C:\Users\User\Downloads\upload\poong-rank
   git add beobbang
   git commit -m "update beobbang bakery dashboard"
   git push origin main

3) 생성 실행
   cd /d C:\Users\User\Downloads\upload\poong-rank\beobbang
   run_make_beobbang_dashboard.bat

4) 생성 파일
   - ygosu_beobbang_dashboard_full.html
   - ygosu_paste.txt
   - ygosu_paste_YYYYMMDD_HHMM.txt

5) 와이고수 자동 수정
   python auto_edit_beobbang.py

주의:
- 로고는 assets/beobbang_logo.png 로 추출해 넣어둠.
- make_beobbang_dashboard.py 안의 LOGO_URL은 GitHub Pages 기준
  https://keyman1335-maker.github.io/poong-rank/beobbang/assets/beobbang_logo.png
  이라서 git push 후 와이고수에서 정상 출력됨.
