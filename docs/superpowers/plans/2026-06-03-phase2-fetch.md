# research-wiki-app — Phase 2: Fetch (watchlist + Naver news) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** Manage a watchlist and fetch Naver news for active tickers into `news_items` (deduped), recording each run in `job_runs`, with dashboard pages and a manual "fetch now" trigger.

**Architecture:** New `app/services/` (naver_client, dedup) + `app/worker/fetch.py` orchestrator. New authed routes for watchlist CRUD, news list, and POST /fetch. TDD with respx-mocked HTTP — no real Naver key needed to build/test; live fetch needs `NAVER_CLIENT_ID/SECRET` in Railway env.

**Tech Stack:** + httpx (runtime), respx (dev). Reuses Phase 1 stack.

**Spec:** research-wiki/docs/superpowers/specs/2026-06-02-railway-watchlist-news-wiki-design.md §6.1

---

## File Structure
```
app/services/__init__.py
app/services/naver_client.py   # search_news(query)->[normalized], url_hash(), clean HTML, parse pubDate
app/services/dedup.py          # filter_new(items, seen_hashes)->fresh (dedupe within batch + vs seen)
app/worker/__init__.py
app/worker/fetch.py            # run_fetch(db): active watchlist -> naver -> dedup -> news_items + job_run
app/web/routes.py              # ADD watchlist CRUD, /news, POST /fetch (all authed)
app/web/templates/watchlist.html, news.html ; index.html updated
tests/test_naver_client.py, test_dedup.py, test_fetch.py, test_web_watchlist.py
pyproject.toml                 # httpx -> runtime dep; respx -> dev dep
```

## Task 1: deps
- [ ] Move `httpx` to runtime deps, add `respx` to dev in pyproject.toml; reinstall `pip install -e ".[dev]"`.
- [ ] Commit.

## Task 2: dedup (pure, TDD)
- [ ] test_dedup: filter_new removes hashes already seen and duplicates within the batch; preserves order.
- [ ] Implement `app/services/dedup.py` `filter_new(items, seen_hashes)`.
- [ ] Run tests, commit.

## Task 3: naver_client (respx-mocked TDD)
- [ ] test_naver_client: mock Naver JSON response → search_news returns normalized dicts (url, url_hash, title/desc HTML-stripped, published_at tz-aware, raw); url_hash stable.
- [ ] Implement `app/services/naver_client.py` (httpx GET openapi.naver.com/v1/search/news.json with X-Naver headers; clean `<b>`/entities; parse RFC-2822 pubDate; prefer originallink).
- [ ] Run tests, commit.

## Task 4: fetch orchestrator (integration TDD)
- [ ] test_fetch: seed 1 active watchlist in sqlite; monkeypatch naver_client.search_news to return 2 items (1 dup of existing) → run_fetch writes only new news_items, sets last_fetched_at, creates a job_run with stats; second run adds nothing (idempotent).
- [ ] Implement `app/worker/fetch.py` `run_fetch(db=None, client=None)` with per-ticker try/except (errors -> job partial), global url_hash guard.
- [ ] Run tests, commit.

## Task 5: web — watchlist CRUD + news + fetch trigger
- [ ] test_web_watchlist: login; POST /watchlist adds row; GET shows it; POST /watchlist/{id}/toggle flips active; POST /watchlist/{id}/delete removes; all redirect 303; anonymous blocked.
- [ ] Implement routes (use get_db dependency) + templates watchlist.html, news.html; update index.html counts; POST /fetch calls run_fetch and redirects to /news.
- [ ] Run tests, commit + push.

## Task 6: deploy
- [ ] `railway up --service research-wiki-app --ci`; verify /watchlist (after login) renders.
- [ ] Add live keys: `railway variables --service research-wiki-app --set NAVER_CLIENT_ID=.. --set NAVER_CLIENT_SECRET=..` (USER provides) → redeploy → real "fetch now" test.

## Notes
- url_hash globally unique (Phase 1 schema) → dedup is global; fetch guards against cross-ticker duplicate inserts.
- Manual trigger only this phase; Railway Cron scheduling is Phase 5.
