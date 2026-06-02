# research-wiki-app — Phase 1: Scaffold & Deploy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a deployable FastAPI + Postgres app on Railway with password login, the full DB schema migrated, and a protected empty dashboard — the foundation the later phases build on.

**Architecture:** Single Railway web service (FastAPI/Uvicorn) + Railway Postgres plugin. SQLAlchemy 2.0 ORM with Alembic migrations. Single-user auth via password + signed session cookie (Starlette SessionMiddleware). Server-rendered templates (Jinja2). The full data model (watchlist, news_items, change_proposals, proposal_news, job_runs) is created now in one migration so later phases only consume it.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2.0, Alembic, psycopg (v3), pydantic-settings, Jinja2, itsdangerous, pytest, httpx (TestClient). Deploy: Railway (Nixpacks or Dockerfile).

**Spec:** `research-wiki/docs/superpowers/specs/2026-06-02-railway-watchlist-news-wiki-design.md`

---

## File Structure (created in this phase)

```
research-wiki-app/
  app/
    __init__.py
    config.py            # env settings (pydantic-settings)
    db.py                # SQLAlchemy engine + session factory + Base
    models.py            # ALL ORM models (full schema)
    auth.py              # password check + require_login dependency
    main.py              # FastAPI app, SessionMiddleware, routers
    web/
      __init__.py
      routes.py          # /login, /logout, / (dashboard home)
      templates/
        base.html
        login.html
        index.html
  alembic/
    env.py               # wired to app.db.Base + DATABASE_URL
    versions/
      0001_initial.py    # full schema
  tests/
    conftest.py          # test client + in-memory/sqlite or pg fixture
    test_config.py
    test_auth.py
    test_dashboard.py
  alembic.ini
  pyproject.toml
  Dockerfile
  .env.example
  .gitignore
  README.md
```

Responsibilities: `config` = env only; `db` = connection only; `models` = schema only; `auth` = session/password only; `web/routes` = HTTP only; `main` = wiring only. One responsibility per file.

---

### Task 1: Create app repo + project scaffold

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.env.example`, `README.md`, `app/__init__.py`

- [ ] **Step 1: Create the GitHub repo and clone it locally**

```bash
gh repo create fabelian/research-wiki-app --private --clone
cd research-wiki-app
```
Expected: empty repo cloned into `research-wiki-app/`.

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "research-wiki-app"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.32",
  "sqlalchemy>=2.0",
  "psycopg[binary]>=3.2",
  "alembic>=1.14",
  "pydantic-settings>=2.6",
  "jinja2>=3.1",
  "python-multipart>=0.0.12",
  "itsdangerous>=2.2",
]

[project.optional-dependencies]
dev = ["pytest>=8.3", "httpx>=0.27"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 3: Write `.gitignore`**

```gitignore
__pycache__/
*.pyc
.venv/
.env
*.sqlite3
.pytest_cache/
```

- [ ] **Step 4: Write `.env.example`**

```bash
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/researchwiki
DASHBOARD_PASSWORD=change-me
SESSION_SECRET=change-me-long-random
# Phase 2+
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-6
GITHUB_TOKEN=
GITHUB_REPO=fabelian/research-wiki
WIKI_BRANCH=main
TZ=Asia/Seoul
```

- [ ] **Step 5: Write minimal `README.md`**

```markdown
# research-wiki-app
Watchlist news -> LLM proposals -> review -> commit to research-wiki (Quartz/Pages).
See spec in research-wiki/docs/superpowers/specs/.

## Dev
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -e ".[dev]"
cp .env.example .env   # fill values
alembic upgrade head
uvicorn app.main:app --reload
```

- [ ] **Step 6: Create empty package marker**

Create `app/__init__.py` (empty file).

- [ ] **Step 7: Set up venv and install**

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e ".[dev]"
```
Expected: install completes, `pytest --version` works.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "chore: scaffold project (pyproject, gitignore, env example)"
```

---

### Task 2: Config module

**Files:**
- Create: `app/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from app.config import Settings

