# ⚡ Engine_lighting: Multi-Agent Lighting Substitution & Compliance Engine

> An enterprise-grade, multi-agent software platform for industrial and architectural lighting tenders. Parses massive technical schedules (300+ page CCTP/BOQ), certifies documentary evidence, eliminates hallucinations through physical validation, and executes multi-criteria substitution using local Small Language Models (SLMs) and an AI Harness.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg)](https://fastapi.tiangolo.com/)
[![Local SLM](https://img.shields.io/badge/SLM-Qwen%202.5%3A3b%20(Ollama)-purple.svg)](https://ollama.com/)
[![Architecture](https://img.shields.io/badge/Swarm-4%20Specialized%20Agents-green.svg)](#-the-4-agent-swarm--ai-harness-architecture)
[![Next.js](https://img.shields.io/badge/Next.js-14%20(App%20Router)-black.svg)](https://nextjs.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/Tests-33%20Passed-success.svg)](#-automated-testing)

---

## 📌 Problem Statement & Core Value

In commercial, architectural, and industrial lighting engineering, responding to tender schedules (CCTP, BOQ, and complex bill-of-quantities in PDF/Excel) requires cross-referencing hundreds of technical line items against manufacturer catalogs. 

Manual substitution is tedious, slow, and presents severe compliance risks:
* **Stringent Regulatory & Photometric Constraints:** Ingress Protection (IP rating), Color Rendering Index (CRI), Correlated Color Temperature (CCT), beam angles, and luminous efficacy ($\text{lm/W}$).
* **Commercial & Ecological Trade-offs:** Balancing distributor gross margins against lifecycle operating cost and carbon footprint ($kg\text{ CO}_2e$).

**Engine_lighting** automates this lifecycle by combining an **Essaim of 4 specialized AI Agents**, an **orchestration AI Harness**, and a **deterministic mathematical matching engine**.

---

## 🏗️ The 4-Agent Swarm & AI Harness Architecture

Rather than relying on a single, expensive, and hallucination-prone monolithic prompt, the system delegates responsibilities across 4 isolated, highly specialized agents orchestrated by a deterministic state-machine Harness:

```mermaid
flowchart TD
    A["Raw Tender Document<br/>(300+ Page PDF / CCTP / BOQ)"] --> B["Agent 1: Analysis & Triage<br/>(analysis_agent.py)"]
    
    subgraph Agent1 ["⚡ Agent 1 : Document Triage (4.09s)"]
        B -->|4-Level Cascade| B1["Native Bookmarks ➔ TOC ➔ Header Scan ➔ Fallback"]
        B1 -->|Eliminates 72% off-topic pages| C["Targeted Lighting Pages Only"]
    end
    
    C --> D["Agent 2: Retrieval & Evidence<br/>(retrieval_agent.py)"]
    
    subgraph Agent2 ["📍 Agent 2 : Retrieval & Evidence Sealing"]
        D -->|Multi-Format Parser| D1["Table Grid · Article Segmentation · Deduplication"]
        D1 -->|Seals certified page number| E["Isolated Line Items with '📍 p.X' Evidence"]
    end
    
    E --> F["Agent 3: Extraction SLM<br/>(extraction_agent.py)"]
    
    subgraph Agent3 ["🤖 Agent 3 : Local SLM Extraction (1.23s/item)"]
        F -->|Ollama: Qwen 2.5:3b| F1["num_ctx: 2048 · temp: 0.0 · JSON Mode"]
        F1 -->|Pydantic Contract| G["Normalized PRO (Project Requirement Object)"]
    end
    
    G --> H["Agent 4: Validation & Reflection<br/>(validation_agent.py)"]
    
    subgraph Agent4 ["🛡️ Agent 4 : Physical Validation & Reflection"]
        H -->|Physical Bounds Check| H1{"lm/W ∈ [25, 250]<br/>CCT ∈ [1800K, 10000K]<br/>CRI ∈ [50, 100]<br/>IP/IK Formats"}
        H1 -->|Valid| I["AUTO_ACCEPTED"]
        H1 -->|Invalid (Max 2 Retries)| H2["TEACHER_CORRECTED (Groq/Ollama)"]
        H2 -->|Unresolved| H3["HUMAN_REVIEW (Flagged Red)"]
    end

    subgraph Harness ["🛡️ AI Harness Orchestration (harness.py)"]
        direction TB
        J["State Machine: IDLE ➔ TRIAGING ➔ RETRIEVING ➔ EXTRACTING ➔ VALIDATING ➔ COMPLETED"]
        K["Anti-Freeze: 15s Strict Timeout per block with Deterministic Fallback"]
        L["Telemetry & Event Emitter: Duration, Confidence, Spans"]
    end

    I --> M["Deterministic Substitution & Matching Engine"]
    H2 --> M
    H3 --> N["HITL Interactive Review Dashboard"]
    N --> M
```

---

## 🎯 Key Engineering Challenges & Solutions

### 1. Document Triage in 4 Seconds on 300+ Page CPS (Agent 1)
* **The Challenge:** Ingesting 300 to 900-page tenders into an LLM exceeds context windows and is prohibitively expensive.
* **Our Solution:** A deterministic 4-level cascade (Bookmarks $\to$ TOC $\to$ Header pattern scanning $\to$ fallback).
* **Measured Benchmark:** On a real 316-page municipal tender (Berkane CPS), Agent 1 triaged the document in **4.09 seconds**, eliminating **227 off-topic pages (-72% payload)** before invoking any neural network.

### 2. Fast Local Inference & Zero Cloud Costs (Agent 3)
* **The Challenge:** Running cloud models (GPT-4) on hundreds of line items incurs latency and high token costs, while risking client data confidentiality.
* **Our Solution:** **Qwen 2.5:3b** running locally via Ollama with strict resource boundaries:
  * `temperature: 0.0` for deterministic outputs.
  * `num_ctx: 2048` bounded context (divides RAM consumption by ~60%, running under 2.5 GB RAM).
  * `keep_alive: 15m` preventing cold-start overhead.
* **Measured Benchmark:** **1.238 seconds per luminaire** on local inference.

### 3. Preventing Hallucinations via Physical Law Validation (Agent 4)
* **The Challenge:** LLMs frequently hallucinate contradictory specifications (e.g., claiming 10W produces 10,000 lumens, or invalid IP ratings like IP99).
* **Our Solution:** Agent 4 enforces immutable laws of physics and regulatory standards:
  * Luminous efficacy ratio check: $25 \le \frac{\text{Lumens}}{\text{Watts}} \le 250\text{ lm/W}$.
  * Thermodynamic bounds: $\text{CCT} \in [1800\text{K}, 10000\text{K}]$, $\text{CRI} \in [50, 100]$.
  * Valid IP/IK regex formatting ($IP20, IP44, IP65, IP66 / IK02-IK10$).
* **3-State Arbiter:** `AUTO_ACCEPTED` (high confidence) $\to$ `TEACHER_CORRECTED` (reflexive retry with error feedback) $\to$ `HUMAN_REVIEW` (transparent flag).

### 4. Zero-Hallucination Deterministic Matching Engine
* **Hard Constraints (Filter):** Non-negotiable physical constraints ($IP_{substitute} \ge IP_{required}$, flux tolerance $\pm 30\%$, voltage class) are executed in pure Python/SQL math—**never by an LLM**.
* **Soft Scoring:** Ranks compliant candidates by optical similarity, efficacy ($\text{lm/W}$), and color fidelity (CRI).
* **Business Overlay:** Optimizes distributor margins, flags stock shortages, and computes lifecycle carbon emission savings:
  $$\Delta \text{CO}_2\text{ (kg)} = \frac{(W_{initial} - W_{substitute}) \times \text{Hours}}{1000} \times 0.4$$

---

## 🌍 Modular Market Packs (Internationalization)

The core engine is 100% market-agnostic. Regional conventions are declared as modular `MarketPack` configurations:

```text
backend/app/modules/ingestion/market_packs/
├── base.py       # Pydantic contract: triage keywords, regex patterns, voltage, units
├── morocco.py    # Pack MA: CPS, CCAG-T, Prix N°, 230V, metric, MAD, SATI/BAES MicroRAG
├── france.py     # Pack FR: CCTP, DPGF, NF EN 12464-1, 230V, EUR (In Progress)
└── registry.py   # Automatic heuristic market detection
```

---

## 📂 Repository File Structure

```text
Engine_lighting/
├── backend/
│   ├── app/
│   │   └── modules/
│   │       ├── ingestion/
│   │       │   ├── document_intelligence/  # Ingestion intelligence & MicroRAG
│   │       │   └── market_packs/           # Modular Market Packs (MA, FR, US)
│   │       └── tuning/                     # Active Learning dataset exporter (JSONL)
│   ├── db/                                 # Async database sessions, Redis cache & seed
│   ├── ingestion/
│   │   ├── extractors/                     # PyMuPDF, Camelot (Lattice/Stream), Excel
│   │   └── pro_builder.py                  # Project Requirement Object normalizer
│   ├── matching/
│   │   ├── canonical.py                    # Standardized attribute normalizers
│   │   ├── hard_filter.py                  # Strict physical constraint satisfaction
│   │   ├── soft_scoring.py                 # Multi-attribute scoring algorithm
│   │   └── overlay.py                      # Tiered margin & stock calculations
│   ├── models/
│   │   ├── domain.py                       # SQLAlchemy async database models
│   │   └── schemas.py                      # Pydantic v2 schemas
│   ├── tests/                              # Pytest unit & integration test suites
│   ├── workflow/
│   │   ├── graph.py                        # LangGraph StateGraph agent definitions
│   │   └── router.py                       # Asynchronous workflow API endpoints
│   ├── Dockerfile
│   ├── main.py                             # FastAPI application entrypoint
│   └── requirements.txt
├── frontend/                               # Fullstack Next.js 14 App Router client
│   ├── src/app/                            # Routes: /project, /review, /line, /finalize
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml                      # Full orchestration: Backend, Frontend, Postgres, Redis, Ollama
├── .env.example                            # Clean environment template
├── ROADMAP.md                              # Master supervision board (Blocs 1-5)
└── README.md                               # Project documentation
```

---

## 🛠️ Tech Stack & Dependencies

| Layer | Technologies |
|---|---|
| **Backend API** | Python 3.11, FastAPI, Pydantic v2, Uvicorn |
| **Multi-Agent Orchestration** | Custom AI Harness, LangGraph, Tenacity (Exponential Backoff) |
| **Local SLM Inference** | Ollama (`qwen2.5:3b`, `qwen2.5:7b`), bounded context (`num_ctx: 2048`) |
| **Cloud Fallback** | Groq API (`llama-3.1-8b-instant`) |
| **Databases & Cache** | PostgreSQL 15, SQLAlchemy (AsyncPG), Redis 7 |
| **Document Processing** | PyMuPDF, Camelot-py, OpenCV, OpenPyXL, Pandas |
| **Frontend UI** | Next.js 14 (App Router), TypeScript, TailwindCSS, Lucide Icons |
| **DevOps & Containers** | Docker, Docker Compose, Healthchecks, Multi-stage builds |

---

## 🚀 Quickstart & Local Setup

### 1. Clone & Configure
```bash
git clone https://github.com/Achraf-sghiouar/Engine_lighting.git
cd Engine_lighting
cp .env.example .env
```

### 2. Launch Services with Docker Compose
```bash
docker-compose up --build
```
* **Frontend Web App:** [http://localhost:3000](http://localhost:3000)
* **Backend Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **PostgreSQL:** `localhost:5432` | **Redis:** `localhost:6379`

---

## 🧪 Automated Testing

The backend includes comprehensive test suites covering agents, extraction accuracy, physical bounds validation, and matching:
```bash
docker-compose exec backend pytest tests/ -v
```
*(All 33/33 tests currently passing).*

---

## 🗺️ Roadmap & Active Development

See [ROADMAP.md](ROADMAP.md) for the complete supervision dashboard.
Current in-progress milestones:
- [x] Swarm of 4 Agents & AI Harness with local SLM inference (Bloc 1).
- [x] Initial Market Pack isolation (`morocco.py`).
- [ ] **Multi-Tenant Catalog Importer (`catalog_importer.py`):** Client-specific Excel/CSV catalog indexing with strict `tenant_id` isolation.
- [ ] **Evidence & Trace Interface (Next.js):** Real-time execution waterfall showing agent step timings and certified source pages (`📍 p.X`).
- [ ] **Compliance Checklist Extractor:** Automatic parsing of tender administrative requirements (CE, ENEC, manufacturer datasheets).
- [ ] **Deliverables Engine:** Automated Excel BOM & Client Submittal PDF generation.

---

## 📄 License
MIT License. Developed by Achraf Sghiouar.
