# 🤖 MUGEN AI — Enterprise Telegram Asset-Request Bot

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

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)](https://python.org)
[![LLaMA](https://img.shields.io/badge/LLM-LLaMA_3.3_70B-purple?logo=meta)](https://groq.com)
[![RAG](https://img.shields.io/badge/RAG-ChromaDB_+_MiniLM-green)](https://www.trychroma.com)
[![PTB](https://img.shields.io/badge/Bot-python--telegram--bot_v20-blue?logo=telegram)](https://python-telegram-bot.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

</div>

---

> **MUGEN AI** is not a form-filler. It is an autonomous, adversarially-hardened enterprise agent that processes IT asset requests through a four-layer intelligence stack — all inside a Telegram chat.

---

## ✨ What Makes It Different

| Typical Asset Bot | MUGEN AI |
|---|---|
| Static form with dropdowns | Free-text NLP with typo correction |
| No policy awareness | Live RAG against your company PDFs |
| Hardcoded approval rules | LLM decision engine with reasoning |
| No security | 6-signal suspicion ensemble + NLP injection scanner |
| Yes/No outcomes | `APPROVED` · `NEEDS_REVIEW` · `REJECTED` with cited policy clauses |

---

## 🏛️ Architecture — Four Intelligence Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                     TELEGRAM USER MESSAGE                        │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                ───────────────▼───────────────
               │  LAYER 1: SUSPICION SCORER    │  ← group -999 middleware
               │  6-signal ensemble            │    fires BEFORE everything
               │  • Regex blacklist    (30%)   │
               │  • Injection probes   (25%)   │
               │  • Entropy anomaly    (15%)   │
               │  • Unicode obfuscation(15%)   │
               │  • Rate abuse window  (15%)   │
               │  • Groq LLM judge  (grey-zone)│
                ───────────────────────────────
                          │              │
                   CLEAN  │              │  SUSPICIOUS
                          ▼              ▼
               ┌──────────────┐    ┌──────────────┐
               │ Continue to  │    │  QUARANTINE  │
               │  business    │    │  + DB log    │
               │  logic       │    │  + HALT      │
               └──────┬───────┘    └──────────────┘
                      │
                ───────▼───────────────────────────
               │  LAYER 2: NLP FRONT-END (Stage 2) │
               │  Per-slot Groq extraction          │
               │  • Typo correction                 │
               │  • Paraphrase normalisation        │
               │  • Confidence scoring (0.0–1.0)    │
               │  • injection_risk: none/low/high   │
               │                                    │
               │  confidence < 0.70 → re-ask user   │
               │  injection_risk=high → FREEZE 🔒   │
                ────────────────────────────────────
                      │
                ───────▼───────────────────────────
               │  LAYER 3: RAG PIPELINE            │
               │  PyMuPDF → RecursiveTextSplitter  │
               │  → all-MiniLM-L6-v2 (local CPU)  │
               │  → ChromaDB similarity search     │
               │  Returns top-K policy chunks      │
                ────────────────────────────────────
                      │
                ───────▼───────────────────────────
               │  LAYER 4: LLM DECISION ENGINE     │
               │  RAG context + static policy JSON │
               │  + HRIS budget entitlement        │
               │  → LLaMA 3.3-70B via Groq         │
               │  → APPROVED / NEEDS_REVIEW /      │
               │     REJECTED + policy citations   │
                ────────────────────────────────────
```

---

## 🧠 NLP Layer Deep Dive (Stage 2)

The NLP extractor is the most sophisticated part of the system. Each slot gets its own dedicated LLM call with a precision-engineered prompt.

### What one extraction call does

```json
// User says: "macbok pro for video editing, kinda urgent, around 2 grand"

// Slot: asset_name
{
  "value": "MacBook Pro",
  "confidence": 0.85,
  "corrected_text": "MacBook Pro",   ← typo fixed
  "injection_risk": "none"
}

// Slot: urgency  
{
  "value": "HIGH",                   ← "kinda urgent" → HIGH
  "confidence": 0.72,
  "corrected_text": null,
  "injection_risk": "none"
}

// Slot: cost_estimate
{
  "value": 2000.0,                   ← "2 grand" → 2000.0
  "confidence": 0.91,
  "corrected_text": null,
  "injection_risk": "none"
}
```

### Confidence Thresholding

```
confidence ≥ 0.70  ──────────────▶ ✅ Slot accepted
confidence 0.40–0.69 ────────────▶ 🔍 Low-confidence re-ask with hint
confidence < 0.40  ──────────────▶ ❓ Failed extraction, original prompt repeated
                                       (max 3 retries, then slot skipped)
```

### Injection Risk — Session Freeze

If **any** slot extraction detects `injection_risk: "high"`:

```
🔒 Session Frozen — Security Alert

MUGEN AI's NLP layer detected a potential prompt-injection or
policy-bypass attempt in your last message.

This session has been permanently frozen and the event has
been logged for administrator review.
```

The `SlotMachine` transitions to `FROZEN` (a terminal state), the `ConversationHandler` ends, and a `INJECTION_FREEZE` event is written to the security_events table.

---

## 📁 Project Structure

```
sd05-asset-request-bot/
│
├── bot/
│   ├── main.py                 # App bootstrap, middleware, routing
│   ├── config.py               # Pydantic-settings (env-driven)
│   │
│   ├── handlers/
│   │   ├── commands.py         # /start, /status, /upload_rulebook
│   │   ├── conversation.py     # PTB ConversationHandler (Stage 2)
│   │   └── messages.py         # Orphan message fallback
│   │
│   ├── slots/
│   │   ├── extractor.py        # 🧠 NLP slot extractor (Stage 2 core)
│   │   └── state.py            # FSM: COLLECTING→CONFIRMING→DECIDING→DONE/FROZEN
│   │
│   ├── validation/
│   │   └── decision.py         # LLM decision engine (RAG + policy)
│   │
│   ├── rag/
│   │   ├── pdf_loader.py       # PyMuPDF → ChromaDB ingestion
│   │   └── retriever.py        # MiniLM embeddings + similarity search
│   │
│   ├── security/
│   │   └── scorer.py           # 6-signal suspicion ensemble
│   │
│   └── db/
│       ├── schema.py            # SQLite WAL schema (4 tables)
│       └── repository.py        # Async aiosqlite data access
│
├── data/
│   ├── hris.json               # Mock employee records
│   ├── asset_policy.json       # Cost caps, category rules
│   └── products.json           # Product catalogue with MSRP
│
├── rulebooks/                  # Drop PDFs here (or via /upload_rulebook)
├── chroma_store/               # Auto-generated vector DB
│
├── Dockerfile                  # Railway-ready, non-root, model pre-baked
├── requirements.txt
└── .env.example
```

---

## 🚀 Quick Start

### 1. Clone & configure

```bash
git clone <repo>
cd sd05-asset-request-bot
cp .env.example .env
```

Edit `.env`:
```dotenv
BOT_TOKEN=your_telegram_bot_token
GROQ_API_KEY=your_groq_api_key
ADMIN_USER_IDS=123456789          # your Telegram user ID
```

### 2. Install & run

```bash
pip install -r requirements.txt
python -m bot.main
```

### 3. Docker (recommended for production)

```bash
docker build -t mugen-ai .
docker run -d \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/rulebooks:/app/rulebooks \
  -v $(pwd)/chroma_store:/app/chroma_store \
  mugen-ai
```

---

## 💬 Bot Commands

| Command | Access | Description |
|---|---|---|
| `/start` | All | Welcome message and capability overview |
| `/request` | All | Start a new asset request (ConversationHandler) |
| `/status [id]` | All | Check request status (latest or by ID) |
| `/cancel` | All | Cancel the current request conversation |
| `/upload_rulebook` | Admin | Upload a policy PDF for RAG indexing |

---

## 📖 How a Request Works

```
User: /request
 Bot: 🖥️ What asset do you need?

User: "I need a macbok pro for editing videos, its urgent"
 Bot: ✏️ (interpreted as: MacBook Pro)
      📝 Why do you need this asset?

User: "video editing for the new marketing campaign"
 Bot: 💰 Approximate cost in USD?

User: "around 2k"
 Bot: 📋 Request Summary
      Asset:     MacBook Pro
      Reason:    video editing for the new marketing campaign
      Urgency:   HIGH
      Est. Cost: $2,000

      Reply Yes to submit · No to restart

User: yes
 Bot: ✅ Decision: APPROVED
      Request ID: A1B2C3D4
      AI Confidence: ██████████ 94%
      Reasoning: MacBook Pro is within the $3,500 laptop budget...
      Policy References:
        • Section 4.2 — Laptop Procurement Policy
```

---

## 🛡️ Security Details

### Layer 1 — Suspicion Scorer (every message)

| Signal | Weight | What it detects |
|---|---|---|
| Regex blacklist | 30% | 20 hardcoded jailbreak / injection / exfil patterns |
| Soft injection probes | 25% | System-prompt manipulation, role spoofing |
| Entropy anomaly | 15% | Base64 / compressed payloads hidden in messages |
| Unicode obfuscation | 15% | RTL overrides, zero-width chars, Cyrillic-Latin mix |
| Rate abuse | 15% | Burst flooding (>12 messages/minute) |
| **Groq LLM judge** | 40% blend | Grey-zone arbitration (score 0.28–0.72 only) |

### Layer 2 — NLP Injection Detection (per slot)

The extractor runs `injection_risk` assessment on **every single slot fill** — completely independent of Layer 1. This catches adversarial inputs that look benign at the message level but attempt manipulation within the slot context.

### Database Audit Trail

Every decision, quarantine event, and security freeze is immutably logged:

```sql
security_events  -- quarantine + freeze events with full signal breakdown
audit_log        -- every APPROVED/REJECTED/NEEDS_REVIEW decision
```

---

## ⚙️ Configuration Reference

```dotenv
# Required
BOT_TOKEN=                    # From @BotFather
GROQ_API_KEY=                 # From console.groq.com
ADMIN_USER_IDS=               # Comma-separated Telegram user IDs

# Security tuning
SUSPICION_THRESHOLD=0.55      # 0.0–1.0; above this → quarantine

# RAG tuning  
RAG_TOP_K=4                   # Policy chunks per query

# Paths (change for Docker volumes)
CHROMA_PERSIST_DIR=./chroma_store
RULEBOOKS_DIR=./rulebooks
DB_PATH=./data/mugen.db

# Logging
LOG_LEVEL=INFO                # DEBUG | INFO | WARNING | ERROR
```

---

## 🗺️ Roadmap

- [x] **Stage 1** — Foundation, suspicion scorer, security middleware
- [x] **Stage 2** — NLP extractor, confidence thresholding, ConversationHandler, injection freeze
- [ ] **Stage 3** — HRIS validation, budget entitlement checks, policy Q&A mode
- [ ] **Stage 4** — Admin dashboard (`/admin_stats`, `/admin_pending`, adjudication commands)
- [ ] **Stage 5** — Webhook mode, Redis-backed rate limiter, Prometheus metrics

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first.

---

<div align="center">

Built with ⚡ by the MUGEN AI team · Powered by [Groq](https://groq.com) · [LLaMA 3.3 · 70B](https://ai.meta.com/llama/)

</div>
