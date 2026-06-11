# 📊 셀사이드 리서치 위키

### 🌐 공개 사이트 → https://fabelian.github.io/research-wiki/
> 브라우저만 있으면 누구나 열람. 검색·다크모드·관계 그래프·모바일 지원.
> 🖥️ 운영 대시보드(비공개·봇 관리) → https://research-wiki-app-production.up.railway.app

---

## 🧒 한마디로 이게 뭐예요?

> **증권사 애널리스트의 "이 주식 살까 말까" 리포트와 매일 쏟아지는 뉴스를,
> AI가 읽고 종목·섹터·테마·거시지표별로 한 장에 정리해 계속 쌓아두는 "주식 위키백과"예요.**

리포트와 뉴스가 수백 건 쌓이면 다시 찾아 읽기가 힘들어요. 그래서 이 프로젝트는
새 자료를 만날 때마다 핵심만 뽑아 **"삼성전자" 노트 한 장에 계속 누적**합니다.
나중엔 그 한 장만 보면 *여러 전문가가 그 종목을 어떻게 봤는지*가 한눈에 보여요.
RAG처럼 매번 원문을 다시 검색하는 게 아니라, **지식을 한 번 컴파일해 최신 상태로 유지**하는 방식이죠. 📒

---

## 🔄 어떻게 동작하나 (전체 그림)

```
              ┌──────────────────────── _app : 자동수집 봇 (별도 저장소) ───────────────────────┐
 📰 뉴스/리포트 →  🐝 수집(네이버)  →  ✍️ AI가 변경안 작성  →  🧑‍⚖️ 사람이 승인/반려  ─┐
              └─────────────────────────────────────────────────────────────────────────────────┘ │
                                                                                                   ▼
                                                          ✅ 승인분만 이 저장소(_repo) main 에 commit·push
                                                                                                   │
   📒 wiki/ (사람은 읽기만, AI가 소유)  ──🛠️ stage.mjs──▶  content/  ──✨ Quartz──▶  🌐 GitHub Pages
                                                                                                   ▲
                                  🤖 매일 CI: fix_wiki → build_macro_dashboard → build_index ──────┘
```

- **AI는 공개 위키를 혼자 못 바꿔요.** 봇은 *변경안(proposal)*만 만들고, 사람이 승인한 것만 반영됩니다(일부 안전한 추가형은 자동승인 옵션).
- 봇이 매일 append하므로, 별도 CI가 **링크 정규화·매크로 대시보드·인덱스**를 재생성하고, 주기적으로 **압축(COMPACT)·헬스체크(LINT)**를 돌립니다.

---

## 📚 지금 무엇이 쌓여 있나

| 종류 | 폴더 | 개수 |
|------|------|------|
| 🏢 종목 | `wiki/stocks/` | **63** |
| 🏭 섹터 | `wiki/sectors/` | **7** |
| 🧑‍💼 애널리스트·논객 | `wiki/analysts/` | **60** |
| 💡 테마 | `wiki/themes/` | **18** |
| 📈 거시지표 | `wiki/macro/` | **8** (+ 대시보드·이슈) |
| 📦 원본 리포트 | `raw/reports/` | **25** |
| 🐦 SNS·블로그 원본 | `raw/social/` | **3** |

> 수치는 대략치이며 봇이 매일 늘립니다. 정확한 목록은 [`index.md`](index.md)(자동 생성)에서 확인하세요.

### 페이지 6종
- **종목**(`stocks/`) — 투자의견 컨센서스·목표주가 히스토리·투자포인트·리스크·상충하는 견해.
- **섹터**(`sectors/`) — 업황 사이클·주요 종목·정책/매크로 변수.
- **애널리스트**(`analysts/`) — 커버리지·콜 적중 이력·성향. SNS/블로그/유튜브 **독립 논객**도 이 타입(비증권사로 명시).
- **테마**(`themes/`) — 예: HBM·온디바이스AI·밸류업. 수혜/피해 종목.
- **거시**(`macro/`) — 지표별 1페이지 누적. **원달러환율·유가·VIX·VKOSPI·공포탐욕지수·한국CDS·한국금리·미국금리** 8종. 스냅샷 히스토리(append-only)·셀사이드 전망(변동성지수 제외)·영향관계.
- **🆕 매크로 대시보드**(`macro/대시보드.md`) — 8개 거시지표의 **최근 14일 값을 `날짜×지표` 매트릭스**로 한눈에. `tools/build_macro_dashboard.py`가 각 거시 페이지의 스냅샷 표를 파싱해 **자동 생성**(직접 편집 금지).

---

## 🔗 마법의 연결고리: `[[대괄호]]`

노트 안 `[[삼성전자]]`처럼 대괄호 두 개로 감싼 단어는 **클릭하면 그 페이지로 점프하는 링크**예요.
회사·전문가·테마·거시가 서로 연결되며 사이트에 **관계 그래프(거미줄 지도)**가 자동으로 그려집니다. 🕸️

