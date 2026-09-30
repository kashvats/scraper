# Security model and deployment boundaries

This deployment serves an administrator-provisioned, trusted small team. It is not designed for public anonymous or hostile multi-tenant signup.

Implemented controls:
- Salted scrypt password hashes; random opaque sessions stored only as hashes; eight-hour expiry; HttpOnly/SameSite=Strict cookies; Secure cookies for HTTPS/production.
- CSRF tokens on authenticated mutations, origin checks, 1 MiB request-body limits, server-side ownership checks for jobs/templates/exports/picker sessions.
- Transport-peer login throttling, per-account job/browser creation limits, bounded queues, process timeouts, browser-session limits and Docker CPU/RAM/PID limits.
- Browser sandbox enabled; non-root containers; a Playwright-supplied seccomp profile; no blanket unconfined profile or SYS_ADMIN capability.
- Outbound proxy validates all resolved public IPv4/IPv6 answers, blocks mixed public/private DNS, and connects to the checked IP. Direct internet routing is absent for the API/worker Compose network. The static demo is a deliberate isolated exception.
- Formula-safe CSV/XLSX cells, text-only DOM rendering in the UI, CSP, no framing, no MIME sniffing, no-store API responses and request IDs.

Boundaries:
- OS/browser sandbox correctness and Docker network rules must be validated on the host. Application unit tests cannot certify them.
- API browser children and workers run under the same container user as their service. A browser sandbox escape can threaten that container's files. Use a dedicated host/VM without unrelated secrets; stronger hostile-tenant isolation requires separately sandboxed browser infrastructure.
- The proxy is a destination-filtering proxy, not a malware scanner or an audited general-purpose internet gateway. Do not expose its port publicly. It does not restrict public domains beyond HTTP/HTTPS ports.
- Browser traffic can contain proprietary information. Results/screenshots are returned only to the owning account; server administrators and volume holders have access to the underlying data.
- Interactive browser cookies are ephemeral and are not copied into scrape jobs. Avoid using the picker as a password manager or a privileged administrative browser.
- No SSO/MFA, role-based administration UI, encrypted-at-rest database, aggregate storage quotas, independent security audit, HA/failover or automated alert delivery is included.
- TLS is supplied by the production gateway. Store backups securely and use host/storage encryption where required.

Dependency and container vulnerability scans must be run before release and on a maintenance schedule. Fixes must be verified against both browser engines before promotion. Report security issues privately to the deployment owner; no public disclosure endpoint is configured by this package.
