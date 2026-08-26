# 🏛️ Architecture

---

## The one idea

> **The analytics are deterministic. The AI only phrases the answer.**

```mermaid
flowchart TB
    subgraph clients[" "]
        UI["React SPA"]
        COP["GitHub Copilot Chat"]
        CURL["Any HTTP client"]
    end

    subgraph api["FastAPI"]
        R["routers/"]
        A["agent/<br/><small>tool-calling shell</small>"]
        M["mcp_server.py"]
    end

    subgraph core["analytics/ — deterministic, LLM-free, fully tested"]
        MX["metrics.py"]
        FL["floor.py"]
        OU["outliers.py"]
        RC["recommend.py"]
    end

    MKT["market/<br/><small>pluggable adapter</small>"]
    DB[("PostgreSQL")]
    AOAI["Azure OpenAI<br/><small>Entra ID</small>"]

    UI --> R
    UI --> A
    CURL --> R
    COP --> M

    R --> core
    A --> core
    M --> core
    A <--> AOAI

    core --> DB
    MKT --> DB
    RC --> MKT

    style core fill:#0B3D2E,stroke:#F5C518,color:#F5F1E8
    style AOAI fill:#12563F,stroke:#FF2E88,color:#F5F1E8
```

**Three surfaces, one implementation.** `agent/` and `mcp_server.py` reach data
*only* through `analytics/`. Neither writes a query.

The consequence: every figure the assistant quotes is one a test already covers,
and the UI and the assistant cannot drift into disagreeing about the same
question — because a second implementation does not exist to drift.

---

## Request flow: a question in chat

```mermaid
sequenceDiagram
    actor U as Floor manager
    participant W as React UI
    participant C as /api/chat
    participant O as orchestrator
    participant AO as Azure OpenAI
    participant T as agent/tools
    participant AN as analytics/
    participant DB as PostgreSQL

    U->>W: "Which penny slots are underperforming?"
    W->>C: POST {message, window_days}
    C->>O: run_conversation()
    O->>AO: messages + 7 tool schemas
    AO-->>O: tool_calls[find_underperformers]

    loop each tool call
        O->>T: dispatch(name, args)
        T->>AN: find_underperformers(session, days)
        AN->>DB: SELECT … GROUP BY machine
        DB-->>AN: rows
        AN-->>T: typed results + peer indices
        T-->>O: truncated payload + summary
    end

    O->>AO: tool results
    AO-->>O: prose answer
    O-->>C: answer + tool_call log
    C-->>W: ChatResponse
    W-->>U: answer + "7 analytics calls produced this"
```

The model never sees the database. It sees tool schemas and tool results.

---

## Data model

```mermaid
erDiagram
    ZONES ||--o{ MACHINES : contains
    MACHINES ||--o{ DAILY_PERFORMANCE : generates

    ZONES {
        int id PK
        string code UK "HL, MFN, MFS…"
        string name
        bool is_high_limit
    }

    MACHINES {
        string asset_number PK "NP-21401"
        int zone_id FK
        string bank_id "NP-214 — unit of action"
        string title
        string game_type
        int denomination_cents
        float par_hold_pct "paytable design"
        date install_date
    }

    DAILY_PERFORMANCE {
        int id PK
        date business_date
        string asset_number FK
        bigint coin_in_cents "wagered, NOT revenue"
        bigint theo_win_cents "coin_in × par"
        bigint actual_win_cents "what it did win"
        int handle_pulls
    }

    MARKET_TITLES {
        string title
        string provider "SYNTHETIC"
        float market_index
        float trend_30d_pct
    }

    COMPETITOR_OFFERINGS {
        string property_name
        string title
        int unit_count
    }
```

**Note what is absent: there is no player table.** SlotSight models machines and
money, never people. That is a deliberate architectural stance — the valuable
analytics problem here does not require PII, and collecting data you do not need
is a liability you chose.

`MARKET_TITLES` and `COMPETITOR_OFFERINGS` have no foreign keys into the floor
on purpose: they represent *external* data, and modelling them as related would
imply a join that does not exist in reality.

---

## Decisions, and what they cost

### Money as integer cents

Stored `BigInteger`, summed as integers, converted to dollars exactly once at
the API boundary.

*Alternative:* `Numeric`/`Decimal`. Exact, but `Decimal` infects every
downstream function and mixes badly with the float ratios that peer indexing
needs.

*Cost:* Postgres `SUM()` over `BIGINT` returns `NUMERIC` anyway, so there is a
coercion at the SQL boundary — and it fails **only** against Postgres, never in
the SQLite tests. Commented at the site.

### Aggregate in SQL, index in Python

Peer indexing needs two passes over the same result set. At ~840 machines the
extra round trip costs more than the arithmetic.

*Cost:* does not scale to 50,000 machines. Fine for one property, and stated
rather than pretended otherwise.

### No Alembic

The database is regenerated from a deterministic seed on every run, so
migrations would be ceremony with no payoff.

*Cost:* a production build needs them. Documented as a known shortcut rather
than hidden.

### The market layer is a Protocol

`market/` defines an interface with exactly one synthetic implementation.

*Why:* honesty — you can see precisely what a real adapter must supply — and
testability. The recommendation engine depends on the Protocol, so tests inject
fixed benchmarks without touching a database.

### The chat layer gets tools, never SQL

*Alternative:* text-to-SQL. More flexible, and it makes every number
unreproducible. That trade is not worth making for a system informing capital
decisions.

*Cost:* a question outside the tool set cannot be answered. The tools say so
rather than guessing.

### `float` for ratios, not `Decimal`

Ratios are derived, not accumulated. `Decimal` precision buys nothing and
complicates everything downstream.

---

## Deterministic data as a test oracle

The generator produces a floor with **a story already in it** — four planted
signals (`seed/scenarios.py`). Golden tests assert the pipeline reaches the
right *conclusion* about a floor whose truth we control.

That inverts the usual relationship: normally tests verify code against expected
values. Here the **dataset is the specification**, and the tests check that the
analytics still read it correctly. Refactor a threshold and unit tests stay
green while golden tests fail — which is exactly the signal you want.

---

## Deployment

```mermaid
flowchart LR
    subgraph rg["Resource group"]
        MI["Managed Identity"]
        ACR["Container Registry"]
        CAE["Container Apps Env"]
        API["ca-api"]
        WEB["ca-web"]
        PG[("PostgreSQL<br/>Flexible Server")]
        KV["Key Vault"]
        AIF["AI Foundry<br/><small>disableLocalAuth</small>"]
        LAW["Log Analytics"]
    end

    MI -->|AcrPull| ACR
    MI -->|Secrets User| KV
    MI -->|OpenAI User| AIF
    API --> PG
    API --> AIF
    API --> KV
    WEB --> API
    API --> LAW
    WEB --> LAW

    style MI fill:#0B3D2E,stroke:#F5C518,color:#F5F1E8
    style AIF fill:#12563F,stroke:#FF2E88,color:#F5F1E8
```

**Every arrow out of `MI` is an RBAC role assignment.** There are no keys and no
connection strings in the templates.

The AI Foundry account sets `disableLocalAuth: true` — key-based auth is turned
off at the resource, so "just use an API key" is not merely discouraged here, it
is impossible.

The one generated secret is the PostgreSQL admin password: created at provision
time, written straight to Key Vault, never an output.

More: [Deploy to Azure](deploy-azure.md)
