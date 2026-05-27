C9 대시보드 LIVE 자동화 v2

포함 파일:
1. index.html
   - 멤버 현황판 + LIVE/OFF 표시 연동 완료
   - live_status.json을 60초마다 다시 읽음

2. cnine_members.json
   - 씨나인 멤버 39명
   - soop_id / soop_url / profile_img 포함

3. live_status.json
   - 초기값. 전원 OFF 상태
   - update_live_status.py 실행하면 최신 상태로 갱신

4. update_live_status.py
   - SOOP 페이지를 확인해서 live_status.json 생성

5. run_update_live_status.bat
   - LIVE 상태 수집 원클릭 실행

사용 순서:
1. 이 압축을 풀어서 GitHub 저장소 최상단에 넣기
   예:
   poong-rank/
    ├ index.html
    ├ cnine_members.json
    ├ live_status.json
    ├ update_live_status.py
    └ run_update_live_status.bat

2. GitHub Desktop에서 Commit + Push
3. 사이트 확인:
   https://keyman1335-maker.github.io/poong-rank/?v=live1

4. LIVE 갱신:
   run_update_live_status.bat 실행
   live_status.json 바뀜
   GitHub Desktop에서 live_status.json Commit + Push

주의:
- 현재는 GitHub Pages 정적 사이트라 live_status.json도 갱신해서 Push해야 사이트에 반영됨.
- 완전 원클릭은 다음 단계에서 git push까지 bat에 묶으면 됨.
