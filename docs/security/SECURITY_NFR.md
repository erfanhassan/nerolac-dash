# Enterprise Security Non-Functional Requirements (NFRs)

**System**: Nerolac Operations Dashboard  
**Architecture**: Next.js 15 App Router + FastAPI (Async ASGI) + PostgreSQL 16 + Redis 7  
**Compliance Baseline**: Bangladesh ICT Act 2006, Bangladesh Cybersecurity Act 2023, ISO 27001, OWASP API Top 10

---

## 1. Secrets Management & Vault Integration (NFR-SEC-01)

- **Zero Plaintext Secrets**: Hardcoding API keys, passwords, database URLs, or private keys in source code, commit history, or plain `.env` files is strictly prohibited.
- **Runtime Secret Retrieval**: All secrets must be dynamically retrieved at runtime via HashiCorp Vault / Azure Key Vault using AppRole or Managed Identity authentication (`src/backend/config/vault.py`).
- **Encrypted Local Fallback**: In offline, developer, or CI testing environments lacking a live Vault cluster, secrets are retrieved from an encrypted local Fernet payload with zero plaintext leakage.
- **Rotation**: Database credentials and API tokens must support automated 30-day rotation without requiring application restarts.

---

## 2. PII Redaction & LLM Context Scrubbing (NFR-SEC-02)

- **Bangladeshi Data Privacy**: Customer, dealer, and employee personally identifiable information (PII) must be redacted before being written to logs, monitoring streams, or sent to external LLM context windows (`src/backend/middleware/pii_masker.py`).
- **Target Redaction Entities**:
  1. **Bangladeshi Phone Numbers**: Formats matching `+8801...`, `8801...`, `01...` with spaces or hyphens are masked as `[BD_PHONE_REDACTED]`.
  2. **National ID (NID) Numbers**: 10-digit Smart NID, 13-digit legacy NID, and 17-digit birth-year NID are masked as `[BD_NID_REDACTED]`.
  3. **Bank Account & Financial Figures**: Bank account numbers (9-18 digits), credit/debit card numbers, and payment routing references are masked as `[BANK_ACCOUNT_REDACTED]`.
- **Enforcement Layers**:
  - `PIIRedactingFormatter`: Custom Python logging formatter redacting log messages and arguments.
  - `mask_llm_context`: Deep scrubber for chat messages and prompts before AI inference.
  - `PIIMaskingMiddleware`: ASGI / FastAPI middleware for payload masking.

---

## 3. Bangladesh Data Sovereignty (NFR-SEC-03)

- **Data Residency**: Per national regulatory guidelines, primary operational databases (PostgreSQL 16) and caching nodes (Redis 7) must physically reside within Bangladesh sovereign territory or authorized enterprise private cloud infrastructure (`src/backend/config/settings.py`).
- **Automated Hostname & IP Validation**:
  - Allowed: Hosts ending in `.bd`, `.nerolacbd.com`, `.gov.bd`, approved sovereign regions (`BD`, `BD-DHAKA-1`, `BD-KALIAKOIR-1`), private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), and loopback addresses.
  - Forbidden: Foreign cloud endpoints (e.g. AWS US/EU RDS, Azure foreign regions) trigger immediate `DataSovereigntyViolationError` on startup.

---

## 4. Threat Boundaries & STRIDE Analysis (NFR-SEC-04)

- Formal STRIDE threat boundaries are maintained in `docs/security/stride_model.json` covering:
  - **SAP SFTP Ingress**: Plant batch manifests, formula protection, Ed25519 authentication, SHA-256 checksum verification.
  - **Meta WhatsApp Webhooks**: HMAC SHA-256 (`X-Hub-Signature-256`) cryptographic verification, idempotency tracking in Redis 7.
  - **Enterprise REST APIs**: RS256 JWT tokens, tenant-scoped data queries (BOLA prevention), Pydantic v2 strict payload validation.
