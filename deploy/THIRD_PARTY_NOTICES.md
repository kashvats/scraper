# Third-party deployment asset

`browser-seccomp.json` was retrieved from Microsoft Playwright:
https://github.com/microsoft/playwright/blob/main/utils/docker/seccomp_profile.json

Upstream project license: Apache License 2.0, included as `PLAYWRIGHT-LICENSE`.
Guidance: https://playwright.dev/python/docs/docker

The profile extends Docker's default policy with namespace operations needed for Chromium's sandbox. It is not a claim that the deployment has undergone a security audit.