---
---

# 🛠️ 기술 세부

여기부터는 기여자·운영자를 위한 설명입니다.

## 📁 저장소 구조 (`_repo` = `fabelian/research-wiki`)

```
wiki/                  # LLM이 소유하는 마크다운(사람은 읽기 전용)
  stocks/ sectors/ analysts/ themes/   # 종목·섹터·애널리스트·테마
  macro/               # 거시지표 8종 + 대시보드.md(자동) + index.md + 이슈.md
raw/                   # 원본(불변, 절대 수정 금지)
  reports/             #   셀사이드 리포트 캡처  (YYYY-MM-DD_증권사_종목.md)
  social/              #   SNS·블로그·유튜브 캡처 (YYYY-MM-DD_플랫폼_계정.md)
CLAUDE.md              # 위키 유지·관리 계약(스키마) — 모든 ingest/lint 전 필독
index.md               # 카테고리별 네비게이션(자동 생성, 직접 편집 금지)
log.md                 # append-only 작업 로그
tools/                 # 보조 스크립트(아래)
stage.mjs              # wiki/ + index.md + raw/ → content/ 복사(빌드용)
pdf_to_md.py           # 리포트 PDF → 마크다운
quartz.config.ts / quartz.layout.ts   # Quartz(정적 사이트 생성기) 설정
.github/workflows/     # CI(아래)
```

## 🧰 도구 모음 (`tools/` · 자세한 사용법은 [`tools/README.md`](tools/README.md))

| 스크립트 | 역할 |
|----------|------|
| `build_index.py` | 각 페이지 프론트매터 → `index.md`를 `updated` 최신순으로 자동 생성 |
| 🆕 `build_macro_dashboard.py` | 거시 페이지들의 `## 스냅샷 히스토리`를 파싱해 `wiki/macro/대시보드.md`(날짜×지표 14일) 생성. 다중 섹션·범위날짜 스킵·셀 첫 숫자·중복날짜 최신행 우선. 파서 테스트는 `tools/test_build_macro_dashboard.py` |
| `compact.py` | 임계(기본 150줄) 초과 위키 페이지를 **DeepSeek V4 Pro(OpenRouter)**로 표준형태 재작성·중복 병합(macro 제외). 보존 규칙 준수 |
| `fix_wiki.py` | 명명 정규화·쓰레기 헤드라인 링크 해제·`type` 보강(읽기 안전 일괄 수정) |
| `lint.py` | 깨진 링크·고아 페이지·`type` 누락·데이터 공백 **보고**(읽기 전용) |
| `yt_ingest.py` | YouTube 채널/영상 **자막 → `raw/social/`** 캡처(자동생성 자막은 `⚠️미확인` 처리) |
| 🆕 `build_graph.py` | 위키 → 타입드 관계 그래프 `graph.html`(필터·관계종류·신뢰도 채색) + `graph.sqlite`. prose `[[링크]]` rel 추론 + frontmatter `edges:`. `graph_view.py` 대체. (`GRAPH_LAYER.md`) |
| 🆕 `graph_query.py` | `graph.sqlite` 1~N hop 이웃 질의(재귀 CTE). 예: `graph_query.py --neighbors "SK하이닉스" --rel SUPPLIES_TO --hops 2`. 없으면 즉석 빌드 |

## ⚙️ 자동화 워크플로 (`.github/workflows/`)

| 워크플로 | 일정 | 하는 일 |
|----------|------|---------|
| `index.yml` | 매일 21:30 UTC(06:30 KST) | `fix_wiki` → 🆕 `build_macro_dashboard` → `build_index` → 변경 시 commit·push |
| `compact.yml` | 주 2회(월·목) 18:00 UTC | `compact.py` 정기 압축 (시크릿 `OPENROUTER_API_KEY` 필요) |
| `lint.yml` | 매주 월 22:00 UTC | `lint.py` 헬스체크 보고 |
| `deploy.yml` | `main` push 시 | `stage.mjs` → `npx quartz build` → **GitHub Pages** 배포 |

## 🤖 자동수집 봇 (`_app` = `fabelian/research-wiki-app`)

위키를 매일 채우는 별도 서비스. **Python + FastAPI + Jinja2 + SQLAlchemy + Postgres**, Railway 배포.
전체 문서는 `_app/README.md` 참고. 핵심 파이프라인:

```
watchlist → fetch → (relevance·날짜 필터) → dedup → propose(LLM) → validate → 검토 큐(pending)
              │                                                                      │
        scheduler(매일 07:00 KST)                              사람 승인 ──▶ upload(commit·push) ──▶ GitHub 재빌드
```

