#!/usr/bin/env python
"""
yt_ingest.py — YouTube 채널/영상의 자막(대본)을 받아 raw/social/ 캡처를 생성한다.

목적: research-wiki의 SNS·블로그 소스 규칙(CLAUDE.md)에 따라, YouTube 영상의
'원본'(자막 포함)을 raw/social/ 에 불변 캡처로 떨궈둔다. 이후 auto-ingest 봇이
이 raw 파일을 읽어 🐦SNS 라벨로 위키 페이지에 정제·반영한다.

사용법:
    python tools/yt_ingest.py @koreanstockrider
    python tools/yt_ingest.py UCdOjVxkj5JA0iDu3_xcsTyQ --limit 5
    python tools/yt_ingest.py "https://www.youtube.com/watch?v=nb0QzDcIYVA"   # 단일 영상

옵션:
    --limit N      최근 영상 N개 처리 (기본 5)
    --lang a,b     자막 우선순위 언어 (기본 ko,ko-KR,en,en-US)
    --out DIR      출력 폴더 (기본 raw/social)
    --date YYYY-MM-DD  파일명/메타 날짜 (기본 오늘)

의존성: youtube-transcript-api  (pip install youtube-transcript-api)
나머지는 표준 라이브러리(urllib, xml, re)만 사용.
"""
import argparse
import datetime as _dt
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) research-wiki/yt_ingest"
RSS = "https://www.youtube.com/feeds/videos.xml?channel_id={cid}"


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def resolve_channel_id(arg: str) -> str:
    """핸들/URL/ID를 채널 ID(UC...)로 변환."""
    if re.fullmatch(r"UC[0-9A-Za-z_-]{22}", arg):
        return arg
    # 채널 URL/핸들 페이지에서 channelId 추출
    if arg.startswith("@"):
        url = f"https://www.youtube.com/{arg}"
    elif "youtube.com" in arg:
        url = arg
    else:
        url = f"https://www.youtube.com/@{arg}"
    html = _get(url)
    m = re.search(r'"channelId":"(UC[0-9A-Za-z_-]{22})"', html) or \
        re.search(r'"externalId":"(UC[0-9A-Za-z_-]{22})"', html) or \
        re.search(r'/channel/(UC[0-9A-Za-z_-]{22})', html)
    if not m:
        sys.exit(f"[ERR] 채널 ID를 찾지 못했습니다: {arg}")
    return m.group(1)


def parse_video_id(arg: str):
    """영상 URL/ID면 (video_id) 반환, 아니면 None."""
    m = re.search(r'(?:v=|youtu\.be/|/shorts/)([0-9A-Za-z_-]{11})', arg)
    if m:
        return m.group(1)
    if re.fullmatch(r"[0-9A-Za-z_-]{11}", arg) and not arg.startswith("UC"):
        return arg
    return None


def fetch_feed(cid: str):
    """채널 RSS → (채널명, [ {id,title,published,link}, ... ])"""
    xml = _get(RSS.format(cid=cid))
    ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    root = ET.fromstring(xml)
    chan = (root.findtext("a:title", default="채널", namespaces=ns) or "채널").strip()
    items = []
    for e in root.findall("a:entry", ns):
        vid = e.findtext("yt:videoId", namespaces=ns)
        title = (e.findtext("a:title", namespaces=ns) or "").strip()
        pub = (e.findtext("a:published", namespaces=ns) or "")[:10]
        link = f"https://www.youtube.com/watch?v={vid}"
        items.append({"id": vid, "title": title, "published": pub, "link": link})
    return chan, items


def fetch_transcript(vid: str, langs):
    """자막 텍스트 반환. 실패 시 (None, 사유)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        sys.exit("[ERR] pip install youtube-transcript-api 필요")
    api = YouTubeTranscriptApi()
    try:
        t = api.fetch(vid, languages=langs)
        text = " ".join(s.text for s in t).strip()
        return text, getattr(t, "language_code", "?")
    except Exception:
        # 우선순위 언어 실패 → 사용 가능한 아무 자막이나 시도
        try:
            tl = api.list(vid)
            tr = next(iter(tl))
            fetched = tr.fetch()
            text = " ".join(s.text for s in fetched).strip()
            return text, tr.language_code
        except Exception as e:
            return None, f"{type(e).__name__}: {str(e)[:120]}"


def safe_name(s: str) -> str:
    return re.sub(r"[\\/:*?\"<>|\s]+", "", s)[:40]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="채널 핸들/URL/ID 또는 영상 URL/ID")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--lang", default="ko,ko-KR,en,en-US")
    ap.add_argument("--out", default="raw/social")
    ap.add_argument("--date", default=_dt.date.today().isoformat())
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    langs = [x.strip() for x in a.lang.split(",") if x.strip()]
    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)

    single = parse_video_id(a.target)
    if single:
        chan, items = "단일영상", [{"id": single,
                                  "title": f"video {single}",
                                  "published": a.date,
                                  "link": f"https://www.youtube.com/watch?v={single}"}]
        cid = None
    else:
        cid = resolve_channel_id(a.target)
        chan, items = fetch_feed(cid)
        items = items[: a.limit]

    lines = [f"# [원본 캡처·불변] {chan} (YouTube)", ""]
    lines += [f"- 플랫폼: YouTube", f"- 캡처일: {a.date}"]
    if cid:
        lines += [f"- 채널ID: {cid}",
                  f"- RSS: {RSS.format(cid=cid)}"]
    lines += ["- ⚠️ SNS/유튜브 출처 — 개인 견해. 셀사이드 리포트 아님. 자막은 자동(오타·오인식 가능).",
              "- 정제 시 CLAUDE.md 'SNS·블로그 소스 규칙' 적용(🐦SNS 라벨, ⚠️미확인, 증분만).", ""]

    ok = 0
    for it in items:
        text, lang = fetch_transcript(it["id"], langs)
        lines += [f"## {it['published']} · {it['title']}", f"- 링크: {it['link']}"]
        if text:
            ok += 1
            lines += [f"- 자막 언어: {lang} · 길이: {len(text)}자", "", "### 자막(대본)", text, ""]
        else:
            lines += [f"- ⚠️ 자막 없음/실패: {lang}", ""]

    fname = f"{a.date}_유튜브_{safe_name(chan)}.md"
    path = outdir / fname
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] {path}  (영상 {len(items)}건 중 자막 {ok}건)")


if __name__ == "__main__":
    main()
