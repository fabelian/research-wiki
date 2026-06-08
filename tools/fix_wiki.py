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
    "테슬라": "Tesla", "하나금투": "하나증권",
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
    if "/" in t:           # raw 경로 링크: 파일 있으면 유지, 없으면 미해결(→해제)
        return None if os.path.exists(t + ".md") else False
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
            if target.startswith("raw/") or is_garbage(target):  # 미존재 raw링크/쓰레기 헤드라인 → 해제
                changed["unlinked"] += 1; changed["files"].add(p)
                if alias:
                    return alias[1:]
                if target.startswith("raw/"):
                    return "🐦" + target.rsplit("_", 1)[-1]   # 블로거 id/키워드만 텍스트로
                return target
            return m.group(0)                # 짧은 미존재 엔티티 → 보존
        new = WIKILINK.sub(repl, txt)
        if new != txt:
            open(p, "w", encoding="utf-8", newline="\n").write(new)
    return changed


KEYLINE = re.compile(r"^[A-Za-z_][\w-]*:")


def dedup_frontmatter():
    """선두의 연속된 다중 프론트매터 블록을 1개로 병합(레이스로 생긴 이중 ---/type 정리)."""
    fixed = []
    for p in glob.glob("wiki/**/*.md", recursive=True):
        lines = open(p, encoding="utf-8").read().split("\n")
        n = len(lines)
        if not lines or lines[0].strip() != "---":
            continue
        keys, seen, pos, blocks = [], set(), 0, 0
        while pos < n and lines[pos].strip() == "---":
            j = pos + 1
            while j < n and lines[j].strip() != "---":
                if KEYLINE.match(lines[j]):
                    k = lines[j].split(":", 1)[0].strip()
                    if k not in seen:
                        seen.add(k); keys.append(lines[j].rstrip())
                j += 1
            blocks += 1
            pos = j + 1  # 닫는 --- 다음
            while pos < n and lines[pos].strip() == "":
                pos += 1  # 블록 사이 빈 줄 건너뜀
        if blocks <= 1:
            continue  # 단일 프론트매터 — 그대로
        body = "\n".join(lines[pos:]).lstrip("\n")
        open(p, "w", encoding="utf-8", newline="\n").write("---\n" + "\n".join(keys) + "\n---\n\n" + body + "\n")
        fixed.append(p)
    return fixed


def fix_frontmatter():
    fixed = []
    for d, typ in TYPE_BY_DIR.items():
        for p in glob.glob(f"wiki/{d}/*.md"):
            base = os.path.splitext(os.path.basename(p))[0]
            if base == "index":
                continue
            lines = open(p, encoding="utf-8").read().splitlines()
            if any(ln.startswith("type:") for ln in lines[:15]):
                continue  # 이미 type 있음(레이스로 인한 이중 추가 방지)
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
    dd = dedup_frontmatter()
    stems = build_valid()
    c = fix_links(stems)
    fm = fix_frontmatter()
    print(f"[0] 이중 프론트매터 병합 {len(dd)}개")
    print(f"[1] 링크 정규화 {c['normalized']}건 · 쓰레기 링크 해제 {c['unlinked']}건 ({len(c['files'])}개 파일)")
    print(f"[3] 프론트매터 type 보강 {len(fm)}개:")
    for p in sorted(fm):
        print(f"    - {p.replace(chr(92), '/')}")


if __name__ == "__main__":
    main()
