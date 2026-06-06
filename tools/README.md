# tools/ — 수집 보조 스크립트

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