def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/db")
    monkeypatch.setenv("DASHBOARD_PASSWORD", "secret")
    monkeypatch.setenv("SESSION_SECRET", "sess")
    s = Settings()
    assert s.database_url.startswith("postgresql+psycopg://")
    assert s.dashboard_password == "secret"
    assert s.anthropic_model == "claude-sonnet-4-6"  # default
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.config'`

- [ ] **Step 3: Write `app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    dashboard_password: str
    session_secret: str

    # Phase 2+ (optional now)
    naver_client_id: str = ""
    naver_client_secret: str = ""
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    github_token: str = ""
    github_repo: str = "fabelian/research-wiki"
    wiki_branch: str = "main"

def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat: env-driven settings"
```

---

### Task 3: Database engine + session

**Files:**
- Create: `app/db.py`

- [ ] **Step 1: Write `app/db.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings

class Base(DeclarativeBase):
    pass

_engine = None
_SessionLocal = None

def engine():
    global _engine
    if _engine is None:
        _engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    return _engine

def SessionLocal():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=engine(), autoflush=False, expire_on_commit=False)
    return _SessionLocal

def get_db():
    db = SessionLocal()()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: Sanity import check (no test needed yet)**

Run: `python -c "import app.db; print('ok')"`
Expected: prints `ok` (settings may need `.env`; if it errors on missing env, that's fine — confirms it reads config).

- [ ] **Step 3: Commit**

```bash
git add app/db.py
git commit -m "feat: db engine and session factory"
```

---

### Task 4: ORM models (full schema)

**Files:**
- Create: `app/models.py`
- Test: `tests/conftest.py`, `tests/test_models.py`

- [ ] **Step 1: Write `app/models.py`**

```python
from datetime import datetime
from sqlalchemy import (
    String, Text, Boolean, Integer, DateTime, ForeignKey, JSON, UniqueConstraint, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

class Watchlist(Base):
    __tablename__ = "watchlist"
    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(128))
    market: Mapped[str] = mapped_column(String(8))  # KR | US
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class NewsItem(Base):
    __tablename__ = "news_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    watchlist_id: Mapped[int] = mapped_column(ForeignKey("watchlist.id"))
    source: Mapped[str] = mapped_column(String(16), default="naver")
    url: Mapped[str] = mapped_column(Text)
    url_hash: Mapped[str] = mapped_column(String(40), unique=True)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="new")  # new|proposed|ingested|dismissed

class ChangeProposal(Base):
    __tablename__ = "change_proposals"
    id: Mapped[int] = mapped_column(primary_key=True)
    watchlist_id: Mapped[int] = mapped_column(ForeignKey("watchlist.id"))
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|approved|rejected
    summary: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)  # {files:[{path,action,new_content,diff,rationale}]}
    model: Mapped[str] = mapped_column(String(64), default="")
    cost_tokens: Mapped[int] = mapped_column(Integer, default=0)
    reviewer_note: Mapped[str] = mapped_column(Text, default="")
    commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class ProposalNews(Base):
    __tablename__ = "proposal_news"
    proposal_id: Mapped[int] = mapped_column(ForeignKey("change_proposals.id"), primary_key=True)
    news_item_id: Mapped[int] = mapped_column(ForeignKey("news_items.id"), primary_key=True)

class JobRun(Base):
    __tablename__ = "job_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), default="fetch_cycle")
    status: Mapped[str] = mapped_column(String(16), default="success")  # success|partial|failed
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 2: Write `tests/conftest.py` (sqlite in-memory for model tests)**

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base
import app.models  # noqa: F401  (register tables)

@pytest.fixture
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    try:
        yield s
    finally:
        s.close()
```

Note: add `pysqlite3`? No — Python ships `sqlite3`; SQLAlchemy uses it via `sqlite+pysqlite`. No extra dep.

- [ ] **Step 3: Write the failing test**

```python
# tests/test_models.py
from datetime import datetime, timezone
from app.models import Watchlist, NewsItem

def test_insert_watchlist_and_news(db_session):
    w = Watchlist(ticker="005930", name="삼성전자", market="KR", aliases=["삼성전자", "005930"])
    db_session.add(w); db_session.commit()
    assert w.id is not None and w.active is True

    n = NewsItem(watchlist_id=w.id, url="http://x/1", url_hash="h1", title="t",
                 published_at=datetime.now(timezone.utc))
    db_session.add(n); db_session.commit()
    assert n.status == "new"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS (tables created from models, rows insert).

