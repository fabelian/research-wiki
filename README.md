# 📊 셀사이드 리서치 위키

## 🌐 https://fabelian.github.io/research-wiki/

> 위 주소에서 그래프·검색·백링크·다크모드로 위키를 탐색할 수 있습니다.
> (옵시디언 없이 브라우저만으로 열람 가능 · 모바일 지원)

---

국내외 증권사 **셀사이드 리서치**를 종목·섹터·애널리스트·테마 단위로 누적·구조화한, **LLM이 관리하는 마크다운 위키**입니다. RAG처럼 매번 원문을 재검색하지 않고, 지식을 한 번 컴파일해 계속 최신 상태로 유지합니다.

현재 커버리지: **메모리 반도체 3강** (SK하이닉스 · 삼성전자 · 마이크론) 중심의 AI 메모리 슈퍼사이클.

---

## 🗂️ 구조 (3계층)

| 경로 | 역할 |
|------|------|
| `raw/reports/` | 원본 리서치(불변). `YYYY-MM-DD_증권사_종목.md` |
| `wiki/` | LLM이 소유·갱신하는 컴파일된 지식 (stocks · sectors · analysts · themes) |
| `CLAUDE.md` | 위키 유지·관리 계약(스키마) |
| `index.md` | 카테고리별 네비게이션 인덱스 (사이트 홈) |
| `log.md` | 시간순 append-only 작업 기록 |

**현재 페이지**: 종목 4 · 섹터 1 · 애널리스트 4 · 테마 4 / **원본 리포트 18건**

---

## 📝 최근 업데이트

- **2026-06-02** — Quartz v4.5.2 + GitHub Pages **자동 배포 파이프라인** 구축. `main` push마다 사이트 자동 갱신.
- **2026-06-02** — 깨진 위키링크 정리(LINT): `[[AI서버]]`·`[[엔비디아]]` 스텁 생성 → 그래프 완전 연결.
- **2026-06-02** — **삼성전자 국내 증권사** 보강(키움 20만 → KB 36만 → 한국투자 57만). 마이크론은 국내 정식 TP 부재 확인 → **read-across**(UBS 15배 PER → "80만전자·700만닉스") 기록.
- **2026-06-01** — **삼성전자·마이크론** 신규 종목 페이지 + 외국계 6건(모건스탠리·노무라·골드만·BofA·UBS) ingest. 골드만 비대칭 발견(삼성·하이닉스 Buy vs 마이크론 Neutral $235).
- **2026-06-01** — **SK하이닉스** 외국계 3건(모건스탠리·노무라 400만·골드만 350만) ingest, 메모리 3강 크로스레퍼런스 구축.
- **2026-06-01** — SK하이닉스 컨센서스 테이블·상충 견해(슈퍼사이클 지속성 논쟁) 정리.

> ⚠️ **출처 주의**: 외국계 IB 원문 PDF는 비공개라, 외국계 리포트는 **공개 보도 기반 2차 요약**입니다. 각 파일 frontmatter에 `source_type`·`source_url`을 명시했습니다.

---

## 🚀 배포 작동 방식

작성 원본(`wiki/` + `index.md`)은 그대로 두고, 빌드 시점에 Quartz 입력으로 복사해 정적 사이트를 생성합니다 — **단일 소스 유지**.

```
wiki/ + index.md   ──(stage.mjs)──▶   content/   ──(Quartz)──▶   public/   ──▶   GitHub Pages
 (작성 원본)                          (빌드 입력)      (정적 사이트)        (배포)
```

- `main`에 push → `.github/workflows/deploy.yml`가 stage → build → 배포 자동 실행
- `content/`는 빌드 산출물(git 미추적), `public/`·`node_modules/`는 `.gitignore`

### 로컬에서 미리보기

```bash
npm install                          # 최초 1회
node stage.mjs && npx quartz build --serve   # http://localhost:8080
```

---

## 📥 리포트 수집 → ingest

자세한 절차는 [`수집_가이드.md`](수집_가이드.md) 참조.

```bash
# 1) raw/reports/ 에 PDF 저장 (YYYY-MM-DD_증권사_종목.pdf)
# 2) 변환
python pdf_to_md.py            # → raw/reports_md/*.md (ingested:false)
# 3) Claude Code에서: "ingest raw/reports_md/ 의 미반영 리포트"
```

> 본인 참고용 수동 수집은 정상. 집계 사이트 대량 자동 스크래핑은 약관 위반이니 지양.
