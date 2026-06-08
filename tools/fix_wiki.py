#!/usr/bin/env python
"""
fix_wiki.py — LINT 후속 일괄 수정(결정적). 보고가 아니라 실제 수정.

1) 명명 불일치 위키링크 정규화 → 실제 파일 stem으로 치환(별칭/대소문자/공백↔밑줄/수동맵)
2) 봇이 만든 '뉴스 헤드라인 통째 위키링크' 해제 → 일반 텍스트
3) 프론트매터 `type` 누락 보강(디렉토리로 추론) + name 없으면 추가

raw/* 경로 링크, 이미 유효한 링크, 짧은 '미존재 엔티티'(향후 페이지/봇 보강 대상)는 건드리지 않는다.
"""
import glob
import os
import re
import sys

WIKILINK = re.compile(r"\[\[([^\]|#]+)((?:#[^\]|]+)?)((?:\|[^\]]*)?)\]\]")

# 교차언어/특수 수동 매핑 (링크 → 실제 파일 stem)
ALIAS = {
    "NAVER": "네이버", "네이버(NAVER)": "네이버",
    "Alphabet": "alphabet",
    "브로드컴": "Broadcom",
    "마이크론 테크놀로지": "마이크론", "마이크론(Micron)": "마이크론",
    "마이크론 테크놀로지(Micron Technology)": "마이크론",
    "Intuitive Machines": "Intuitive_Machines",
    "달 탐사": "달_탐사",
}

TYPE_BY_DIR = {"stocks": "stock", "sectors": "sector", "themes": "theme",
               "analysts": "analyst", "macro": "macro"}


def build_valid():
    stems = set()
    for p in glob.glob("wiki/**/*.md", recursive=True) + glob.glob("raw/**/*.md", recursive=True):
        stems.add(os.path.splitext(os.path.basename(p))[0])
    return stems


def resolve(target, stems):
    """None=이미유효(유지), str=치환대상 stem, False=미해결."""
    t = target.strip()
    if "/" in t:           # raw/social/... 같은 경로 링크는 유지
        return None
    if t in stems:
        return None
    if t in ALIAS and ALIAS[t] in stems:
        return ALIAS[t]
    low = {s.lower(): s for s in stems}
    if t.lower() in low:
        return low[t.lower()]
    for cand in (t.replace(" ", "_"), t.replace("_", " ")):
        if cand in stems:
            return cand
    return False


def is_garbage(target):
    t = target.strip()
    return ("," in t) or ("…" in t) or ("..." in t) or len(t) > 24


def fix_links(stems):
    changed = {"normalized": 0, "unlinked": 0, "files": set()}
    for p in glob.glob("wiki/**/*.md", recursive=True):
        txt = open(p, encoding="utf-8").read()

        def repl(m):
            target, anchor, alias = m.group(1).strip(), m.group(2) or "", m.group(3) or ""
            r = resolve(target, stems)
            if r is None:
                return m.group(0)            # 유효 → 유지
            if r:                            # 정규화
                changed["normalized"] += 1; changed["files"].add(p)
                return f"[[{r}{anchor}{alias}]]"
            if is_garbage(target):           # 쓰레기 헤드라인 → 링크 해제
                changed["unlinked"] += 1; changed["files"].add(p)
                return (alias[1:] if alias else target)
            return m.group(0)                # 짧은 미존재 엔티티 → 보존
        new = WIKILINK.sub(repl, txt)
        if new != txt:
            open(p, "w", encoding="utf-8", newline="\n").write(new)
    return changed


def fix_frontmatter():
    fixed = []
    for d, typ in TYPE_BY_DIR.items():
        for p in glob.glob(f"wiki/{d}/*.md"):
            base = os.path.splitext(os.path.basename(p))[0]
            if base == "index":
                continue
            lines = open(p, encoding="utf-8").read().splitlines()
            if lines and lines[0].strip() == "---":
                # frontmatter 존재 — type 있나?
                end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
                if end is None:
                    continue
                keys = [ln.split(":", 1)[0].strip() for ln in lines[1:end] if ":" in ln]
                if "type" in keys:
                    continue
                ins = [f"type: {typ}"]
                if "name" not in keys:
                    ins.append(f"name: {base}")
                lines[1:1] = ins
                open(p, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
                fixed.append(p)
            else:
                # frontmatter 없음 — 새로 추가
                fm = ["---", f"type: {typ}", f"name: {base}", "---", ""]
                open(p, "w", encoding="utf-8", newline="\n").write("\n".join(fm) + "\n".join(lines) + "\n")
                fixed.append(p)
    return fixed


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    stems = build_valid()
    c = fix_links(stems)
    fm = fix_frontmatter()
    print(f"[1] 링크 정규화 {c['normalized']}건 · 쓰레기 링크 해제 {c['unlinked']}건 ({len(c['files'])}개 파일)")
    print(f"[3] 프론트매터 type 보강 {len(fm)}개:")
    for p in sorted(fm):
        print(f"    - {p.replace(chr(92), '/')}")


if __name__ == "__main__":
    main()
