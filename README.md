<div align="center">

```
     ███╗   ███╗██╗   ██╗ ██████╗ ███████╗███╗   ██╗     █████╗ ██╗
     ████╗ ████║██║   ██║██╔════╝ ██╔════╝████╗  ██║    ██╔══██╗██║
     ██╔████╔██║██║   ██║██║  ███╗█████╗  ██╔██╗ ██║    ███████║██║
     ██║╚██╔╝██║██║   ██║██║   ██║██╔══╝  ██║╚██╗██║    ██╔══██║██║
     ██║ ╚═╝ ██║╚██████╔╝╚██████╔╝███████╗██║ ╚████║    ██║  ██║██║
     ╚═╝     ╚═╝ ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═══╝    ╚═╝  ╚═╝╚═╝
```

### **Enterprise-Grade AI Asset Management Platform**
#### Autonomous · Policy-Aware · Adversarially Hardened

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![LLaMA](https://img.shields.io/badge/LLM-LLaMA_3.3_70B-7C3AED?style=flat-square&logo=meta)](https://groq.com)
[![RAG](https://img.shields.io/badge/RAG-ChromaDB_·_MiniLM-16A34A?style=flat-square)](https://trychroma.com)
[![PTB](https://img.shields.io/badge/Bot-python--telegram--bot_v20-0088CC?style=flat-square&logo=telegram)](https://python-telegram-bot.org)
[![License](https://img.shields.io/badge/License-MIT-F59E0B?style=flat-square)](LICENSE)

---

### 🎯 **What is MUGEN AI?**

MUGEN AI transforms enterprise IT asset management through intelligent automation. Unlike traditional form-based systems, it leverages advanced natural language processing, retrieval-augmented generation, and multi-layered security to deliver autonomous, policy-compliant asset request processing — entirely within Telegram.

**Key Differentiators:**
- 🧠 Natural language understanding with typo correction and context awareness
- 📚 Dynamic policy enforcement via live RAG from company documentation
- 🔒 6-signal adversarial hardening against injection attacks
- ⚡ Real-time decision intelligence powered by LLaMA 3.3-70B
- 📊 Confidence-scored approvals with full citation traceability

[**📹 Watch Demo Video**](./Video) | [**📖 View Documentation**](./Documents) | [**🚀 Quick Start**](#-quick-start)

</div>

---

## 📊 **Comparative Analysis**

| **Capability** | Traditional Asset Bot | **MUGEN AI** |
|:---|:---:|:---:|
| **Input Processing** | Static dropdowns, rigid forms | Free-text NLP with typo correction and context understanding |
| **Policy Management** | Hardcoded business rules | Live RAG retrieval from company PDFs with A-D grading |
| **Decision Intelligence** | Basic rule engine | LLaMA 3.3-70B with HRIS, catalogue, and RAG context fusion |
| **Confidence Scoring** | Binary approval | Per-slot confidence scoring (0–100%) with re-ask thresholds |
| **Security Architecture** | Minimal validation | 6-signal adversarial ensemble + LLM-based threat detection |
| **Decision Outcomes** | Approve / Reject | `approved` · `flagged` · `rejected` with full citation traceability |
| **Alternative Suggestions** | None | Intelligent in-stock alternative recommendations |
| **Audit Trail** | Basic logs | Complete request history with confidence metrics and policy references |

---

## 🏗️ **System Architecture**

MUGEN AI implements a sophisticated **four-layer intelligence pipeline** that processes user requests from raw Telegram messages through security validation, natural language understanding, policy retrieval, and autonomous decision-making.

### **Processing Pipeline Overview**

<div align="center">
<pre>
          ┌──────────────────────────────────────┐
          │      TELEGRAM USER MESSAGE INPUT     │
          └─────────────────┬────────────────────┘
                            │
          ╔═════════════════▼═════════════════════╗
          ║   LAYER 1 · SECURITY & THREAT SCORING ║
          ║          (Priority Group -999)        ║
          ║                                       ║
          ║  • Regex Pattern Matching ····· 30%   ║
          ║  • Injection Probe Detection ·· 25%   ║
          ║  • Entropy Anomaly Analysis ··· 15%   ║
          ║  • Unicode Obfuscation Check ·· 15%   ║
          ║  • Rate Limit Enforcement ····· 15%   ║
          ║  • LLM Grey-Zone Arbitration          ║
          ╚══════════════╤═══════════╤════════════╝
                    SAFE │     THREAT│
                         │           ▼
                         │    ⛔ QUARANTINE + AUDIT LOG
          ╔══════════════▼════════════════════════╗
          ║    LAYER 2 · NLP EXTRACTION ENGINE    ║
          ║                                       ║
          ║  Typo Correction:                     ║
          ║    "macbok" ───────────► MacBook Pro  ║
          ║  Semantic Normalization:              ║
          ║    "ASAP" ─────────────► HIGH urgency ║
          ║  Confidence Gating:                   ║
          ║    score < 0.70 ───────► re-ask user  ║
          ║  Risk Assessment:                     ║
          ║    injection_risk=high ─► 🔒 FREEZE   ║
          ╚══════════════╤════════════════════════╝
                         │
          ╔══════════════▼════════════════════════╗
          ║    LAYER 3 · RAG RETRIEVAL PIPELINE   ║
          ║                                       ║
          ║  Policy Documents:                    ║
          ║    PDF ─► chunk(400/60) ─► embed      ║
          ║  Deduplication:                       ║
          ║    SHA-256 fingerprinting             ║
          ║  Semantic Search:                     ║
          ║    MiniLM-L6-v2 embeddings            ║
          ║  Relevance Grading:                   ║
          ║    A (≤0.35) · B (≤0.50) · C · D      ║
          ╚══════════════╤════════════════════════╝
                         │
          ╔══════════════▼════════════════════════╗
          ║   LAYER 4 · DECISION INTELLIGENCE     ║
          ║                                       ║
          ║  Context Fusion:                      ║
          ║    • HRIS employee profile            ║
          ║    • Extracted request slots          ║
          ║    • Product catalogue data           ║
          ║    • Graded RAG policy chunks         ║
          ║    • Static policy rules              ║
          ║           ↓                           ║
          ║    LLaMA 3.3-70B (via Groq)          ║
          ║           ↓                           ║
          ║  ┌────────┴────────┬─────────┐       ║
          ║  ▼                 ▼         ▼       ║
          ║ approved        flagged   rejected   ║
          ╚═══════════════════════════════════════╝
</pre>
</div>

---

## 🧠 **Natural Language Processing Layer**

### **Intelligent Slot Extraction**

Each information slot is processed through a dedicated LLM call with domain-specific prompts, enabling precise extraction with confidence quantification.

#### **Extraction Example**

| Slot | User Input | Extracted Value | Typo Corrected | Confidence | Risk Level |
|:---:|:---:|:---:|:---:|:---:|:---:|
| `asset_name` | "macbok pro" | `MacBook Pro` | ✅ Yes | 85% | None |
| `urgency` | "kinda urgent" | `HIGH` | — | 72% | None |
| `cost_estimate` | "2 grand" | `2000.0` | — | 91% | None |

#### **Confidence-Based Validation Strategy**

| Confidence Score | System Response | Retry Policy |
|:---:|:---|:---|
| **≥ 70%** | ✅ Slot immediately accepted | No retry needed |
| **40% – 69%** | 🔍 Contextual hint provided, re-ask user | Single retry with guidance |
| **< 40%** | ❓ Original prompt repeated | Up to 3 retries |
| **High Injection Risk** | 🔒 Session permanently frozen | Security lockout |

### **Identity Verification Workflow**

Every asset request begins with secure identity verification to ensure audit traceability and HRIS data correlation.

```
User  →  /request
 Bot  →  👋 Hello, John!

         Before processing your asset request, identity verification is required.

         📛 Please provide your full name and Employee ID
         Example: "Alice Johnson, EMP001"

User  →  "Pranesh, EMP004"
 Bot  →  ✅ Identity verified: Pranesh, EMP004

         📋 Initiating asset request workflow...
         🖥️ What asset do you need?
```

**Security Benefits:**
- Binds each request to authenticated employee records
- Enables role-based policy enforcement
- Provides complete audit trail for compliance
- Facilitates admin dashboard correlation

---

## 📚 **RAG Ingestion Pipeline**

### **Intelligent Document Processing**

The RAG (Retrieval-Augmented Generation) pipeline transforms company policy PDFs into semantically searchable knowledge bases with relevance-graded retrieval.

<div align="center">
<pre>
   Company Policy PDF
          │
          ▼
   ┌──────────────────────────────────────────────┐
   │  STAGE 1 · DOCUMENT VALIDATION               │
   │  • File size limit: ≤ 50 MB                  │
   │  • Format verification: %PDF magic bytes     │
   │  • SHA-256 deduplication check               │
   │  • Skip if already indexed                   │
   └─────────────────────┬────────────────────────┘
                         │
                         ▼
   ┌──────────────────────────────────────────────┐
   │  STAGE 2 · TEXT EXTRACTION (PyMuPDF)         │
   │  • Page-by-page sequential parsing           │
   │  • Page number markers: [Page N]             │
   │  • Automatic header/footer removal           │
   │  • Image-only page filtering (< 30 chars)    │
   └─────────────────────┬────────────────────────┘
                         │
                         ▼
   ┌──────────────────────────────────────────────┐
   │  STAGE 3 · INTELLIGENT CHUNKING              │
   │  • Algorithm: RecursiveCharacterTextSplitter │
   │  • Chunk size: 400 characters                │
   │  • Overlap: 60 characters                    │
   │  • Metadata: source, page, index, hash       │
   └─────────────────────┬────────────────────────┘
                         │
                         ▼
   ┌──────────────────────────────────────────────┐
   │  STAGE 4 · EMBEDDING & VECTOR STORAGE        │
   │  • Model: all-MiniLM-L6-v2 (local, no API)   │
   │  • Vector DB: ChromaDB with persistence      │
   │  • Deterministic IDs: idempotent re-ingestion│
   │  • Atomic upsert operations                  │
   └──────────────────────────────────────────────┘
</pre>
</div>

### **Semantic Relevance Grading**

Retrieved policy chunks are automatically graded based on cosine similarity to ensure high-quality contextual decision-making.

| Grade | Cosine Distance | Weight in Decision Engine | Usage Pattern |
|:---:|:---:|:---:|:---|
| **A** | ≤ 0.35 | Primary evidence | Directly cited as authoritative source |
| **B** | ≤ 0.50 | Supporting evidence | Cited with confidence qualifier |
| **C** | ≤ 0.65 | Weak signal | Used as contextual background |
| **D** | > 0.65 | Low relevance | Flagged as potentially irrelevant |

**Technical Advantages:**
- **Local embedding generation** eliminates API dependency and latency
- **Deterministic chunk IDs** enable idempotent re-ingestion without duplicates
- **SHA-256 deduplication** prevents redundant processing of identical documents
- **Graded retrieval** ensures decision transparency and explainability

---

## ⚖️ **Decision Intelligence Engine**

### **Multi-Context Fusion Architecture**

The decision engine synthesizes five distinct contextual data sources into a unified prompt for the LLM, enabling nuanced, policy-compliant asset allocation decisions.

<div align="center">
<pre>
   ╔════════════════════════════════════════════════╗
   ║  CONTEXT BLOCK 1 · EMPLOYEE PROFILE (HRIS)    ║
   ║  • Full name and employee ID                  ║
   ║  • Job role and organizational grade          ║
   ║  • Annual budget allocation                   ║
   ║  • Tenure and historical request patterns     ║
   ╠════════════════════════════════════════════════╣
   ║  CONTEXT BLOCK 2 · STRUCTURED REQUEST DATA    ║
   ║  • Extracted and validated information slots  ║
   ║  • Cost enrichment from product catalogue     ║
   ║  • Urgency classification and justification   ║
   ╠════════════════════════════════════════════════╣
   ║  CONTEXT BLOCK 3 · PRODUCT CATALOGUE          ║
   ║  • Real-time pricing information              ║
   ║  • Current inventory stock levels             ║
   ║  • Minimum grade eligibility requirements     ║
   ║  • Alternative product recommendations        ║
   ╠════════════════════════════════════════════════╣
   ║  CONTEXT BLOCK 4 · RAG POLICY EXCERPTS        ║
   ║  • Top-3 semantically relevant chunks         ║
   ║  • Graded by relevance (A, B, C, D)          ║
   ║  • Full source attribution with page numbers  ║
   ╠════════════════════════════════════════════════╣
   ║  CONTEXT BLOCK 5 · STATIC POLICY RULES        ║
   ║  • Category-specific spending caps            ║
   ║  • Prohibited items and restricted categories ║
   ║  • Approval workflow escalation rules         ║
   ╚════════════════════════════════════════════════╝
                            │
                            ▼
   ╔════════════════════════════════════════════════╗
   ║     LLaMA 3.3-70B DECISION MODEL (Groq API)   ║
   ║     Temperature: 0.1 (deterministic)          ║
   ║     Max tokens: 2048                          ║
   ╚════════════════════════════════════════════════╝
                            │
            ┌───────────────┴────────────────┐
            ▼                ▼               ▼
       ✅ approved      ⚠️ flagged      ❌ rejected
</pre>
</div>

### **Decision Outcome Classification**

| Status | Trigger Conditions | Response Actions |
|:---:|:---|:---|
| **✅ Approved** | Within budget · In stock · Grade-eligible · Policy-compliant | Immediate approval with full citation trail |
| **⚠️ Flagged** | Near budget limit · Manager approval required · Ambiguous policy match | Route to manual review with context |
| **❌ Rejected** | Exceeds hard limit · Below minimum grade · Prohibited item | Rejection with policy explanation + alternatives |

### **Transparency & Explainability**

Every decision includes:
- **Confidence percentage** (0–100%) based on policy alignment
- **RAG signal strength** indicator (Strong / Moderate / Weak)
- **Policy reference citations** with exact document and page numbers
- **Alternative product suggestions** when primary request is rejected/flagged

---

## 💬 **Complete Request Walkthrough**

### **End-to-End User Experience**

```plaintext
User  →  /request
 Bot  →  👋 Hello, Alice!

         Identity verification is required before proceeding.

         📛 Please provide your name and Employee ID
         Example format: "Alice Johnson, EMP001"

User  →  "Alice Johnson, EMP001"
 Bot  →  ✅ Identity verified: Alice Johnson, EMP001

         📋 Initiating new asset request workflow...
         🖥️ What asset do you need?

User  →  "macbok pro 14 for video editing, its urgent"
 Bot  →  ✏️ Interpreted as: MacBook Pro 14"
         (Typo corrected: "macbok" → "MacBook")
         
         📝 Please describe your business justification

User  →  "post-production for the new marketing campaign"
 Bot  →  ⏱️ What is the urgency level?

User  →  "kinda urgent"
 Bot  →  🔍 Confidence: 72% — Please clarify
         Reply with: HIGH, NORMAL, or LOW

User  →  HIGH
 Bot  →  💰 What is the approximate cost in USD?

User  →  "around 2k"
 Bot  →  📊 Request Summary
         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         Asset       MacBook Pro 14"
         Reason      Post-production for marketing campaign
         Urgency     HIGH
         Cost Est.   $2,000
         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         
         Reply "Yes" to submit or "No" to restart

User  →  yes
 Bot  →  ✅ DECISION: APPROVED
         
         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         Request ID:       A1B2C3D4
         Confidence:       ████████░░ 94%
         RAG Signal:       🟢 Strong policy alignment
         Employee Grade:   IC3
         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         
         📋 REASONING:
         MacBook Pro 14" (SKU: LAP-001, $1,999) falls within
         the $3,500 laptop budget cap for IC3 employees.
         
         HIGH urgency justified for campaign deadline.
         Current stock: 8 units available.
         
         📚 POLICY REFERENCES:
           • asset_policy.json § laptop.max_usd (Grade A, ≤0.31)
           • Company_Rulebook.pdf p.12 (Grade A, ≤0.34)
           • products.json #LAP-001 (catalogue match)
```

### **Key User Experience Features**

- **Conversational interface** eliminates rigid forms
- **Real-time typo correction** improves data quality
- **Confidence-based re-asking** ensures extraction accuracy
- **Transparent decision reasoning** builds user trust
- **Full audit trail** for compliance and governance

---

## 📁 **Project Structure**

```plaintext
CodeBadgers-Mugen-AI/
│
├── 📂 bot/                          Core application logic
│   ├── main.py                      Application entry point, middleware, routing
│   ├── config.py                    Environment-driven configuration (Pydantic)
│   │
│   ├── 📂 handlers/                 Telegram bot event handlers
│   │   ├── commands.py              Bot commands: /start, /status, /upload_rulebook
│   │   ├── conversation.py          Multi-turn conversation state machine
│   │   │                            • GREETING → identity verification
│   │   │                            • SLOT_COLLECT → asset information extraction
│   │   │                            • CONFIRMING → user approval workflow
│   │   └── messages.py              Fallback handler for orphaned messages
│   │
│   ├── 📂 slots/                    NLP extraction layer
│   │   ├── extractor.py             Per-slot LLM extraction with confidence scoring
│   │   └── state.py                 FSM: COLLECTING → CONFIRMING → DECIDING → DONE/FROZEN
│   │
│   ├── 📂 validation/               Decision intelligence components
│   │   ├── decision.py              LLaMA 3.3-70B decision engine with context fusion
│   │   └── hris.py                  Employee data lookup and grade derivation
│   │
│   ├── 📂 rag/                      Retrieval-augmented generation pipeline
│   │   ├── pdf_loader.py            PDF ingestion: PyMuPDF → Chunker → ChromaDB
│   │   └── retriever.py             Semantic search with MiniLM embeddings + A–D grading
│   │
│   ├── 📂 security/                 Adversarial threat detection
│   │   └── scorer.py                6-signal suspicion ensemble with LLM judge
│   │
│   └── 📂 db/                       Data persistence layer
│       ├── schema.py                SQLite WAL schema (4 normalized tables)
│       └── repository.py            Async data access layer (aiosqlite)
│
├── 📂 admin_panel/                  Web-based administration interface
│   ├── api.py                       FastAPI REST endpoints
│   │                                • GET /api/hris — employee management
│   │                                • GET /api/requests — request audit trail
│   │                                • POST /api/config — API key management
│   └── 📂 static/
│       └── index.html               SPA dashboard (requests, HRIS, rulebooks, config)
│
├── 📂 data/                         Configuration and master data
│   ├── hris.json                    Employee roster (auto-normalized schema)
│   ├── asset_policy.json            Category rules, spending caps, prohibitions
│   └── products.json                Product catalogue (20 items with stock/pricing)
│
├── 📂 rulebooks/                    Policy document repository
│   └── [PDF files uploaded via bot or admin panel]
│
├── 📂 chroma_store/                 Vector database (auto-generated)
│   └── [ChromaDB persistent storage with MiniLM embeddings]
│
├── 📂 Documents/                    Project documentation
│   ├── MUGEN AI - Architecture Report.pdf
│   ├── MUGEN AI - CAPABILITY REPORT.pdf
│   ├── MUGEN AI - PROMPT DOCUMENTATION.pdf
│   └── USE CASE & DIAGRAMS REPORT.pdf
│
├── 📂 Video/                        Demo and walkthrough materials
│   └── README.md                    Link to full demonstration video
│
├── Dockerfile                       Production containerization (Railway-ready)
├── requirements.txt                 Python dependencies (pinned versions)
├── .env.example                     Environment variable template
├── .gitignore                       Git exclusion rules
└── README.md                        This file
```

### **Key Design Principles**

- **Modular architecture:** Clear separation of concerns (handlers, NLP, RAG, security, DB)
- **Async-first:** aiosqlite and PTB async handlers for high concurrency
- **Configuration as code:** Pydantic-validated environment-driven settings
- **Idempotent operations:** SHA-256 deduplication, deterministic chunk IDs
- **Production-ready:** Docker support, structured logging, graceful error handling

---

## 🚀 **Quick Start Guide**

### **Prerequisites**

- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Groq API Key (from [console.groq.com](https://console.groq.com))
- Docker (optional, for containerized deployment)

---

### **Local Development Setup**

#### **1. Clone and Configure**

```bash
git clone https://github.com/White-fang10/CodeBadgers-Mugen-AI.git
cd CodeBadgers-Mugen-AI
cp .env.example .env
```

Edit `.env` with your credentials:
```bash
BOT_TOKEN=your_telegram_bot_token_here
GROQ_API_KEY=your_groq_api_key_here
ADMIN_USER_IDS=123456789,987654321  # Comma-separated Telegram user IDs
```

#### **2. Install Dependencies**

```bash
pip install -r requirements.txt
```

#### **3. Launch Application**

```bash
python -m bot.main
```

The bot will start on Telegram, and the admin dashboard will be available at:
```
http://localhost:8080
```

---

### **Production Deployment (Docker)**

#### **Build Container Image**

```bash
docker build -t mugen-ai:latest .
```

#### **Run with Volume Mounts**

```bash
docker run -d \
  --name mugen-ai \
  --env-file .env \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/rulebooks:/app/rulebooks \
  -v $(pwd)/chroma_store:/app/chroma_store \
  --restart unless-stopped \
  mugen-ai:latest
```

**Volume mount benefits:**
- `data/` — Persists HRIS, policies, and product catalogue
- `rulebooks/` — Retains uploaded policy PDFs across restarts
- `chroma_store/` — Preserves vector database embeddings

---

### **Admin Dashboard Configuration**

Navigate to `http://localhost:8080` and use the following tabs:

| Tab | Functionality |
|:---|:---|
| **🔑 API Keys** | Configure `BOT_TOKEN` and `GROQ_API_KEY` without editing `.env` |
| **📚 Rulebook Manager** | Upload company policy PDFs for RAG ingestion |
| **👥 HRIS Manager** | Add/edit employee records with budget allocations |
| **📊 Requests Dashboard** | View approval/rejection statistics and audit trail |

---

### **Initial Policy Setup**

#### **Via Telegram Bot**

```
/upload_rulebook  →  [Send your company policy PDF]
```

#### **Via Admin Dashboard**

1. Navigate to the **📚 Rulebook Manager** tab
2. Click **Upload PDF**
3. Select your policy document (≤ 50 MB)
4. Wait for ingestion confirmation

The RAG pipeline will automatically:
- Extract text using PyMuPDF
- Chunk into 400-character segments
- Generate MiniLM embeddings
- Store in ChromaDB with SHA-256 deduplication

---

### **Telegram Bot Commands**

| Command | Description |
|:---|:---|
| `/start` | Initialize bot and display welcome message |
| `/request` | Begin new asset request workflow |
| `/status` | Check current request status |
| `/upload_rulebook` | Upload company policy PDF (admin only) |

---

### **Environment Variables Reference**

| Variable | Required | Default | Description |
|:---|:---:|:---:|:---|
| `BOT_TOKEN` | ✅ | — | Telegram Bot API token from @BotFather |
| `GROQ_API_KEY` | ✅ | — | Groq Cloud API key for LLaMA 3.3-70B access |
| `ADMIN_USER_IDS` | ✅ | — | Comma-separated Telegram user IDs with admin privileges |
| `SUSPICION_THRESHOLD` | ❌ | `0.55` | Security quarantine threshold (0.0–1.0) |
| `RAG_TOP_K` | ❌ | `4` | Number of policy chunks retrieved per query |
| `CHROMA_PERSIST_DIR` | ❌ | `./chroma_store` | Vector database persistence path |
| `RULEBOOKS_DIR` | ❌ | `./rulebooks` | Policy PDF storage directory |
| `DB_PATH` | ❌ | `./data/mugen.db` | SQLite database file location |
| `LOG_LEVEL` | ❌ | `INFO` | Logging verbosity: `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |

> **💡 Tip:** Use the **🔑 API Keys** tab in the admin dashboard to update `BOT_TOKEN` and `GROQ_API_KEY` dynamically without container restart.

---

## 🛡️ **Security Architecture**

### **Six-Signal Adversarial Threat Detection**

MUGEN AI implements a multi-layered security ensemble that processes every message through six independent threat detection signals before reaching the NLP layer.

| Signal | Weight | Detection Capability | Implementation |
|:---|:---:|:---|:---|
| **Regex Blacklist** | 30% | 20+ jailbreak patterns, injection keywords, data exfiltration attempts | Pattern matching against curated threat database |
| **Injection Probes** | 25% | System-prompt manipulation, role-spoofing, privilege escalation | Structural analysis of message syntax |
| **Entropy Anomaly** | 15% | Base64-encoded payloads, compressed data, obfuscated commands | Shannon entropy calculation with threshold detection |
| **Unicode Obfuscation** | 15% | RTL override characters, zero-width joiners, Cyrillic lookalikes | Character normalization and homoglyph detection |
| **Rate Abuse Detection** | 15% | Burst flooding (>12 msg/min), DDoS attempts, bot behavior | Sliding window rate limiter with penalty scoring |
| **LLM Grey-Zone Judge** | 40% blend | Ambiguous threats requiring contextual reasoning | Groq LLM analysis for scores 0.28–0.72 only |

### **Threat Response Protocol**

```
Message Arrives
     │
     ▼
 Suspicion Score Calculation
     │
     ├─► Score < 0.55  →  ✅ SAFE (proceed to NLP layer)
     │
     └─► Score ≥ 0.55  →  ⛔ THREAT DETECTED
                           │
                           ├─► Permanent session quarantine
                           ├─► SQLite audit log with full context
                           ├─► Admin notification via dashboard
                           └─► User receives generic rejection message
```

### **Security Best Practices**

- **Defense in depth:** Multiple independent signals prevent single-point bypass
- **Grey-zone arbitration:** LLM judge only invoked for ambiguous cases (reduces API cost)
- **Audit trail:** All quarantined messages logged with timestamp, user ID, and score breakdown
- **Session isolation:** Compromised sessions frozen permanently, no retry allowed

---

## ⚙️ **Advanced Configuration**

### **Fine-Tuning Security Parameters**

Adjust the adversarial threat detection sensitivity:

```bash
# .env file
SUSPICION_THRESHOLD=0.55  # Lower = more strict (more false positives)
                          # Higher = more permissive (potential false negatives)
                          # Recommended range: 0.45–0.65
```

**Threshold tuning guidelines:**
- **High-security environments** (financial, healthcare): `0.45–0.50`
- **Balanced deployments** (corporate IT): `0.55` (default)
- **High-throughput scenarios** (startups, testing): `0.60–0.65`

---

### **RAG Retrieval Optimization**

Control the number of policy chunks retrieved per query:

```bash
RAG_TOP_K=4  # Default: retrieves top 4 most relevant chunks
             # Higher values (6–8): More context, slower decisions
             # Lower values (2–3): Faster, but may miss nuanced policies
```

**Performance vs. Accuracy Trade-off:**
- `RAG_TOP_K=2`: Fast decisions, suitable for simple policies
- `RAG_TOP_K=4`: Balanced (recommended for most deployments)
- `RAG_TOP_K=6–8`: Comprehensive context for complex policy documents

---

### **Database and Storage Paths**

Customize persistence layer locations:

```bash
DB_PATH=./data/mugen.db              # SQLite database
CHROMA_PERSIST_DIR=./chroma_store    # Vector embeddings
RULEBOOKS_DIR=./rulebooks            # Policy PDFs
```

**Production deployment best practices:**
- Mount external volumes for `data/`, `chroma_store/`, and `rulebooks/`
- Enable SQLite WAL mode (automatically handled)
- Schedule periodic backups of all three directories

---

### **Logging Configuration**

Adjust verbosity for debugging or production monitoring:

```bash
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR
```

| Level | Use Case | Output Volume |
|:---|:---|:---:|
| `DEBUG` | Development troubleshooting | Very High |
| `INFO` | Production monitoring (default) | Moderate |
| `WARNING` | Minimal logging, errors + warnings | Low |
| `ERROR` | Critical issues only | Very Low |

---

## 🗺️ **Development Roadmap**

| Phase | Status | Deliverables | Timeline |
|:---:|:---:|:---|:---:|
| **1** | ✅ **Completed** | Foundation architecture · 6-signal security ensemble · Middleware framework | Q4 2025 |
| **2** | ✅ **Completed** | NLP slot extraction · Confidence gating · ConversationHandler · Injection freeze | Q4 2025 |
| **3** | ✅ **Completed** | PDF RAG pipeline · A–D relevance grading · Graded decision context fusion | Q1 2026 |
| **4** | ✅ **Completed** | HRIS integration · Product catalogue · Alternative suggestion engine | Q1 2026 |
| **5** | ✅ **Completed** | Admin dashboard · Rulebook manager · HRIS manager · API key management | Q2 2026 |
| **5b** | ✅ **Completed** | User identity verification workflow (name + employee ID) | Q2 2026 |
| **6** | 🔲 **Planned** | Webhook mode · Redis-based rate limiting · Prometheus metrics · Grafana dashboards | Q3 2026 |
| **7** | 🔲 **Planned** | Multi-language support · Voice input processing · Advanced analytics dashboard | Q4 2026 |

### **Upcoming Features (Phase 6)**

- **Webhook Mode:** Replace long-polling with webhook-based message delivery for improved scalability
- **Redis Integration:** Distributed rate limiting and session management for multi-instance deployments
- **Observability Stack:** Prometheus metrics collection with pre-built Grafana dashboards
  - Request throughput and latency metrics
  - Security threat detection rates
  - RAG retrieval performance
  - Decision confidence distributions

### **Future Enhancements (Phase 7)**

- **Multi-Language NLP:** Support for Spanish, French, German, and Mandarin
- **Voice Input:** Telegram voice message transcription and processing
- **Advanced Analytics:** Machine learning-based request pattern analysis and predictive budgeting

---

## 👨‍💻 **Development Team**

<div align="center">

**Built with dedication by the SD-05 Engineering Team**

<br>

| Team Member | Role | Resume |
|:---:|:---:|:---:|
| **V. Pranesh** | Lead Backend Engineer & Architecture | [📄 View Resume](https://drive.google.com/file/d/1IjJbjL1S_Tk2pCws4osd8_7SZ0d985vq/view?usp=sharing) |
| **S. Pratap** | NLP & Security Systems Engineer | [📄 View Resume](https://drive.google.com/file/d/1BI-C1PoN5Yd99f4piTS--RJFIS-x-IBe/view?usp=sharing) |
| **M. Subitha** | RAG Pipeline & Data Engineer | [📄 View Resume](https://drive.google.com/file/d/1mCh6FU0gjZjZh3ofObzyfq0EhYshHPlx/view?usp=sharing) |
| **V. Adhithyan** | Frontend & Integration Engineer | [📄 View Resume](https://drive.google.com/file/d/14K-X-M5YYHaa3pAQAeQPJdpTiK5GQSdF/view?usp=sharing) |

<br>

---

### **Technology Stack**

Built with industry-leading open-source technologies

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![SQLite](https://img.shields.io/badge/SQLite-3.45-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)

**AI & Machine Learning:**  
[Groq](https://groq.com) · [LLaMA 3.3 (70B)](https://ai.meta.com/llama/) · [ChromaDB](https://trychroma.com) · [Sentence Transformers](https://sbert.net)

**Frameworks & Libraries:**  
[python-telegram-bot v20](https://python-telegram-bot.org) · [PyMuPDF](https://pymupdf.readthedocs.io) · [Pydantic](https://docs.pydantic.dev) · [aiosqlite](https://aiosqlite.omnilib.dev)

<br>

---

### **License**

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

### **Acknowledgments**

Special thanks to the open-source community and the teams behind Groq, LLaMA, ChromaDB, and python-telegram-bot for providing the foundational technologies that power MUGEN AI.

---

<sub>**MUGEN AI** · Enterprise Asset Management Reimagined · © 2026 SD-05 Team</sub>

</div>
