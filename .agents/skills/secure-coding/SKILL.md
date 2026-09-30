---
name: secure-coding
description: Production-grade secure coding skill for frontend, backend, APIs, authentication, authorization, databases, infrastructure integrations, secrets, file handling, and dependency safety. Use when implementing or modifying application code that handles users, permissions, data, authentication, external input, APIs, files, credentials, payments, infrastructure, or sensitive operations.
---

# Secure Coding

## Mission

Write production code that minimizes security risk without breaking application behavior.

Security must be considered during implementation, not added afterward.

Every change should preserve:

- confidentiality
- integrity
- availability
- authentication
- authorization
- auditability
- least privilege

Do not weaken existing security controls for convenience.

---

# 1. Security First Principles

Always follow:

1. Never trust client input
2. Validate at trust boundaries
3. Authenticate users before protected operations
4. Authorize every sensitive action
5. Apply least privilege
6. Fail securely
7. Minimize sensitive data exposure
8. Keep secrets outside source code
9. Avoid insecure defaults
10. Log security-relevant events without leaking secrets

Security controls must exist on the server where enforcement matters.

Frontend checks improve UX but are not security boundaries.

---

# 2. Do Not Trust Client-Side Validation

Client-side validation is useful for user experience.

It must not be considered authoritative.

Always enforce important validation on the backend.

Examples:

- permissions
- ownership
- allowed values
- input length
- file types
- resource access
- pricing
- business rules
- role-based operations

Never trust values merely because they came from your own frontend.

---

# 3. Authentication

When working with authentication:

- use established authentication libraries
- use secure password hashing
- never store plaintext passwords
- never implement custom cryptography
- protect login endpoints from abuse
- rotate authentication credentials when appropriate
- invalidate sessions when security-sensitive credentials change
- avoid exposing authentication tokens in logs

Do not build custom authentication protocols when a mature solution exists.

---

# 4. Authorization

Authentication answers:

"Who is this user?"

Authorization answers:

"Is this user allowed to perform this operation?"

Always enforce authorization server-side.

Check permissions for:

- reading resources
- creating resources
- updating resources
- deleting resources
- exporting data
- administrative actions
- cross-tenant access
- file access
- sensitive reports

Never rely only on:

- hidden buttons
- disabled UI
- route guards
- frontend roles

---

# 5. Object-Level Authorization

When an API accepts identifiers such as:

```text
/users/123
/cameras/42
/orders/928
/employees/91