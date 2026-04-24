# Credit Investment Memo Agent

An AI-powered credit analysis agent built with [LangChain Deep Agents](https://github.com/langchain-ai/deepagents) that generates comprehensive credit investment memos for leveraged loans, high yield bonds, direct lending deals, and CLO tranches.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Credit Memo Orchestrator                │
│              (Deep Agent — GPT-4.1)                  │
│                                                     │
│  Middleware:                                        │
│  ├── TodoListMiddleware                             │
│  ├── FilesystemMiddleware                           │
│  ├── SubAgentMiddleware                             │
│  ├── SkillsMiddleware                               │
│  └── ComplianceGuardrailMiddleware (custom)         │
│                                                     │
│  Memory (namespaced Store):                         │
│  ├── ("analyst", <id>) → analyst preferences        │
│  └── ("market", <sector>) → sector intelligence     │
│                                                     │
├──────────────┬──────────────┬───────────────────────┤
│              │              │                        │
▼              ▼              ▼                        │
┌──────────┐ ┌──────────┐ ┌──────────────┐           │
│ Research  │ │   Data   │ │ Calculations │           │
│ Subagent │ │ Subagent │ │  Subagent    │           │
│          │ │          │ │              │           │
│ Tavily   │ │  SQLite  │ │  LangSmith  │           │
│ + RAG    │ │ queries  │ │  Sandbox    │           │
└──────────┘ └──────────┘ └──────────────┘           │
```

### Components

| Component | Purpose | Tools |
|-----------|---------|-------|
| **Orchestrator create_deep_agent** | Plans workflow, coordinates subagents, assembles final memo | `generate_memo_docx`, `write_todos`, `task`, memory tools |
| **Research Subagent** | Gathers public + internal qualitative research | `web_search`, `rag_search` |
| **Data Subagent** | Queries internal deal database for comps and exposure | `query_deals_db`, `get_db_schema` |
| **Calculations Subagent** | Runs financial math in a secure sandbox | `run_financial_calculation` |

### Key Features

- **Multi-source research**: Combines internet data (Tavily or Perplexity) with internal docs (RAG) and deal data (SQLite)
- **Precise calculations**: Financial metrics computed via LangSmith code sandbox — no LLM arithmetic
- **Branded output**: Generates formatted `.docx` memos using a structured template (Deep Agents Skill)
- **Citation tracking**: Every fact tagged with its source, compiled into a Sources appendix
- **Compliance guardrails**: Custom middleware filters MNPI, enforces disclaimers, logs data access
- **Persistent memory**: Analyst preferences and market intelligence persist across sessions via namespaced Store
- **Evaluation suite**: Five evaluator types with model comparison and LangSmith dataset for systematic quality testing

## Setup

### 1. Install dependencies

```bash
cd credit-investment-memo-agent
uv sync        
```

### 2. Configure API keys

```bash
cp .env.example .env
# Edit .env with your actual API keys
```

You'll need:
- **OpenAI API key** — powers the orchestrator and subagents (GPT-4.1)
- **Tavily API key or Perplexity API key** — web search (free tier at [tavily.com](https://tavily.com))
- **LangSmith API key** — tracing + sandbox + evals ([smith.langchain.com](https://smith.langchain.com/))

Swap Tavily for Perplexity (richer citations) — see `agent/tools/web_search.py` for instructions.

### 3. Seed the database

```bash
python agent/data/seed_db.py
```

This creates `agent/data/deals.db` with dummy historical deal data and portfolio holdings.

## Usage

### Command line

```bash
# Analyze a specific borrower
python agent/main.py "Generate a credit memo for Acme Corp"

# Specify deal details
python agent/main.py 'Analyze Summit Healthcare Partners for a new 200M dollar term loan'

# Interactive mode
python agent/main.py
```

### LangGraph Studio

You can open this project in [LangGraph Studio](https://github.com/langchain-ai/langgraph-studio) to visualize the agent graph, inspect state at each node, and experiment interactively.

```bash
uv run langgraph dev
```

This reads `langgraph.json` in the project root, which points to `agent/graph.py:graph`. The server automatically seeds the database, initializes the RAG vector store, and loads memory — no manual setup needed. Open the Studio UI to send requests, watch tool calls in real time, and explore subagent delegation.

### Example output

The agent will:
1. Plan the memo workflow (TodoList)
2. Read analyst preferences and sector intelligence from memory
3. Research the borrower via web search + internal docs
4. Query the deal database for comparable transactions
5. Calculate credit metrics and run stress tests in a sandbox
6. Load the memo template Skill for formatting guidance
7. Assemble everything into a formatted `.docx` memo
8. Save the document to `agent/output/`

## Project Structure

```
├── agent/                           # Agent code
│   ├── main.py                      # Entry point + orchestrator setup
│   ├── middleware.py                # ComplianceGuardrailMiddleware
│   │
│   ├── subagents/
│   │   ├── research.py              # Research subagent (Tavily/Perplexity + RAG)
│   │   ├── data.py                  # Data subagent (SQLite)
│   │   └── calculations.py         # Calculations subagent (sandbox)
│   │
│   ├── tools/
│   │   ├── web_search.py            # Internet search (Tavily active, Perplexity commented)
│   │   ├── rag_retriever.py         # Semantic search over internal docs
│   │   ├── sqlite_query.py          # SQL queries against deal database
│   │   ├── sandbox_calc.py          # LangSmith sandbox for financial math
│   │   ├── memo_writer.py           # python-docx document generation
│   │   └── memory_tools.py          # Store-backed analyst/market memory access
│   │
│   ├── skills/
│   │   └── credit-memo-template/
│   │       └── SKILL.md             # Branded memo template + section guidance
│   │
│   ├── data/
│   │   ├── seed_db.py               # Database seeder script
│   │   ├── deals.db                 # SQLite database (generated)
│   │   └── internal_docs/           # Dummy internal research memos
│   │       ├── acme_corp_q3_review.md
│   │       ├── globaltech_credit_note.md
│   │       └── summit_healthcare_memo.md
│   │
│   └── output/                      # Generated memo documents
│
├── eval/                            # Evaluation suite
│   ├── dataset.py                   # Test dataset (3 examples, uploads to LangSmith)
│   ├── evaluators.py                # Five evaluator types
│   └── run_eval.py                  # Evaluation runner with model comparison
```

## Memory Architecture

The agent uses an `InMemoryStore` with namespaced keys for persistent memory, accessed via custom tools:

| Namespace | Persistence | Purpose | Tool |
|-----------|-------------|---------|------|
| `("analyst", <id>)` | Cross-session | Analyst preferences, style, focus areas | `read_analyst_prefs` |
| `("market", <sector>)` | Cross-session | Sector trends, typical metrics, comps | `read_market_intel` / `save_market_intel` |

Analyst preferences and market intelligence build up over time — analyzing healthcare borrowers enriches the `("market", "healthcare")` data that benefits future healthcare memos.

## Compliance Middleware

The `ComplianceGuardrailMiddleware` demonstrates custom `AgentMiddleware` using `wrap_tool_call`:

1. **MNPI Filter** — Scans tool outputs for material non-public information keywords and blocks them
2. **Disclaimer Check** — Validates memos include required compliance language before writing
3. **Audit Logging** — Logs every external data access to `agent/output/audit_log.json`

## Evaluations

The project includes a full evaluation suite with five evaluator types, a test dataset, and a runner script that supports model comparison. Results are visualized in LangSmith.

### Evaluator Types

| Evaluator | Type | What it checks |
|-----------|------|----------------|
| `structural_quality` | Code check | All 8 required memo sections are present in the output |
| `trajectory_quality` | LLM judge | Tool call sequence is logical, arguments are well-formed, execution is efficient |
| `goal_achievement` | LLM judge | Memo achieves specific goals (recommendation, metrics, risk analysis, citations, etc.) |
| `regex_patterns` | Code check | Output contains expected formatting — leverage ratios (`4.7x`), percentages (`20.0%`), dollar amounts (`$300M`), ratings (`BB-`), disclaimer text |
| `pe_credit_diligence` | LLM judge | PE credit fund diligence — sponsor equity, downside/recovery, covenants, key-person risk, exit paths, relative value, ESG |

### Test Dataset

Three evaluation examples covering different borrowers and deal types:

| Example | Borrower | Sector | Deal Type |
|---------|----------|--------|-----------|
| 1 | Acme Corp | Industrials | Term Loan |
| 2 | Summit Healthcare Partners | Healthcare | Direct Lending |
| 3 | GlobalTech Industries | Technology | Leveraged Loan |

Each example includes:
- **Input**: borrower request with sector and deal type metadata
- **Reference outputs**: required sections list, 10 specific goals, expected tool sequence, regex patterns, 7 PE diligence criteria

### Running Evaluations

```bash
# Step 1: Upload the test dataset to LangSmith
python eval/dataset.py

# Step 2: Run all evaluators — compares gpt-4.1-mini vs gpt-4.1 side-by-side
python eval/run_eval.py

# Step 3: View results in LangSmith under the "Credit Memo Agent Evals" dataset
#         Each model produces a separate experiment for side-by-side comparison

# Custom experiment prefix
python eval/run_eval.py --experiment-prefix v2-with-perplexity

# Run a single specific model only
python eval/run_eval.py --single-model gpt-4.1

# Compare custom set of models
python eval/run_eval.py --models gpt-4.1-mini gpt-4.1 gpt-4.1-nano
```

### How Each Evaluator Works

**Structural Quality** (`structural_quality`)
Checks that the agent's final response mentions all 8 required memo sections (Executive Summary, Business Overview, Capital Structure, etc.). Scores proportionally — 6/8 sections = 0.75 score.

**Trajectory Quality** (`trajectory_quality`)
An LLM judge (GPT-4.1-mini) that reviews the full tool call trajectory captured during agent execution. It evaluates three dimensions on a 1-5 scale: tool selection (right tools used?), argument quality (well-formed instructions to subagents?), and efficiency (no redundant calls?). The overall score is normalized to 0-1.

**Goal Achievement** (`goal_achievement`)
An LLM judge that checks the memo against 10 specific goals defined in the dataset — things like "includes specific leverage ratio with a numeric value" or "references internal deal history." Each goal is binary (met or missed), and the score is the proportion achieved.

**Regex Patterns** (`regex_patterns`)
A deterministic code check that validates formatting conventions using regex:
- `leverage_ratio`: matches patterns like `4.7x`, `2.1x`
- `percentage`: matches `20.0%`, `15.3%`
- `dollar_amount`: matches `$300M`, `$950`
- `rating`: matches `BB-`, `B+`, `CCC`
- `disclaimer_present`: checks for "internal use only" text

**PE Credit Diligence** (`pe_credit_diligence`)
An LLM judge applying private equity credit diligence standards. Checks 7 criteria that a PE credit fund's investment committee would require:
- Sponsor equity contribution and alignment of interests
- Downside protection with recovery estimates under stress
- Management quality and key-person risk assessment
- Covenant package evaluation (maintenance vs incurrence, headroom)
- Exit or refinancing pathways and timeline
- Relative value comparison against comparable credits
- ESG risk considerations specific to the borrower's sector

### Model Comparison

The eval runner defaults to comparing `gpt-4.1-mini` and `gpt-4.1` side-by-side. Each model produces a separate experiment on the same dataset in LangSmith, making it easy to compare scores across all five evaluators.

### Evaluator Output Format

All evaluators return `{"score": float, "comment": str}` which renders natively in LangSmith's evaluation UI. The metric name is auto-derived from the function name (e.g., `structural_quality` becomes the metric label).

## Tracing

All agent runs are traced in LangSmith. Set these in your `.env`:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-key
LANGSMITH_PROJECT=credit-memo-agent
```

View traces at [smith.langchain.com](https://smith.langchain.com/) to see the full orchestration flow, subagent delegation, and tool calls.

## Dummy Data

The demo includes realistic dummy data:

- **20 historical deals** across Healthcare, Technology, Industrials, Consumer, and Energy sectors
- **10 portfolio holdings** with current pricing and risk ratings
- **3 internal research memos** (Acme Corp, GlobalTech Industries, Summit Healthcare Partners)

This data is seeded automatically on first run and simulates a real firm's internal knowledge base.
