# Requirements Document

## Introduction

This document specifies the requirements for deploying and testing the MUGEN AI Telegram Bot application (sd05-asset-request-bot) in both local development and cloud production environments. The system consists of two main services: a Python Telegram Bot service and a FastAPI Admin Panel. The deployment workflow ensures proper environment configuration, comprehensive testing of all bot capabilities, Docker containerization, and cloud deployment readiness with complete documentation.

## Glossary

- **Bot_Service**: The Python Telegram Bot application running via `python -m bot.main` that handles user interactions
- **Admin_Panel**: The FastAPI web application running via `python -m admin_panel.run` on port 8080 for administrative functions
- **Environment_File**: The `.env` configuration file containing credentials (BOT_TOKEN, GROQ_API_KEY, ADMIN_USER_IDS)
- **RAG_Pipeline**: Retrieval-Augmented Generation system using ChromaDB and PDF processing for policy enforcement
- **HRIS_System**: Human Resource Information System containing employee data in `data/hris.json`
- **Deployment_Package**: Complete Docker image with all dependencies, volumes, and configurations ready for cloud deployment
- **Health_Check**: Automated verification that confirms all system components are operational
- **Railway_Platform**: Cloud platform target for production deployment
- **Security_Middleware**: The suspicion scoring system that validates all incoming messages
- **Slot_Extractor**: NLP component that extracts structured data from user messages with confidence scoring

## Requirements

### Requirement 1: Environment Configuration and Setup

**User Story:** As a developer, I want to configure the environment with required credentials and dependencies, so that the application can run successfully in both local and cloud environments.

#### Acceptance Criteria

1. WHEN the `.env` file is missing required values (BOT_TOKEN, GROQ_API_KEY, ADMIN_USER_IDS), THE System SHALL provide clear error messages indicating which credentials are missing
2. THE Environment_Setup SHALL validate that Python 3.11 or higher is installed before proceeding
3. WHEN installing dependencies, THE System SHALL install all packages from requirements.txt without version conflicts
4. THE System SHALL verify that required directories exist (data/, chroma_store/, rulebooks/) and create them if missing
5. WHEN BOT_TOKEN is configured, THE System SHALL validate the token format matches Telegram's token pattern (digit:alphanumeric)
6. WHEN GROQ_API_KEY is configured, THE System SHALL validate it is non-empty and properly formatted
7. THE System SHALL parse ADMIN_USER_IDS as comma-separated integers and validate each is a valid Telegram user ID

### Requirement 2: Local Testing of Bot Commands

**User Story:** As a developer, I want to test all bot commands locally, so that I can verify core functionality works before deployment.

#### Acceptance Criteria

1. WHEN the `/start` command is sent, THE Bot_Service SHALL respond with a welcome message listing available commands
2. WHEN the `/request` command is sent, THE Bot_Service SHALL initiate the asset request conversation flow starting with identity verification
3. WHEN the `/status` command is sent with an active request, THE Bot_Service SHALL return the current status of that request
4. WHEN the `/history` command is sent, THE Bot_Service SHALL return the user's request history from the SQLite database
5. WHEN the `/cancel` command is sent during an active conversation, THE Bot_Service SHALL terminate the conversation and clear user state
6. WHEN an invalid command is sent, THE Bot_Service SHALL respond with a helpful message suggesting valid commands
7. THE System SHALL log all command executions with timestamp, user_id, and command type to the database

### Requirement 3: User Request Flow Testing

**User Story:** As a developer, I want to test the complete user request workflow, so that I can verify the conversation state machine and decision engine work correctly.

#### Acceptance Criteria

1. WHEN a user starts `/request`, THE Bot_Service SHALL first request identity verification (name and Employee ID)
2. WHEN identity is provided in format "Name, EMP_ID", THE Bot_Service SHALL validate the EMP_ID exists in HRIS_System before proceeding
3. WHEN the asset name contains typos or variations, THE Slot_Extractor SHALL correct them and present the normalized form with confidence score
4. WHEN a slot extraction has confidence below 0.70, THE Bot_Service SHALL re-ask the user with contextual hints
5. WHEN all slots are collected with confidence ≥ 0.70, THE Bot_Service SHALL present a summary and request confirmation
6. WHEN the user confirms the request, THE System SHALL invoke the decision engine with HRIS, catalogue, RAG, and policy contexts
7. THE Decision_Engine SHALL return one of three outcomes: approved, flagged, or rejected with reasoning and policy references
8. WHEN a request is approved, THE Bot_Service SHALL store the complete request record in the database with status "approved"
9. WHEN injection_risk is detected as high for any slot, THE Bot_Service SHALL freeze the session and log a security event