**주요 구성요소**
- `app/worker/` — `fetch.py`(수집), `propose.py`(변경안 생성), `run_cycle.py`(수집+제안 일일 사이클).
- `app/services/` — `naver_client`(네이버 뉴스), `relevance`(잡뉴스·오래된 뉴스 필터), `dedup`(중복 제거), `proposer`(LLM 호출, 모델 교체 가능), `validator`(환각 출처·과도 삭제 경고), `patcher`(**append-only** 연산 적용 — `upsert_block`은 지정 블록만 교체), `wiki_repo`(위키 clone·읽기), `review_service`(승인 시 commit·push), `llm_config`(모델 선택 저장).
- `app/scheduler.py` — `ENABLE_SCHEDULER=1`이면 매일 자동 실행(`CRON_HOUR_UTC`, 기본 22 = 07:00 KST).
- `scripts/seed_macro.py` — 거시지표를 `market='MACRO'` watchlist로 시드해 동일 파이프라인으로 흐르게 함. **현재 8종(원달러환율·한국금리·미국금리·유가·VIX·🆕VKOSPI·공포탐욕지수·한국CDS)**. 배포 후 1회 실행 필요: `python -m scripts.seed_macro`(idempotent).

**원칙·옵션**
- **추가 전용(append-only):** AI는 기존 줄을 수정·삭제 못 하고 새 내용만 제안 → 기존 정보 유실 방지.
- **모델 선택:** 대시보드 드롭다운에서 OpenRouter 모델을 골라 `app_settings`에 저장(DeepSeek V4 Flash/Pro, Kimi K2.6, GLM-5.1, GPT-oss-120b 등).
- **자동 승인:** `AUTO_APPROVE_CLEAN=1`이면 경고 없고 추가만 하는 깨끗한 변경안은 사람 확인 없이 게시(끄면 전수 수동 검토).
- **배포:** Railway. 서버 기동 시 `alembic upgrade head`로 DB 스키마 자동 정렬.

## 🚀 로컬에서 사이트 미리보기

```bash
npm install                                   # 최초 1회
node stage.mjs && npx quartz build --serve    # http://localhost:8080
```
성공 시 `Parsed N Markdown files / Filtered out 0 files`. 중간에 `frontmatter ERROR`가 없으면 OK.

## 📥 새 소스 추가 (Ingest)

- **자동(기본):** `_app` 봇이 watchlist 종목·거시지표의 뉴스를 매일 수집→제안→(승인)→반영.
- **수동 리포트:** `raw/reports/`에 `YYYY-MM-DD_증권사_종목.md`로 저장(또는 `pdf_to_md.py`로 PDF 변환) → Claude Code에 "ingest" 요청. 자세한 절차는 [`수집_가이드.md`](수집_가이드.md).
- **SNS/블로그/유튜브:** `raw/social/`에 원본 캡처(`yt_ingest.py` 등) → `🐦SNS·계정명` 라벨·`⚠️미확인`·**증분 인사이트만** 반영(CLAUDE.md "SNS·블로그 소스 규칙").

> ⚠️ 본인 참고용 수동 수집은 정상이나, 집계 사이트 **대량 자동 스크래핑은 약관 위반**이라 금지. 외국계 IB 원문은 비공개라 **공개 보도 기반 2차 요약**으로만 다룹니다(출처 표시).

## ⚠️ 프론트매터 주의 (가장 흔한 빌드 실패 원인)

모든 페이지 맨 위 `---`로 감싼 **프론트매터(YAML)** 형식이 조금만 틀려도 **사이트 빌드가 통째로 실패**합니다.

```yaml
---
type: stock
ticker: '005930'
name: 삼성전자
sector: "[[반도체]]"      # [[ ]] 가 들어가는 값은 반드시 따옴표로!
created: 2026-06-01
updated: 2026-06-03
---
```
- 위아래를 `---`로 정확히 **여닫기**(닫는 `---` 누락이 잦은 사고 원인).
- `[[위키링크]]` 값은 따옴표 `" "`로 감싸기. 값이 여럿이면 콤마 대신 블록 시퀀스(목록)로.

---

## 🧱 사용 기술 한눈에

| 기술 | 역할 |
|------|------|
| **Markdown** | 위키 노트 형식 |
| **Quartz v4** | 노트 → 웹사이트(검색·그래프·다크모드) |
| **GitHub Pages + Actions** | `main` push 시 자동 배포 + 매일 정리·압축·헬스체크 CI |
| **Python** | 위키 도구(`tools/`)·PDF 변환·봇 백엔드 |
| **FastAPI + SQLAlchemy + Postgres** | 자동수집 봇(`_app`) |
| **LLM (Claude / OpenRouter)** | 리포트·뉴스를 읽고 변경안 작성, 정기 압축 |
| **Railway** | 봇 서비스 호스팅 |
| **Obsidian** | 노트 편집·그래프 보기(선택) |
