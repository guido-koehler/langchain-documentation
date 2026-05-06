# LangChain Multi-Agent — Implementation Guide for TJ-Sales

> **Companion to:** `docs/langchain-multi-agent-evaluation.md`  
> **Purpose:** Step-by-step instructions to implement every agent described in the evaluation document.  
> **Follow the phases in order.** Each phase builds on the previous one.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Project Structure Setup](#2-project-structure-setup)
3. [Dependencies & Environment](#3-dependencies--environment)
4. [Shared Infrastructure](#4-shared-infrastructure)
   - 4.1 [Settings](#41-settings)
   - 4.2 [LLM Client](#42-llm-client)
   - 4.3 [LangGraph Checkpointer](#43-langgraph-checkpointer)
5. [Shared Tools](#5-shared-tools)
   - 5.1 [Filesystem Tools](#51-filesystem-tools)
   - 5.2 [.NET / dotnet CLI Tools](#52-net--dotnet-cli-tools)
   - 5.3 [Nx / pnpm Tools](#53-nx--pnpm-tools)
   - 5.4 [GitHub Tools](#54-github-tools)
   - 5.5 [Jira Tools](#55-jira-tools)
6. [Convention Files](#6-convention-files)
7. [Phase 1 — Code Review Agent](#7-phase-1--code-review-agent)
8. [Phase 2 — Translation Agent](#8-phase-2--translation-agent)
9. [Phase 3 — CI/CD Monitor Agent](#9-phase-3--cicd-monitor-agent)
10. [Phase 4 — Backend Scaffold Agent](#10-phase-4--backend-scaffold-agent)
11. [Phase 5 — Full Feature Workflow](#11-phase-5--full-feature-workflow)
    - 11.1 [Feature Planner Agent](#111-feature-planner-agent)
    - 11.2 [Frontend Scaffold Agent](#112-frontend-scaffold-agent)
    - 11.3 [Test Writer Agent](#113-test-writer-agent)
    - 11.4 [LangGraph Feature Graph](#114-langgraph-feature-graph)
12. [Release Notes Agent](#12-release-notes-agent)
13. [Webhook Server & Entry Point](#13-webhook-server--entry-point)
14. [Observability](#14-observability)
15. [Testing the Agents](#15-testing-the-agents)
16. [Deployment](#16-deployment)

---

## 1. Prerequisites

Before writing any code, ensure the following are in place:

### Accounts & Tokens

| Requirement | Where to get it | Environment variable |
|---|---|---|
| Azure OpenAI endpoint + key | Azure Portal → your OpenAI resource | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY` |
| Azure OpenAI deployment name | Azure AI Studio → Deployments | `AZURE_OPENAI_DEPLOYMENT` |
| GitHub Personal Access Token (PAT) with `repo`, `pull_requests`, `actions` scopes | GitHub → Settings → Developer settings → PAT | `GITHUB_TOKEN` |
| Jira API token | `id.atlassian.com` → Security → API tokens | `JIRA_API_TOKEN` |
| Jira base URL + user email | Your Atlassian instance URL | `JIRA_BASE_URL`, `JIRA_USER_EMAIL` |
| LangSmith API key (optional but recommended) | `smith.langchain.com` | `LANGCHAIN_API_KEY` |

### Local Toolchain

```bash
# Verify required tools are available on PATH
python --version          # 3.11+
dotnet --version          # 8.x
node --version            # 20+
pnpm --version            # 9+
gh --version              # GitHub CLI
git --version
```

### Python Version

Use the same Python version as the existing `ai/` service (3.11+). Create a dedicated virtual environment for the agents package to avoid dependency conflicts with `ai/`.

---

## 2. Project Structure Setup

Create the `agents/` directory at the repository root, alongside the existing `ai/` directory:

```
tj-sales/
├── ai/                   # Existing AI service (do not modify)
├── agents/               # NEW — agent orchestration layer
│   ├── .env.example
│   ├── requirements.txt
│   ├── main.py
│   ├── config/
│   │   └── settings.py
│   ├── conventions/
│   │   ├── backend-patterns.md
│   │   ├── frontend-patterns.md
│   │   └── test-patterns.md
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── filesystem_tools.py
│   │   ├── dotnet_tools.py
│   │   ├── nx_tools.py
│   │   ├── github_tools.py
│   │   └── jira_tools.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── code_review.py
│   │   ├── translation.py
│   │   ├── ci_monitor.py
│   │   ├── backend_scaffold.py
│   │   ├── planner.py
│   │   ├── frontend_scaffold.py
│   │   ├── test_writer.py
│   │   └── release_notes.py
│   ├── graphs/
│       ├── __init__.py
│       ├── feature_workflow.py
│       ├── review_workflow.py
│       └── ci_recovery_workflow.py
│   └── evals/
│       ├── __init__.py
│       ├── create_dataset.py
│       ├── evaluators.py
│       └── run_eval.py
├── backend-v2/
├── frontend/
└── ...
```

Run once to create the skeleton:

```bash
cd tj-sales
mkdir -p agents/config agents/conventions agents/tools agents/agents agents/graphs
touch agents/tools/__init__.py agents/agents/__init__.py agents/graphs/__init__.py
```

---

## 3. Dependencies & Environment

### `agents/requirements.txt`

```text
# LangChain + LangGraph
langchain>=1.0.0
langchain-core>=1.0.0
langgraph>=1.0.0
langgraph-checkpoint-sqlite>=2.0.0    # required for AsyncSqliteSaver
langchain-openai>=0.3.0               # Azure OpenAI integration

# HTTP & API clients
httpx>=0.27.0                   # async HTTP (Jira, GitHub REST)
PyGithub>=2.3.0                 # GitHub API wrapper

# Web server (for webhooks)
fastapi>=0.115.0
uvicorn[standard]>=0.30.0

# Config
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0

# Observability
langsmith>=0.3.0

# Utilities
tenacity>=9.0.0
```

Install:

```bash
cd agents
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### `agents/.env.example`

```dotenv
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o          # deployment name for scaffolding / review
AZURE_OPENAI_MINI_DEPLOYMENT=gpt-4o-mini  # cheaper model for translation / summaries

# GitHub
GITHUB_TOKEN=ghp_...
GITHUB_REPO=Gedat-GmbH/tj-sales

# Jira
JIRA_BASE_URL=https://your-org.atlassian.net
JIRA_USER_EMAIL=your@email.com
JIRA_API_TOKEN=your-jira-token
JIRA_PROJECT_KEY=TJS

# Repository root (absolute path on the machine running agents)
REPO_ROOT=/path/to/tj-sales

# LangSmith (optional)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=ls__...
LANGCHAIN_PROJECT=tj-sales-agents

# Webhook server
WEBHOOK_SECRET=a-random-string-to-validate-github-webhooks
WEBHOOK_PORT=8080
```

---

## 4. Shared Infrastructure

### 4.1 Settings

**`agents/config/settings.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Azure OpenAI
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_mini_deployment: str = "gpt-4o-mini"

    # GitHub
    github_token: str
    github_repo: str = "Gedat-GmbH/tj-sales"

    # Jira
    jira_base_url: str
    jira_user_email: str
    jira_api_token: str
    jira_project_key: str = "TJS"

    # Local paths
    repo_root: Path

    # Webhook
    webhook_secret: str = ""
    webhook_port: int = 8080


settings = Settings()
```

### 4.2 LLM Client

**`agents/config/llm.py`**

```python
from langchain_openai import AzureChatOpenAI
from agents.config.settings import settings


def get_llm(mini: bool = False) -> AzureChatOpenAI:
    """
    Returns an Azure OpenAI chat model.
    Use mini=True for cheap, high-throughput tasks (translation, summaries).
    Use mini=False (default) for code generation and complex reasoning.
    """
    deployment = (
        settings.azure_openai_mini_deployment if mini
        else settings.azure_openai_deployment
    )
    return AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        azure_deployment=deployment,
        api_version="2024-08-01-preview",
        temperature=0,          # deterministic output for code generation
        max_retries=3,
    )
```

### 4.3 LangGraph Checkpointer

The checkpointer persists agent state so that workflows can be paused (human-in-the-loop) and resumed without losing progress.

**`agents/config/checkpointer.py`**

```python
from contextlib import asynccontextmanager
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pathlib import Path
from agents.config.settings import settings

# Store state in a local SQLite file next to the repo
_DB_PATH = settings.repo_root / ".agents" / "checkpoints.db"
_DB_PATH.parent.mkdir(exist_ok=True)


@asynccontextmanager
async def get_checkpointer():
    """Yields an async SQLite checkpointer for LangGraph state persistence."""
    async with AsyncSqliteSaver.from_conn_string(str(_DB_PATH)) as checkpointer:
        yield checkpointer
```

> **Note:** For multi-machine or containerised deployments, swap `AsyncSqliteSaver` for `AsyncRedisSaver` from `langgraph-checkpoint-redis`.

---

## 5. Shared Tools

Every tool is a plain async Python function decorated with `@tool` from LangChain. Agents import and bind only the tools they need.

### 5.1 Filesystem Tools

**`agents/tools/filesystem_tools.py`**

```python
import os
from pathlib import Path
from langchain_core.tools import tool
from agents.config.settings import settings


def _resolve(relative_path: str) -> Path:
    """Resolve a repo-relative path safely."""
    full = (settings.repo_root / relative_path).resolve()
    # Guard against path traversal outside the repo
    if not str(full).startswith(str(settings.repo_root.resolve())):
        raise ValueError(f"Path {relative_path!r} escapes the repository root.")
    return full


@tool
def read_file(relative_path: str) -> str:
    """Read the contents of a file relative to the repository root."""
    return _resolve(relative_path).read_text(encoding="utf-8")


@tool
def write_file(relative_path: str, content: str) -> str:
    """Write content to a file relative to the repository root. Creates parent dirs."""
    path = _resolve(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"Written {len(content)} chars to {relative_path}"


@tool
def list_files(relative_dir: str, pattern: str = "**/*") -> list[str]:
    """List files matching a glob pattern under a directory (repo-relative)."""
    base = _resolve(relative_dir)
    return [
        str(p.relative_to(settings.repo_root))
        for p in base.glob(pattern)
        if p.is_file()
    ]


@tool
def search_in_files(relative_dir: str, search_string: str) -> list[str]:
    """Find lines containing search_string across all files in a directory."""
    results = []
    base = _resolve(relative_dir)
    for p in base.rglob("*"):
        if p.is_file():
            try:
                for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                    if search_string in line:
                        results.append(f"{p.relative_to(settings.repo_root)}:{i}: {line.strip()}")
            except Exception:
                pass
    return results
```

### 5.2 .NET / dotnet CLI Tools

**`agents/tools/dotnet_tools.py`**

```python
import asyncio
from langchain_core.tools import tool
from agents.config.settings import settings


async def _run(cmd: list[str], cwd: str | None = None, timeout: int = 120) -> dict:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd or str(settings.repo_root / "backend-v2"),
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return {"exit_code": -1, "stdout": "", "stderr": f"Timed out after {timeout}s"}
    return {
        "exit_code": proc.returncode,
        "stdout": stdout.decode(errors="replace"),
        "stderr": stderr.decode(errors="replace"),
    }


@tool
async def dotnet_build(project_or_solution: str = "") -> dict:
    """
    Build the .NET solution or a specific project.
    Pass a path relative to backend-v2/ or leave empty to build the full solution.
    Returns exit_code, stdout, stderr.
    """
    target = project_or_solution or "Gedat.TimeJobOnline.Sales.sln"
    return await _run(["dotnet", "build", target, "--no-restore", "-v", "quiet"])


@tool
async def dotnet_restore() -> dict:
    """Restore NuGet packages for the solution."""
    return await _run(["dotnet", "restore", "Gedat.TimeJobOnline.Sales.sln"])


@tool
async def dotnet_test_unit(filter_expression: str = ".UnitTest") -> dict:
    """
    Run .NET unit tests. Defaults to --filter .UnitTest.
    Returns exit_code, stdout (includes test summary), stderr.
    """
    return await _run(
        ["dotnet", "test", "--filter", filter_expression, "--no-build", "-v", "normal"],
        timeout=180,
    )


@tool
async def dotnet_format(project_path: str = "") -> dict:
    """Run dotnet format on a project to auto-fix style issues."""
    target = project_path or "Gedat.TimeJobOnline.Sales.sln"
    return await _run(["dotnet", "format", target])
```

### 5.3 Nx / pnpm Tools

**`agents/tools/nx_tools.py`**

```python
import asyncio
from langchain_core.tools import tool
from agents.config.settings import settings

_FRONTEND = str(settings.repo_root / "frontend")


async def _nx(args: list[str], timeout: int = 120) -> dict:
    proc = await asyncio.create_subprocess_exec(
        "pnpm", "nx", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=_FRONTEND,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return {"exit_code": -1, "stdout": "", "stderr": f"Timed out after {timeout}s"}
    return {
        "exit_code": proc.returncode,
        "stdout": stdout.decode(errors="replace"),
        "stderr": stderr.decode(errors="replace"),
    }


@tool
async def nx_build(project: str) -> dict:
    """Build an Nx project (e.g. 'sales', 'shared')."""
    return await _nx(["run", f"{project}:build"], timeout=180)


@tool
async def nx_test(project: str) -> dict:
    """Run Vitest tests for an Nx project."""
    return await _nx(["run", f"{project}:test"], timeout=120)


@tool
async def nx_lint(project: str) -> dict:
    """Lint an Nx project with ESLint."""
    return await _nx(["run", f"{project}:lint"])


@tool
async def nx_generate_component(project: str, name: str, path: str) -> dict:
    """
    Generate an Angular standalone component with OnPush change detection.
    Example: project='sales', name='my-component', path='feature/my-feature'
    """
    return await _nx([
        "generate", "@schematics/angular:component",
        f"--name={path}/{name}",
        f"--project={project}",
        "--changeDetection=OnPush",
        "--inlineTemplate=true",
        "--standalone=true",
        "--skipTests=true",
    ])


@tool
async def nx_generate_service(project: str, name: str, path: str) -> dict:
    """Generate an Angular service in the given project."""
    return await _nx([
        "generate", "@schematics/angular:service",
        f"--name={path}/{name}",
        f"--project={project}",
    ])


@tool
async def nx_openapi_gen() -> dict:
    """Regenerate the frontend API client from the backend Swagger definition."""
    return await _nx(["run", "shared:openapi-gen"], timeout=60)
```

### 5.4 GitHub Tools

**`agents/tools/github_tools.py`**

```python
import httpx
from langchain_core.tools import tool
from agents.config.settings import settings

_HEADERS = {
    "Authorization": f"Bearer {settings.github_token}",
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
_BASE = "https://api.github.com"
_REPO = settings.github_repo


@tool
async def get_pr_diff(pr_number: int) -> str:
    """Fetch the unified diff of a pull request."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_BASE}/repos/{_REPO}/pulls/{pr_number}",
            headers={**_HEADERS, "Accept": "application/vnd.github.v3.diff"},
        )
        r.raise_for_status()
        return r.text


@tool
async def get_pr_details(pr_number: int) -> dict:
    """Fetch metadata (head branch, title, author) for a pull request."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_BASE}/repos/{_REPO}/pulls/{pr_number}", headers=_HEADERS
        )
        r.raise_for_status()
        return r.json()


@tool
async def post_pr_review_comment(pr_number: int, body: str, commit_id: str, path: str, line: int) -> dict:
    """Post an inline review comment on a specific line of a PR diff."""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{_BASE}/repos/{_REPO}/pulls/{pr_number}/comments",
            headers=_HEADERS,
            json={"body": body, "commit_id": commit_id, "path": path, "line": line, "side": "RIGHT"},
        )
        r.raise_for_status()
        return r.json()


@tool
async def post_pr_review(pr_number: int, body: str, event: str = "COMMENT") -> dict:
    """
    Submit a top-level PR review.
    event: 'APPROVE', 'REQUEST_CHANGES', or 'COMMENT'
    """
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{_BASE}/repos/{_REPO}/pulls/{pr_number}/reviews",
            headers=_HEADERS,
            json={"body": body, "event": event},
        )
        r.raise_for_status()
        return r.json()


@tool
async def create_pull_request(title: str, body: str, head: str, base: str = "main") -> dict:
    """Create a pull request from head branch to base branch."""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{_BASE}/repos/{_REPO}/pulls",
            headers=_HEADERS,
            json={"title": title, "body": body, "head": head, "base": base},
        )
        r.raise_for_status()
        return r.json()


@tool
async def get_failed_workflow_logs(run_id: int) -> str:
    """Download and return the logs of all failed jobs in a workflow run."""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Get jobs
        jobs_r = await client.get(
            f"{_BASE}/repos/{_REPO}/actions/runs/{run_id}/jobs",
            headers=_HEADERS,
        )
        jobs_r.raise_for_status()
        failed_jobs = [j for j in jobs_r.json()["jobs"] if j["conclusion"] == "failure"]

        logs = []
        for job in failed_jobs:
            log_r = await client.get(
                f"{_BASE}/repos/{_REPO}/actions/jobs/{job['id']}/logs",
                headers=_HEADERS,
            )
            # Truncate to last 8000 chars to fit context window
            logs.append(f"=== Job: {job['name']} ===\n{log_r.text[-8000:]}")
        return "\n\n".join(logs)


@tool
async def list_merged_prs_since_tag(tag: str) -> list[dict]:
    """List all PRs merged into main since a given git tag."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_BASE}/repos/{_REPO}/pulls",
            headers=_HEADERS,
            params={"state": "closed", "base": "main", "per_page": 100},
        )
        r.raise_for_status()
        # Filter to merged PRs only — full tag-based filtering requires comparing
        # PR merge_commit_sha against git log; this returns recently merged PRs as a starting point.
        return [pr for pr in r.json() if pr.get("merged_at")]
```

### 5.5 Jira Tools

**`agents/tools/jira_tools.py`**

```python
import httpx
import base64
from langchain_core.tools import tool
from agents.config.settings import settings

_token = base64.b64encode(
    f"{settings.jira_user_email}:{settings.jira_api_token}".encode()
).decode()
_HEADERS = {
    "Authorization": f"Basic {_token}",
    "Content-Type": "application/json",
}
_BASE = f"{settings.jira_base_url}/rest/api/3"


@tool
async def get_jira_ticket(issue_key: str) -> dict:
    """
    Fetch a Jira issue by key (e.g. 'TJS-123').
    Returns summary, description, acceptance criteria, status, labels, and linked issues.
    """
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_BASE}/issue/{issue_key}",
            headers=_HEADERS,
            params={"fields": "summary,description,status,labels,issuetype,subtasks,comment"},
        )
        r.raise_for_status()
        data = r.json()
        fields = data["fields"]
        return {
            "key": data["key"],
            "summary": fields.get("summary"),
            "status": fields["status"]["name"],
            "type": fields["issuetype"]["name"],
            "description": _extract_text(fields.get("description")),
            "subtasks": [s["key"] for s in fields.get("subtasks", [])],
            "labels": fields.get("labels", []),
        }


@tool
async def add_jira_comment(issue_key: str, comment: str) -> dict:
    """Add a plain-text comment to a Jira issue."""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{_BASE}/issue/{issue_key}/comment",
            headers=_HEADERS,
            json={"body": {"type": "doc", "version": 1, "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": comment}]}
            ]}},
        )
        r.raise_for_status()
        return {"id": r.json()["id"]}


@tool
async def create_jira_ticket(
    project_key: str,
    summary: str,
    description: str,
    issue_type: str = "Bug",
    labels: list[str] | None = None,
) -> dict:
    """Create a new Jira issue and return its key and URL."""
    body: dict = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
            "description": {
                "type": "doc", "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}],
            },
        }
    }
    if labels:
        body["fields"]["labels"] = labels

    async with httpx.AsyncClient() as client:
        r = await client.post(f"{_BASE}/issue", headers=_HEADERS, json=body)
        r.raise_for_status()
        key = r.json()["key"]
        return {"key": key, "url": f"{settings.jira_base_url}/browse/{key}"}


def _extract_text(adf_node: dict | None) -> str:
    """Recursively extract plain text from Atlassian Document Format."""
    if not adf_node:
        return ""
    if adf_node.get("type") == "text":
        return adf_node.get("text", "")
    return " ".join(_extract_text(child) for child in adf_node.get("content", []))
```

---

## 6. Convention Files

These Markdown files are loaded at agent startup and injected into system prompts as project context. Keep them updated whenever architecture patterns change — they are the single source of truth for agents.

### `agents/conventions/backend-patterns.md`

````markdown
# TJ-Sales Backend Conventions

## Module Structure
Each module lives under `backend-v2/Modules/{ModuleName}/` with layers:
Application / Domain / Endpoints / Infrastructure / Contracts / IntegrationEvents

## CQRS Pattern
- Commands: inherit `BaseCommand<TResponse>` or `BaseCommandWithTenantId<TResponse>`
- Handlers: implement `ICommandHandler<TCommand, TResponse>`
- Queries: inherit `BaseQuery<TResponse>`
- Query Handlers: implement `IQueryHandler<TQuery, TResponse>`

## Patch / Update Command Base Types
Use the most specific base class for the operation:

| Base class | Use when |
|---|---|
| `BasePatchCommand<T>` | Simple patch, no auth context needed |
| `BasePatchCommandWithResourceId<T>` | Patch that includes a resource/entity ID |
| `BasePatchCommandWithResourceAndUserId<T>` | Patch requiring both resource ID and user ID |
| `BasePatchCommandWithTenant<T>` | Patch scoped to a specific tenant |
| `BasePatchCommandWithExtraClaim<T>` | **Use when the authenticated user's `UserId` must be extracted from the JWT `ext` claim** (via FastEndpoints `[FromClaim]`). Required for all branch-access-controlled operations. |

```csharp
// Example: command that needs authenticated UserId from JWT ext claim
public sealed class UpdateTalentCommand : BasePatchCommandWithExtraClaim<UpdateTalentResponse>
{
    public required Guid TalentId { get; init; }
    // UserId is automatically populated from JWT ext claim by BasePatchCommandWithExtraClaim
}
```

## Result Pattern (NEVER throw exceptions from handlers)
```csharp
// Return success
return Result.Success(value);
// Return failure
return Result.Failure<T>(ModuleErrors.SomeError);
```

## Object Mapping
Use **Mapster** for all object mapping. Never use manual property assignment or AutoMapper.

```csharp
// Map domain entity → response DTO
var response = entity.Adapt<EntityResponse>();

// Map command → domain entity
var entity = command.Adapt<Entity>();

// Map with custom configuration (if needed)
var config = new TypeAdapterConfig();
config.NewConfig<Source, Destination>()
    .Map(dest => dest.Name, src => src.FullName);
var result = source.Adapt<Destination>(config);
```

## Endpoints
Inherit `BaseEndpoint<TRequest, TResponse>` (with response body) or `BaseEndpoint<TRequest>` (no response body).
**Always wrap the response DTO in `BaseResponseModel<T>`.**

```csharp
public class GetTenantByIdEndpoint : BaseEndpoint<GetTenantByIdRequest, BaseResponseModel<GetTenantByIdResponse>>
{
    public override void Configure()
    {
        Get("/tenant/{id}");
        AuthSchemes(AuthenticationSchema.AzureAd);          // Standard endpoints
        // AuthSchemes(AuthenticationSchema.IdentityServer); // Client-facing endpoints (e.g. feedback retrieval)
        // AllowAnonymous();                                  // Public endpoints (combine with AuthSchemes for mixed auth/anon)
    }

    public override async Task HandleAsync(GetTenantByIdRequest request, CancellationToken ct)
    {
        var result = await _mediator.Send(new GetTenantByIdQuery(request.Id), ct);
        if (result.IsSuccess)
            await Send.ResponseAsync(new BaseResponseModel<GetTenantByIdResponse>(result.Value), cancellation: ct);
        else
            await HandleError(result, ct);
    }
}
```

## Validation
Use FluentValidation. Register via `AddValidatorsFromAssembly`. Rule example:
```csharp
RuleFor(x => x.BranchOfficeId).NotEmpty().NotEqual(Guid.Empty);
```

**Do NOT call `_validator.ValidateAsync()` manually inside handlers.** The `ValidationPipelineBehavior`
MediatR pipeline behavior runs FluentValidation automatically for every command/query. Explicit validator
calls inside handlers are redundant.

## MediatR Pipeline Behaviors (cross-cutting, auto-applied to every handler)
- `ValidationPipelineBehavior` — runs FluentValidation; handlers only execute if input is valid
- `TelemetryEnricherPipelineBehavior` — injects APM/telemetry context automatically
- `ReferenceEnrichmentBehavior` — hydrates domain references automatically

Do not replicate the logic of these behaviors inside handlers.

## DI Registration
Use `ITransient`, `IScoped`, or `ISingleton` marker interfaces — no manual registration needed.

## Namespaces
- Sales modules: `Gedat.TimeJobOnline.Sales.{Module}`
- People modules: `Gedat.TimeJobOnline.People.{Module}`
- Disposition modules: `Gedat.TimeJobOnline.Disposition.{Module}`

## Cosmos DB Repository Registration
Register repositories in `InfrastructureServiceInstaller`:
```csharp
services.AddRepositoryForTenant<TEntity>(options =>
{
    options.ContainerName = "entities";
    options.UseSingleDatabase = true;  // shared DB across modules (vs. per-module DB)
    // Partition key is typically "/id" for single-tenant documents
});
```
Use **hierarchical partition keys (HPK)** to overcome the 20 GB per-partition limit where needed.

## Multi-tenancy Access Control
- All handlers that access branch-scoped data MUST inject and call `IBranchOfficeAccessService`.
- **Correct access-check pattern:**
```csharp
// Load entity first, then check access
var canAccess = await _branchOfficeAccessService.CanUserAccessBranchOffice(
    entity.BranchOfficeId, request.UserId, request.ResourceId);
if (!canAccess)
    return Result.Failure<T>(AccessErrors.Unauthorized);
```
- For commands that need the authenticated `UserId`, use `BasePatchCommandWithExtraClaim<T>` (see above).

## ElasticSearch Integration
Five modules use ElasticSearch: **Talent, LandingPage, Contact, Company, Activity**.
```csharp
// Inject ISearchService from Common.Application.ElasticSearch
// After create/update/delete, update the search index:
await _searchService.IndexAsync(entity, cancellationToken);

// Use ElasticSearchExtension helper methods for common search patterns
// Reindexing for schema migrations:
await _searchService.ReindexAsync(cancellationToken);
```
**Always check whether the target module uses ElasticSearch before generating infrastructure code.**
If the module is in the list above, `InfrastructureServiceInstaller` must register the ElasticSearch
services and all write operations must update the index.

## Integration Events (Cross-Module Communication)
- Modules communicate asynchronously via integration events using MassTransit on Azure Service Bus.
- Each module that publishes events defines them in its `[Module].IntegrationEvents` project.
- Event classes follow the naming convention: `[Entity][Action]IntegrationEvent` (e.g., `TalentCreatedIntegrationEvent`).
- Handlers implement `IConsumer<TEvent>` and are registered via the MassTransit `IServiceInstaller`.
- Never use direct method calls across module boundaries — use integration events.

## Additional Services
Use these common services where appropriate — do not reinvent their functionality:

| Service | Location | Use for |
|---|---|---|
| `IHangfireService` | `Common.Application/BackgroundJob/` | Scheduling background/recurring jobs via Hangfire |
| `IFeatureFlagManagementService` | `Common.Application` | Reading Azure App Configuration feature flags |
| `IAddressGeocodingService<TAddress>` | `Common.Application` | Address-to-coordinates conversion. Always call `HasAddressChanged()` on Update/Patch to avoid unnecessary Azure Maps API calls |
| `ITelemetryEnricherContext` | `Common.Application/Telemetry/` | Enriching APM telemetry data |
````

### `agents/conventions/frontend-patterns.md`

```markdown
# TJ-Sales Frontend Conventions

> **IMPORTANT — Nx AI Agent Guidance:** Before generating any Nx-related code (project configuration,
> generators, task runners, module federation, build targets), read and follow the guidance in
> `frontend/AGENTS.md`. This file contains Nx-specific AI agent guidance tailored to this project.

## Components
- Always use `changeDetection: ChangeDetectionStrategy.OnPush`
- Standalone components only (`standalone: true`)
- Inline templates for small components; separate .html for large ones
- "Dumb" components: input/output only, no service injection
- "Smart" pages: inject services, use Component Store or signals

## State Management
- Prefer Angular signals over observables for local state
- Use `@ngrx/component-store` for feature-level state

## i18n
- All user-facing strings via Transloco: `{{ 'key' | transloco }}`
- Translation files: `shared/src/lib/assets/i18n/{lang}.json`
- New keys must be added to ALL locale files simultaneously

## API Calls
- Use auto-generated services from `shared/src/lib/api/services/`
- Never call HttpClient directly in feature code
- Regenerate after backend changes: `pnpm nx run shared:openapi-gen`

## Forms
- Use **reactive forms** for all form components
- Use custom validators from `shared/src/lib/locale/` — do not write ad-hoc inline validators

## UI Components
- Use **PrimeNG** components for standard UI elements (`p-table`, `p-dialog`, `p-button`, `p-dropdown`, etc.)
- Do not re-implement UI patterns that PrimeNG already provides
- Use **Angular CDK** for low-level interaction primitives (overlay, drag-drop, etc.)

## Styling
- TailwindCSS utility classes only
- Use `tailwind-merge` for dynamic class composition
- Custom theme lives in `theme/`

## Module Federation — DO NOT MODIFY
**Do NOT modify** remote entry files, module federation configuration, or app bootstrap files:
- `module-federation.config.ts`
- `app.routes.ts` (remote registrations)
- `main.ts` (bootstrap)

Scope all generated code to **feature-level components and services** within the existing app
structure. The host/remote architecture (core as host; sales, dispo, people, login as remotes)
must not be altered by scaffolded code.
```

### `agents/conventions/test-patterns.md`

```markdown
# TJ-Sales Test Conventions

## Backend Unit Tests
- Framework: xUnit
- Assertions: AwesomeAssertions (`result.Should().BeSuccess()`)
- Mocking: Moq (`Mock<IService>`)
- Fixtures: AutoFixture via `Fake.Create<T>()`
- File naming: `{ClassName}UnitTests.cs`

## Backend Integration Tests
- Inherit module TestBase (e.g., `TalentTestBase`)
- Tests run against real Cosmos DB Emulator
- File naming: `{ClassName}IntegrationTests.cs`
- Always call `RegisterCommonServices()` to mock external deps

## Frontend Unit Tests
- Framework: Vitest
- Use `TestBed` with `provideHttpClientTesting`
- File naming: `{component}.spec.ts` alongside the component

## AutoFixture Wrapper

`Fake.Create<T>()` is a **project-specific extension wrapper** over AutoFixture. It is defined in `Common.Tests` and provides convention-based fixture creation. Do NOT use `fixture.Create<T>()` directly — always use `Fake.Create<T>()`.

## Assertion Library by Module

- **All modules except Competency**: use `AwesomeAssertions` (e.g., `result.Should().BeSuccess()`)
- **Competency module only**: uses `FluentAssertions` — generate assertions using its API instead.
```

---

## 7. Phase 1 — Code Review Agent

> **Risk:** Low — read-only, never modifies code.  
> **Trigger:** GitHub webhook on `pull_request` event (opened / synchronize).

### Step 1 — Implement the agent

**`agents/agents/code_review.py`**

```python
from langchain_core.messages import SystemMessage, HumanMessage
from agents.config.llm import get_llm
from agents.tools.github_tools import get_pr_diff, post_pr_review
from agents.conventions import load_convention

_SYSTEM = f"""
You are a senior software engineer reviewing pull requests for the tj-sales monorepo.
You check ONLY for the following categories — do not comment on style or formatting:

BACKEND RULES (for .cs files):
1. Every handler must return Result or Result<T> — never throw exceptions.
2. FluentValidation must be present for every command that has user input.
3. If the code touches entities with BranchOfficeId, IBranchOfficeAccessService must be called.
4. Endpoints must call HandleError(result, ct) on failure.
5. New services must use ITransient/IScoped/ISingleton marker interfaces.

FRONTEND RULES (for .ts/.html files):
1. All components must have changeDetection: ChangeDetectionStrategy.OnPush.
2. User-facing strings must use Transloco — no hardcoded strings.
3. New API calls must use the generated service from shared/api, not raw HttpClient.

GENERAL:
1. Tests must be added for any new handler, command, or non-trivial component.

Project conventions:
{load_convention('backend-patterns.md')}
{load_convention('frontend-patterns.md')}

Respond in this exact JSON format:
{{
  "summary": "One-sentence overall assessment",
  "issues": [
    {{"file": "relative/path", "line": 42, "rule": "Rule name", "comment": "Explanation and fix suggestion"}}
  ],
  "approved": true | false
}}
"""


async def run_code_review(pr_number: int, commit_sha: str) -> dict:
    llm = get_llm()

    diff = await get_pr_diff.ainvoke({"pr_number": pr_number})

    response = await llm.ainvoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=f"PR #{pr_number} diff:\n\n{diff[:30000]}"),
    ])

    import json
    try:
        result = json.loads(response.content)
    except json.JSONDecodeError:
        result = {"summary": response.content, "issues": [], "approved": False}

    # Post top-level review
    event = "APPROVE" if result.get("approved") else "REQUEST_CHANGES"
    body_lines = [f"**Automated Code Review**\n\n{result['summary']}\n"]
    for issue in result.get("issues", []):
        body_lines.append(f"- `{issue['file']}` line {issue['line']}: **{issue['rule']}** — {issue['comment']}")

    await post_pr_review.ainvoke({
        "pr_number": pr_number,
        "body": "\n".join(body_lines),
        "event": event,
    })

    # Post review summary back to the linked Jira ticket (extracted from branch name)
    from agents.tools.github_tools import get_pr_details
    from agents.tools.jira_tools import add_jira_comment
    import re as _re
    pr_details = await get_pr_details.ainvoke({"pr_number": pr_number})
    branch = pr_details.get("head", {}).get("ref", "")
    jira_match = _re.search(r"([A-Z]+-\d+)", branch)
    if jira_match:
        jira_key = jira_match.group(1)
        status = "✅ Approved" if result.get("approved") else "🔴 Changes requested"
        await add_jira_comment.ainvoke({
            "issue_key": jira_key,
            "comment": f"Automated code review for PR #{pr_number}: {status}\n\n{result['summary']}",
        })

    return result
```

**`agents/conventions/__init__.py`**

```python
from pathlib import Path

_DIR = Path(__file__).parent


def load_convention(filename: str) -> str:
    return (_DIR / filename).read_text(encoding="utf-8")
```

### Step 2 — Wire the workflow graph

**`agents/graphs/review_workflow.py`**

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict
from agents.agents.code_review import run_code_review


class ReviewState(TypedDict):
    pr_number: int
    commit_sha: str
    review_result: dict | None


async def review_node(state: ReviewState) -> ReviewState:
    result = await run_code_review(state["pr_number"], state["commit_sha"])
    return {**state, "review_result": result}


def build_review_graph():
    g = StateGraph(ReviewState)
    g.add_node("review", review_node)
    g.set_entry_point("review")
    g.add_edge("review", END)
    return g.compile()
```

### Step 3 — Register the webhook trigger

See [Section 13](#13-webhook-server--entry-point) for the webhook server. The `pull_request` event calls `build_review_graph().ainvoke({"pr_number": ..., "commit_sha": ..., "review_result": None})`.

### Step 4 — Validate

Open a test PR in the repository. Confirm that:
- A review comment appears within 30 seconds.
- The comment correctly identifies any missing `Result` pattern usage in the diff.
- No comments are posted for pure documentation changes.

---

## 8. Phase 2 — Translation Agent

> **Risk:** Low — creates a PR with translation additions; human merges.  
> **Trigger:** Scheduled (nightly cron) or manual.

### Step 1 — Implement the agent

**`agents/agents/translation.py`**

```python
import json
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage
from agents.config.llm import get_llm
from agents.config.settings import settings

_SOURCE_LANG = "de"   # Primary locale; adjust if your source is different
_TARGET_LANGS = ["de"]  # Add other locales as needed


def _get_i18n_dirs(repo_root: Path) -> list[Path]:
    """Return all i18n asset directories: shared library + each app."""
    dirs = [repo_root / "frontend" / "shared" / "src" / "lib" / "assets" / "i18n"]
    apps_root = repo_root / "frontend" / "apps"
    if apps_root.exists():
        for app_dir in sorted(apps_root.iterdir()):
            candidate = app_dir / "src" / "assets" / "i18n"
            if candidate.is_dir():
                dirs.append(candidate)
    return dirs


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _find_missing_keys(source: dict, target: dict, prefix: str = "") -> list[str]:
    missing = []
    for key, value in source.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if key not in target:
            missing.append(full_key)
        elif isinstance(value, dict):
            missing.extend(_find_missing_keys(value, target.get(key, {}), full_key))
    return missing


async def translate_missing_keys(source_lang: str = "en") -> dict[str, list[str]]:
    """
    Compare i18n JSON files across all app and shared directories, detect missing keys,
    generate translations via LLM, and write updated files.
    Returns a dict of {lang: [translated_keys]}.
    """
    llm = get_llm(mini=True)
    translated: dict[str, list[str]] = {}

    for i18n_dir in _get_i18n_dirs(settings.repo_root):
        source_path = i18n_dir / f"{source_lang}.json"
        if not source_path.exists():
            continue

        source = _load_json(source_path)

        for lang in _TARGET_LANGS:
            if lang == source_lang:
                continue
            target_path = i18n_dir / f"{lang}.json"
            target = _load_json(target_path)
            missing_keys = _find_missing_keys(source, target)

            if not missing_keys:
                translated.setdefault(lang, [])
                continue

            # Build a flat dict of only the missing key-value pairs for the prompt
            missing_values = {k: _get_nested(source, k.split(".")) for k in missing_keys}

            response = await llm.ainvoke([
                SystemMessage(content=(
                    f"You are a professional translator. Translate the following JSON values "
                    f"from {source_lang} to {lang}. "
                    "Preserve any {{interpolation}} placeholders exactly as-is. "
                    "Return ONLY valid JSON with the same keys and translated values."
                )),
                HumanMessage(content=json.dumps(missing_values, ensure_ascii=False)),
            ])

            try:
                translations = json.loads(response.content)
            except json.JSONDecodeError:
                continue

            # Merge translations back into target
            for key, value in translations.items():
                _set_nested(target, key.split("."), value)

            _save_json(target_path, target)
            translated.setdefault(lang, [])
            translated[lang] += list(translations.keys())

    return translated


def _get_nested(d: dict, keys: list[str]):
    for k in keys:
        d = d.get(k, {})
    return d


def _set_nested(d: dict, keys: list[str], value) -> None:
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value
```

### Step 2 — Create a CLI runner

```python
# agents/graphs/translation_workflow.py
import asyncio
from agents.agents.translation import translate_missing_keys


async def run():
    result = await translate_missing_keys()
    for lang, keys in result.items():
        print(f"{lang}: translated {len(keys)} keys: {keys}")


if __name__ == "__main__":
    asyncio.run(run())
```

Run manually: `python -m agents.graphs.translation_workflow`

Then commit and open a PR with the updated translation files.

---

## 9. Phase 3 — CI/CD Monitor Agent

> **Risk:** Low-Medium — creates Jira tickets; does not touch code.  
> **Trigger:** GitHub webhook on `workflow_run` event (completed, conclusion=failure).

### Step 1 — Implement the agent

**`agents/agents/ci_monitor.py`**

```python
from langchain_core.messages import SystemMessage, HumanMessage
from agents.config.llm import get_llm
from agents.config.settings import settings
from agents.tools.github_tools import get_failed_workflow_logs
from agents.tools.jira_tools import create_jira_ticket

_SYSTEM = """
You are a DevOps engineer analysing GitHub Actions failures for the tj-sales project.
Given the raw log output of a failed workflow run, produce a structured diagnosis.

## Known Workflows
Use the workflow name to provide more specific diagnoses:
- `main.yml`: Main deployment pipeline (build, test, Docker, Helm)
- `pr-main.yml`: PR preview environment deployment
- `staging.yml` / `production.yml`: Staging / production deployments (approval-gated)
- `helm-deployment.yaml`: Reusable Helm chart deployment (called by other workflows)
- `ui-test.yaml`: Playwright E2E tests (frontend)
- `pull-request-closed.yml`: Ephemeral PR preview environment cleanup on PR close
- `cleanup-resources.yaml` / `delete-resource.yml`: Azure resource lifecycle automation
- `accent-push.yaml` / `accent-pull.yaml` / `rw-accent-push.yaml`: Translation file sync
- `retry.yaml` / `rw-retry.yaml`: Deployment retry workflows

## Category Definitions
- `build-error`: Compilation failure (.NET `dotnet build`, Docker image build, Nx build)
- `test-failure`: Failing unit tests (xUnit backend) or E2E tests (Playwright via `ui-test.yaml`)
- `lint`: ESLint (frontend), dotnet format (backend), or **SonarQube quality gate failure** (backend)
- `deployment`: Helm chart failure, Kubernetes apply error, Azure resource provisioning error
- `other`: Anything not matching the above

Respond in this exact JSON format:
{
  "root_cause": "One-sentence summary of what failed",
  "category": "build-error | test-failure | lint | deployment | other",
  "affected_component": "backend | frontend | ai | infra | unknown",
  "suggested_fix": "Concrete actionable fix in 1-3 sentences",
  "jira_summary": "CI Failure: <concise title under 80 chars>",
  "jira_description": "Full description including log excerpt and suggested fix"
}
"""


async def analyse_ci_failure(run_id: int, workflow_name: str, repo_ref: str) -> dict:
    llm = get_llm(mini=True)

    logs = await get_failed_workflow_logs.ainvoke({"run_id": run_id})

    response = await llm.ainvoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=(
            f"Workflow: {workflow_name}\n"
            f"Ref: {repo_ref}\n"
            f"Run ID: {run_id}\n\n"
            f"Failed job logs:\n{logs}"
        )),
    ])

    import json
    try:
        analysis = json.loads(response.content)
    except json.JSONDecodeError:
        analysis = {
            "root_cause": "Could not parse LLM response",
            "category": "other",
            "affected_component": "unknown",
            "suggested_fix": response.content,
            "jira_summary": f"CI Failure: {workflow_name} (run {run_id})",
            "jira_description": response.content,
        }

    # Create Jira ticket
    run_url = f"https://github.com/{settings.github_repo}/actions/runs/{run_id}"
    ticket = await create_jira_ticket.ainvoke({
        "project_key": settings.jira_project_key,
        "summary": analysis["jira_summary"],
        "description": f"{analysis['jira_description']}\n\nGitHub Run: {run_url}",
        "issue_type": "Bug",
        "labels": ["ci-failure", analysis["affected_component"]],
    })

    analysis["jira_ticket"] = ticket
    return analysis
```

### Step 2 — Wire the workflow graph

**`agents/graphs/ci_recovery_workflow.py`**

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict
from agents.agents.ci_monitor import analyse_ci_failure


class CIState(TypedDict):
    run_id: int
    workflow_name: str
    repo_ref: str
    analysis: dict | None


async def analyse_node(state: CIState) -> CIState:
    analysis = await analyse_ci_failure(state["run_id"], state["workflow_name"], state["repo_ref"])
    return {**state, "analysis": analysis}


def build_ci_recovery_graph():
    g = StateGraph(CIState)
    g.add_node("analyse", analyse_node)
    g.set_entry_point("analyse")
    g.add_edge("analyse", END)
    return g.compile()
```

---

## 10. Phase 4 — Backend Scaffold Agent

> **Risk:** Medium — writes files and opens a PR; never auto-merges.  
> **Trigger:** Manual CLI invocation or Jira webhook (ticket "In Progress").

### Step 1 — Implement the agent

**`agents/agents/backend_scaffold.py`**

```python
import re
from pathlib import Path
from typing import Literal
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage
from agents.config.llm import get_llm
from agents.config.settings import settings
from agents.conventions import load_convention

_SYSTEM = f"""
You are a senior .NET developer generating backend feature slices for the tj-sales modular monolith.

When asked to scaffold a feature, produce ALL required files in one response.
Use the following conventions exactly:

{load_convention('backend-patterns.md')}

Respond with a JSON array. Each element is a file to create:
[
  {{
    "path": "Modules/Talent/Talent.Application/Features/CreateTalent/CreateTalentCommand.cs",
    "content": "using ...\\n\\nnamespace ...\\n{{"
  }}
]

Include these files for a new command feature:
1. Command (inherits BaseCommand<TResponse> or BaseCommandWithTenantId<TResponse>)
2. CommandHandler (implements ICommandHandler)
3. Validator (FluentValidation AbstractValidator)
4. Endpoint (inherits BaseEndpoint)
5. Response DTO (in Contracts layer)
6. Request DTO (in Contracts layer, used by Endpoint)

Use the correct namespace based on module type (Sales/People/Disposition).
"""


class ScaffoldPlan(BaseModel):
    module: str
    feature_name: str
    operation: Literal["command", "query", "both"]
    description: str
    namespace_prefix: str  # e.g., "Gedat.TimeJobOnline.Sales"


async def scaffold_backend_feature(plan: ScaffoldPlan) -> list[dict]:
    """Generate and write .cs files for a new backend feature slice."""
    llm = get_llm()

    response = await llm.ainvoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=(
            f"Scaffold a {plan.operation} for the {plan.module} module.\n"
            f"Feature name: {plan.feature_name}\n"
            f"Description: {plan.description}\n"
            f"Namespace prefix: {plan.namespace_prefix}\n"
            f"Base path: backend-v2/Modules/{plan.module}/"
        )),
    ])

    import json
    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\n?|```$", "", response.content.strip(), flags=re.MULTILINE)
    files = json.loads(raw)

    written = []
    for f in files:
        full_path = settings.repo_root / "backend-v2" / f["path"]
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(f["content"], encoding="utf-8")
        written.append(f["path"])

    return written
```

### Step 2 — Add a build-and-fix loop

After writing files, the scaffold agent should verify the build and attempt to fix compile errors:

```python
# In agents/agents/backend_scaffold.py (continued)

from agents.tools.dotnet_tools import dotnet_build


async def scaffold_and_verify(plan: ScaffoldPlan, max_fix_attempts: int = 2) -> dict:
    written_files = await scaffold_backend_feature(plan)

    for attempt in range(max_fix_attempts + 1):
        build_result = await dotnet_build.ainvoke({})
        if build_result["exit_code"] == 0:
            return {"status": "success", "files": written_files, "build": build_result}

        if attempt == max_fix_attempts:
            break

        # Ask LLM to fix the compile errors
        llm = get_llm()
        fix_response = await llm.ainvoke([
            SystemMessage(content="Fix the following .NET compile errors. Return only the corrected file contents as a JSON array with {path, content} objects."),
            HumanMessage(content=f"Errors:\n{build_result['stderr']}\n\nStdout:\n{build_result['stdout']}"),
        ])
        import json, re
        raw = re.sub(r"^```(?:json)?\n?|```$", "", fix_response.content.strip(), flags=re.MULTILINE)
        try:
            fixes = json.loads(raw)
            for f in fixes:
                full_path = settings.repo_root / "backend-v2" / f["path"]
                if full_path.exists():
                    full_path.write_text(f["content"], encoding="utf-8")
        except Exception:
            pass

    return {"status": "build_failed", "files": written_files, "build": build_result}
```

### Step 3 — Express the fix loop as a LangGraph cycle

The `scaffold_and_verify` function above uses a plain Python `for`-loop internally. The following shows the same pattern expressed as a **proper LangGraph cyclic graph** — making the retry behaviour explicit, inspectable in LangSmith, and independently resumable after a checkpoint.

**`agents/graphs/build_fix_loop_graph.py`**

```python
from typing import TypedDict
from langgraph.graph import StateGraph, END
from agents.agents.backend_scaffold import scaffold_backend_feature, ScaffoldPlan
from agents.tools.dotnet_tools import dotnet_build
from agents.config.llm import get_llm
from langchain_core.messages import SystemMessage, HumanMessage
import json, re

MAX_FIX_ATTEMPTS = 3


class BuildState(TypedDict):
    plan: ScaffoldPlan
    written_files: list[str]
    build_output: dict | None
    attempt: int
    status: str          # "pending" | "success" | "build_failed" | "max_attempts"


# ── Nodes ─────────────────────────────────────────────────────────────────────

async def scaffold_node(state: BuildState) -> BuildState:
    files = await scaffold_backend_feature(state["plan"])
    return {**state, "written_files": files, "attempt": 0}


async def build_check_node(state: BuildState) -> BuildState:
    result = await dotnet_build.ainvoke({})
    return {**state, "build_output": result}


async def fix_node(state: BuildState) -> BuildState:
    llm = get_llm()
    build = state["build_output"]
    fix_response = await llm.ainvoke([
        SystemMessage(content=(
            "Fix the following .NET compile errors. "
            "Return only corrected files as a JSON array: [{\"path\": \"...\", \"content\": \"...\"}]"
        )),
        HumanMessage(content=f"Errors:\n{build['stderr']}\n\nStdout:\n{build['stdout']}"),
    ])
    from agents.config.settings import settings
    raw = re.sub(r"^```(?:json)?\n?|```$", "", fix_response.content.strip(), flags=re.MULTILINE)
    try:
        for f in json.loads(raw):
            full_path = settings.repo_root / "backend-v2" / f["path"]
            if full_path.exists():
                full_path.write_text(f["content"], encoding="utf-8")
    except Exception:
        pass
    return {**state, "attempt": state["attempt"] + 1}


# ── Routing ───────────────────────────────────────────────────────────────────

def route_after_build(state: BuildState) -> str:
    if state["build_output"]["exit_code"] == 0:
        return "success"
    if state["attempt"] >= MAX_FIX_ATTEMPTS:
        return "max_attempts"
    return "fix"


# ── Graph assembly ─────────────────────────────────────────────────────────────

def build_build_fix_loop_graph():
    g = StateGraph(BuildState)

    g.add_node("scaffold", scaffold_node)
    g.add_node("build_check", build_check_node)
    g.add_node("fix", fix_node)

    g.set_entry_point("scaffold")
    g.add_edge("scaffold", "build_check")

    # Conditional edge: loops back to fix_node on failure, exits on success or exhaustion
    g.add_conditional_edges("build_check", route_after_build, {
        "success":      END,
        "fix":          "fix",          # ← cyclic edge: creates the loop
        "max_attempts": END,
    })

    # After fixing, re-run the build — this is the cycle
    g.add_edge("fix", "build_check")

    return g.compile()
```

This graph is **cyclic**: `build_check → fix → build_check → ...` repeats until the build passes or `MAX_FIX_ATTEMPTS` is reached. Each cycle is a separate node execution, fully traced in LangSmith with its own state snapshot — you can inspect exactly which compile error triggered each fix attempt.

---

## 11. Phase 5 — Full Feature Workflow

This phase connects all agents into a single end-to-end LangGraph that takes a Jira ticket and produces a ready-to-review PR.

### 11.1 Feature Planner Agent

**`agents/agents/planner.py`**

```python
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage
from agents.config.llm import get_llm
from agents.tools.jira_tools import get_jira_ticket
from agents.conventions import load_convention


class FeaturePlan(BaseModel):
    jira_key: str
    module: str
    namespace_prefix: str
    feature_name: str
    operation: str          # "command" | "query" | "both"
    description: str
    frontend_project: str   # "sales" | "dispo" | "people" | "admin"
    branch_name: str
    needs_frontend: bool
    needs_tests: bool


async def plan_feature(jira_key: str) -> FeaturePlan:
    llm = get_llm()
    ticket = await get_jira_ticket.ainvoke({"issue_key": jira_key})

    response = await llm.ainvoke([
        SystemMessage(content=(
            f"You are a software architect for tj-sales.\n"
            f"Given a Jira ticket, produce a feature plan.\n\n"
            f"Available modules: Activity, Absence, Catalog, Company, Competency, Contact, "
            f"Disposition, DocumentSigning, EconomicClassification, EmploymentRequirement, "
            f"Finance, JobHub, LandingPage, Matching, Talent, Tenant, User\n\n"
            f"Namespace mapping: Sales modules → Gedat.TimeJobOnline.Sales, "
            f"People modules → Gedat.TimeJobOnline.People, "
            f"Disposition/Matching → Gedat.TimeJobOnline.Disposition\n\n"
            f"Frontend apps: sales, dispo, people, admin, login, contract, candidates-landing-page\n\n"
            f"{load_convention('backend-patterns.md')}\n\n"
            "Respond with a JSON object matching this schema exactly:\n"
            '{"module": "...", "namespace_prefix": "...", "feature_name": "...", '
            '"operation": "command|query|both", "description": "...", '
            '"frontend_project": "...", "branch_name": "feature/TJS-xxx-short-name", '
            '"needs_frontend": true|false, "needs_tests": true|false}'
        )),
        HumanMessage(content=(
            f"Jira key: {ticket['key']}\n"
            f"Summary: {ticket['summary']}\n"
            f"Description: {ticket['description']}"
        )),
    ])

    import json, re
    raw = re.sub(r"^```(?:json)?\n?|```$", "", response.content.strip(), flags=re.MULTILINE)
    data = json.loads(raw)
    return FeaturePlan(jira_key=jira_key, **data)
```

### 11.2 Frontend Scaffold Agent

**`agents/agents/frontend_scaffold.py`**

```python
from agents.config.llm import get_llm
from agents.tools.nx_tools import nx_generate_component, nx_generate_service, nx_openapi_gen
from agents.config.settings import settings
from agents.conventions import load_convention
from langchain_core.messages import SystemMessage, HumanMessage
import json, re


async def scaffold_frontend_feature(project: str, feature_name: str, description: str) -> dict:
    llm = get_llm()

    # Ask LLM what components and services to generate
    response = await llm.ainvoke([
        SystemMessage(content=(
            f"You are an Angular developer for tj-sales.\n"
            f"{load_convention('frontend-patterns.md')}\n\n"
            "Given a feature description, list the Angular artefacts to generate. "
            "Respond with JSON:\n"
            '{{"components": [{{"name": "...", "path": "feature/..."}}], '
            '"services": [{{"name": "...", "path": "feature/..."}}], '
            '"i18n_keys": ["feature.key1", "feature.key2"]}}'
        )),
        HumanMessage(content=f"Project: {project}\nFeature: {feature_name}\nDescription: {description}"),
    ])

    raw = re.sub(r"^```(?:json)?\n?|```$", "", response.content.strip(), flags=re.MULTILINE)
    plan = json.loads(raw)

    results = []
    for comp in plan.get("components", []):
        r = await nx_generate_component.ainvoke({"project": project, "name": comp["name"], "path": comp["path"]})
        results.append({"type": "component", "name": comp["name"], "result": r})

    for svc in plan.get("services", []):
        r = await nx_generate_service.ainvoke({"project": project, "name": svc["name"], "path": svc["path"]})
        results.append({"type": "service", "name": svc["name"], "result": r})

    # Regenerate API client to pick up new backend endpoints
    gen_result = await nx_openapi_gen.ainvoke({})
    results.append({"type": "openapi-gen", "result": gen_result})

    return {"generated": results, "i18n_keys": plan.get("i18n_keys", [])}
```

### 11.3 Test Writer Agent

**`agents/agents/test_writer.py`**

```python
import re
from agents.config.llm import get_llm
from agents.config.settings import settings
from agents.conventions import load_convention
from agents.tools.dotnet_tools import dotnet_test_unit
from langchain_core.messages import SystemMessage, HumanMessage


async def write_backend_tests(module: str, feature_name: str, handler_code: str) -> dict:
    llm = get_llm()

    response = await llm.ainvoke([
        SystemMessage(content=(
            "You are a .NET test engineer for tj-sales.\n"
            f"{load_convention('test-patterns.md')}\n\n"
            "Generate an xUnit unit test class for the given handler. "
            "Use AwesomeAssertions, AutoFixture (Fake.Create<T>()), and Moq.\n"
            "Respond with a single JSON object: {\"path\": \"...\", \"content\": \"...\"}"
        )),
        HumanMessage(content=(
            f"Module: {module}\nFeature: {feature_name}\n\nHandler code:\n{handler_code}"
        )),
    ])

    import json
    raw = re.sub(r"^```(?:json)?\n?|```$", "", response.content.strip(), flags=re.MULTILINE)
    file_info = json.loads(raw)

    full_path = settings.repo_root / "backend-v2" / file_info["path"]
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(file_info["content"], encoding="utf-8")

    # Run unit tests to check the generated tests compile and pass
    test_result = await dotnet_test_unit.ainvoke({"filter_expression": feature_name})

    return {
        "file": file_info["path"],
        "test_result": test_result,
    }
```

### 11.4 LangGraph Feature Graph

**`agents/graphs/feature_workflow.py`**

```python
import asyncio
import subprocess
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agents.agents.planner import plan_feature, FeaturePlan
from agents.agents.backend_scaffold import scaffold_and_verify, ScaffoldPlan
from agents.agents.frontend_scaffold import scaffold_frontend_feature
from agents.agents.test_writer import write_backend_tests
from agents.agents.code_review import run_code_review
from agents.tools.github_tools import create_pull_request
from agents.tools.jira_tools import add_jira_comment
from agents.config.settings import settings


class FeatureState(TypedDict):
    jira_key: str
    plan: FeaturePlan | None
    backend_result: dict | None
    frontend_result: dict | None
    test_result: dict | None
    pr_number: int | None
    error: str | None


# ── Node implementations ──────────────────────────────────────────────────────

async def plan_node(state: FeatureState) -> FeatureState:
    try:
        plan = await plan_feature(state["jira_key"])
        # Create a git branch
        subprocess.run(
            ["git", "checkout", "-b", plan.branch_name],
            cwd=str(settings.repo_root), check=True,
        )
        return {**state, "plan": plan}
    except Exception as e:
        return {**state, "error": str(e)}


async def backend_node(state: FeatureState) -> FeatureState:
    plan = state["plan"]
    scaffold_plan = ScaffoldPlan(
        module=plan.module,
        feature_name=plan.feature_name,
        operation=plan.operation,
        description=plan.description,
        namespace_prefix=plan.namespace_prefix,
    )
    result = await scaffold_and_verify(scaffold_plan)
    return {**state, "backend_result": result}


async def frontend_node(state: FeatureState) -> FeatureState:
    plan = state["plan"]
    if not plan.needs_frontend:
        return {**state, "frontend_result": {"skipped": True}}
    result = await scaffold_frontend_feature(
        plan.frontend_project, plan.feature_name, plan.description
    )
    return {**state, "frontend_result": result}


async def test_node(state: FeatureState) -> FeatureState:
    plan = state["plan"]
    if not plan.needs_tests:
        return {**state, "test_result": {"skipped": True}}

    backend = state["backend_result"]
    if not backend or backend.get("status") == "build_failed":
        return {**state, "test_result": {"skipped": True, "reason": "build_failed"}}

    # Read the generated handler file to pass as context
    handler_path = next(
        (f for f in backend.get("files", []) if "Handler" in f), None
    )
    handler_code = ""
    if handler_path:
        full = settings.repo_root / "backend-v2" / handler_path
        if full.exists():
            handler_code = full.read_text(encoding="utf-8")

    result = await write_backend_tests(plan.module, plan.feature_name, handler_code)
    return {**state, "test_result": result}


async def open_pr_node(state: FeatureState) -> FeatureState:
    plan = state["plan"]

    # Commit everything
    subprocess.run(["git", "add", "-A"], cwd=str(settings.repo_root), check=True)
    subprocess.run(
        ["git", "commit", "-m", f"feat({plan.module}): scaffold {plan.feature_name} [{plan.jira_key}]"],
        cwd=str(settings.repo_root), check=True,
    )
    subprocess.run(
        ["git", "push", "-u", "origin", plan.branch_name],
        cwd=str(settings.repo_root), check=True,
    )

    pr = await create_pull_request.ainvoke({
        "title": f"feat({plan.module}): {plan.feature_name} [{plan.jira_key}]",
        "body": (
            f"## {plan.feature_name}\n\n"
            f"Jira: [{plan.jira_key}]({settings.jira_base_url}/browse/{plan.jira_key})\n\n"
            f"**Auto-generated scaffold.** Please review all files carefully before merging.\n\n"
            f"### Checklist\n- [ ] Business logic implemented in handler\n"
            f"- [ ] Integration test added\n- [ ] Translation keys reviewed"
        ),
        "head": plan.branch_name,
        "base": "main",
    })

    await add_jira_comment.ainvoke({
        "issue_key": plan.jira_key,
        "comment": f"Scaffold PR created: {pr['html_url']}",
    })

    return {**state, "pr_number": pr["number"]}


# ── Routing ───────────────────────────────────────────────────────────────────

def route_after_plan(state: FeatureState) -> str:
    return "error_end" if state.get("error") else "scaffold"


def route_after_backend(state: FeatureState) -> str:
    plan = state["plan"]
    # Run backend and frontend in parallel; test waits for both
    return "parallel_scaffold"


# ── Graph assembly ─────────────────────────────────────────────────────────────

def build_feature_graph(checkpointer) -> "CompiledGraph":
    g = StateGraph(FeatureState)

    g.add_node("plan", plan_node)
    g.add_node("backend", backend_node)
    g.add_node("frontend", frontend_node)
    g.add_node("tests", test_node)
    g.add_node("open_pr", open_pr_node)

    g.set_entry_point("plan")
    g.add_conditional_edges("plan", route_after_plan, {
        "error_end": END,
        "scaffold": "backend",
    })

    # Sequential scaffold (simple default); see parallel variant below
    g.add_edge("backend", "frontend")
    g.add_edge("frontend", "tests")

    # Human-in-the-loop: graph pauses at open_pr until a developer approves
    g.add_edge("tests", "open_pr")

    g.add_edge("open_pr", END)
    return g.compile(checkpointer=checkpointer, interrupt_before=["open_pr"])
```

#### Parallel scaffold with `Send`

To run backend and frontend scaffolding in parallel (recommended for Phase 5), replace the sequential edges with a `Send`-based dispatch:

```python
from langgraph.constants import Send
from typing import Annotated
import operator


class FeatureStateParallel(TypedDict):
    jira_key: str
    plan: FeaturePlan | None
    # Reducer: parallel nodes append their results to this list
    scaffold_results: Annotated[list[dict], operator.add]
    test_result: dict | None
    pr_number: int | None
    error: str | None


def dispatch_scaffold(state: FeatureStateParallel) -> list[Send]:
    """Fan out to backend and (optionally) frontend in parallel."""
    targets = [Send("backend", state)]
    if state["plan"] and state["plan"].needs_frontend:
        targets.append(Send("frontend", state))
    return targets


def build_parallel_feature_graph(checkpointer) -> "CompiledGraph":
    g = StateGraph(FeatureStateParallel)

    g.add_node("plan", plan_node)
    g.add_node("backend", backend_node)
    g.add_node("frontend", frontend_node)
    g.add_node("tests", test_node)
    g.add_node("open_pr", open_pr_node)

    g.set_entry_point("plan")
    # dispatch_scaffold returns list[Send] for fan-out — it is a router, not a node
    g.add_conditional_edges("plan", dispatch_scaffold)

    # Both backend and frontend run in parallel; LangGraph joins them automatically
    # before proceeding to tests (both must complete to advance)
    g.add_edge("backend", "tests")
    g.add_edge("frontend", "tests")
    g.add_edge("tests", "open_pr")
    g.add_edge("open_pr", END)

    return g.compile(checkpointer=checkpointer, interrupt_before=["open_pr"])
```

#### Human-in-the-loop: approving and resuming

When `interrupt_before=["open_pr"]` is set, the graph **pauses** after tests complete and waits for explicit approval. Resume flow:

```python
import asyncio
from agents.config.checkpointer import get_checkpointer
from agents.graphs.feature_workflow import build_feature_graph

async def approve_and_resume(thread_id: str):
    """
    Called by a developer (via CLI, Slack bot, or GitHub comment) to approve
    the scaffold and open the PR.
    """
    async with get_checkpointer() as checkpointer:
        graph = build_feature_graph(checkpointer)

        # Inspect what the agent has done so far
        state = await graph.aget_state(config={"configurable": {"thread_id": thread_id}})
        plan = state.values.get("plan")
        print(f"Approving scaffold for {plan.jira_key}: {plan.feature_name}")
        print(f"Files written: {state.values.get('backend_result', {}).get('files', [])}")

        # Resume — passing None as input continues from the checkpoint
        result = await graph.ainvoke(
            None,
            config={"configurable": {"thread_id": thread_id}},
        )
        print(f"PR opened: #{result['pr_number']}")


# Trigger initial run (will pause before open_pr)
async def trigger_feature(jira_key: str):
    async with get_checkpointer() as checkpointer:
        graph = build_feature_graph(checkpointer)
        thread_id = f"feature-{jira_key}"
        await graph.ainvoke(
            {"jira_key": jira_key, "plan": None, "backend_result": None,
             "frontend_result": None, "test_result": None, "pr_number": None, "error": None},
            config={"configurable": {"thread_id": thread_id}},
        )
        print(f"Graph paused. Approve with: python -c \"asyncio.run(approve_and_resume('{thread_id}'))\"")
```

---

## 12. Release Notes Agent

> **Trigger:** GitHub webhook on `create` event (tag pushed).

**`agents/agents/release_notes.py`**

```python
from langchain_core.messages import SystemMessage, HumanMessage
from agents.config.llm import get_llm
from agents.tools.github_tools import list_merged_prs_since_tag


async def generate_release_notes(new_tag: str, previous_tag: str) -> str:
    llm = get_llm(mini=True)

    prs = await list_merged_prs_since_tag.ainvoke({"tag": previous_tag})

    pr_list = "\n".join(
        f"- #{pr['number']} {pr['title']} (@{pr['user']['login']})"
        for pr in prs
    )

    response = await llm.ainvoke([
        SystemMessage(content=(
            "You are a technical writer generating release notes for tj-sales. "
            "Group the PRs by module (Activity, Company, Talent, Frontend, CI/CD, etc.). "
            "Use emoji section headers. Write for a developer audience. "
            "Keep each entry to one sentence. "
            "Format as Markdown."
        )),
        HumanMessage(content=(
            f"New version: {new_tag}\nPrevious version: {previous_tag}\n\n"
            f"Merged PRs:\n{pr_list}"
        )),
    ])

    notes = f"# Release {new_tag}\n\n{response.content}"
    # Write to repo
    from agents.config.settings import settings
    out = settings.repo_root / "CHANGELOG.md"
    existing = out.read_text(encoding="utf-8") if out.exists() else ""
    out.write_text(notes + "\n\n" + existing, encoding="utf-8")
    return notes
```

---

## 13. Webhook Server & Entry Point

**`agents/main.py`**

```python
import hashlib
import hmac
import logging

import uvicorn
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks

from agents.config.settings import settings
from agents.graphs.review_workflow import build_review_graph
from agents.graphs.ci_recovery_workflow import build_ci_recovery_graph
from agents.graphs.feature_workflow import build_feature_graph

logger = logging.getLogger("agents")
app = FastAPI(title="TJ-Sales Agent Orchestrator")


def _verify_github_signature(body: bytes, signature: str) -> bool:
    if not settings.webhook_secret:
        return True
    expected = "sha256=" + hmac.new(
        settings.webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.post("/webhooks/github")
async def github_webhook(request: Request, background: BackgroundTasks):
    body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    if not _verify_github_signature(body, sig):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = request.headers.get("X-GitHub-Event", "")
    payload = await request.json()

    if event == "pull_request" and payload.get("action") in ("opened", "synchronize"):
        pr = payload["pull_request"]
        background.add_task(
            build_review_graph().ainvoke,
            {"pr_number": pr["number"], "commit_sha": pr["head"]["sha"], "review_result": None},
        )

    elif event == "workflow_run" and payload.get("action") == "completed":
        run = payload["workflow_run"]
        if run["conclusion"] == "failure":
            background.add_task(
                build_ci_recovery_graph().ainvoke,
                {"run_id": run["id"], "workflow_name": run["name"], "repo_ref": run["head_branch"], "analysis": None},
            )

    elif event == "create" and payload.get("ref_type") == "tag":
        tag = payload["ref"]
        logger.info(f"New tag pushed: {tag} — release notes generation triggered")
        # Trigger release notes (implementation left as exercise)

    return {"status": "accepted"}


@app.post("/webhooks/jira")
async def jira_webhook(request: Request, background: BackgroundTasks):
    payload = await request.json()

    # Trigger feature workflow when ticket moves to "In Progress"
    if (
        payload.get("webhookEvent") == "jira:issue_updated"
        and payload.get("changelog", {}).get("items", [{}])[0].get("toString") == "In Progress"
    ):
        issue_key = payload["issue"]["key"]
        background.add_task(
            build_feature_graph().ainvoke,
            {"jira_key": issue_key, "plan": None, "backend_result": None,
             "frontend_result": None, "test_result": None, "pr_number": None, "error": None},
        )

    return {"status": "accepted"}


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.webhook_port, log_level="info")
```

### Webhook Registration

**GitHub:** Repository Settings → Webhooks → Add webhook  
- Payload URL: `https://<your-host>/webhooks/github`  
- Content type: `application/json`  
- Events: `Pull requests`, `Workflow runs`, `Branch or tag creation`

**Jira:** Project Settings → Automation → Webhooks (or Jira Admin → System → WebHooks)  
- URL: `https://<your-host>/webhooks/jira`  
- Events: `Issue updated`

---

## 14. Observability

### LangSmith Tracing

Add to `.env`:

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=ls__...
LANGCHAIN_PROJECT=tj-sales-agents
```

Every LLM call, tool invocation, and graph transition is automatically traced with no further code changes. Access traces at `smith.langchain.com`. Each trace shows a flame-graph breakdown of node durations, LLM token usage, tool inputs/outputs, and the state delta at every step — making it straightforward to diagnose why an agent routed to "fix" instead of "open_pr", or which prompt caused a wrong namespace to be generated.

### LangSmith Evaluation: Datasets and Evaluators

Beyond tracing, LangSmith supports **dataset-based evaluation** — running an agent against a set of reference examples and scoring outputs with custom functions. This is how you benchmark quality and catch regressions after prompt changes.

#### Step 1 — Create a benchmark dataset

Collect representative inputs (Jira ticket descriptions) and, optionally, reference outputs. The dataset is stored in LangSmith and reused across evaluation runs.

**`agents/evals/create_dataset.py`**

```python
from langsmith import Client

client = Client()

# Create the dataset once; subsequent runs reuse it by name
dataset = client.create_dataset(
    "scaffold-benchmark",
    description="Representative Jira tickets for backend scaffold quality benchmarking",
)

# Add examples: each has an 'inputs' dict and an optional 'outputs' dict
examples = [
    {
        "inputs": {"jira_key": "TJS-TEST-1", "description": "Add a GetTalentById query endpoint to the Talent module returning name, branch office, and status."},
        "outputs": {"expected_files": ["TalentQuery.cs", "TalentQueryHandler.cs", "GetTalentByIdEndpoint.cs"]},
    },
    {
        "inputs": {"jira_key": "TJS-TEST-2", "description": "Add a CreateCompany command with FluentValidation for name and tenantId."},
        "outputs": {"expected_files": ["CreateCompanyCommand.cs", "CreateCompanyCommandHandler.cs", "CreateCompanyValidator.cs"]},
    },
]

for ex in examples:
    client.create_example(
        inputs=ex["inputs"],
        outputs=ex["outputs"],
        dataset_name="scaffold-benchmark",
    )

print(f"Dataset created: {dataset.id}")
```

Run once: `python -m agents.evals.create_dataset`

#### Step 2 — Write evaluators

Each evaluator receives a `run` (agent output) and an `example` (reference input/output) and returns a score between 0 and 1.

**`agents/evals/evaluators.py`**

```python
from langsmith.schemas import Run, Example


def uses_result_pattern(run: Run, example: Example) -> dict:
    """Score 1 if every generated .cs file uses Result.Success / Result.Failure."""
    files: list[dict] = run.outputs.get("files", [])
    handler_files = [f for f in files if "Handler" in f.get("path", "")]
    if not handler_files:
        return {"score": 0, "key": "uses_result_pattern", "comment": "No handler file found"}
    compliant = all(
        "Result.Success" in f.get("content", "") or "Result.Failure" in f.get("content", "")
        for f in handler_files
    )
    return {"score": 1 if compliant else 0, "key": "uses_result_pattern"}


def has_fluent_validation(run: Run, example: Example) -> dict:
    """Score 1 if a FluentValidation validator file is present."""
    files: list[dict] = run.outputs.get("files", [])
    has_validator = any("Validator" in f.get("path", "") for f in files)
    return {"score": 1 if has_validator else 0, "key": "has_fluent_validation"}


def build_succeeds(run: Run, example: Example) -> dict:
    """Score 1 if the dotnet build step completed with exit_code 0."""
    build = run.outputs.get("build", {})
    passed = build.get("exit_code") == 0
    return {
        "score": 1 if passed else 0,
        "key": "build_succeeds",
        "comment": build.get("stderr", "")[:500] if not passed else "",
    }


def correct_namespace(run: Run, example: Example) -> dict:
    """Score 1 if generated files use a valid TJ-Sales namespace prefix."""
    valid_prefixes = (
        "Gedat.TimeJobOnline.Sales",
        "Gedat.TimeJobOnline.People",
        "Gedat.TimeJobOnline.Disposition",
    )
    files: list[dict] = run.outputs.get("files", [])
    cs_files = [f for f in files if f.get("path", "").endswith(".cs")]
    if not cs_files:
        return {"score": 0, "key": "correct_namespace", "comment": "No .cs files generated"}
    compliant = all(
        any(prefix in f.get("content", "") for prefix in valid_prefixes)
        for f in cs_files
    )
    return {"score": 1 if compliant else 0, "key": "correct_namespace"}
```

#### Step 3 — Run an evaluation suite

**`agents/evals/run_eval.py`**

```python
import asyncio
from langsmith.evaluation import aevaluate
from agents.agents.backend_scaffold import scaffold_and_verify, ScaffoldPlan
from agents.agents.planner import plan_feature
from agents.evals.evaluators import (
    uses_result_pattern,
    has_fluent_validation,
    build_succeeds,
    correct_namespace,
)


async def target(inputs: dict) -> dict:
    """Run planner + scaffold for a given Jira ticket description."""
    plan = await plan_feature(inputs["jira_key"])
    scaffold_plan = ScaffoldPlan(
        module=plan.module,
        feature_name=plan.feature_name,
        operation=plan.operation,
        description=plan.description,
        namespace_prefix=plan.namespace_prefix,
    )
    result = await scaffold_and_verify(scaffold_plan)
    # Return all generated file paths and contents for evaluators
    from agents.config.settings import settings
    files = []
    for path in result.get("files", []):
        full = settings.repo_root / "backend-v2" / path
        files.append({"path": path, "content": full.read_text(encoding="utf-8") if full.exists() else ""})
    return {"files": files, "build": result.get("build", {})}


async def main():
    results = await aevaluate(
        target,
        data="scaffold-benchmark",
        evaluators=[uses_result_pattern, has_fluent_validation, build_succeeds, correct_namespace],
        experiment_prefix="scaffold-v1",
        max_concurrency=2,
    )
    print(f"Evaluation complete. View results at: {results.experiment_url}")


async def compare(new_prompt_version: str = "scaffold-v2"):
    """
    Run a second experiment with a modified prompt and compare in LangSmith.
    Swap out the target function below to test a different prompt or model.
    """
    async def target_v2(inputs: dict) -> dict:
        # Example: test with the mini model or a revised system prompt
        # Adjust backend_scaffold._SYSTEM and re-import before calling this
        return await target(inputs)

    results_v2 = await aevaluate(
        target_v2,
        data="scaffold-benchmark",
        evaluators=[uses_result_pattern, has_fluent_validation, build_succeeds, correct_namespace],
        experiment_prefix=new_prompt_version,
        max_concurrency=2,
    )
    print(f"Comparison experiment: {results_v2.experiment_url}")
    print("Open LangSmith → scaffold-benchmark dataset → Compare Experiments to view side-by-side scores.")


if __name__ == "__main__":
    asyncio.run(main())
```

Run: `python -m agents.evals.run_eval`

Results appear in the LangSmith UI under the `scaffold-benchmark` dataset. Re-run after every prompt change to guard against regressions. To compare two prompt versions side-by-side, run both `main()` and `compare()` — LangSmith's **Compare Experiments** view shows per-evaluator score deltas between `scaffold-v1` and `scaffold-v2` across every example in the dataset.

#### Step 4 — Add `evals/` to the project structure

Update `agents/` with the new directory:

```
agents/
├── evals/
│   ├── __init__.py
│   ├── create_dataset.py    # Run once to seed the benchmark dataset
│   ├── evaluators.py        # Scoring functions for tj-sales quality checks
│   └── run_eval.py          # Entry point: runs evaluation suite against LangSmith
```

Add to `requirements.txt`:

```text
langsmith>=0.3.0             # already present — covers both tracing and evaluation SDK
```

> **Tracked metrics:** see the evaluation document (`docs/langchain-multi-agent-evaluation.md § LangSmith Evaluation`) for the full benchmarking target table (compilation success rate, convention compliance, latency, cost per run).

### Azure Application Insights

Reuse the existing Application Insights setup from `ai/`:

```python
# agents/config/settings.py — add:
azure_application_insights_connection_string: str = ""

# agents/main.py — add at startup:
from azure.monitor.opentelemetry import configure_azure_monitor
if settings.azure_application_insights_connection_string:
    configure_azure_monitor(connection_string=settings.azure_application_insights_connection_string)
```

### Structured Logging

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "agent": "%(name)s", "msg": "%(message)s"}',
)
```

---

## 15. Testing the Agents

### Unit Testing Tools

Each tool function is independently testable by mocking external calls:

```python
# tests/test_jira_tools.py
import pytest
from unittest.mock import AsyncMock, patch
from agents.tools.jira_tools import get_jira_ticket


@pytest.mark.asyncio
async def test_get_jira_ticket_extracts_fields():
    mock_response = {"key": "TJS-1", "fields": {
        "summary": "Test", "status": {"name": "In Progress"},
        "issuetype": {"name": "Story"}, "description": None,
        "subtasks": [], "labels": [],
    }}
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.raise_for_status = lambda: None
        result = await get_jira_ticket.ainvoke({"issue_key": "TJS-1"})
    assert result["key"] == "TJS-1"
    assert result["status"] == "In Progress"
```

### Integration Testing Agents

Run agents against your real Jira/GitHub test project with a designated `TJS-TEST-*` ticket:

```bash
cd agents
python -c "
import asyncio
from agents.agents.planner import plan_feature
result = asyncio.run(plan_feature('TJS-TEST-1'))
print(result)
"
```

### Testing Graphs

```bash
python -c "
import asyncio
from agents.graphs.review_workflow import build_review_graph
graph = build_review_graph()
# Use a real open PR number from your repository
result = asyncio.run(graph.ainvoke({'pr_number': 42, 'commit_sha': 'abc123', 'review_result': None}))
print(result)
"
```

---

## 16. Deployment

### Local Development

```bash
cd agents
source .venv/bin/activate
python main.py
# Webhook server starts at http://localhost:8080
# Use ngrok to expose locally: ngrok http 8080
```

### Container

Create `agents/Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Install system dependencies including .NET 8 and Node 20
# Required for dotnet CLI tools and nx/pnpm commands called by agents
RUN apt-get update && apt-get install -y \
    curl git wget apt-transport-https \
    && rm -rf /var/lib/apt/lists/*

# Install .NET 8 SDK
RUN wget https://dot.net/v1/dotnet-install.sh -O dotnet-install.sh \
    && chmod +x dotnet-install.sh \
    && ./dotnet-install.sh --channel 8.0 --install-dir /usr/local/dotnet \
    && rm dotnet-install.sh
ENV DOTNET_ROOT=/usr/local/dotnet
ENV PATH=$PATH:$DOTNET_ROOT

# Install Node 20
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g pnpm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /agents
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/agents

CMD ["python", "main.py"]
```

Build and run:

```bash
docker build -t tj-sales-agents:latest ./agents
docker run -d \
  --name tj-sales-agents \
  --env-file agents/.env \
  -v /path/to/tj-sales:/repo \
  -p 8080:8080 \
  tj-sales-agents:latest
```

### Important: The agent container needs access to the repository file system to read and write files. Mount the repo as a volume or run the agent on the same machine as the development environment.

### AKS Deployment (Helm)

The agent service can be deployed as a Helm-managed pod in the **existing AKS cluster** alongside the backend:

```yaml
# deployments/helm-charts/agents/values.yaml
replicaCount: 1

image:
  repository: <your-acr>.azurecr.io/tj-sales-agents
  tag: latest
  pullPolicy: Always

service:
  type: ClusterIP
  port: 8080

env:
  AZURE_OPENAI_ENDPOINT: ""        # injected from Azure Key Vault via CSI driver
  AZURE_OPENAI_API_KEY: ""
  AZURE_OPENAI_DEPLOYMENT: "gpt-4o"
  GITHUB_TOKEN: ""
  GITHUB_REPO: "Gedat-GmbH/tj-sales"
  JIRA_BASE_URL: ""
  JIRA_USER_EMAIL: ""
  JIRA_API_TOKEN: ""
  JIRA_PROJECT_KEY: "TJS"
  REPO_ROOT: "/repo"
  LANGSMITH_TRACING: "true"
  LANGCHAIN_PROJECT: "tj-sales-agents"

volumeMounts:
  - name: repo
    mountPath: /repo

volumes:
  - name: repo
    persistentVolumeClaim:
      claimName: tj-sales-repo-pvc   # or use a git-sync init container
```

Deploy:

```bash
helm upgrade --install tj-sales-agents deployments/helm-charts/agents \
  --namespace tj-sales \
  --set image.tag=$(git rev-parse --short HEAD)
```

**Repository access in AKS:** The agent needs to read/write the codebase. Two options:
1. **Git-sync init container** — clones the repo on pod start; suitable for read-heavy agents (CI monitor, release notes)
2. **Ephemeral job per run** — spawn a Kubernetes `Job` per Jira webhook, clone repo, run agent, push branch, clean up — better isolation for code-writing agents

### GitHub Actions Integration

#### Manual trigger via `workflow_dispatch`

Add `.github/workflows/run-agent.yml` to trigger any agent manually from the GitHub Actions UI:

```yaml
name: Run Agent

on:
  workflow_dispatch:
    inputs:
      task:
        description: "Task to run (e.g. 'TJS-123' for feature scaffold, 'ci-monitor' for CI check)"
        required: true

jobs:
  run-agent:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r agents/requirements.txt
      - run: python -m agents.main --task "${{ github.event.inputs.task }}"
        env:
          AZURE_OPENAI_ENDPOINT: ${{ secrets.AZURE_OPENAI_ENDPOINT }}
          AZURE_OPENAI_API_KEY: ${{ secrets.AZURE_OPENAI_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GH_PAT }}
          JIRA_BASE_URL: ${{ secrets.JIRA_BASE_URL }}
          JIRA_USER_EMAIL: ${{ secrets.JIRA_USER_EMAIL }}
          JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
          JIRA_PROJECT_KEY: TJS
          REPO_ROOT: ${{ github.workspace }}
          LANGSMITH_API_KEY: ${{ secrets.LANGSMITH_API_KEY }}
```

#### Automated eval on agent code changes

Add `.github/workflows/agent-eval.yml` to run the LangSmith benchmark automatically on every PR that modifies `agents/`:

```yaml
name: Agent Evaluation

on:
  pull_request:
    paths:
      - "agents/**"

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r agents/requirements.txt
      - name: Run LangSmith benchmark
        run: python -m agents.evals.run_eval
        env:
          AZURE_OPENAI_ENDPOINT: ${{ secrets.AZURE_OPENAI_ENDPOINT }}
          AZURE_OPENAI_API_KEY: ${{ secrets.AZURE_OPENAI_API_KEY }}
          JIRA_BASE_URL: ${{ secrets.JIRA_BASE_URL }}
          JIRA_USER_EMAIL: ${{ secrets.JIRA_USER_EMAIL }}
          JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
          JIRA_PROJECT_KEY: TJS
          REPO_ROOT: ${{ github.workspace }}
          LANGSMITH_TRACING: "true"
          LANGSMITH_API_KEY: ${{ secrets.LANGSMITH_API_KEY }}
          LANGCHAIN_PROJECT: tj-sales-agents-ci
```

This ensures every prompt or tool change is regression-tested against the `scaffold-benchmark` dataset before merging.

### Environment Variables Summary

All required variables are documented in `agents/.env.example`. Copy to `.env` and fill in values before first run.

---

*Document authored with GitHub Copilot · Last updated: 2026-04-30*