### Requirement 4: Admin Dashboard Functionality

**User Story:** As an administrator, I want to use the Admin Panel to manage requests, HRIS data, and rulebooks, so that I can maintain the system without direct database access.

#### Acceptance Criteria

1. WHEN the Admin_Panel starts, THE System SHALL serve the dashboard at http://localhost:8080
2. WHEN the Requests tab is accessed, THE Admin_Panel SHALL display all requests with user_identity, asset_name, status, and decision reasoning
3. WHEN the Requests tab loads, THE System SHALL display aggregate counts for Approved and Rejected requests
4. WHEN the HRIS tab is accessed, THE Admin_Panel SHALL display all employee records with normalized field names (id, name, role, grade, budget)
5. WHEN HRIS data is modified through the Admin_Panel, THE System SHALL validate the JSON structure before saving to `data/hris.json`
6. WHEN the Rulebook Manager tab is accessed, THE Admin_Panel SHALL list all PDF files in the rulebooks directory
7. WHEN a PDF is uploaded through the Rulebook Manager, THE System SHALL validate it is a valid PDF ≤50MB before processing
8. WHEN the API Keys tab is accessed, THE Admin_Panel SHALL allow updating BOT_TOKEN and GROQ_API_KEY and persist changes to the Environment_File

### Requirement 5: RAG Pipeline Verification

**User Story:** As a developer, I want to verify the RAG pipeline processes PDFs correctly, so that policy decisions are based on accurate document retrieval.

#### Acceptance Criteria

1. WHEN a PDF rulebook is uploaded, THE RAG_Pipeline SHALL extract text using PyMuPDF and skip pages with fewer than 30 characters
2. WHEN text is extracted, THE RAG_Pipeline SHALL chunk it using RecursiveTextSplitter with chunk_size=400 and chunk_overlap=60
3. WHEN chunks are created, THE RAG_Pipeline SHALL compute SHA-256 hash of each chunk and use it for deduplication
4. WHEN chunks are embedded, THE RAG_Pipeline SHALL use all-MiniLM-L6-v2 model and store vectors in ChromaDB at chroma_persist_dir
5. WHEN a policy query is performed, THE RAG_Pipeline SHALL retrieve top-k chunks (default k=4) and grade them A/B/C/D based on cosine distance
6. WHEN cosine distance is ≤0.35, THE System SHALL assign grade A and cite the chunk directly in decision reasoning
7. WHEN cosine distance is >0.65, THE System SHALL assign grade D and flag the chunk as low-relevance
8. WHEN the same PDF is re-uploaded, THE RAG_Pipeline SHALL detect duplicate SHA-256 hash and skip re-indexing

### Requirement 6: Security Middleware Testing

**User Story:** As a developer, I want to verify the security middleware correctly identifies and blocks malicious inputs, so that the system is protected against attacks.

#### Acceptance Criteria

1. WHEN any user message is received, THE Security_Middleware SHALL execute before all other handlers (handler group -999)
2. WHEN a message is analyzed, THE Security_Middleware SHALL compute a suspicion score from six signals: regex blacklist (30%), injection probes (25%), entropy anomaly (15%), unicode obfuscation (15%), rate abuse (15%), and LLM judge (blend at 40% for grey zone only)
3. WHEN the suspicion score exceeds SUSPICION_THRESHOLD (default 0.55), THE Security_Middleware SHALL quarantine the message and send a security alert to the user
4. WHEN a message is quarantined, THE System SHALL log the security event to the database with user_id, score, signals, and text_snippet
5. WHEN a quarantined message is from an active request session, THE Security_Middleware SHALL cancel the session and clear user state
6. WHEN rate abuse is detected (>12 messages per minute), THE Security_Middleware SHALL increase the suspicion score by 15%
7. WHEN an admin user sends a message, THE Security_Middleware SHALL still apply all security checks without exemption

