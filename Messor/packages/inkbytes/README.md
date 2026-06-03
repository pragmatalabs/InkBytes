# `inkbytes` — Shared kernel

This package exposes the shared code used by every Python service in the
InkBytes platform under a single Python namespace:

```
inkbytes.common.*      # API clients, file/IO helpers, system utilities, logger
inkbytes.models.*      # Pydantic domain models (Article, Outlet, Entity, ...)
inkbytes.database.*    # Database adapters (TinyDB, future Postgres, ...)
```

## Install (editable, for local development)

```bash
pip install -e packages/inkbytes
```

Or, from a consumer's `requirements.txt`:

```
-e ../../packages/inkbytes
```

## Layout

The source of truth lives at the repo root (`/common`, `/models`,
`/database`) for backward compatibility with legacy services (Entopics,
Synochi, Unitas) that haven't migrated yet.

The `inkbytes/` directory inside this package is a thin namespace
wrapper that exposes those repo-root directories as proper Python
sub-packages via symlinks:

```
packages/inkbytes/
├── pyproject.toml
├── README.md
└── inkbytes/
    ├── __init__.py
    ├── common    -> ../../../common
    ├── models    -> ../../../models
    └── database  -> ../../../database
```

When the legacy services migrate to depend on this package (Sprint-2),
the symlinks will be replaced with the actual source moved into this
directory, and the repo-root copies will be archived.

## Versioning

`0.1.0` — initial extraction from the symlink-based layout.

Bump to `0.2.0` when source physically moves under `packages/inkbytes/inkbytes/`.
