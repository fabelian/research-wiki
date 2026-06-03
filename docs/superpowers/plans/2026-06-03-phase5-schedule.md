# research-wiki-app — Phase 5: Schedule + async triggers + observability

> REQUIRED SUB-SKILL: superpowers:executing-plans.

**Goal:** Run the full cycle (fetch → propose) automatically once a day, make the manual web triggers non-blocking (fixing the HTTP timeout), and expose run history at /runs.

**Architecture:** Single web service (Approach A) with an **in-process APScheduler** firing `run_cycle` daily (07:00 KST = 22:00 UTC), gated by `ENABLE_SCHEDULER`. Manual `/fetch` and `/propose` use FastAPI `BackgroundTasks` so requests return immediately. `/runs` lists `job_runs`.

**Tech Stack:** + apscheduler.

## Files
```
app/worker/run_cycle.py   # run_cycle(): run_fetch() then generate_proposals(); __main__ entry
app/scheduler.py          # build_scheduler()/start_scheduler() — daily CronTrigger
app/config.py             # + enable_scheduler: bool=False, cron_hour_utc: int=22
app/main.py               # lifespan: start scheduler if enabled; shutdown on exit
app/web/routes.py         # /fetch,/propose -> BackgroundTasks; add /runs
app/web/templates/runs.html ; index.html nav += /runs
pyproject.toml            # + apscheduler
tests/test_run_cycle.py, test_web_runs.py, test_scheduler.py
```

## Tasks
1. deps: add apscheduler; install.
2. config: enable_scheduler (False), cron_hour_utc (22).
3. run_cycle: TDD — monkeypatch run_fetch/generate_proposals -> returns {"fetch":..,"propose":..}.
4. scheduler: build_scheduler() registers job id "daily_cycle" (test: get_job not None, no start()).
5. main lifespan: start scheduler only if settings.enable_scheduler (off in tests).
6. routes: /fetch,/propose via BackgroundTasks (call run_fetch()/generate_proposals() with own session); /runs list. TDD: /runs shows seeded JobRun; anon blocked.
7. deploy: railway up; set ENABLE_SCHEDULER=1 (+ optional CRON_HOUR_UTC). Verify /runs renders; manual "지금 수집" returns instantly and a job_run appears shortly after.

## Notes
- Single web instance assumed (replicas=1) so the in-process scheduler fires once. Note in README if scaling.
- run_fetch/generate_proposals already manage their own sessions + job_runs; run_cycle just chains them.
- Daily auto-propose consumes Anthropic tokens — intended (review gate still requires human approve before publish).
