# Module: root

> Generated navigation map. Source code is authoritative.

## `Dockerfile`

- language: `unknown`
- size: 689 bytes
- hash: `7a783034cf5c`

## `app.py`

- language: `py`
- size: 10916 bytes
- hash: `9f185f3a3d6a`
- symbols:
  - `async-function` `lifespan` — line 29
  - `async-function` `boundaries` — line 50
  - `function` `live` — line 73
  - `function` `ready` — line 76
  - `function` `config_info` — line 85
  - `function` `owned` — line 88
  - `function` `public_job` — line 93
  - `function` `list_jobs` — line 97
  - `function` `create_job` — line 102
  - `function` `job_details` — line 109
  - `function` `cancel_job` — line 115
  - `function` `resume` — line 123
  - `function` `delete_job` — line 135
  - `function` `safe_cell` — line 143
  - `function` `result_rows` — line 148
  - `function` `export` — line 153
  - `class` `Template` — line 180
  - `function` `templates` — line 185
  - `function` `save_template` — line 190
  - `function` `delete_template` — line 201
  - `function` `home` — line 207
- routes:
  - `GET /health/live` → `live` — line 73
  - `GET /health/ready` → `ready` — line 76
  - `GET /api/settings` → `config_info` — line 85
  - `GET /api/jobs` → `list_jobs` — line 97
  - `POST /api/jobs` → `create_job` — line 102
  - `GET /api/jobs/{jid}` → `job_details` — line 109
  - `POST /api/jobs/{jid}/cancel` → `cancel_job` — line 115
  - `POST /api/jobs/{jid}/resume` → `resume` — line 123
  - `DELETE /api/jobs/{jid}` → `delete_job` — line 135
  - `GET /api/jobs/{jid}/export/{fmt}` → `export` — line 153
  - `GET /api/templates` → `templates` — line 185
  - `POST /api/templates` → `save_template` — line 190
  - `DELETE /api/templates/{tid}` → `delete_template` — line 201
  - `GET /` → `home` — line 207
- imports:
  - `auth`
  - `contextlib`
  - `csv`
  - `fastapi`
  - `fastapi.responses`
  - `fastapi.staticfiles`
  - `io`
  - `json`
  - `logging`
  - `openpyxl`
  - `openpyxl.cell`
  - `os`
  - `picker`
  - `pydantic`
  - `scraper`
  - `settings`
  - `starlette.background`
  - `starlette.middleware.trustedhost`
  - `store`
  - `tempfile`
  - `time`
  - `urllib.parse`
  - `uuid`

## `auth.py`

- language: `py`
- size: 3185 bytes
- hash: `f0ccc12613fa`
- symbols:
  - `function` `password_hash` — line 13
  - `function` `verify` — line 17
  - `function` `token_hash` — line 24
  - `function` `current_user` — line 26
  - `class` `Login` — line 36
  - `function` `login` — line 41
  - `function` `me` — line 58
  - `function` `logout` — line 61
- routes:
  - `POST /login` → `login` — line 41
  - `GET /me` → `me` — line 58
  - `POST /logout` → `logout` — line 61
- imports:
  - `fastapi`
  - `hashlib`
  - `hmac`
  - `pydantic`
  - `secrets`
  - `settings`
  - `store`
  - `time`

## `compose.production.yaml`

- language: `yaml`
- size: 428 bytes
- hash: `4a3eb68de132`

## `compose.yaml`

- language: `yaml`
- size: 2111 bytes
- hash: `6713cc2c588a`

## `egress_proxy.py`

- language: `py`
- size: 4479 bytes
- hash: `5435df94cb7a`
- symbols:
  - `function` `resolve_public` — line 15
  - `function` `dial` — line 24
  - `class` `Proxy` — line 38
  - `method` `Proxy.log_message` — line 40
  - `method` `Proxy.setup` — line 41
  - `method` `Proxy.handle_one_request` — line 43
  - `method` `Proxy.do_CONNECT` — line 47
  - `method` `Proxy.forward` — line 67
- imports:
  - `http.server`
  - `ipaddress`
  - `os`
  - `select`
  - `socket`
  - `threading`
  - `time`
  - `urllib.parse`

## `manage.py`

- language: `py`
- size: 2332 bytes
- hash: `e7cb0228d173`
- symbols:
  - `function` `main` — line 12
