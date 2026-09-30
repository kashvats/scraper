# Route Map

> Generated best-effort HTTP/API route index.

| Method | Route | File | Symbol | Line |
|---|---|---|---|---:|
| `GET` | `/` | `app.py` | `home` | 207 |
| `GET` | `/api/jobs` | `app.py` | `list_jobs` | 97 |
| `POST` | `/api/jobs` | `app.py` | `create_job` | 102 |
| `DELETE` | `/api/jobs/{jid}` | `app.py` | `delete_job` | 135 |
| `GET` | `/api/jobs/{jid}` | `app.py` | `job_details` | 109 |
| `POST` | `/api/jobs/{jid}/cancel` | `app.py` | `cancel_job` | 115 |
| `GET` | `/api/jobs/{jid}/export/{fmt}` | `app.py` | `export` | 153 |
| `POST` | `/api/jobs/{jid}/resume` | `app.py` | `resume` | 123 |
| `GET` | `/api/settings` | `app.py` | `config_info` | 85 |
| `GET` | `/api/templates` | `app.py` | `templates` | 185 |
| `POST` | `/api/templates` | `app.py` | `save_template` | 190 |
| `DELETE` | `/api/templates/{tid}` | `app.py` | `delete_template` | 201 |
| `GET` | `/health/live` | `app.py` | `live` | 73 |
| `GET` | `/health/ready` | `app.py` | `ready` | 76 |
| `POST` | `/login` | `auth.py` | `login` | 41 |
| `POST` | `/logout` | `auth.py` | `logout` | 61 |
| `GET` | `/me` | `auth.py` | `me` | 58 |
| `DELETE` | `/{sid}` | `picker.py` | `close_browser` | 147 |
| `POST` | `/{sid}/action` | `picker.py` | `action` | 143 |