- [ ] **Step 5: Commit**

```bash
git add app/models.py tests/conftest.py tests/test_models.py
git commit -m "feat: full ORM schema + model tests"
```

---

### Task 5: Alembic initial migration

**Files:**
- Create: `alembic.ini`, `alembic/env.py`, `alembic/versions/0001_initial.py`

- [ ] **Step 1: Initialize Alembic**

```bash
alembic init alembic
```
Expected: creates `alembic.ini` and `alembic/`.

- [ ] **Step 2: Edit `alembic/env.py` to use our Base + DATABASE_URL**

Replace the `target_metadata = None` line and config URL wiring with:

```python
from app.db import Base
from app.config import get_settings
import app.models  # noqa: F401  (register tables)

target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", get_settings().database_url)
```

(Keep the rest of the generated `env.py`. Ensure these imports are near the top after `config = context.config`.)

- [ ] **Step 3: Autogenerate the initial migration**

Requires a reachable DB. Start a local Postgres (Docker) or point `DATABASE_URL` at Railway dev DB, then:

```bash
alembic revision --autogenerate -m "initial schema"
```
Expected: creates `alembic/versions/<hash>_initial_schema.py` with all 5 tables. Rename file prefix to `0001_` for ordering clarity (optional).

- [ ] **Step 4: Apply and verify**

```bash
alembic upgrade head
```
Expected: tables created. Verify: `python -c "from sqlalchemy import inspect; from app.db import engine; print(sorted(inspect(engine()).get_table_names()))"`
Expected output includes: `['alembic_version','change_proposals','job_runs','news_items','proposal_news','watchlist']`

- [ ] **Step 5: Commit**

```bash
git add alembic.ini alembic/
git commit -m "feat: alembic initial schema migration"
```

---

### Task 6: FastAPI app + health endpoint

**Files:**
- Create: `app/main.py`, `app/web/__init__.py`, `app/web/routes.py`
- Test: `tests/test_dashboard.py` (health portion)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dashboard.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_ok():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dashboard.py::test_health_ok -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 3: Write `app/web/__init__.py` (empty) and `app/web/routes.py`**

```python
# app/web/routes.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/healthz")
def healthz():
    return {"status": "ok"}
```

- [ ] **Step 4: Write `app/main.py`**

```python
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from app.config import get_settings
from app.web.routes import router

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="research-wiki-app")
    app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
    app.include_router(router)
    return app

app = create_app()
```

Note: TestClient import triggers `get_settings()`. In CI/tests set env via `tests/conftest.py` autouse fixture (Step 5).

- [ ] **Step 5: Add autouse env fixture to `tests/conftest.py`**

Append to `tests/conftest.py`:

```python
@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("DASHBOARD_PASSWORD", "secret")
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_dashboard.py::test_health_ok -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add app/main.py app/web/ tests/test_dashboard.py tests/conftest.py
git commit -m "feat: FastAPI app + health endpoint"
```

---

### Task 7: Password login + session auth

**Files:**
- Create: `app/auth.py`, `app/web/templates/base.html`, `app/web/templates/login.html`
- Modify: `app/web/routes.py`
- Test: `tests/test_auth.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_auth.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_login_rejects_bad_password():
    r = client.post("/login", data={"password": "wrong"}, follow_redirects=False)
    assert r.status_code == 200
    assert "비밀번호" in r.text  # re-renders login with error

def test_login_accepts_and_sets_session():
    r = client.post("/login", data={"password": "secret"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/"

def test_protected_redirects_when_anonymous():
    fresh = TestClient(app)
    r = fresh.get("/", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_auth.py -v`
Expected: FAIL (no `/login` route, no protected `/`).

- [ ] **Step 3: Write `app/auth.py`**

