# 0.3.0 candidate

Replaces the anonymous, in-memory prototype with a single-host authenticated application.

- Administrator-provisioned accounts, scrypt hashes, hashed opaque sessions and CSRF protection.
- Owner-scoped jobs, downloads, saved scraper configurations and interactive browser sessions.
- SQLite WAL durable job queue, atomic page/result checkpoints, fenced worker leases and resumable jobs.
- Separate worker service and supervised browser child processes with cancellation/time budgets.
- Sandboxed non-root Chromium, outbound destination-checking proxy and internal Docker network.
- Per-account creation limits, request/body caps, retention, health/readiness and audit records.
- Point-and-click mapping retained; screenshot revisions reject stale actions; saved scraper workflows and paginated results added.
- Streaming CSV and write-only XLSX generation with formula-safe values.
- HTTPS gateway override, dependency locks, operations/security documentation and live acceptance CI.

Compatibility: uses a new database with account ownership. Anonymous prototype jobs are not automatically imported. See README for export-before-upgrade guidance.

Validation: 22 backend tests and DOM/UI mapping checks pass. Docker/browser/host acceptance is still required; see VALIDATION.md.
