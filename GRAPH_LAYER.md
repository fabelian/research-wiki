# 관계 그래프 레이어 도입 계획 — research-wiki

> Claude Code 실행용 스펙. 레포 루트에 두고 `"GRAPH_LAYER.md 읽고 Phase 1 실행해줘"` 식으로 단계별 구동한다.
> 이 문서는 `CLAUDE.md`(스키마 계약서)를 **대체하지 않고 확장**한다. 충돌 시 `CLAUDE.md`의 원칙이 우선이며, 본 작업 완료 시 해당 변경분을 `CLAUDE.md`에 반영한다.

## 0. 문제 정의

현재 위키는 관계를 prose 안의 `[[위키링크]]`로만 표현한다. 노드가 커지면서 세 가지가 무너진다.

1. **보기 힘듦** — `graph_view.py`가 만드는 `graph.html`은 모든 `[[링크]]`를 타입·가중치 없는 동일 엣지로 그려 hairball이 된다. 필터·관계종류·신뢰도 구분이 없다.
2. **질의 불가** — “엔비디아 공급망에 걸린 한국 종목”, “이 테마에 묶인 종목”같은 multi-hop 질문이 prose를 읽어야만 답이 된다. 구조화된 질의 대상이 없다.
3. **이슈 dedup 부재** — 같은 사건(예: “AI 서버 메모리 탑재량 축소 우려”)이 여러 종목 페이지의 `## 주요 이벤트` 불릿으로 흩어진다. 사건을 묶는 **Issue/Event 노드 타입이 없다.**

## 1. 설계 원칙 (반드시 준수)

- **markdown이 source of truth.** Graph는 위키에서 **파생되는 build artifact**다. Graph DB를 본체로 삼지 않는다.
- **Quartz의 “사람이 읽는” 강점을 버리지 않는다.** prose `[[링크]]`는 읽기용으로 그대로 유지한다.
- **상시 가동 DB를 도입하지 않는다.** 파생물은 CI에서 빌드되는 정적 산출물(`graph.html`, `graph.sqlite`)이다. 기존 `tools/*`와 동일한 방식.
- **idempotent.** 재실행해도 안전. raw 불변·정보 비삭제 원칙 유지.
- **Neo4j/Memgraph는 Phase 4(보류).** RSS 인제스트 규모에서 SQLite 파생 그래프로 multi-hop이 실제로 느려질 때만 승격한다.

## 2. 핵심 변경 3가지

### (A) 구조화된 관계 레이어 — entity 페이지 frontmatter `edges:`

prose 링크는 읽기용으로 두고, **질의용 타입드 엣지**를 frontmatter에 추가한다. 엣지는 출발 노드(해당 페이지) 기준으로 기록.

```yaml
edges:
  - rel: SUPPLIES_TO          # AFFECTS / SUPPLIES_TO / COMPETES_WITH / BELONGS_TO_THEME / HAS_RISK / MENTIONS
    target: "[[엔비디아]]"
    confidence: 0.8           # 0~1
    claim_type: 보도           # 공식발표 / 보도 / 추정 / 루머
    source: raw/social/2026-06-09_...
    date: 2026-06-09
```

- `confidence`/`claim_type`/`source`/`date`는 **필수**. 이게 없으면 “정확한 지식망”이 아니라 “오류 섞인 관계망”이 된다.
- `build_index.py`의 naive 파서는 flat key만 읽으므로 `edges:` 리스트를 무시한다(영향 없음). **새 graph 빌더는 PyYAML 같은 정식 파서**를 쓴다.

### (B) Issue/Event 노드 타입 신설 — `wiki/issues/`

흩어진 사건을 묶는 dedup primitive. 같은 사건은 **하나의 issue 페이지**로 모은다.

```yaml
type: issue
issue_id: ai-server-memory-2026q2
status: open                  # open / resolved / obsolete
created: 2026-06-01
updated: 2026-06-10
entities: ["[[엔비디아]]","[[SK하이닉스]]","[[삼성전자]]"]
themes: ["[[HBM]]"]
```

본문: `📌 최신 요약` → **정의** → **시간순 이벤트 체인**(날짜·이벤트·출처, 내림차순) → **현재 판단**(악재→증권사 반박→완화 등) → 출처.
종목 페이지의 `## 주요 이벤트`는 그대로 두되, 다종목에 걸친 사건은 issue로 승격하고 종목 페이지에서 `[[issue]]`로 링크한다.

### (C) 파생 그래프 빌더 — `tools/build_graph.py` (graph_view.py 확장/대체)

위키를 읽어 두 산출물을 만든다. 항상 빌드 가능, 의존성 최소.

1. **`graph.html`** — 타입드·필터 가능 뷰어:
   - 엣지 색 = `rel` 종류, 굵기/투명도 = `confidence`, 점선 = `claim_type ∈ {추정, 루머}`
   - 노드 타입 필터(stock/sector/theme/issue/analyst), issue용 시간 슬라이더
   - 기존 `graph_view.py`의 노드 색·`_missing` 고아 처리 로직 재사용
2. **`graph.sqlite`** — LLM/에이전트 질의용. DDL:

```sql
CREATE TABLE nodes (id TEXT PRIMARY KEY, type TEXT, name TEXT, ticker TEXT, updated TEXT);
CREATE TABLE edges (
  src TEXT, rel TEXT, dst TEXT,
  confidence REAL, claim_type TEXT, source TEXT, date TEXT
);
CREATE INDEX idx_edges_src ON edges(src);
CREATE INDEX idx_edges_dst ON edges(dst);
```