```python
from fastapi import Request
from fastapi.responses import RedirectResponse
from app.config import get_settings

def is_authed(request: Request) -> bool:
    return request.session.get("authed") is True

def login(request: Request, password: str) -> bool:
    if password == get_settings().dashboard_password:
        request.session["authed"] = True
        return True
    return False

def logout(request: Request) -> None:
    request.session.clear()

def require_login(request: Request):
    """Dependency: returns None if authed, else raises via redirect sentinel."""
    if not is_authed(request):
        return RedirectResponse("/login", status_code=303)
    return None
```

- [ ] **Step 4: Write `app/web/templates/base.html`**

```html
<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<title>{% block title %}research-wiki-app{% endblock %}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
</head><body>
<main>{% block body %}{% endblock %}</main>
</body></html>
```

- [ ] **Step 5: Write `app/web/templates/login.html`**

```html
{% extends "base.html" %}
{% block title %}로그인{% endblock %}
{% block body %}
<h1>로그인</h1>
{% if error %}<p style="color:red">비밀번호가 올바르지 않습니다.</p>{% endif %}
<form method="post" action="/login">
  <input type="password" name="password" placeholder="비밀번호" autofocus>
  <button type="submit">로그인</button>
</form>
{% endblock %}
```

- [ ] **Step 6: Rewrite `app/web/routes.py`**

```python
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from app import auth

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")

@router.get("/healthz")
def healthz():
    return {"status": "ok"}

@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(request, "login.html", {})

@router.post("/login")
def login_submit(request: Request, password: str = Form(...)):
    if auth.login(request, password):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"error": True})

@router.get("/logout")
def logout(request: Request):
    auth.logout(request)
    return RedirectResponse("/login", status_code=303)

@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    if not auth.is_authed(request):
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "index.html",
                                      {"pending": 0, "runs": [], "watch_counts": []})
```

- [ ] **Step 7: Write placeholder `app/web/templates/index.html`**

```html
{% extends "base.html" %}
{% block title %}대시보드{% endblock %}
{% block body %}
<h1>셀사이드 리서치 위키 — 관리</h1>
<p>검토 대기: {{ pending }}건</p>
<p><a href="/logout">로그아웃</a></p>
{% endblock %}
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `pytest tests/test_auth.py -v`
Expected: PASS (3 tests).

- [ ] **Step 9: Commit**

```bash
git add app/auth.py app/web/routes.py app/web/templates/
git commit -m "feat: password login + session-protected dashboard"
```

---

### Task 8: Full test run + Dockerfile + Railway config

**Files:**
- Create: `Dockerfile`, `railway.json`

- [ ] **Step 1: Run the whole suite**

Run: `pytest -v`
Expected: all tests PASS (config, models, dashboard health, auth).

- [ ] **Step 2: Write `Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .
COPY . .
ENV PORT=8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
```

- [ ] **Step 3: Write `railway.json`**

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": { "builder": "DOCKERFILE", "dockerfilePath": "Dockerfile" },
  "deploy": { "restartPolicyType": "ON_FAILURE", "restartPolicyMaxRetries": 3 }
}
```

- [ ] **Step 4: Build the image locally to verify it compiles**

Run: `docker build -t research-wiki-app .`
Expected: build succeeds. (If Docker unavailable locally, skip and rely on Railway build in Task 9.)

- [ ] **Step 5: Commit**

```bash
git add Dockerfile railway.json
git commit -m "chore: Dockerfile + Railway build config"
git push -u origin main
```

---

### Task 9: Deploy to Railway (web + Postgres)

**Files:** none (infra). Manual/CLI steps.

- [ ] **Step 1: Create Railway project + Postgres**

```bash
railway login
railway init                 # create project, link this repo dir
railway add --database postgres
```
Expected: project created; Postgres plugin provisions `DATABASE_URL`.

- [ ] **Step 2: Set service env vars**

Set in Railway dashboard or CLI (`railway variables --set KEY=VALUE`):
```
DASHBOARD_PASSWORD=<strong>
SESSION_SECRET=<long random>
TZ=Asia/Seoul
```
(DATABASE_URL is injected automatically by the Postgres plugin. Phase 2+ keys added later.)

Note: Railway's `DATABASE_URL` is `postgresql://...`; SQLAlchemy+psycopg v3 needs `postgresql+psycopg://...`. In `app/config.py`, normalize: if `database_url` starts with `postgresql://`, replace prefix with `postgresql+psycopg://`. Add this now:

