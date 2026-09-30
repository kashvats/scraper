# Release validation — Harvest 0.3 candidate

## Completed in this environment

**22 Python tests passed.** Coverage includes:
- Nested traversal, pagination, URL deduplication and page limits.
- Simulated crash after an atomic checkpoint; recovery continues without duplicate output rows.
- Concurrent workers cannot claim the same job; stale lease holders cannot commit.
- Login, cookie flags, CSRF, logout, expired sessions and disabled accounts.
- Owner isolation for jobs, saved configurations, exports and picker sessions.
- Queue cancellation, resumption, deletion, worker readiness and retention cleanup.
- CSV/XLSX Unicode/quoting/formula safety and zero-value preservation.
- Request validation, size limits and response security headers.
- IPv4/IPv6 private/link-local/metadata/reserved targets, mixed DNS answers and disallowed ports are rejected by proxy resolution logic.
- Login throttling and stale screenshot revision rejection.

**DOM and UI-logic tests passed** in JSDOM: exact versus similar selectors, parent selection, image/link URLs, custom-column mapping, duplicate-column prevention and nested-link rules.

Python compilation, JavaScript syntax, deployment/CI YAML and seccomp JSON checks passed. One upstream Starlette warning recommends httpx2 for future TestClient usage; the current locked test stack passes with httpx.

## Not completed here — mandatory before promotion

This environment cannot launch Chromium (restricted socket operation) and has no Docker engine. Therefore none of the following is claimed as passed:

- Docker image build and actual Chromium sandbox startup.
- Live Playwright/Selenium scraping, screenshot rendering, click-coordinate picking and real browser UI/mobile checks.
- Network isolation and proxy blocking under the deployed Docker network.
- HTTPS certificate provisioning and secure-cookie operation through the production gateway.
- Live process-kill/restart behavior with real browsers, backup restoration, concurrency/load/resource capacity and prolonged reliability.
- Dependency/container vulnerability scans and independent security review.

## Included acceptance automation

The CI workflow builds Docker, starts a disposable deployment/account, tests both engines on the fixture catalog, verifies CSV/XLSX downloads, checks blocked metadata/internal targets, exercises visual browser selection and captures desktop/mobile screenshots, then checks persisted jobs after an API restart.

Run it in your repository or use `tests/browser_acceptance.py` against a disposable local stack. Inspect the generated evidence and fix any failures before deploying. Unit tests and an included workflow are not substitutes for an executed deployment test.

## Promotion checklist

1. Browser/Docker acceptance passes on the actual deployment image.
2. A test crash during a multi-page job resumes without duplicate rows; confirm page/row limits, cancellation and queue fairness with the intended user count.
3. HTTPS and cross-user access checks pass; private/metadata requests fail through both engines.
4. Backup restore is demonstrated on an isolated volume.
5. Capacity/soak tests meet the deployment's expected load and storage budget.
6. Dependency and container scans are reviewed and release blockers resolved.
7. Record the tested image digest, configuration and rollback backup.

Until these gates are complete, label this package a **release candidate**, not a production-verified build.
