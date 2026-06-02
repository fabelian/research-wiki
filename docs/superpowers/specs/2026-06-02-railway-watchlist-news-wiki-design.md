# 설계: 관심종목 기반 뉴스 자동수집 → LLM 위키 갱신 (Railway + Postgres)

- 작성일: 2026-06-02
- 상태: 승인됨 (구현 계획 대기)
- 대상 앱 repo: `fabelian/research-wiki-app` (신규, 별도)
- 콘텐츠 repo: `fabelian/research-wiki` (기존, 변경 없음 — Quartz/Pages로 공개)

## 1. 목적 / 문제

관심종목(watchlist)을 저장하고, 정기적으로 관련 **뉴스**를 자동 수집해, 그것으로 기존 **LLM 마크다운 위키**(셀사이드 리서치)를 갱신한다. 단, 위키 공개 반영은 **사람 검토·승인 후**에만 일어난다.

## 2. 핵심 결정 (확정)

| 항목 | 결정 |
|------|------|
| 위키 거처 | **git 유지** — 위키는 markdown으로 `research-wiki` repo에 남고, 기존 Quartz→GitHub Pages가 공개 열람 담당. 새 앱은 자동화 백엔드 + 검토 대시보드 |
| 수집 소스 | **네이버 뉴스 검색 API** (합법·국내 종목 뉴스에 최적). 그 외 소스는 범위 외(YAGNI) |
| 자율성 | **검토 게이트** — 수집·중복제거·LLM 제안은 자동, 공개 반영은 사람 승인 후 |
| 스택 | **Python + FastAPI**, 서버렌더 대시보드(Jinja2 + HTMX) |
| 인증 | **단일 사용자 + 비밀번호** (서명 세션 쿠키, 사용자 테이블 없음) |
| Railway 토폴로지 | **단일 web 서비스 + Railway Cron + Postgres 플러그인** |
| 앱 코드 위치 | **별도 repo** `research-wiki-app` (콘텐츠 repo는 순수 유지) |
| LLM | Claude (Anthropic), 모델은 env로 설정. 프롬프트 캐싱 사용 |
| 주기 | 일 1회(예: 07:00 KST), env/cron으로 조정 가능 |

## 3. 아키텍처

```
[Railway]
  ├─ web 서비스 (FastAPI + Jinja2/HTMX)   ← 단일 사용자 대시보드(비밀번호 세션)
  ├─ Railway Cron → `python -m app.worker.run_cycle` (같은 이미지, 다른 엔트리포인트)
  └─ Postgres 플러그인

[외부]
  ├─ 네이버 뉴스 검색 API      (수집)
  ├─ Anthropic API (Claude)    (변경안 생성)
  └─ GitHub repo research-wiki (clone / commit / push)

[기존 — 변경 없음]
  └─ GitHub Actions (Quartz 빌드) → GitHub Pages 공개 사이트
```

### 모듈 경계 (독립 테스트 가능 단위)
- `naver_client` — 뉴스 조회 (입력: 질의·since / 출력: 정규화 기사). 의존: 네이버 키
- `dedup` — 신규 기사 선별 (입력: 기사+기존 해시 / 출력: 신규)
- `proposer` — LLM 변경안 (입력: 위키 원문+신규 기사+스키마 규칙 / 출력: ChangeProposal). 의존: Anthropic
- `validator` — LLM 출력 사후 검증(출처 환각·과도 삭제 등) → 플래그
- `wiki_repo` — clone/read/write/commit/push. 의존: GitHub PAT
- `review_service` — 승인·반려 적용 (wiki_repo 사용)
- `web` — FastAPI 라우트·인증·템플릿
- `db` — SQLAlchemy 모델 + Alembic
- `worker` — 사이클 오케스트레이션 (엔트리포인트)

## 4. 데이터 흐름

### 4.1 일일 자동 사이클 (Cron → worker)
1. 활성 관심종목마다 네이버 뉴스 API 조회 (name+aliases, `last_fetched_at` 이후분만)
2. 정규화 + 중복 제거(`url_hash` UNIQUE) → 신규만 `news_items`(status=new)
3. 종목별 신규 기사 + **현재 위키 페이지 원문**(repo 얕은 클론)을 Claude에 전달
4. Claude가 **구조화 변경안** 반환(수정 파일·새 본문·근거·상충)
5. `change_proposals`(status=pending)에 **목표 파일 전체 + diff + 인용 기사 id** 저장. 자동 커밋 없음
6. 종목 단위 격리 — 한 종목 실패가 전체 사이클을 멈추지 않음

