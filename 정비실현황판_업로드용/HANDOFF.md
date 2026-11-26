# 정비실 현황판 — GitHub Pages 자동 갱신 작업 안내 (Claude용)

## 목표
저장소 루트에 `index.html`(정비실 현황판 정적 페이지)을 올려 GitHub Pages로 공개하고,
평일 08~19시(한국시간) 1시간마다 CMS 데이터를 다시 조회해 갱신·푸시한다.

## 파일
- `build.py`      : `data/*.json`을 읽어 **저장소 루트 `index.html`의 `const D = ...;` 줄만** 교체(디자인·기능 유지). 개인 고객명은 그대로 표시(마스킹 해제). 데이터가 그대로면 파일을 건드리지 않음.
- `template.html` 은 예전 버전 틀이라 더 이상 쓰지 않는다(루트 `index.html`이 최신 페이지).
- `queries.json`  : CMS 조회 SQL (데이터셋 이름 → SQL). CMS-MCP `query_db`로 실행.
- `data/`         : 마지막 조회 결과(예시이자 초기값).

## 갱신 절차 (매 실행)
1. `queries.json`의 각 SQL을 CMS-MCP `query_db`로 실행 → 결과 rows를 `data/<이름>.json`으로 저장.
   - `boxes_m`, `crossbars_m`은 그대로 실행해도 되고, 두 쿼리를 합쳐 item이 '크로스바'로 시작하는지로 나눠도 됨.
   - `ret_summary`는 `cnt` 합계만 쓰므로 `[{"cnt": N}]` 형태면 충분.
2. (선택) 수정 값은 Google Apps Script 저장소(config.json의 api_url)에서 페이지가 실시간으로 읽으므로 갱신 때 따로 가져올 필요 없다.
   아래 아티팩트 값은 저장소가 연결되지 않았을 때 보여 줄 기본값일 뿐이다. Claude 현황판(아티팩트 slug `ef0dda22-7b5b-49c9-b395-433310d9b5e5`)의 저장값을 `db_list`로 읽어 저장:
   - `data/team/hidden_returns` → `data/hidden.json` : `[{"detail_id": "..."}]`
   - `data/team/unreg_status`   → `data/unreg_status.json` : `[{"id": "...", "status": "..."}]`
   - `data/team/parts_price`    → `data/price.json` : `[{model, part, price, labor, sort}]`
   (아티팩트 도구를 쓸 수 없으면 기존 파일을 그대로 둔다.)
3. `python3 정비실현황판_업로드용/build.py` → 출력이 `changed`면 루트 `index.html`이 갱신된 것, `unchanged`면 CMS 변동 없음.
4. `changed`일 때만 `index.html`을 커밋·푸시 (메시지 예: `data: 2026-11-25 14:00 갱신`). `data/`는 커밋하지 않는다.

## 자동 실행
평일 08~19시(KST) 5분마다 `change_check.sql`을 먼저 실행해, 결과가 `data/.marker`에 저장된 직전 값과 다를 때만 위 절차를 실행한다(5분 주기는 세션 cron, 매시 03분 예약 작업이 그 cron이 살아 있는지 확인·재생성). CMS-MCP 커넥터로 조회하므로 GitHub Actions에는 CMS 접속 정보가 필요 없다.

## 수정 기능 (Apps Script)
- `apps_script/Code.gs`를 Google 스프레드시트의 Apps Script에 붙여 웹 앱으로 배포한 주소를 `config.json`의 `api_url`에 넣는다.
- 페이지는 그 주소로 상태값 변경·차량 삭제/복원·단가 수정을 저장하고, 열 때마다 최신 값을 읽는다.
- CMS 접속 정보는 페이지에도 Apps Script에도 넣지 않는다.

## 주의
- data/ 폴더는 커밋하지 않는다(.gitignore). 개인 고객명이 마스킹 전 상태로 들어 있다.
- 개인 고객명 마스킹은 사용자 요청으로 해제했다(공개 페이지에 실명이 보임).
