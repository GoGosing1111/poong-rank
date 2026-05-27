C9 LIVE 상태 수집기 v3 - bjapi 방식

이전 문제:
- SOOP 일반 페이지 HTML에는 방송중 정보가 없어서 전원 OFF 처리됨.

이번 해결:
- https://bjapi.afreecatv.com/api/{soop_id}/station
  API를 직접 조회해서 station.broad 정보를 기준으로 LIVE 판정.

사용법:
1. 기존 대시보드 폴더에 이 파일들을 넣는다.
   - update_live_status.py
   - run_update_live_status.bat

2. 같은 폴더에 cnine_members.json이 있어야 함.

3. run_update_live_status.bat 실행.

4. 생성/갱신되는 파일:
   - live_status.json
   - live_status_debug.txt

5. live_status.json을 GitHub에 Commit + Push.

확인:
- live_status_debug.txt에서 [LIVE]가 잡히는지 확인.
- 홈페이지는 live_status.json을 읽어서 LIVE/OFF를 표시함.

주의:
- GitHub Pages는 정적 사이트라 live_status.json을 Push해야 반영됨.
- 다음 단계에서 git add/commit/push까지 BAT에 묶으면 원클릭 가능.
