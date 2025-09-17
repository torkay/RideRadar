# CI Workflow Archive and Disable Instructions

This repository previously ran the scheduled GitHub Actions workflow at `.github/workflows/schedule.yml`. We’ve archived a copy under `engine/tools/ci/archive_schedule.yml` and recommend disabling or removing the active workflow in `.github/workflows/` to prevent unnecessary CI runs.

Disable options (pick one)
- Remove workflow: `git rm .github/workflows/schedule.yml`
- Rename to disable: `git mv .github/workflows/schedule.yml .github/workflows/schedule.yml.disabled`
- Restrict triggers (edit): change `on:` to only allow manual dispatch:
  
  on:
    workflow_dispatch:

- Hard-disable (edit): add an always-false job condition:
  
  jobs:
    scrape:
      if: ${{ false }}

Notes
- CI on Debian runners is unreliable for headless Selenium in this project; disabling saves compute and noise.
- The archived file in `engine/tools/ci/` is non-executable and for reference only.
- Keep `main` protected and use `ops/pipeline` (or similar) for development; merge via PR.