```python
# in app/config.py, after class Settings — add a validator
from pydantic import field_validator

    @field_validator("database_url")
    @classmethod
    def _normalize(cls, v: str) -> str:
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v
```
Commit this fix: `git add app/config.py && git commit -m "fix: normalize Railway DATABASE_URL for psycopg" && git push`

- [ ] **Step 3: Deploy**

```bash
railway up
```
Expected: build runs Dockerfile, container starts, `alembic upgrade head` runs migration on Railway Postgres, Uvicorn boots.

- [ ] **Step 4: Generate a public domain and verify health**

```bash
railway domain
```
Then: `curl -s https://<domain>/healthz`
Expected: `{"status":"ok"}`

- [ ] **Step 5: Verify login works in browser**

Open `https://<domain>/` → redirects to `/login` → enter `DASHBOARD_PASSWORD` → lands on dashboard.
Expected: anonymous `/` redirects to login; correct password reaches dashboard; wrong password shows error.

- [ ] **Step 6: Verify migration applied on Railway**

```bash
railway run python -c "from sqlalchemy import inspect; from app.db import engine; print(sorted(inspect(engine()).get_table_names()))"
```
Expected: lists all 5 tables + `alembic_version`.

---

## Phase 1 Done When
- `pytest -v` green locally.
- Railway web service live; `/healthz` returns ok; login gate works.
- All 5 tables migrated on Railway Postgres.
- Repo `fabelian/research-wiki-app` on `main` with everything committed.

---

## Subsequent Phases (each becomes its own plan when Phase 1 lands)

- **Phase 2 — Fetch:** `watchlist` CRUD UI; `app/services/naver_client.py` (httpx, respx-mocked tests); `app/services/dedup.py` (url_hash, pure-function tests); `/news` list; manual "fetch now" → writes `news_items` + `job_runs`. Add deps: `httpx`, `respx` (dev). Add env: `NAVER_CLIENT_ID/SECRET`.
- **Phase 3 — Propose:** `app/services/wiki_repo.py` (shallow clone + read pages, subprocess git, temp-repo tests); `app/services/proposer.py` (Anthropic structured output → `ChangeProposal`, mocked-SDK tests, prompt caching, CLAUDE.md schema injected); `app/services/validator.py` (citation/over-deletion/source checks, pure tests); writes `change_proposals`; `/proposals` + `/proposals/{id}` diff view (`difflib`). Add deps: `anthropic`. Add env: `ANTHROPIC_API_KEY/MODEL`, `GITHUB_TOKEN/REPO`.
- **Phase 4 — Approve & publish:** `app/services/review_service.py` (apply approved files → commit → push, with re-clone/retry; temp-repo tests); approve/reject/edit endpoints (HTMX); on approve set `commit_sha`, mark `ingested`/`approved`; verify existing Quartz Action auto-deploys.
- **Phase 5 — Schedule & observability:** `app/worker/run_cycle.py` entrypoint (orchestrates fetch→propose per active ticker, per-ticker isolation, writes `job_runs`); Railway Cron schedule `0 22 * * *` UTC; `/runs` view; structured logging; `cost_tokens` accounting.

---

## Self-Review (completed)

- **Spec coverage:** Phase 1 covers spec §3 (architecture skeleton), §5 (full data model — all tables created now), §7 (login + dashboard shell), §8 (Railway deploy + secrets). Spec §6/§9/§10/§11 map to Phases 2–5 (listed above). No Phase-1 requirement left untasked.
- **Placeholder scan:** No TBD/TODO; every code step has concrete code; infra steps have exact commands + expected output.
- **Type consistency:** `Settings` fields used in `db.py`/`auth.py` match definitions; model table/column names match the migration source (autogenerated from `models.py`); `auth.is_authed/login/logout` names consistent across `auth.py` and `routes.py`; templates referenced (`login.html`, `index.html`, `base.html`) all created.
- **Note:** `require_login` defined in `auth.py` but routes use explicit `auth.is_authed` checks (simpler for redirect semantics); `require_login` retained for Phase 2+ dependency use. Not a contradiction — documented here.
