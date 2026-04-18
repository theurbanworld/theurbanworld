# Contributing to The Urban World

Thanks for your interest in contributing. This guide covers how to set up the project locally, what we expect in pull requests, and how work is organized across the two subprojects.

## Project Layout

- [`web/`](web/) — Nuxt 4 frontend ([`web/README.md`](web/README.md))
- [`pipeline/`](pipeline/) — Python data pipeline ([`pipeline/README.md`](pipeline/README.md))
- [`pipeline/DATA_LINEAGE.md`](pipeline/DATA_LINEAGE.md) — end-to-end data provenance

## Prerequisites

- [pnpm](https://pnpm.io/) (`pnpm@10+`) for the frontend
- [uv](https://docs.astral.sh/uv/) for the pipeline
- Python 3.11–3.13
- Node.js 22+

## Frontend Setup

```bash
pnpm install
cp web/.env.example web/.env   # fill in values as needed
pnpm dev:app
```

Quality gates (run before pushing):

```bash
pnpm --filter app lint
pnpm --filter app typecheck
pnpm --filter app test:run
```

## Pipeline Setup

```bash
cd pipeline
uv sync
cp .env.example .env           # R2 + Postgres credentials (optional for most tasks)
```

Most scripts are runnable without credentials if you first pull pre-computed data:

```bash
uv run python -m src.download.download_h3_r8
```

Quality gates:

```bash
uv run ruff check .
uv run ruff format --check .
```

> **Don't want to reprocess 150 GB of raw data?** The pre-computed R2 dataset is the easiest entry point — see `pipeline/README.md` for details.

## Making a Change

1. **Open an issue first** for anything larger than a small bugfix, so we can align on scope.
2. **Branch from `main`** with a short descriptive name (`feat/…`, `fix/…`, `docs/…`).
3. **Write focused commits.** Small, reviewable PRs merge faster.
4. **Run the quality gates** listed above for whichever subproject you touched.
5. **Update documentation** when you change user-visible behavior or pipeline output schemas.
6. **Open a pull request** targeting `main`. The CI must pass.

## Coding Conventions

- **Frontend:** TypeScript, Tailwind CSS utilities, Nuxt UI 4 components. Prefer composables over mixins. In Vue SFCs, order sections `<script>`, `<template>`, `<style>`.
- **Pipeline:** Python 3.11+, type hints where useful, `ruff` for linting/formatting, `pandera` schemas for every parquet output.
- **Commits:** imperative mood ("Add radial profile export"), concise first line, details in the body if needed.

## AI Agent Instructions

Each subproject has an `AGENTS.md` (frontend and pipeline) with task-specific guidance for Claude Code, Cursor, and similar tools. If you use one of those tools, please leave those files in sync when conventions change.

## Data and Licensing

- Code contributions are accepted under the project's [MIT](LICENSE) license.
- Content and derived data ship under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
- Upstream GHSL data is © European Commission JRC under CC BY 4.0.

By submitting a pull request, you confirm that your contribution can be distributed under these terms.

## Reporting Bugs and Requesting Features

Open a [GitHub issue](https://github.com/theurbanworld/theurbanworld/issues).
