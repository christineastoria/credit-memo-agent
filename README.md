# Credit Investment Memo Agent

An AI-powered credit analysis agent built with [LangChain Deep Agents](https://github.com/langchain-ai/deepagents) that generates comprehensive credit investment memos for leveraged loans, high yield bonds, direct lending deals, and CLO tranches.

## Contents

- [Setup](#setup)
- [1. Agent Architecture](#1-agent-architecture)
- [2. Evaluations](#2-evaluations)
- [3. Testing in Studio](#3-testing-in-studio)
- [Project Structure](#project-structure)

## Setup

```bash
cd credit-investment-memo-agent
uv sync
cp .env.example .env   # then add your API keys
```

You'll need:
- **OpenAI API key** — powers the orchestrator and subagents (GPT-4.1)
- **Tavily API key or Perplexity API key** — web search (free tier at [tavily.com](https://tavily.com))
- **LangSmith API key** — tracing + sandbox + evals ([smith.langchain.com](https://smith.langchain.com/))

---

## 1. Agent Architecture

```
                    ┌──────────────────────────────────────┐
                    │      Credit Memo Orchestrator         │
                    │        (Deep Agent — GPT-4.1)         │
                    │                                      │
                    │  Tools: generate_memo_docx            │
                    │         read/save_market_intel        │
                    │         read_analyst_prefs            │
                    │         write_todos, task             │
                    └──────┬───────────┬───────────┬───────┘
                           │           │           │
              ┌────────────┘           │           └────────────┐
              ▼                        ▼                        ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   Research Subagent  │  │    Data Subagent     │  │ Calculations Subagent│
│                     │  │                     │  │                     │
│  web_search (Tavily) │  │  query_deals_db     │  │  run_financial_     │
│  rag_search (Chroma) │  │  get_db_schema      │  │  calculation        │
└──────────┬──────────┘  └──────────┬──────────┘  └──────────┬──────────┘
           │                        │                        │
           ▼                        ▼                        ▼
   ┌───────────────┐       ┌───────────────┐       ┌───────────────┐
   │  Tavily API   │       │    SQLite     │       │   LangSmith   │
   │  + Chroma RAG │       │   deals.db   │       │    Sandbox    │
   └───────────────┘       └───────────────┘       └───────────────┘

  ╔══════════════════════════════════════════════════════════════════╗
  ║  Middleware                    ║  Memory (namespaced Store)      ║
  ║  ├── TodoListMiddleware        ║  ("analyst", id) → preferences  ║
  ║  ├── FilesystemMiddleware      ║  ("market", sector) → intel     ║
  ║  ├── SubAgentMiddleware        ╚═════════════════════════════════╣
  ║  ├── SkillsMiddleware                                           ║
  ║  └── compliance_guardrail (custom @wrap_tool_call)              ║
  ╚═════════════════════════════════════════════════════════════════╝
```

### Components

| Component | Purpose | Tools |
|-----------|---------|-------|
| **Orchestrator** (`create_deep_agent`) | Plans workflow, coordinates subagents, assembles final memo | `generate_memo_docx`, `write_todos`, `task`, memory tools |
| **Research Subagent** | Gathers public + internal qualitative research | `web_search`, `rag_search` |
| **Data Subagent** | Queries internal deal database for comps and exposure | `query_deals_db`, `get_db_schema` |
| **Calculations Subagent** | Runs financial math in a secure sandbox | `run_financial_calculation` |

### Key Features

- **Multi-source research**: Combines internet data (Tavily or Perplexity) with internal docs (RAG) and deal data (SQLite)
- **Precise calculations**: Financial metrics computed via LangSmith code sandbox — no LLM arithmetic
- **Branded output**: Generates formatted `.docx` memos using a structured template (Deep Agents Skill)
- **Citation tracking**: Every fact tagged with its source, compiled into a Sources appendix
- **Compliance guardrails**: Custom `@wrap_tool_call` middleware filters MNPI, enforces disclaimers, logs data access
- **Persistent memory**: Analyst preferences and market intelligence persist across sessions via namespaced Store

### How It Works

The agent follows a 10-step workflow:

1. Read analyst preferences and sector intelligence from memory
2. Plan the memo workflow using `write_todos`
3. Delegate research to the Research subagent (web search + internal docs)
4. Delegate data queries to the Data subagent (comparable deals, portfolio exposure)
5. Delegate calculations to the Calculations subagent (credit metrics, stress tests)
6. Load the `credit-memo-template` Skill for formatting guidance
7. Synthesize all findings into the memo template sections
8. Generate a formatted `.docx` memo and save to `agent/output/`

Steps 3 and 4 run in parallel. Step 5 depends on both.

### Memory

| Namespace | Purpose | Tool |
|-----------|---------|------|
| `("analyst", <id>)` | Analyst preferences, style, focus areas | `read_analyst_prefs` |
| `("market", <sector>)` | Sector trends, typical metrics, comps | `read_market_intel` / `save_market_intel` |

### Compliance Middleware

The `compliance_guardrail` middleware uses the `@wrap_tool_call` decorator to intercept every tool call:

1. **MNPI Filter** — Scans tool outputs for material non-public information keywords and blocks them
2. **Disclaimer Check** — Validates memos include required compliance language before writing
3. **Audit Logging** — Logs every external data access to `agent/output/audit_log.json`

### Dummy Data

The demo includes realistic dummy data seeded automatically on first run:

- **20 historical deals** across Healthcare, Technology, Industrials, Consumer, and Energy sectors
- **10 portfolio holdings** with current pricing and risk ratings
- **3 internal research memos** (Acme Corp, GlobalTech Industries, Summit Healthcare Partners)

### Command Line

```bash
python agent/main.py "Generate a credit memo for Acme Corp"
python agent/main.py 'Analyze Summit Healthcare Partners for a new 200M dollar term loan'
python agent/main.py   # interactive mode
```

---

## 2. Evaluations

The project includes a full evaluation suite with five evaluator types, a test dataset, and a runner script that supports model comparison. Results are visualized in LangSmith.

### Evaluator Types

| Evaluator | Type | What it checks |
|-----------|------|----------------|
| `structural_quality` | Code check | All 8 required memo sections present in the output |
| `trajectory_quality` | LLM judge | Tool call sequence is logical, arguments well-formed, execution efficient |
| `goal_achievement` | LLM judge | Memo achieves 10 specific goals (recommendation, metrics, risk analysis, citations) |
| `regex_patterns` | Code check | Formatting conventions — leverage ratios (`4.7x`), percentages (`20.0%`), dollar amounts (`$300M`), ratings (`BB-`), disclaimer |
| `pe_credit_diligence` | LLM judge | PE diligence criteria — sponsor involvement, stress scenarios, management, covenants, comps, sector risks |

### Test Dataset

Three examples covering different borrowers and deal types, uploaded to LangSmith:

| Borrower | Sector | Deal Type |
|----------|--------|-----------|
| Acme Corp | Industrials | Term Loan |
| Summit Healthcare Partners | Healthcare | Direct Lending |
| GlobalTech Industries | Technology | Leveraged Loan |

Each example includes reference outputs: required sections, 10 goals, expected tool sequence, regex patterns, and 7 PE diligence criteria.

### Running Evaluations

```bash
# Upload the test dataset to LangSmith
python eval/dataset.py

# Run all evaluators — compares gpt-4.1-mini vs gpt-4.1 side-by-side
python eval/run_eval.py

# Custom experiment prefix
python eval/run_eval.py --experiment-prefix v2-with-perplexity

# Single model only
python eval/run_eval.py --single-model gpt-4.1

# Compare custom set of models
python eval/run_eval.py --models gpt-4.1-mini gpt-4.1 gpt-4.1-nano
```

Each model produces a separate experiment on the same dataset in LangSmith for side-by-side comparison. All evaluators return `{"score": float, "comment": str}` which renders natively in LangSmith's evaluation UI.

### Tracing

All agent runs are traced in LangSmith. Set these in your `.env`:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-key
LANGSMITH_PROJECT=credit-memo-agent
```

---

## 3. Testing in Studio

Open the project in [LangGraph Studio](https://github.com/langchain-ai/langgraph-studio) to visualize the agent graph, inspect state at each node, and experiment interactively.

```bash
uv run langgraph dev
```

This reads `langgraph.json` in the project root, which points to `agent/graph.py:graph`. The server automatically seeds the database, initializes the RAG vector store, and loads memory — no manual setup needed.

### Example Queries

```
Generate a credit memo for Acme Corp evaluating a new $300M term loan opportunity.
Use reasonable assumptions for missing data. Do not ask questions, just produce the memo.
```

```
Analyze Summit Healthcare Partners for a potential $200M direct lending facility.
They operate outpatient surgery centers in the Southeast. Produce the full memo.
```

```
Generate a credit memo for GlobalTech Industries evaluating their BB- rated leveraged loan.
Do not ask questions, produce the memo.
```

---

## Project Structure

```
├── agent/
│   ├── main.py                      # CLI entry point
│   ├── deep_agent.py                # create_orchestrator() — Deep Agent config
│   ├── graph.py                     # LangGraph Studio entry point
│   ├── middleware.py                 # Compliance guardrail (@wrap_tool_call)
│   ├── subagents/
│   │   ├── research.py              # Research subagent (Tavily/Perplexity + RAG)
│   │   ├── data.py                  # Data subagent (SQLite)
│   │   └── calculations.py          # Calculations subagent (sandbox)
│   ├── tools/
│   │   ├── web_search.py            # Internet search
│   │   ├── rag_retriever.py         # Semantic search over internal docs
│   │   ├── sqlite_query.py          # SQL queries against deal database
│   │   ├── sandbox_calc.py          # LangSmith sandbox for financial math
│   │   ├── memo_writer.py           # python-docx document generation
│   │   └── memory_tools.py          # Store-backed analyst/market memory
│   ├── skills/
│   │   └── credit-memo-template/
│   │       └── SKILL.md             # Branded memo template + section guidance
│   ├── data/
│   │   ├── seed_db.py               # Database seeder script
│   │   ├── deals.db                 # SQLite database (generated)
│   │   └── internal_docs/           # Internal research memos
│   └── output/                      # Generated memo documents
├── eval/
│   ├── dataset.py                   # Test dataset (3 examples)
│   ├── evaluators.py                # Five evaluator types
│   └── run_eval.py                  # Evaluation runner with model comparison
├── langgraph.json                   # LangGraph Studio config
└── pyproject.toml
```
