# Security Baseline — v1.0 draft (LGD Engine MVP)

Public sources:
- OWASP Top 10 (2021): https://owasp.org/Top10/
- OWASP Top 10 for LLM Applications (2025): https://owasp.org/www-project-top-10-for-large-language-model-applications/

Status legend: **Done** = shipped in this MVP tree; **Planned** = designed, lands post-MVP.

---

## A. OWASP Top 10 (2021)

| ID | Risk | Framework risk point | Defense | Status |
|---|---|---|---|---|
| A01 | Broken Access Control | AI seats could call merge/arbitration tools without authorization | RBAC ceilings in skill manifests (read-only / suggest / execute); seats default read-only; merge gate requires gatekeeper+finalizer | Done (manifest) |
| A02 | Cryptographic Failures | Secrets in plaintext on disk | Keys only via env / OS secret store; never printed; `security_scan.py` blocks plaintext keys at CI | Done (scan) |
| A03 | Injection | Skill params flow into shell / SQL / prompt | Parameterized SQLite binding; manifest input schema validation; no shell string concat; `prompt_injection_defense.py` three layers | Done (scan + sample) |
| A04 | Insecure Design | Missing threat modeling for gate bypass | `gate_bot.py` mandatory pre-merge checks; fail-closed degradation to "hold" | Done |
| A05 | Security Misconfiguration | Default bind exposed to LAN | Default bind 127.0.0.1; public exposure requires explicit flag + TLS + OAuth2 | Planned |
| A06 | Vulnerable & Outdated Components | Transitive deps with CVEs | Lockfile required check in `security_scan.py`; SBOM recommendation; CI dep-vuln scan post-MVP | Done (scan hint) |
| A07 | Identification & Authentication Failures | Weak key reuse across hosts | Per-host X-API-Key; rotation in one place; re-check after rotation | Planned |
| A08 | Software & Data Integrity Failures | Tampered skill packages / untrusted pickle | No pickle on untrusted data; JSON envelopes schema-checked; ed25519 skill signature planned | Planned |
| A09 | Security Logging & Monitoring Failures | Undetected abuse of AI seats | Append-only audit log (who/when/input-hash/verdict); gate events logged | Planned |
| A10 | SSRF | Adapters fetch attacker-controlled URLs | Outbound domain whitelist for adapters; demo Web frontend output escaping | Planned |

## B. OWASP Top 10 for LLM Applications (2025)

| ID | Risk | Defense in this framework | Status |
|---|---|---|---|
| LLM01 | Prompt Injection | L1 input validation (length/structure/sensitive-instruction patterns) in `prompt_injection_defense.py`; retrieved web content treated as untrusted data, never as instructions | Done (sample) |
| LLM02 | Sensitive Information Disclosure | Output-side regex scan of LLM text for key/ORCID/email patterns before returning; `desanitize_check.py` gates the release tree | Done |
| LLM03 | Supply Chain | Pinned deps + lockfile; SBOM note; skill manifests with signatures before execution | Done (hint) |
| LLM04 | Data and Model Poisoning | Golden test set frozen offline; KB writes go through evidence gates (有籍有证有门禁) | Planned |
| LLM05 | Improper Output Handling | LLM-generated HTML/commands sanitized/sandboxed before execution; output filter L3 | Done (sample) |
| LLM06 | Excessive Agency | RBAC ceiling per skill; unauthorized tool calls rejected + audited (L2 sample); no autonomous merge | Done (sample) |
| LLM07 | System Prompt Leakage | System prompt holds no secrets; secrets live in env, never in prompt context | Done (design) |
| LLM08 | Vector & Embedding Weaknesses | KB documents tagged with source trust level; untrusted ingestion quarantined | Planned |
| LLM09 | Misinformation | Verdict always carries citations; unsupported claim → "hold", never fabricated "go" | Done (design) |
| LLM10 | Unbounded Consumption | Per-key rate limits; timeout caps on judge calls; max-output token budgets | Planned |