### 4.2 검토 흐름 (사람, 대시보드)
7. 로그인 → pending 변경안을 diff·출처링크·검증 플래그와 함께 확인
8. **승인** → `review_service`가 repo 클론에 본문 write → commit·push → 기존 Quartz Action 자동 배포. 제안=approved, 기사=ingested, `commit_sha` 저장
9. **반려/수정** → rejected(+메모), 기사 상태 갱신

## 5. 데이터 모델 (Postgres, Alembic 마이그레이션)

```
watchlist(id PK, ticker, name, market[KR|US], aliases text[],
          active bool default true, last_fetched_at, created_at)

news_items(id PK, watchlist_id FK, source 'naver', url, url_hash UNIQUE,
           title, description, published_at, fetched_at, raw jsonb,
           status [new|proposed|ingested|dismissed])

change_proposals(id PK, watchlist_id FK, status [pending|approved|rejected],
                 summary, payload jsonb[{path,action,new_content,diff,rationale}],
                 model, cost_tokens int, reviewer_note, commit_sha,
                 created_at, reviewed_at)

proposal_news(proposal_id FK, news_item_id FK)   -- N:N 근거 기사

job_runs(id PK, kind 'fetch_cycle', status [success|partial|failed],
         stats jsonb, error, started_at, finished_at)
```

설계 포인트:
- 인증은 테이블 불필요(단일 비밀번호 env + 서명 쿠키).
- `url_hash UNIQUE` → 중복 수집 무시, 재실행 멱등.
- `payload`에 목표 파일 전체 본문 저장 → 승인 적용이 결정적, 위키가 그새 바뀌어도 안전.
- `status` 전이가 재처리 가드(approved/ingested 재처리 불가).
- `cost_tokens`로 Claude 비용 가시화.

## 6. 파이프라인 상세

### 6.1 네이버 수집 (`naver_client` + `dedup`)
- `GET https://openapi.naver.com/v1/search/news.json`, 헤더 `X-Naver-Client-Id/Secret`
- 질의: aliases 조합, `sort=date`, `display=100`, 페이지네이션
- 증분: `published_at > last_fetched_at`만 채택
- 정규화: HTML 태그 제거, `url_hash = sha1(정규화 URL)`
- rate limit(일 25,000) 내, 429 지수 백오프
- 종목당 신규 상한(예: 30/사이클), 초과분은 `job_runs.stats`에 드롭 수 기록(조용한 누락 금지)

### 6.2 LLM 변경안 (`proposer`)
- 입력: (a) 해당 종목 관련 현재 위키 페이지 원문(stocks + 연결 sectors/themes) (b) 신규 기사(제목·요약·URL·일자)
- Anthropic SDK **구조화 출력(tool use)** → Pydantic 스키마 강제:
  ```
  ChangeProposal {
    summary: str
    citations: [url...]            # 입력 기사 URL에서만
    files: [FileChange{ path, action[create|update], new_content, rationale }]
    conflicts: [str]
  }
  ```
- 프롬프트에 **CLAUDE.md 스키마 주입**: 출처·날짜 동반 / 정보 비삭제 / 폐기 견해 obsolete 보존 / TP·투자의견은 히스토리 테이블에 **추가** / 보도기반은 `source_type` 명시
- **프롬프트 캐싱**으로 위키 원문·스키마 캐시 → 비용 절감

### 6.3 규칙 검증 (`validator`) — 소프트 게이트(차단 아님, 플래그)
- citations가 전부 입력 기사 URL에 존재하는가(환각 출처 차단)
- update인데 과도한 줄 삭제(비삭제 원칙) → diff로 검출
- 새 TP/수치에 출처·날짜 문자열 동반 여부
- update path가 실제 존재 파일인가
- 위반 시 버리지 않고 ⚠️ 플래그 → 최종 판단은 검토자

