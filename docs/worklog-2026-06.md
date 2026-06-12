# 작업 로그 — 2026년 6월 (VKOSPI · 매크로 대시보드 · 관계 그래프 레이어)

> 2026-06-10 ~ 06-13 세션에서 진행한 변경의 요약. 상세 스펙은 [`GRAPH_LAYER.md`](../GRAPH_LAYER.md),
> 스키마 계약은 [`CLAUDE.md`](../CLAUDE.md), 설계/계획 문서는 `docs/superpowers/` 참고.
> 저장소: `_repo`(위키 콘텐츠·도구, github.com/fabelian/research-wiki) · `_app`(자동수집 봇, research-wiki-app).

## 1. VKOSPI 거시 지표 추가 + 매크로 대시보드  (_repo #1, _app #1)

- **VKOSPI**(코스피200 변동성지수)를 거시 지표 8번째로 추가.
  - `wiki/macro/VKOSPI.md` 신규(웹검색 시딩, 출처 동반·미확인일 N/A), `CLAUDE.md` 대상지표 7→8종, VIX 역링크.
- **매크로 대시보드** `wiki/macro/대시보드.md` — 8개 거시지표의 최근 14일 값을 `날짜×지표` 매트릭스로 **자동 생성**.
  - 도구 `tools/build_macro_dashboard.py`(스냅샷 히스토리 표 파싱: 다중 섹션·범위날짜 스킵·셀 첫 숫자·중복날짜 최신행 우선) + 테스트.
  - `.github/workflows/index.yml`(매일)에 대시보드 재생성 스텝 추가.
- **봇 연동**: `_app/scripts/seed_macro.py`에 VKOSPI 타깃 추가 + prod DB seed 실행(Watchlist 행 생성).
- **알려진 한계**: VIX.md의 "반도체 VIX" 행 때문에 대시보드 일부 셀이 별도 지표 값을 집을 수 있음(스냅샷 표 정제는 COMPACT 영역).

## 2. README 제로베이스 재작성  (_repo #2)

- 친근 소개 + 기술 세부 하이브리드. 누락돼 있던 **거시 페이지·대시보드·VKOSPI·도구 모음·CI 워크플로·자동수집 봇 아키텍처**를 실제 소스 기준으로 반영. 최신 카운트 갱신.

## 3. 관계 그래프 레이어 (GRAPH_LAYER, Phase 0~3)

markdown을 source of truth로 두고, 위키에서 **파생되는** 타입드 관계 그래프를 도입. 상세는 `GRAPH_LAYER.md`.

| Phase | 내용 | PR |
|------|------|-----|
| **0 — 스키마** | `CLAUDE.md`에 `edges:`(타입드 엣지)·`type: issue` 페이지 타입·INGEST 3규칙 추가. `GRAPH_LAYER.md` 저장. | _repo #3 |
| **1 — 빌더** | `tools/build_graph.py`(타입드·필터 `graph.html` + `graph.sqlite`) · `tools/graph_query.py`(재귀 CTE 1~N hop). `index.yml`에 graph 재빌드. `graph_view.py` 대체. 콘텐츠 변경 0. | _repo #4 |
| **2 — 이슈 노드** | `wiki/issues/` 신설·다종목 사건 3건 마이그레이션(출처 보존)·종목 백링크. `build_graph` 시간 슬라이더. `lint.py` 규칙([5]중복 issue·[6]다종목인데 issue 없음). | _repo #5 |
| **3 — edges backfill** | 반도체·HBM·엔비디아 체인 5종에 frontmatter `edges:` 20건(추정 1 포함). `build_graph` 구조화 엣지 우선. `index.yml` PyYAML 설치. | _repo #6 |

- **엣지 규칙**: `rel`(AFFECTS/SUPPLIES_TO/COMPETES_WITH/BELONGS_TO_THEME/HAS_RISK/MENTIONS)·`target`·`confidence`·`claim_type`·`source`·`date`. 추정/루머는 `confidence ≤ 0.5`(점선).
- **산출물**: `graph.html`(레포 루트, 매일 재생성·커밋) / `graph.sqlite`(gitignore, 없으면 graph_query가 즉석 빌드).
- **Phase 4(전용 Graph DB)는 보류** — SQLite 파생 그래프로 multi-hop이 실제로 느릴 때만.

## 4. 후속 작업 (그래프 레이어 안정화)

- **데이터 하이진** (_repo #7): 그래프가 드러낸 **stem 충돌 4건 해소**(중복 `wiki/거시/` 폴더·빈 `themes/현대차`·`themes/자동차·우주항공`은 섹터로 병합 후 삭제). 망가진 프론트매터 교정(`스트라이커` 잘못된 미래에셋증권 프론트매터→SYK, `2차전지` 프론트매터 부재→추가). 종목 69→70·섹터 6→7·테마 18→15.
- **그래프 사이트 노출** (_repo #8): `deploy.yml`이 빌드 후 `public/graph.html` 발행 → **https://fabelian.github.io/research-wiki/graph.html**. index 홈·README 링크.
- **이슈 통합** (_repo #9): lint [6] 5건이 모두 같은 '검은 월요일' 폭락의 facet이라, 새 이슈로 쪼개지 않고 **검은월요일 이슈를 코스피 전반으로 확장**(네이버·현대차·Tesla·증권주 흡수). lint [6] 5→0.
- **edges 확장** (_repo #10): 자동차·로보틱스 체인 5종(현대차·현대모비스·기아·두산로보틱스·Tesla)에 12엣지. 구조화 엣지 20→32.

## 5. 봇 자동화 연결 — 그래프 레이어가 "수동 → 자동 유지"  (_app #2)

auto-ingest 봇이 GRAPH_LAYER INGEST 규칙을 **자동으로** 따르게 함.

- **`patcher.py` 신규 연산 `add_edges`** — frontmatter `edges:`에 **append-only 병합**(기존 보존·멱등 dedup·frontmatter 없으면 안전 no-op). validator의 append-only 불변식과 호환(줄 추가만).
- **`proposer.py`** — submit_proposal 스키마에 `add_edges` op + `edges` 필드. 프롬프트에 3규칙: add_edges(검증 게이트), 이슈 라우팅(2+종목 → `wiki/issues/`), 엔티티 해소(append vs create).
- **`wiki_repo.list_inventory`** — issues 포함(중복 이슈 생성 방지).
- **안전성**: 봇 제안은 사람 검토(pending→승인) 게이트. _app 전체 테스트 **141 passed**.
- **운영**: 머지 후 **Railway 재배포**되면 다음 봇 사이클부터 적용(add_edges는 순수 코드, 별도 DB seed 불필요).

## 부록: 주요 도구·산출물

| 경로 | 역할 |
|------|------|
| `tools/build_macro_dashboard.py` | 거시 스냅샷 → `wiki/macro/대시보드.md` |
| `tools/build_graph.py` | 위키 → `graph.html` + `graph.sqlite` (타입드·필터·신뢰도·시간 슬라이더) |
| `tools/graph_query.py` | `graph.sqlite` 1~N hop 이웃 질의(`--rel`/`--hops`/`--min-conf`/`--both`) |
| `_app: patcher.add_edges` | 봇이 frontmatter `edges:`를 append-only로 기록 |
| `GRAPH_LAYER.md` | 그래프 레이어 전체 스펙·Phase·진행 상태 |
