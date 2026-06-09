<div align="center">

```
     ███╗   ███╗██╗   ██╗ ██████╗ ███████╗███╗   ██╗     █████╗ ██╗
     ████╗ ████║██║   ██║██╔════╝ ██╔════╝████╗  ██║    ██╔══██╗██║
     ██╔████╔██║██║   ██║██║  ███╗█████╗  ██╔██╗ ██║    ███████║██║
     ██║╚██╔╝██║██║   ██║██║   ██║██╔══╝  ██║╚██╗██║    ██╔══██║██║
     ██║ ╚═╝ ██║╚██████╔╝╚██████╔╝███████╗██║ ╚████║    ██║  ██║██║
     ╚═╝     ╚═╝ ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═══╝    ╚═╝  ╚═╝╚═╝
```

**Autonomous · Policy-Aware · Adversarially Hardened**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![LLaMA](https://img.shields.io/badge/LLM-LLaMA_3.3_70B-7C3AED?style=flat-square&logo=meta)](https://groq.com)
[![RAG](https://img.shields.io/badge/RAG-ChromaDB_·_MiniLM-16A34A?style=flat-square)](https://trychroma.com)
[![PTB](https://img.shields.io/badge/Bot-python--telegram--bot_v20-0088CC?style=flat-square&logo=telegram)](https://python-telegram-bot.org)
[![License](https://img.shields.io/badge/License-MIT-F59E0B?style=flat-square)](LICENSE)

<br>

> MUGEN AI is not a form-filler. It is an autonomous, adversarially-hardened enterprise agent  
> that processes IT asset requests through a **four-layer intelligence stack** — all inside Telegram.

<br>

</div>

---

## 🏗️ System Architecture

<div align="center">

![MUGEN AI Enhanced Architecture](./Architecture.png)

</div>

---

## Why MUGEN AI?

| | Typical Asset Bot | **MUGEN AI** |
|:---|:---:|:---:|
| **Input** | Static dropdowns | Free-text NLP + typo correction |
| **Policy** | Hardcoded rules | Live RAG from company PDFs |
| **Decision** | Rule engine | LLaMA 3.3-70B + HRIS + Catalogue |
| **Confidence** | None | Per-slot 0–100% scoring |
| **Security** | None | 6-signal ensemble + NLP scanner |
| **Outcomes** | Approve / Reject | `approved` · `flagged` · `rejected` + cited refs |
| **Alternatives** | None | Suggests best in-stock option automatically |

---

## 🏛️ Four-Layer Intelligence Stack

<div align="center">
<pre>
          ┌──────────────────────────────────────┐
          │         TELEGRAM USER MESSAGE        │
          └─────────────────┬────────────────────┘
                            │
          ╔═════════════════▼═════════════════════╗
          ║        LAYER 1 · SUSPICION SCORER     ║
          ║              group -999               ║
          ║                                       ║
          ║  Regex Blacklist ·········· 30 %      ║
          ║  Injection Probes ·········· 25 %     ║
          ║  Entropy Anomaly ·········· 15 %      ║
          ║  Unicode Obfuscation ······ 15 %      ║
          ║  Rate Abuse Window ········ 15 %      ║
          ║  Groq LLM Judge ···· grey-zone only   ║
          ╚══════════════╤═══════════╤════════════╝
                    SAFE │     THREAT│
                         │           ▼
                         │    ⛔ QUARANTINE + DB log
          ╔══════════════▼════════════════════════╗
          ║         LAYER 2 · NLP FRONT-END       ║
          ║                                       ║
          ║  "macbok" ──────────► MacBook Pro     ║
          ║  "ASAP"   ──────────► HIGH urgency    ║
          ║  confidence < 0.70 ─► re-ask user     ║
          ║  injection_risk=high ► 🔒 FREEZE      ║
          ╚══════════════╤════════════════════════╝
                         │
          ╔══════════════▼════════════════════════╗
          ║         LAYER 3 · RAG PIPELINE        ║
          ║                                       ║
          ║  PDF ─► chunk 400/60 ─► MiniLM-L6-v2  ║
          ║  SHA-256 dedup · idempotent upsert    ║
          ║  Top-3 chunks · Grade A / B / C / D   ║
          ╚══════════════╤════════════════════════╝
                         │
          ╔══════════════▼════════════════════════╗
          ║         LAYER 4 · DECISION ENGINE     ║
          ║                                       ║
          ║  HRIS ──┐                             ║
          ║  Slots ─┤─► LLaMA 3.3-70B via Groq    ║
          ║  RAG ───┤                             ║
          ║  Catalogue ──► approved / flagged /   ║
          ║                rejected + alt suggest ║
          ╚═══════════════════════════════════════╝
</pre>
</div>

---

## 🧠 NLP Layer — Slot Extraction

**Each slot gets its own dedicated LLM call with a precision-engineered prompt.**

| Slot | User Said | Extracted | Corrected | Confidence | Risk |
|:---:|:---:|:---:|:---:|:---:|:---:|
| `asset_name` | "macbok pro" | `MacBook Pro` | ✏️ yes | 0.85 | none |
| `urgency` | "kinda urgent" | `HIGH` | — | 0.72 | none |
| `cost_estimate` | "2 grand" | `2000.0` | — | 0.91 | none |

| Confidence | Action |
|:---:|:---|
| `≥ 0.70` | ✅ Slot accepted |
| `0.40 – 0.69` | 🔍 Re-ask with contextual hint |
| `< 0.40` | ❓ Re-ask with original prompt (max 3 retries) |
| `injection_risk: high` | 🔒 Session permanently frozen |

---

## 💬 User Identity Flow

Before processing any asset request, MUGEN AI verifies the user's identity:

```
User  →  /request
 Bot  →  👋 Hello, John!

         Before we begin your asset request, I need to verify your identity.

         📛 Please tell me your name and Employee ID
         e.g. "Alice Johnson, EMP001"

User  →  "Pranesh, EMP004"
 Bot  →  ✅ Identity recorded: Pranesh, EMP004

         📋 New Asset Request — Let's collect the details...
         🖥️ What asset do you need?
```

The identity is stored with each request and visible to admins in the dashboard.

---

## 🗂️ RAG Ingestion Pipeline

<div align="center">
<pre>
   Admin PDF
       │
       ▼
   ┌──────────────────────────────────────────────┐
   │  STEP 1 · VALIDATION                         │
   │  Size ≤ 50 MB · %PDF magic bytes             │
   │  SHA-256 dedup → skip if already indexed     │
   └─────────────────────┬────────────────────────┘
                         │
                         ▼
   ┌──────────────────────────────────────────────┐
   │  STEP 2 · TEXT EXTRACTION  ( PyMuPDF )       │
   │  Page-by-page · [Page N] markers             │
   │  Header / footer stripping                   │
   │  Skip image-only pages ( < 30 chars )        │
   └─────────────────────┬────────────────────────┘
                         │
                         ▼
   ┌──────────────────────────────────────────────┐
   │  STEP 3 · CHUNKING  ( RecursiveTextSplitter )│
   │  chunk_size = 400  ·  chunk_overlap = 60     │
   │  Metadata: source, page, chunk_index, hash   │
   └─────────────────────┬────────────────────────┘
                         │
                         ▼
   ┌──────────────────────────────────────────────┐
   │  STEP 4 · EMBED + UPSERT                     │
   │  all-MiniLM-L6-v2  ( local CPU, no API )     │
   │  Deterministic IDs → idempotent re-ingest    │
   └──────────────────────────────────────────────┘
</pre>
</div>

| Grade | Cosine Distance | Weight in Decision |
|:---:|:---:|:---|
| **A** | ≤ 0.35 | Cited directly |
| **B** | ≤ 0.50 | Cited with confidence |
| **C** | ≤ 0.65 | Used as weak signal |
| **D** | > 0.65 | Flagged as low-relevance |

---

## ⚖️ Decision Engine

**The LLM receives five structured context blocks in every decision call.**

<div align="center">
<pre>
   ╔══════════════════════════════════════════╗
   ║  BLOCK 1 · EMPLOYEE PROFILE ( HRIS )     ║
   ║  name · role · grade · budget · tenure   ║
   ╠══════════════════════════════════════════╣
   ║  BLOCK 2 · ASSET REQUEST                 ║
   ║  slots + cost enrichment from catalogue  ║
   ╠══════════════════════════════════════════╣
   ║  BLOCK 3 · PRODUCT CATALOGUE CONTEXT     ║
   ║  price · stock · min_grade · alternatives║
   ╠══════════════════════════════════════════╣
   ║  BLOCK 4 · RAG POLICY CHUNKS ( A–D )     ║
   ║  top-3 graded excerpts from company PDFs ║
   ╠══════════════════════════════════════════╣
   ║  BLOCK 5 · STATIC POLICY RULES           ║
   ║  asset_policy.json hard rules            ║
   ╚══════════════════════════════════════════╝
                        │
                        ▼
   ╔══════════════════════════════════════════╗
   ║       LLaMA 3.3-70B via Groq             ║
   ╚══════════════════════════════════════════╝
                        │
            ┌───────────┴────────────┐
            ▼           ▼            ▼
       approved      flagged      rejected
</pre>
</div>

| Status | Condition |
|:---:|:---|
| `approved` | In-budget, in-stock, grade-eligible, policy-compliant |
| `flagged` | Near-budget, needs manager sign-off, or ambiguous policy |
| `rejected` | Over hard limit, grade below minimum, or prohibited item |

---

## 💬 Full Request Walkthrough

```
User  →  /request
 Bot  →  👋 Hello, Alice!

         Before we begin your asset request, I need to verify your identity.

         📛 Please tell me your name and Employee ID
         e.g. "Alice Johnson, EMP001"

User  →  "Alice Johnson, EMP001"
 Bot  →  ✅ Identity recorded: Alice Johnson, EMP001

         📋 New Asset Request — Let's collect the details...
         🖥️ What asset do you need?

User  →  "macbok pro 14 for video editing, its urgent"
 Bot  →  ✏️ Interpreted as: MacBook Pro 14
         📝 Why do you need this asset?

User  →  "post-production for the new marketing campaign"
 Bot  →  ⏱️ How urgent is this?

User  →  "kinda urgent"
 Bot  →  🔍 Confidence 72% — Please reply HIGH, NORMAL, or LOW.

User  →  HIGH
 Bot  →  💰 Approximate cost in USD?

User  →  "around 2k"
 Bot  →  📋 Request Summary
         Asset      MacBook Pro 14
         Reason     Post-production for marketing campaign
         Urgency    HIGH   ·   Cost  $2,000
         ───────────────────────────────────
         Reply Yes to submit · No to restart

User  →  yes
 Bot  →  ✅ Decision: APPROVED

         Request ID      A1B2C3D4
         Confidence      ██████████ 94%
         RAG Signal      🟢 Strong policy signal
         Employee Grade  IC3

         Reasoning: MacBook Pro 14 (LAP-001, $1,999) is within the
         $3,500 laptop cap for IC3 grade. HIGH urgency for a campaign
         deadline is justified. 8 units in stock.

         Policy References:
           • asset_policy.json §laptop.max_usd
           • rulebook.pdf p.12 (Grade A)
           • products.json #LAP-001
```

---

## 📁 Project Structure

```
sd05-asset-request-bot/
│
├── bot/
│   ├── main.py                    Application bootstrap · middleware · routing
│   ├── config.py                  Pydantic-settings (env-driven)
│   │
│   ├── handlers/
│   │   ├── commands.py            /start  /status  /upload_rulebook
│   │   ├── conversation.py        PTB ConversationHandler  (/request flow)
│   │   │                          ↳ GREETING → identity verification (name + EMP ID)
│   │   │                          ↳ SLOT_COLLECT → asset details
│   │   │                          ↳ CONFIRMING → yes / no submission
│   │   └── messages.py            Orphan message fallback
│   │
│   ├── slots/
│   │   ├── extractor.py           Per-slot NLP · confidence · injection_risk
│   │   └── state.py               FSM: COLLECTING → CONFIRMING → DECIDING → DONE/FROZEN
│   │
│   ├── validation/
│   │   ├── decision.py            Stage 4 LLM decision engine
│   │   └── hris.py                Employee lookup · grade derivation
│   │
│   ├── rag/
│   │   ├── pdf_loader.py          PyMuPDF → Chunker → ChromaDB
│   │   └── retriever.py           MiniLM embeddings · A–D grading · RagContext
│   │
│   ├── security/
│   │   └── scorer.py              6-signal suspicion ensemble
│   │
│   └── db/
│       ├── schema.py              SQLite WAL schema (4 tables)
│       └── repository.py          Async aiosqlite data access
│
├── admin_panel/
│   ├── api.py                     FastAPI admin REST endpoints
│   │                              ↳ GET  /api/hris           — normalised field names
│   │                              ↳ GET  /api/requests       — includes user_identity
│   └── static/
│       └── index.html             Admin dashboard UI
│                                  ↳ Shows Approved / Rejected counts on load
│                                  ↳ Employee identity shown in Requests tab
│
├── data/
│   ├── hris.json                  Employee roster (id / budget fields auto-normalised)
│   ├── asset_policy.json          Cost caps · category rules · prohibited items
│   └── products.json              20-item catalogue with stock · price · min_grade
│
├── rulebooks/                     Drop PDFs here or via /upload_rulebook
├── chroma_store/                  Auto-generated ChromaDB vector store
│
├── Dockerfile                     Railway-ready · non-root · model pre-baked
├── requirements.txt               All deps pinned
└── .env.example                   Environment variable template
```

---

## 🚀 Quick Start

**1 · Clone & configure**

```bash
git clone <repo-url> && cd sd05-asset-request-bot
cp .env.example .env
# Edit .env: BOT_TOKEN, GROQ_API_KEY, ADMIN_USER_IDS
```

**2 · Install & run locally**

```bash
pip install -r requirements.txt
python -m bot.main
```

**3 · Access the Admin Dashboard**

```
http://localhost:8080
```

Use the **🔑 API Keys** tab to configure your Telegram Bot Token and Groq API Key directly from the browser.

**4 · Docker (production)**

```bash
docker build -t mugen-ai .
docker run -d --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/rulebooks:/app/rulebooks \
  -v $(pwd)/chroma_store:/app/chroma_store \
  mugen-ai
```

**5 · Index your first policy rulebook**

```
/upload_rulebook  →  send your company policy PDF
```

Or use the **📚 Rulebook Manager** tab in the admin dashboard.

---

## 🛡️ Security Reference

| Signal | Weight | Detects |
|:---|:---:|:---|
| Regex blacklist | 30% | 20 jailbreak / injection / exfil patterns |
| Injection probes | 25% | System-prompt manipulation, role spoofing |
| Entropy anomaly | 15% | Base64 / compressed payloads |
| Unicode obfuscation | 15% | RTL overrides, zero-width chars, Cyrillic mix |
| Rate abuse | 15% | Burst flooding > 12 msg / min |
| Groq LLM judge | 40% blend | Grey-zone arbitration (score 0.28–0.72 only) |

---

## ⚙️ Configuration

| Variable | Default | Purpose |
|:---|:---:|:---|
| `BOT_TOKEN` | **required** | From @BotFather |
| `GROQ_API_KEY` | **required** | From console.groq.com |
| `ADMIN_USER_IDS` | **required** | Comma-separated Telegram user IDs |
| `SUSPICION_THRESHOLD` | `0.55` | Quarantine threshold (0.0–1.0) |
| `RAG_TOP_K` | `4` | Chunks returned per policy query |
| `CHROMA_PERSIST_DIR` | `./chroma_store` | Vector DB path |
| `RULEBOOKS_DIR` | `./rulebooks` | PDF upload directory |
| `DB_PATH` | `./data/mugen.db` | SQLite path |
| `LOG_LEVEL` | `INFO` | DEBUG · INFO · WARNING · ERROR |

> **Tip:** Use the **🔑 API Keys** tab in the admin dashboard to update `BOT_TOKEN` and `GROQ_API_KEY` without manually editing `.env`.

---

## 🗺️ Roadmap

| Stage | Status | Description |
|:---:|:---:|:---|
| 1 | ✅ Done | Foundation · 6-signal suspicion scorer · middleware |
| 2 | ✅ Done | NLP extractor · confidence gating · ConversationHandler · injection freeze |
| 3 | ✅ Done | PDF RAG pipeline · A–D grading · graded decision context |
| 4 | ✅ Done | HRIS integration · product catalogue · suggested alternatives |
| 5 | ✅ Done | Admin dashboard · Rulebook manager · HRIS manager · API key management |
| 5b | ✅ Done | User identity verification (name + EMP ID) before each request |
| 6 | 🔲 Planned | Webhook mode · Redis rate limiter · Prometheus metrics |

---

## 👨‍💻 Meet the Team

<div align="center">

Built with dedication by the **SD-05** team.

| Name | Resume |
|:---:|:---:|
| **V. Pranesh** | [📄 View Resume](https://drive.google.com/file/d/1IjJbjL1S_Tk2pCws4osd8_7SZ0d985vq/view?usp=sharing) |
| **S. Pratap** | [📄 View Resume](https://drive.google.com/file/d/1BI-C1PoN5Yd99f4piTS--RJFIS-x-IBe/view?usp=sharing) |
| **M. Subitha** | [📄 View Resume](https://drive.google.com/file/d/1mCh6FU0gjZjZh3ofObzyfq0EhYshHPlx/view?usp=sharing) |
| **V .Adhithyan** | [📄 View Resume](https://drive.google.com/file/d/14K-X-M5YYHaa3pAQAeQPJdpTiK5GQSdF/view?usp=sharing) |

<br>

Built with ⚡ &nbsp;·&nbsp; Powered by [Groq](https://groq.com) &nbsp;·&nbsp; [LLaMA 3.3 · 70B](https://ai.meta.com/llama/) &nbsp;·&nbsp; [ChromaDB](https://trychroma.com) &nbsp;·&nbsp; [python-telegram-bot v20](https://python-telegram-bot.org)

</div>