3. **`tools/graph_query.py`** — 1~2 hop 헬퍼(재귀 CTE). 예: `python tools/graph_query.py --neighbors "엔비디아" --rel SUPPLIES_TO --hops 2 --min-conf 0.5`. LLM이 INGEST/QUERY 때 호출해 컨텍스트를 좁힌다.

## 3. INGEST 워크플로 변경 (CLAUDE.md의 INGEST에 추가)

1. **Entity resolution(append vs create)** — 새 사건을 만나면 새 페이지를 찍기 전에 **기존 issue/entity 페이지가 있는지 먼저 확인**한다(`graph_query.py`/`build_index.py` 산출물 활용). 있으면 append, 없을 때만 create.
2. **다종목 사건은 issue로 라우팅** — 2개 이상 종목에 걸치면 `wiki/issues/`에 issue 노드 생성/갱신 후 각 종목에서 `[[issue]]` 링크.
3. **타입드 엣지 기록** — 추출한 관계를 source 페이지 frontmatter `edges:`에 `confidence/claim_type/source/date`와 함께 추가. **검증 게이트**: `claim_type`이 추정/루머면 `confidence ≤ 0.5`로 캡, prose에는 `⚠️미확인` 규칙(기존)과 일관되게 표기.

## 4. 단계별 실행

각 Phase는 독립 PR. 완료 기준(Acceptance)을 만족해야 다음으로 간다.

### Phase 0 — 스키마 확정

- `CLAUDE.md`에 `edges:` 스펙, `type: issue` 페이지 타입, INGEST 변경분을 추가한다.
- **Acceptance:** `CLAUDE.md`만으로 봇이 새 규칙을 따를 수 있을 만큼 명확.

### Phase 1 — 빌더부터 (콘텐츠 변경 0)

- `tools/build_graph.py` 작성: **지금 존재하는 prose `[[링크]]`만으로** 타입드 graph.html + graph.sqlite 생성(엣지 rel은 일단 `MENTIONS`/페이지타입 기반 추론, confidence=null 허용).
- `tools/graph_query.py` 작성. `.github/workflows/index.yml`(매일)에 graph 재빌드 스텝 추가.
- **Acceptance:** 콘텐츠 한 줄 안 바꾸고도 `graph.html`이 필터·타입 구분되는 뷰로 개선됨. `graph_query.py --neighbors "SK하이닉스"`가 동작. **이 단계만으로 “보기 힘듦”이 즉시 완화된다.**

### Phase 2 — Issue/Event 노드

- `wiki/issues/` 신설. 현존하는 다종목 사건 3~5건을 issue로 마이그레이션(종목 페이지 이벤트는 보존, issue로 링크).
- INGEST에 entity resolution + issue 라우팅 반영. `tools/lint.py`에 규칙 추가: **중복 issue 후보 탐지**, **다종목 이벤트인데 issue 없음** 플래그.
- **Acceptance:** 같은 사건이 단일 issue로 모이고, graph.html에서 issue 노드가 시간 슬라이더로 흐름이 보임. lint가 중복/누락을 보고.

### Phase 3 — 구조화된 엣지 backfill

- INGEST가 `edges:`(confidence/claim_type/source/date)를 기록하도록 전환. 핵심 종목/테마(반도체·HBM·엔비디아 체인 등)부터 backfill.
- `build_graph.py`가 구조화 엣지를 우선 사용, 없으면 prose 링크로 fallback.
- **Acceptance:** graph가 신뢰도·관계종류로 채색·필터됨. 추정/루머 엣지가 시각적으로 구분됨.

### Phase 4 — (보류) 전용 Graph DB

- Phase 1~3의 SQLite 파생 그래프로 multi-hop 질의가 **실제로** 느려서 못 견딜 때만 착수.
- `graph.sqlite` → Memgraph/Neo4j export 스크립트. 위키·빌더는 그대로 두고 질의 백엔드만 교체.
- **현실 판단:** RSS 인제스트 규모에선 이 벽에 부딪힐 일이 드물다. 미리 하지 않는다.

## 5. 하지 말 것

- raw/ 수정 금지, prose `[[링크]]` 삭제 금지, 정보 삭제 금지(폐기 견해는 `obsolete` 표기).
- Graph를 source of truth로 만들지 말 것. 항상 markdown → graph 단방향 파생.
- Phase 1~3 건너뛰고 Neo4j부터 세우지 말 것.
- 검증 없이 LLM 추출 관계를 confidence 없이 confirm으로 넣지 말 것(관계망 오염).

## 6. 빠른 시작 (Claude Code)

```
1) "GRAPH_LAYER.md와 CLAUDE.md 읽고 Phase 0 적용해줘"  → CLAUDE.md 스키마 확장 PR
2) "Phase 1 실행해줘"  → build_graph.py / graph_query.py / index.yml 스텝
3) graph.html 확인 후 "Phase 2로 issue 노드 도입, 최근 다종목 사건부터 마이그레이션"
4) 안정화되면 "Phase 3 엣지 backfill을 반도체·HBM 체인부터"
```

## 진행 상태 (Progress)

- **Phase 0 — 스키마 확정:** ✅ 완료 (2026-06-11) — 본 문서 레포 루트 저장 + `CLAUDE.md`에 `edges:`·`type: issue`·INGEST 변경 반영.
- Phase 1~4: 대기.