### Requirement 7: Database Operations Verification

**User Story:** As a developer, I want to verify all database operations work correctly, so that data integrity is maintained across the application lifecycle.

#### Acceptance Criteria

1. WHEN the Bot_Service starts, THE System SHALL execute init_db() to create all required tables if they do not exist
2. THE Database SHALL use SQLite with WAL (Write-Ahead Logging) mode for concurrent read/write operations
3. WHEN a request is created, THE System SHALL insert a record with session_id, user_id, user_identity, asset_name, reason, urgency, cost_estimate, and status
4. WHEN a request decision is made, THE System SHALL update the record with decision_outcome, decision_reasoning, confidence_score, and rag_signal_quality
5. WHEN a security event occurs, THE System SHALL insert a record into the security_events table with user_id, event_type, score, signals, and snippet
6. WHEN the `/history` command is invoked, THE System SHALL query requests table ordered by created_at descending and limit to 10 most recent
7. WHEN the Admin_Panel queries requests, THE System SHALL return all fields including user_identity for display in the dashboard

### Requirement 8: Docker Containerization

**User Story:** As a developer, I want to build and test a Docker image, so that the application can be deployed consistently across environments.

#### Acceptance Criteria

1. WHEN `docker build` is executed, THE System SHALL create an image based on python:3.11-slim with all system dependencies (libmupdf, libgl1-mesa-glx)
2. WHEN the Docker image is built, THE System SHALL pre-download the all-MiniLM-L6-v2 model to avoid cold-start delays
3. WHEN the container starts, THE System SHALL mount three volumes: /app/chroma_store, /app/data, and /app/rulebooks
4. WHEN the container runs, THE System SHALL execute as non-root user "mugen" (UID 1001) for security hardening
5. WHEN the healthcheck runs, THE System SHALL execute `python -c "import bot.config; bot.config.get_settings()"` and return success if configuration loads
6. WHEN the container is running, THE System SHALL expose the same functionality as the local installation without modification
7. WHEN environment variables are passed via `--env-file`, THE System SHALL read them from the Environment_File and apply all configurations

### Requirement 9: Groq LLM Integration Testing

**User Story:** As a developer, I want to verify the Groq LLM integration works correctly, so that slot extraction and decision making function as designed.

#### Acceptance Criteria

1. WHEN the Slot_Extractor makes an LLM call, THE System SHALL use the Groq API with model "llama-3.3-70b-versatile" (or configured groq_model)
2. WHEN a slot extraction fails due to network error, THE System SHALL retry up to 3 times with exponential backoff using tenacity
3. WHEN the GROQ_API_KEY is invalid, THE System SHALL raise a clear authentication error and prevent the bot from starting
4. WHEN the Decision_Engine invokes the LLM, THE System SHALL include five context blocks: HRIS profile, asset request, product catalogue, RAG chunks, and static policy rules
5. WHEN the LLM response is received, THE System SHALL parse the JSON response containing decision_outcome, reasoning, confidence, and alternatives
6. WHEN the LLM suggests alternatives, THE System SHALL include them in the response message with product details from the catalogue
7. WHEN the grey-zone LLM judge is invoked (suspicion score 0.28-0.72), THE System SHALL blend the judge result at 40% weight with other security signals

### Requirement 10: Multi-Service Orchestration

**User Story:** As a developer, I want to run both the Bot_Service and Admin_Panel concurrently, so that all system features are available during testing.

#### Acceptance Criteria

1. WHEN both services are needed, THE System SHALL provide a mechanism to start Bot_Service and Admin_Panel in separate processes
2. WHEN the Bot_Service is running, THE System SHALL use polling mode and process all Telegram updates
3. WHEN the Admin_Panel is running, THE System SHALL serve HTTP requests on port 8080 without blocking the Bot_Service
4. WHEN either service crashes, THE System SHALL not affect the other service's operation
5. WHEN both services are stopped, THE System SHALL cleanly close all database connections and release file handles
6. THE System SHALL provide clear logging output distinguishing messages from Bot_Service and Admin_Panel
7. WHEN a docker-compose configuration is provided, THE System SHALL orchestrate both services with proper networking and shared volumes

### Requirement 11: Cloud Deployment Preparation

**User Story:** As a developer, I want to prepare the application for Railway cloud deployment, so that it can be deployed to production with minimal configuration.

