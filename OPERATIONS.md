# Operations runbook

## Supported topology

One Linux Docker host; local persistent storage; one API process; one worker by default. The API lock fails startup if a second API uses the same data directory. More worker containers can share the local volume, with a proportional increase in CPU/RAM. Do not scale APIs or use an NFS volume.

## Health and monitoring

- `/health/live`: API process availability.
- `/health/ready`: database accessible and a worker heartbeat within 30 seconds. This does not probe external sites or certify browser launch.
- `docker compose logs api worker`: request IDs, job IDs and operational exceptions. Do not expose logs to unauthenticated users.
- Monitor disk usage, memory/OOM kills, queue age, repeated page errors and readiness. Set alerts outside this app; alert delivery is not configured by this package.
- Export failures refer to request IDs. Browser failures use a generic user-visible message; details stay in service logs.

## Backup and restore

1. Create a consistent online backup using SQLite's backup API:
   `docker compose exec api python manage.py backup /app/data/backups/backup-YYYYMMDD.sqlite3`
2. Copy it off-host: `docker compose cp api:/app/data/backups/backup-YYYYMMDD.sqlite3 ./backup-YYYYMMDD.sqlite3`
3. Encrypt/protect the backup in your storage system. Test restoration in a separate environment regularly.
4. To restore a target environment, stop **API and all workers**. Keep a backup of its current volume.
5. Copy the selected backup into the stopped volume as `harvest.sqlite3`, owned by UID/GID 10001. Remove only that database's stale `harvest.sqlite3-wal` and `harvest.sqlite3-shm` sidecars before startup. Do not overwrite a running database.
6. Start the stack, verify readiness, sign in, and verify known exports. Any restored running job is recovered after lease expiration; queued jobs may run. Stop/delete unwanted jobs before starting workers if replay is undesirable.
7. A restored backup contains old sessions. Revoke them before exposure with an administrator maintenance command that deletes `sessions`, or reset account passwords using `manage.py user`.

Backups include users, sessions, configuration, results and audit records. Export files are temporary and regenerated from committed rows.

## Updates and rollback

- Build a candidate image, run unit/DOM/browser acceptance, scan dependencies/images, and record its digest.
- Back up the database before promotion. Use the verified image, not a newly rebuilt mutable tag.
- Apply production configuration and roll out. Confirm readiness and a sample job.
- Schema v1 is created idempotently. No downgrade or later migration is implied. Rollback of a future schema-changing release requires that release's documented migration/restore procedure.

## Restart and recovery

An API restart closes visual sessions; users reopen the site. Scraping is independent. A worker's clean shutdown requeues its active job from the last checkpoint. A crash is detected after 90 seconds. Lease tokens prevent an old worker from committing after reassignment.

Pages committed before a crash are not emitted twice by replay. This does not promise deduplication of two distinct URLs serving the same product; identity is URL/depth-based.

## Retention and capacity

Worker maintenance deletes terminal jobs beyond `RETENTION_DAYS` (default 30), expired sessions/rate records, and audit records older than 90 days. SQLite may retain freed file space for reuse. Schedule an offline VACUUM only if needed after a backup; do not run it during heavy work.

Results are capped at 50 MiB per job, but aggregate account storage is not quota-managed. Monitor disk, adjust retention and restrict account creation. Five concurrent/queued jobs per user and 100 globally limit queue growth; they do not replace disk monitoring.

## Release gates

See VALIDATION.md. Full Docker/browser tests, sandbox capability, proxy blocking, HTTPS cookies, restart recovery, backup restore, workload capacity and vulnerability scan evidence are required before promoting the release. External site anti-bot behavior is not covered by the local demo tests.
