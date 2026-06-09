<div align="center">

```
███╗   ███╗██╗   ██╗ ██████╗ ███████╗███╗   ██╗     █████╗ ██╗
████╗ ████║██║   ██║██╔════╝ ██╔════╝████╗  ██║    ██╔══██╗██║
██╔████╔██║██║   ██║██║  ███╗█████╗  ██╔██╗ ██║    ███████║██║
██║╚██╔╝██║██║   ██║██║   ██║██╔══╝  ██║╚██╗██║    ██╔══██║██║
██║ ╚═╝ ██║╚██████╔╝╚██████╔╝███████╗██║ ╚████║    ██║  ██║██║
╚═╝     ╚═╝ ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═══╝    ╚═╝  ╚═╝╚═╝
```

### Autonomous · Policy-Aware · Adversarially Hardened

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![LLaMA](https://img.shields.io/badge/LLM-LLaMA_3.3_70B-7C3AED?style=flat-square&logo=meta)](https://groq.com)
[![RAG](https://img.shields.io/badge/RAG-ChromaDB_·_MiniLM-16A34A?style=flat-square)](https://trychroma.com)
[![PTB](https://img.shields.io/badge/Bot-python--telegram--bot_v20-0088CC?style=flat-square&logo=telegram)](https://python-telegram-bot.org)
[![License](https://img.shields.io/badge/License-MIT-F59E0B?style=flat-square)](LICENSE)

<br/>

> **MUGEN AI** is not a form-filler. It is an autonomous, adversarially-hardened enterprise agent  
> that processes IT asset requests through a **four-layer intelligence stack** — all inside Telegram.

<br/>

</div>

---

<div align="center">

## 🆚 Why MUGEN AI

| | Typical Asset Bot | MUGEN AI |
|:---:|:---|:---|
| **Input** | Static dropdowns | Free-text NLP with typo correction |
| **Policy** | Hardcoded rules | Live RAG from uploaded company PDFs |
| **Decision** | Rule engine | LLaMA 3.3-70B with cited policy refs |
| **Confidence** | N/A | Per-slot 0–100% confidence scoring |
| **Security** | None | 6-signal ensemble + NLP injection scanner |
| **Outcomes** | Approve / Reject | `APPROVED` · `NEEDS_REVIEW` · `REJECTED` |

</div>

---

<div align="center">

## 🏛️ Four-Layer Intelligence Stack

</div>

```
                    ┌──────────────────────────────────────┐
                    │        TELEGRAM USER MESSAGE          │
                    └─────────────────┬────────────────────┘
                                      │
               ╔══════════════════════▼═══════════════════════╗
               ║         LAYER 1 — SUSPICION SCORER           ║
               ║         (PTB handler group -999)             ║
               ║                                              ║
               ║   Regex Blacklist    ████░░░░░░  30 %        ║
               ║   Injection Probes   ██████░░░░  25 %        ║
               ║   Entropy Anomaly    ████░░░░░░  15 %        ║
               ║   Unicode Obfusc.    ████░░░░░░  15 %        ║
               ║   Rate Abuse         ████░░░░░░  15 %        ║
               ║   LLM Judge          ────── grey zone ─────  ║
               ╚════════════════╤═════════════════╤══════════╝
                           SAFE │           THREAT │
                                ▼                  ▼
                         Continue          ⛔ QUARANTINE
                                │            + DB log
               ╔════════════════▼══════════════════════════════╗
               ║        LAYER 2 — NLP FRONT-END               ║
               ║        (Per-slot Groq extraction)            ║
               ║                                              ║
               ║   Typo correction    "macbok" → MacBook Pro  ║
               ║   Normalisation      "ASAP"   → HIGH         ║
               ║   Confidence gate    < 0.70   → re-ask       ║
               ║   injection_risk     high     → 🔒 FREEZE    ║
               ╚════════════════╤══════════════════════════════╝
                                │
               ╔════════════════▼══════════════════════════════╗
               ║        LAYER 3 — RAG PIPELINE                ║
               ║        (Stage 3 — this release)              ║
               ║                                              ║
               ║   PyMuPDF  →  chunk 400/60  →  MiniLM-L6-v2 ║
               ║   SHA-256 dedup  ·  idempotent upsert        ║
               ║   Top-3 chunks with A / B / C / D grades     ║
               ╚════════════════╤══════════════════════════════╝
                                │
               ╔════════════════▼══════════════════════════════╗
               ║        LAYER 4 — DECISION ENGINE             ║
               ║                                              ║
               ║   Graded RAG context → LLaMA 3.3-70B        ║
               ║   + asset_policy.json  + products.json       ║
               ║   → APPROVED / NEEDS_REVIEW / REJECTED       ║
               ║      with policy citations & confidence      ║
               ╚══════════════════════════════════════════════╝
```

---

<div align="center">

## 🧠 NLP Layer — How Slot Extraction Works

</div>

Each slot gets its **own dedicated LLM call** with a precision-engineered prompt.

<div align="center">

```
User says: "need a macbok pro for video editing, kinda urgent, 2 grand"
```

| Slot | Extracted | Corrected | Confidence | Risk |
|:----:|:---:|:---:|:---:|:---:|
| `asset_name` | `MacBook Pro` | ✏️ `macbok` → `MacBook Pro` | 0.85 | none |
| `urgency` | `HIGH` | "kinda urgent" → `HIGH` | 0.72 | none |
| `cost_estimate` | `2000.0` | "2 grand" → `2000.0` | 0.91 | none |

</div>

### Confidence Thresholding

<div align="center">

```
≥ 0.70  ──────────────▶  ✅  Slot accepted, move on
0.40–0.69 ────────────▶  🔍  Re-ask with a contextual hint
< 0.40  ──────────────▶  ❓  Re-ask with the original prompt
                              (max 3 retries → slot skipped)
```

</div>

### Injection Freeze

If **any** slot extraction detects `injection_risk: "high"`, the session transitions to `FROZEN` — a permanent terminal state. No further input is accepted, and a `INJECTION_FREEZE` event is logged to the database.

---

<div align="center">

## 🗂️ Stage 3 RAG Pipeline

</div>

<div align="center">

```
 Admin sends PDF
       │
       ▼
 ┌─────────────────────────────────────────────────────────┐
 │  STEP 1 — VALIDATION                                    │
 │  • Size cap: 50 MB                                      │
 │  • Magic-byte check (%PDF)                              │
 │  • SHA-256 dedup → skip if already indexed              │
 └─────────────────────────┬───────────────────────────────┘
                           │
                           ▼
 ┌─────────────────────────────────────────────────────────┐
 │  STEP 2 — TEXT EXTRACTION  (PyMuPDF)                   │
 │  • Page-by-page with [Page N] markers                   │
 │  • Header/footer stripping                              │
 │  • Skips image-only pages (< 30 chars)                  │
 └─────────────────────────┬───────────────────────────────┘
                           │
                           ▼
 ┌─────────────────────────────────────────────────────────┐
 │  STEP 3 — CHUNKING  (RecursiveCharacterTextSplitter)   │
 │  • chunk_size = 400  ·  chunk_overlap = 60             │
 │  • Separators: \n\n → \n → sentence → word             │
 │  • Rich metadata: source, page, chunk_index, hash       │
 └─────────────────────────┬───────────────────────────────┘
                           │
                           ▼
 ┌─────────────────────────────────────────────────────────┐
 │  STEP 4 — UPSERT  (all-MiniLM-L6-v2 → ChromaDB)       │
 │  • Deterministic IDs: hash[:16]_chunk_idx               │
 │  • Idempotent: re-ingesting same file = no-op           │
 └─────────────────────────────────────────────────────────┘
```

</div>

### Relevance Grading (A–D)

<div align="center">

| Grade | Cosine Distance | Meaning | Decision weight |
|:---:|:---:|:---:|:---:|
| **A** | ≤ 0.35 | Highly relevant | Cited directly |
| **B** | ≤ 0.50 | Relevant | Cited with confidence |
| **C** | ≤ 0.65 | Marginal | Used as weak signal |
| **D** | > 0.65 | Low relevance | Flagged in context |

</div>

---

<div align="center">

## 💬 Full Request Flow

</div>

```
User  → /request
 Bot  → 🖥️ What asset do you need?

User  → "macbok pro 14 for video editing"
 Bot  → ✏️ (interpreted as: MacBook Pro 14)
         📝 Why do you need this asset?

User  → "new marketing campaign post-production"
 Bot  → ⏱️ How urgent is this?

User  → "kinda urgent"
 Bot  → 🔍 (Confidence: 72% — let me double-check)
         Please reply with HIGH, NORMAL, or LOW.

User  → "HIGH"
 Bot  → 💰 Approximate cost in USD?

User  → "around 2k"
 Bot  → 📋 Request Summary
         Asset    : MacBook Pro 14
         Reason   : new marketing campaign post-production
         Urgency  : HIGH
         Cost     : $2,000
         ─────────────────────────────
         Reply Yes to submit · No to restart

User  → yes
 Bot  → ✅ Decision: APPROVED
         Request ID   : A1B2C3D4
         AI Confidence: ██████████ 94%
         Reasoning    : MacBook Pro 14 is within the $3,500 laptop cap
                        per asset_policy.json §laptop.max_usd. The HIGH
                        urgency for a campaign deadline is justified.
         Policy refs  : asset_policy.json §laptop · rulebook.pdf p.12 (Grade A)
```

---

<div align="center">

## 📁 Project Structure

</div>

```
sd05-asset-request-bot/
│
├── bot/
│   ├── main.py                    Application bootstrap, middleware, routing
│   ├── config.py                  Pydantic-settings (env-driven)
│   │
│   ├── handlers/
│   │   ├── commands.py            /start  /status  /upload_rulebook
│   │   ├── conversation.py        PTB ConversationHandler (/request flow)
│   │   └── messages.py            Orphan message fallback
│   │
│   ├── slots/
│   │   ├── extractor.py           NLP slot extractor · confidence · injection_risk
│   │   └── state.py               FSM: COLLECTING → CONFIRMING → DECIDING → DONE/FROZEN
│   │
│   ├── validation/
│   │   └── decision.py            LLM decision engine (RAG + graded context)
│   │
│   ├── rag/
│   │   ├── pdf_loader.py          PyMuPDF → Chunker → ChromaDB (Stage 3)
│   │   └── retriever.py           MiniLM embeddings · A–D grading · RagContext
│   │
│   ├── security/
│   │   └── scorer.py              6-signal suspicion ensemble
│   │
│   └── db/
│       ├── schema.py              SQLite WAL schema (4 tables)
│       └── repository.py          Async aiosqlite data access
│
├── data/
│   ├── hris.json                  Mock employee records
│   ├── asset_policy.json          Cost caps · category rules · prohibited items
│   └── products.json              Product catalogue with MSRP pricing
│
├── rulebooks/                     Drop PDFs here (or via /upload_rulebook)
├── chroma_store/                  Auto-generated ChromaDB vector store
│
├── Dockerfile                     Railway-ready · non-root · model pre-baked
├── requirements.txt               All deps pinned
└── .env.example                   Environment variable template
```

---

<div align="center">

## 🚀 Quick Start

</div>

**1. Clone & configure**

```bash
git clone <repo-url>
cd sd05-asset-request-bot
cp .env.example .env
```

Edit `.env`:

```dotenv
BOT_TOKEN=your_telegram_bot_token
GROQ_API_KEY=your_groq_api_key
ADMIN_USER_IDS=123456789        # your Telegram user ID
```

**2. Install & run**

```bash
pip install -r requirements.txt
python -m bot.main
```

**3. Docker (recommended)**

```bash
docker build -t mugen-ai .
docker run -d \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/rulebooks:/app/rulebooks \
  -v $(pwd)/chroma_store:/app/chroma_store \
  mugen-ai
```

**4. Index your first rulebook**

```
/upload_rulebook   →   Send your company policy PDF
```

The bot will validate, extract, chunk (400/60), embed, and store it. Future requests are automatically graded against it.

---

<div align="center">

## 🛡️ Security Reference

### Layer 1 — Suspicion Scorer

| Signal | Weight | Detects |
|:---:|:---:|:---|
| Regex blacklist | 30% | 20 jailbreak / injection / exfil patterns |
| Injection probes | 25% | System-prompt manipulation, role spoofing |
| Entropy anomaly | 15% | Base64 / compressed payloads in messages |
| Unicode obfuscation | 15% | RTL overrides, zero-width chars, Cyrillic mix |
| Rate abuse | 15% | Burst flooding (> 12 msg / min sliding window) |
| Groq LLM judge | 40% blend | Grey-zone arbitration (score 0.28–0.72 only) |

### Layer 2 — NLP Injection Detection

Every slot extraction independently evaluates `injection_risk` on the raw message. Detects adversarial inputs that appear benign at the message level but attempt manipulation within the slot context.

</div>

---

<div align="center">

## ⚙️ Configuration

| Variable | Default | Description |
|:---:|:---:|:---|
| `BOT_TOKEN` | _(required)_ | From @BotFather |
| `GROQ_API_KEY` | _(required)_ | From console.groq.com |
| `ADMIN_USER_IDS` | _(required)_ | Comma-separated Telegram user IDs |
| `SUSPICION_THRESHOLD` | `0.55` | Score above this → quarantine |
| `RAG_TOP_K` | `4` | Policy chunks per query (overridden to 3 in Stage 3) |
| `CHROMA_PERSIST_DIR` | `./chroma_store` | Vector DB storage path |
| `RULEBOOKS_DIR` | `./rulebooks` | PDF upload directory |
| `DB_PATH` | `./data/mugen.db` | SQLite database path |
| `LOG_LEVEL` | `INFO` | `DEBUG` · `INFO` · `WARNING` · `ERROR` |

</div>

---

<div align="center">

## 🗺️ Roadmap

| Stage | Status | What |
|:---:|:---:|:---|
| 1 | ✅ Done | Foundation · 6-signal suspicion scorer · security middleware |
| 2 | ✅ Done | NLP extractor · confidence thresholding · ConversationHandler · injection freeze |
| 3 | ✅ Done | PDF RAG pipeline · A–D grading · graded decision engine |
| 4 | 🔲 Next | HRIS validation · budget entitlement · policy Q&A mode |
| 5 | 🔲 | Admin dashboard (`/admin_stats`, `/admin_pending`, adjudication) |
| 6 | 🔲 | Webhook mode · Redis rate limiter · Prometheus metrics |

<br/>

---

Built with ⚡ — Powered by [Groq](https://groq.com) · [LLaMA 3.3 · 70B](https://ai.meta.com/llama/) · [ChromaDB](https://trychroma.com) · [python-telegram-bot v20](https://python-telegram-bot.org)

</div>
