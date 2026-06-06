# tools/ — 수집·정제 보조 스크립트

## compact.py — 위키 정기 압축(정제)
봇이 매일 append만 해서 페이지에 중복이 쌓인다. 임계 줄수를 넘는 `wiki/` 페이지를
Claude Opus로 재작성해 **중복 병합·표준형태**로 정제한다. 원본은 `raw/`에 불변 보존되므로
위키는 과감히 압축해도 정보 손실이 없다.

```
ANTHROPIC_API_KEY=... python tools/compact.py            # 임계(기본 150줄) 초과 전부
python tools/compact.py --threshold 120
python tools/compact.py wiki/stocks/삼성전자.md           # 특정 파일만
python tools/compact.py --dry-run                         # 호출 없이 대상만
```
- 표준형태: `📌 최신 요약 → 핵심/쟁점 → 상충하는 견해(보존) → 타임라인(압축) → 출처`. `updated` 자동 갱신.
- **보존 규칙**: 구별되는 사실·날짜·출처·상충 견해는 최소 1회 유지(중복만 제거). 안전장치로 프론트매터로 시작 + 더 짧을 때만 적용.
- **macro 페이지는 제외**(스냅샷 시계열 구조라 별도 규칙 필요).
- 자동화: `.github/workflows/compact.yml`이 **주 2회(월·목)** 실행. GitHub에 `ANTHROPIC_API_KEY` 시크릿 필요. 수동 실행은 Actions → "Compact wiki" → Run workflow.

## yt_ingest.py — YouTube 자막 파이프라인
YouTube 채널/영상의 **자막(대본)**을 받아 `raw/social/`에 원본 캡처(불변)를 생성한다.
이후 auto-ingest 봇이 그 raw 파일을 읽어 CLAUDE.md의 "SNS·블로그 소스 규칙"(🐦SNS 라벨·⚠️미확인·증분만)에 따라 위키에 정제·반영한다.

### 설치 (최초 1회)
```
.venv/Scripts/python -m pip install -r tools/requirements.txt
```

### 사용
```
# 채널 핸들 / 채널ID / 영상URL 모두 지원
python tools/yt_ingest.py @koreanstockrider --limit 5
python tools/yt_ingest.py UCdOjVxkj5JA0iDu3_xcsTyQ
python tools/yt_ingest.py "https://www.youtube.com/watch?v=VIDEOID"
```
옵션: `--limit N`(최근 N개), `--lang ko,en`(자막 우선순위), `--out DIR`, `--date YYYY-MM-DD`.

출력: `raw/social/YYYY-MM-DD_유튜브_채널명.md` (채널 메타 + 영상별 제목/링크/자막).

### 메모
- 자막은 **자동 생성 자막**이 많아 오타·오인식이 있을 수 있음 → 정제 시 `⚠️미확인` 처리.
- `raw/social/`은 Quartz `ignorePatterns`로 **사이트 퍼블리시에서 제외**(자막이 길어 bloat 방지). git에는 보존되어 봇이 읽는다.
- 네트워크가 막힌 클라우드 IP에서는 YouTube가 자막 요청을 차단할 수 있음 → 가급적 로컬/봇 환경에서 실행.
