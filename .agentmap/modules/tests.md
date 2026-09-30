# Module: tests

> Generated navigation map. Source code is authoritative.

## `tests/browser_acceptance.py`

- language: `py`
- size: 4441 bytes
- hash: `e5df06703a58`
- symbols:
  - `function` `run` — line 16
- imports:
  - `csv`
  - `httpx`
  - `io`
  - `openpyxl`
  - `os`
  - `pathlib`
  - `playwright.sync_api`
  - `time`

## `tests/test_app.py`

- language: `py`
- size: 9120 bytes
- hash: `feea31915ffa`
- symbols:
  - `function` `client` — line 13
  - `function` `login` — line 19
  - `function` `config` — line 23
  - `class` `FakeBrowser` — line 24
  - `method` `FakeBrowser.__init__` — line 25
  - `method` `FakeBrowser.__enter__` — line 26
  - `method` `FakeBrowser.__exit__` — line 27
  - `method` `FakeBrowser.visit` — line 28
  - `method` `FakeBrowser.extract` — line 29
  - `function` `test_traversal_limits` — line 34
  - `function` `test_recovery_and_fencing` — line 40
  - `function` `test_atomic_claim` — line 56
  - `function` `test_auth_csrf_logout` — line 61
  - `function` `test_ownership` — line 70
  - `function` `test_exports` — line 79
  - `function` `test_cancel_resume_delete` — line 87
  - `function` `test_validation_headers` — line 96
  - `function` `test_picker_ownership` — line 104
  - `function` `test_private_network_blocked` — line 113
  - `function` `test_dns_mixed_records_ports` — line 116
  - `function` `test_readiness_retention` — line 120
  - `function` `test_login_throttle` — line 127
  - `function` `test_expired_session_and_disabled_user` — line 131
  - `function` `test_stale_picker_revision_rejected` — line 139
- imports:
  - `app`
  - `auth`
  - `concurrent.futures`
  - `csv`
  - `egress_proxy`
  - `fastapi.testclient`
  - `io`
  - `json`
  - `openpyxl`
  - `pytest`
  - `scraper`
  - `settings`
  - `socket`
  - `store`
  - `time`