- imports:
  - `argparse`
  - `auth`
  - `getpass`
  - `json`
  - `pathlib`
  - `settings`
  - `sqlite3`
  - `store`
  - `uuid`

## `package-lock.json`

- language: `json`
- size: 18826 bytes
- hash: `a2807da9a06b`

## `package.json`

- language: `json`
- size: 171 bytes
- hash: `c57d23b4981a`

## `picker.py`

- language: `py`
- size: 7855 bytes
- hash: `76f1ffa6f254`
- symbols:
  - `class` `Open` — line 23
  - `class` `Action` — line 25
  - `class` `PageSession` — line 37
  - `method` `PageSession.__init__` — line 38
  - `method` `PageSession.snapshot` — line 39
  - `method` `PageSession.act` — line 44
  - `function` `browser_process` — line 70
  - `class` `Session` — line 95
  - `method` `Session.__init__` — line 96
  - `method` `Session.receive` — line 103
  - `method` `Session.submit` — line 109
  - `method` `Session.close` — line 118
  - `function` `find` — line 123
  - `function` `open_browser` — line 129
  - `function` `action` — line 143
  - `function` `close_browser` — line 147
  - `function` `reaper` — line 152
  - `function` `startup` — line 160
  - `function` `shutdown` — line 162
- routes:
  - `POST /{sid}/action` → `action` — line 143
  - `DELETE /{sid}` → `close_browser` — line 147
- imports:
  - `auth`
  - `base64`
  - `fastapi`
  - `logging`
  - `multiprocessing`
  - `os`
  - `pathlib`
  - `pydantic`
  - `scraper`
  - `store`
  - `threading`
  - `time`
  - `typing`
  - `uuid`
  - `worker`

## `picker_dom.js`

- language: `js`
- size: 2619 bytes
- hash: `5a993a4d494d`
- symbols:
  - `function` `token` — line 6
  - `function` `exact` — line 10
  - `function` `similar` — line 25
  - `function` `clean` — line 2
  - `function` `esc` — line 3
  - `function` `count` — line 4
  - `function` `classes` — line 5

## `requirements.txt`

- language: `txt`
- size: 85 bytes
- hash: `187db505d538`

## `scraper.py`

- language: `py`
- size: 11636 bytes
- hash: `81bd9b41255e`
- symbols:
  - `class` `Column` — line 9
  - `class` `Config` — line 15
  - `method` `Config.validate_config` — line 32
  - `function` `canonical` — line 45
  - `class` `Browser` — line 72
  - `method` `Browser.__init__` — line 73
  - `method` `Browser.__enter__` — line 76
  - `method` `Browser.visit` — line 113
  - `method` `Browser.extract` — line 130
  - `method` `Browser.__exit__` — line 134
  - `function` `crawl` — line 140
- imports:
  - `collections`
  - `os`
  - `pydantic`
  - `time`
  - `typing`
  - `urllib.parse`

## `settings.py`

- language: `py`
- size: 1189 bytes
- hash: `7d1cd11a8492`
- symbols:
  - `function` `validate` — line 16
- imports:
  - `os`
  - `pathlib`

## `store.py`

- language: `py`
- size: 6563 bytes
- hash: `ae738cccd826`
- symbols:
  - `function` `connection` — line 10
  - `function` `migrate` — line 25
  - `function` `audit` — line 42
  - `function` `rate` — line 45
  - `function` `create_job` — line 54
  - `function` `get_job` — line 64
  - `function` `decode` — line 69
  - `function` `claim` — line 75
  - `function` `heartbeat` — line 87
  - `function` `checkpoint` — line 94
  - `function` `finish` — line 103
  - `function` `cancelled` — line 107
  - `function` `cleanup` — line 111
- imports:
  - `contextlib`
  - `json`
  - `settings`
  - `sqlite3`
  - `time`
  - `uuid`

## `worker.py`

- language: `py`
- size: 3317 bytes
- hash: `d2a1ad91aa9c`
- symbols:
  - `function` `execute` — line 15
  - `function` `terminate` — line 32
  - `function` `main` — line 47
- imports:
  - `logging`
  - `multiprocessing`
  - `os`
  - `scraper`
  - `settings`
  - `signal`
  - `store`
  - `threading`
  - `time`
  - `uuid`

