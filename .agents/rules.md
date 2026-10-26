# Repository Guardrails & Agent Directives: Nerolac Dash

> **CRITICAL DIRECTIVE FOR ALL AI AGENTS & CONTRIBUTORS**
> This repository enforces strict architectural patterns, UI/UX constraints, schema integrity locks, and data flow standards. Deviations, hallucinations, unapproved libraries, or non-compliant design elements will trigger automated build failures and AST compliance blocks.

---

## 1. Mandatory Architecture

All development across this codebase must adhere strictly to the following four-tier architecture:

1. **Frontend**: **Next.js 15 App Router**
   - **Language**: TypeScript (`strict: true`)
   - **Component Model**: React Server Components (RSC) by default. Use `'use client'` strictly when client-side state, event handlers, or browser APIs are required.
   - **Routing**: App Router directory structure (`app/`). Pages and layouts must leverage RSC for data fetching and streaming with Suspense.

2. **Backend**: **Python FastAPI (Async ASGI)**
   - **Runtime**: Python 3.9+ async ASGI with `uvicorn`.
   - **Endpoints**: Every route handler MUST be defined as `async def`.
   - **Validation & Serialization**: Strict Pydantic v2 schemas for all request payloads and response models.
   - **Database Access**: Fully asynchronous database queries using `asyncpg` and SQLAlchemy async engine/sessions. Blocking synchronous database calls (e.g., standard `psycopg2` or synchronous ORM queries) are strictly forbidden.

3. **Database**: **PostgreSQL 16**
   - Relational data model with explicit foreign key constraints, indexing, and strict schema versioning.
   - All migrations must be managed via Alembic or versioned DDL scripts validated through automated test suites.

4. **Cache & Message Broker**: **Redis 7**
   - High-throughput asynchronous caching, real-time pub/sub pipelines, and rate limiting via `redis-py` async client (`redis.asyncio`).

---

## 2. UI/UX Design Constraints: Bright Light Corporate Mode

The user interface represents Nerolac's enterprise operations dashboard and must convey maximum reliability, clarity, and precision.

### Color Palette & Design Tokens

- **Canvas (Background)**: `#FFFFFF` (Pure White).
- **Containers & Cards**: `#F8FAFC` (Slate 50 / Crisp corporate grey-white).
- **Accents & Highlights**: `#D32F2F` (Official Nerolac Red).
- **Borders & Dividers**: `1px solid #E2E8F0` (Slate 200).
- **Typography & Number Display**: `tabular-nums` (`font-variant-numeric: tabular-nums`) is **mandatory** on all numeric values, KPIs, data tables, metrics, inventory counts, timestamps, and currency displays.
- **Spacing Grid**: Strict 4px/8px corporate grid.

### Explicit Prohibitions (Zero Tolerance)

- **NO Dark Mode**: Complete ban on dark theme tokens, `dark:` classes, `prefers-color-scheme: dark`, `#000000` / `#121212` backgrounds, or user-toggled dark modes.
- **NO Glassmorphism**: Complete ban on `backdrop-filter`, `backdrop-blur`, semi-transparent frosted cards, or fuzzy translucent panels.
- **NO Floating Gradients**: Complete ban on `linear-gradient`, `radial-gradient`, decorative gradient blobs, or `bg-gradient-to-*` styling.
- **NO Loose Padding**: Padding must be structured, tight, aligned, and bounded to the corporate 8px grid system. No arbitrary, exaggerated, or floating margins/paddings.

---

## 3. Schema Lock & Database Integrity

- **Target File**: `/workspace/knowledge/Backend_Database_Schema_(PostgreSQL_16_DDL).md` (and `knowledge/Backend_Database_Schema_(PostgreSQL_16_DDL).md`).
- **Policy**: Absolute lock on schema modifications.
- **Directives**:
  1. Agents and developers are strictly forbidden from altering database schemas, DDL files, or table structures without executing automated regression and test suites.
  2. Modifying table names, column types, foreign key constraints, or removing indexes without formal schema migration verification will trigger automated CI/CD and pre-commit rejections.

---

## 4. Zero Frontend Mock Data

- **Policy**: Pristine, clean frontend interfaces awaiting live backend pipeline feeds.
- **Directives**:
  1. **Never** render fake, dummy, or hardcoded mock datasets (`const mockData = [...]`, `const dummyUsers = [...]`, fake JSON arrays) in frontend components.
  2. Frontend components must render clean loading skeletons, pristine empty states, or type-safe props receiving data fetched directly from live backend FastAPI endpoints.
  3. All TypeScript component prop interfaces must map directly to OpenAPI / Pydantic response schemas.

---

## 5. Automated Verification & Guardrails

- **AST Code Trees**: Every Python file and TypeScript/JavaScript file is parsed and validated by `scripts/verify_agent_compliance.py`.
- **Pre-Commit Enforcement**: Husky pre-commit hooks at `.husky/pre-commit` execute:
  - `Ruff`: Python linting and code quality
  - `mypy`: Strict static type checking
  - `ESLint`: Frontend code linting
  - `Prettier`: Code formatting and layout verification
  - `verify_agent_compliance.py`: Architectural and AST rule verification