#### Acceptance Criteria

1. THE System SHALL provide documentation listing all required environment variables for Railway_Platform deployment
2. THE Deployment_Package SHALL include the Dockerfile optimized for Railway's build system
3. WHEN deployed to Railway_Platform, THE System SHALL read environment variables from Railway's secret management
4. THE System SHALL document the required Railway services: single container with three persistent volumes
5. THE Deployment_Package SHALL include health check configuration compatible with Railway's monitoring
6. THE System SHALL document Railway CLI commands for deployment: `railway login`, `railway init`, `railway up`
7. THE System SHALL provide rollback instructions documenting how to revert to a previous Railway deployment

### Requirement 12: Deployment Documentation and Verification

**User Story:** As a developer, I want comprehensive deployment documentation and verification procedures, so that any team member can deploy and troubleshoot the application.

#### Acceptance Criteria

1. THE System SHALL provide a deployment guide covering local setup, Docker build, and Railway deployment with step-by-step instructions
2. THE Deployment_Guide SHALL include a troubleshooting section addressing common issues: missing credentials, port conflicts, database lock errors, and ChromaDB initialization failures
3. THE System SHALL document all bot commands with expected inputs and outputs for testing
4. THE System SHALL provide a verification checklist confirming: bot responds to commands, admin dashboard accessible, RAG ingests PDFs, LLM decisions execute, and Docker container runs
5. THE System SHALL document monitoring approach: log analysis, error tracking, and performance metrics
6. THE System SHALL provide rollback procedures for both Docker (revert to previous image tag) and Railway (use Railway dashboard rollback)
7. THE System SHALL document backup procedures for SQLite database, ChromaDB vector store, and uploaded PDF rulebooks

### Requirement 13: Parse and Format Environment Configuration

**User Story:** As a developer, I want the system to parse and format environment configuration correctly, so that configuration errors are caught early.

#### Acceptance Criteria

1. THE Configuration_Parser SHALL load settings from the Environment_File using pydantic-settings with case-insensitive matching
2. WHEN ADMIN_USER_IDS contains whitespace or invalid characters, THE Configuration_Parser SHALL strip whitespace and filter non-digit entries
3. WHEN a required field is missing, THE Configuration_Parser SHALL raise a ValidationError listing all missing fields before the application starts
4. WHEN SUSPICION_THRESHOLD is outside range [0.0, 1.0], THE Configuration_Parser SHALL reject the value and raise a validation error
5. WHEN file paths are provided (db_path, chroma_persist_dir, rulebooks_dir), THE Configuration_Parser SHALL convert them to Path objects and resolve them relative to the application root
6. THE Pretty_Printer SHALL format the loaded configuration as a JSON object for debugging purposes
7. FOR ALL valid Configuration objects, loading then formatting then loading SHALL produce an equivalent object (round-trip property)

### Requirement 14: End-to-End Integration Testing

**User Story:** As a developer, I want to perform end-to-end integration testing, so that I can verify all components work together correctly.

#### Acceptance Criteria

1. WHEN the full system is running, THE Test SHALL simulate a complete user journey from `/request` through identity verification to final decision
2. WHEN testing the request flow, THE Test SHALL verify that HRIS lookup, slot extraction, RAG retrieval, and LLM decision all execute in sequence
3. WHEN testing security, THE Test SHALL submit known malicious patterns and verify they are quarantined with correct suspicion scores
4. WHEN testing the Admin_Panel, THE Test SHALL verify API endpoints return correct data and match database state
5. WHEN testing PDF upload, THE Test SHALL upload a sample policy PDF and verify chunks appear in ChromaDB with correct metadata
6. WHEN testing database persistence, THE Test SHALL create requests, stop the services, restart, and verify data is retained
7. WHEN testing error recovery, THE Test SHALL simulate LLM failures and verify the bot provides appropriate fallback messages

## Notes

This requirements document prioritizes testability and operational readiness. Each requirement includes specific acceptance criteria that can be verified through automated tests or manual procedures. The deployment workflow emphasizes safety through environment validation, Docker containerization, and comprehensive documentation before cloud deployment.

The RAG pipeline and configuration parser include explicit round-trip properties that MUST be tested to ensure data integrity. These are critical for system reliability.
