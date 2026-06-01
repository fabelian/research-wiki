#!/usr/bin/env node
/**
 * stage.mjs — 위키 원본을 Quartz 빌드 입력(content/)으로 복사한다.
 *
 * 작성 원본은 wiki/ + index.md (Obsidian 볼트 + CLAUDE.md ingest 워크플로)에 그대로 두고,
 * content/ 는 매 빌드마다 새로 생성되는 산출물(gitignore)이다. → 단일 소스 유지.
 *
 * 발행 대상: index.md(홈) + wiki/(컴파일된 지식) + raw/reports/(출처 원문)
 * 제외: CLAUDE.md, log.md (스키마·운영 메타), .obsidian, .omc 등
 */
import { rmSync, mkdirSync, cpSync, existsSync } from "node:fs"

const OUT = "content"

if (existsSync(OUT)) rmSync(OUT, { recursive: true, force: true })
mkdirSync(OUT, { recursive: true })

// 홈페이지
cpSync("index.md", `${OUT}/index.md`)

// 컴파일된 위키 페이지
cpSync("wiki", `${OUT}/wiki`, { recursive: true })

// 출처 원문 (citations)
if (existsSync("raw")) cpSync("raw", `${OUT}/raw`, { recursive: true })

console.log("staged -> content/ (index.md + wiki/ + raw/)")