### 6.4 git 적용 (`wiki_repo` + `review_service`) — 승인 시에만
- fine-grained PAT로 얕은 클론 → `payload.files` write → commit(메시지 `auto-ingest: <종목> via <N>건 [proposal #id]` + Co-Authored-By) → push `main`
- push 거부 시 re-clone→재적용(결정적)→재push, 최대 3회
- 성공 시 `commit_sha`/`ingested`/`approved` 갱신
- 이후 기존 Quartz Action 자동 배포 (추가 작업 0)
- `index.md`·`log.md` 갱신도 `files`에 포함 가능(LLM 제안)

## 7. 대시보드 (FastAPI + Jinja2 + HTMX)

```
/login                 비밀번호 → 서명 세션 쿠키
/                      pending 수, 최근 job_runs, 종목별 신규 기사 수
/watchlist             관심종목 CRUD (ticker·name·market·aliases·active)
/proposals             검토 큐 (종목·요약·기사수·⚠️플래그)
/proposals/{id}        파일별 diff + 근거 기사 + 검증 플래그 / [승인][반려][수정후승인]
/news                  수집 기사 로그 (필터: 종목·상태)
/runs                  사이클 이력 (성공/부분/실패 + stats + 에러) / "지금 수집" 수동 트리거
```
- diff는 서버(`difflib`)에서 생성·HTML 렌더, 승인/반려는 HTMX 인라인(SPA 불필요)

## 8. Railway 배포 / 시크릿

- 서비스 1개(`web`): `uvicorn app.main:app`, Postgres 플러그인(`DATABASE_URL` 자동)
- Railway Cron: 예 `0 22 * * *` UTC(=07:00 KST) → `python -m app.worker.run_cycle`
- 위키 repo는 런타임 얕은 클론(ephemeral FS, 소형 repo라 볼륨 불필요)
- 환경변수:
  ```
  DATABASE_URL (자동)
  NAVER_CLIENT_ID / NAVER_CLIENT_SECRET
  ANTHROPIC_API_KEY / ANTHROPIC_MODEL
  GITHUB_TOKEN(fine-grained PAT: research-wiki contents RW만) / GITHUB_REPO / WIKI_BRANCH
  DASHBOARD_PASSWORD / SESSION_SECRET
  TZ=Asia/Seoul
  ```
- 키는 전부 Railway env로만 보관, 코드/깃 미포함. PAT는 최소권한.

## 9. 오류 처리 / 멱등성 / 관측성

- 네이버 429 백오프, 부분 실패는 `job_runs.status=partial`+stats. `url_hash UNIQUE`로 재실행 안전
- LLM 파싱 실패 1회 재시도→실패 시 해당 종목 skip, 기사 `new` 유지(다음 사이클 재시도)
- push 거부 re-clone 재적용 최대 3회
- 제안 status 전이 가드로 중복 적용 방지, 외부호출 타임아웃·재시도 래핑
- `job_runs` + 구조화 JSON 로깅, 실패는 대시보드 배지. (이메일/슬랙 알림은 범위 외)
- `cost_tokens` 누적으로 비용 추적

## 10. 테스트 전략

- 단위: `naver_client`(HTTP 모킹), `dedup`, `wiki_repo`(임시 git repo), `proposer`(Anthropic 모킹·스키마 검증), `validator`, `review_service`(임시 repo 적용)
- 통합: 모킹 네이버·Anthropic + 임시 git repo로 전체 사이클 → 제안 생성 / 승인→커밋 확인
- 수동: Railway 스테이징에서 실종목 1개 엔드투엔드
- 핵심 모듈(dedup·validator·review_service) TDD 우선

## 11. 단계별 구축 (각 단계 독립 배포 가능)

1. **스캐폴드**: repo·FastAPI·Postgres·Alembic·로그인·Railway 배포(빈 대시보드)
2. **수집**: watchlist CRUD + `naver_client`+`dedup` + `/news` + 수동 트리거 + `job_runs`
3. **제안**: `wiki_repo`(읽기)+`proposer`+`validator` → `change_proposals` + `/proposals` diff 뷰
4. **승인·게시**: `review_service`(commit·push) + 승인/반려 + Quartz 자동배포 확인
5. **스케줄**: Railway Cron + 관측성 마무리

## 12. 범위 외 (YAGNI)
- 네이버 외 소스(RSS·글로벌 API·스크래핑), 수동 PDF 업로드(추후 확장 가능)
- 멀티 사용자·역할, 이메일/슬랙 알림, 자동 커밋(검토 게이트 유지)
- 위키를 DB로 이전(현재 git 유지)
