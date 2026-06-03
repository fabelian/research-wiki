# research-wiki-app — Phase 3: LLM change proposals Implementation Plan

> REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use `- [ ]`.

**Goal:** From collected `new` news, have Claude propose wiki edits (full target file contents + rationale) following the CLAUDE.md schema, validate them, store as `change_proposals` (status=pending) with diffs, and review them in the dashboard. No commit/push yet (Phase 4).

**Architecture:** `wiki_repo` shallow-clones the (public) research-wiki repo to read CLAUDE.md + relevant pages. `proposer` calls Claude with forced tool-use (structured `ChangeProposal`) + prompt caching of the schema. `validator` flags hallucinated citations / over-deletion / missing-target. `worker/propose.generate_proposals` orchestrates per active ticker; diffs via difflib. Dashboard lists proposals and shows per-file diffs.

**Tech Stack:** + anthropic SDK. Read-only git clone (no token needed for public repo; GITHUB_TOKEN used if present).

**Spec:** research-wiki/docs/superpowers/specs/2026-06-02-...-design.md §6.2–6.3

---

## Files
```
app/services/wiki_repo.py     # clone_repo()->Path, read_file(repo,rel), relevant_pages(repo,name), cleanup(repo)
app/services/proposer.py      # propose(name,ticker,news_items,schema_md,current_pages,client)->dict (tool-use + cache)
app/services/validator.py     # validate(proposal,news_items,current_pages)->[flag str]
app/worker/propose.py         # generate_proposals(db,wiki_clone,client): new news -> proposal rows + diffs
app/web/routes.py             # ADD /proposals, /proposals/{id}, POST /propose
app/web/templates/proposals.html, proposal_detail.html
tests/test_validator.py, test_proposer.py, test_propose_worker.py, test_wiki_repo.py
pyproject.toml                # + anthropic
```

## Task 1: deps
- [ ] Add `anthropic>=0.40` to dependencies; `pip install anthropic`.

## Task 2: validator (pure TDD)
- [ ] test: hallucinated citation (not in news urls) flagged; update to missing path flagged; >30% line deletion flagged; clean proposal -> [].
- [ ] Implement `validate(proposal, news_items, current_pages)`.

## Task 3: wiki_repo (TDD with temp dir / mocked subprocess)
- [ ] test_read_file: create temp dir with a file -> read_file returns text; missing -> None. test clone_repo builds expected git args (monkeypatch subprocess.run).
- [ ] Implement clone_repo/read_file/relevant_pages/cleanup.

## Task 4: proposer (TDD mocked Anthropic)
- [ ] test: fake client returns a tool_use block -> propose() returns dict with files/citations + _tokens/_model. Assert tool_choice forced, schema present in call.
- [ ] Implement propose() with forced tool-use + system cache_control on schema.

## Task 5: propose worker (integration TDD)
- [ ] test: seed watchlist + 2 new NewsItem (sqlite); monkeypatch wiki_repo.clone_repo/read_file/relevant_pages and proposer.propose -> generate_proposals creates 1 ChangeProposal (pending) with computed diff, links proposal_news, flips those news to status='proposed'. Re-run: no new proposal (no new news).
- [ ] Implement generate_proposals(db, client) with difflib unified diffs; cleanup temp clone.

## Task 6: web (proposals list + diff detail + trigger)
- [ ] test: login; seed a pending proposal; GET /proposals lists it; GET /proposals/{id} shows file path + diff + flags; anonymous blocked.
- [ ] Implement routes + templates (difflib HTML render). POST /propose calls generate_proposals, redirects to /proposals. Dashboard `pending` count wired.

## Task 7: deploy + live
- [ ] Tests green; commit+push; `railway up --ci`. Verify /proposals after login.
- [ ] Live: with ANTHROPIC_API_KEY set + new news present, POST /propose -> a real proposal appears with a sensible diff for an existing stock page (e.g., 삼성전자).

## Notes
- Proposer reads CLAUDE.md from the clone and injects it (schema contract). Citations restricted to provided news URLs (validator enforces).
- payload.files[].new_content = full target file; diff stored for review. Apply/commit is Phase 4.
- Per-ticker isolation; cleanup temp clone in finally.
