# Epic Events CRM

Command-line CRM for the Epic Events event agency. Manages employees, clients,
contracts, and events, with role-based permissions (management, sales, support),
JWT authentication, and Sentry error reporting.

## Features

- **Authentication**: login / logout, JWT session token stored with
  owner-only permissions (0600), generic failure message (no user enumeration).
- **Employees** (management): create, update, list collaborators.
- **Clients** (sales): create, update own clients, universal read.
- **Contracts** (management): create, update, filter by unsigned / unpaid.
- **Events**: created by sales on a signed contract, assigned to support by
  management, updated by the assigned support. Filters by missing support
  and by "mine" (role-aware).
- **Sentry**: unexpected exceptions are reported with their stack trace.
  Expected business errors remain user-facing only.

Every permission, scope, and validation rule lives in the service layer.
The CLI is a thin presentation layer (Click + Rich).

## Requirements

- Python 3.12+
- PostgreSQL

## Installation

```bash
git clone https://github.com/Nasunaj/epic-events-crm.git
cd epic-events-crm

python3 -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"
```

## Configuration

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```
   Variable | Description |
 |---|---|
 | `DB_HOST` / `DB_PORT` | PostgreSQL host and port |
 | `DB_NAME` / `DB_USER` / `DB_PASSWORD` | Database credentials |
 | `JWT_SECRET` | Secret used to sign tokens (`openssl rand -base64 32`) |
 | `JWT_EXPIRATION_HOURS` | Token lifetime in hours |
 | `SENTRY_DSN` | Sentry project DSN (optional: without it, error reporting is disabled) |

**Never commit your `.env` file** — it contains your secrets.

## Database setup

Create the database (once):

```sql
CREATE DATABASE epicevents_db;
CREATE USER epicevents_user WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE epicevents_db TO epicevents_user;
```

Then initialize the application:

```bash
# 1. Create the tables
python -m scripts.init_db

# 2. Seed the three roles (gestion, commercial, support) — idempotent
python -m scripts.seed_roles

# 3. Create the first admin account (interactive, prompts for password)
python -m scripts.create_admin
```

## Usage

```bash
epicevents login
epicevents whoami
epicevents employees list
epicevents clients list
epicevents contracts list --unsigned
epicevents events list --no-support
epicevents logout
```

Run `epicevents --help` or `epicevents <group> --help` for the full
command reference. Every command except `login`, `whoami`, and `logout`
requires an authenticated session.

## Tests

```bash
pytest tests/ -v --cov=epicevents
```

133 tests, ~91% overall coverage. Tests run on an
in-memory SQLite database: no PostgreSQL and no token file are needed.

## Project structure

```
epicevents/
├── models.py          # SQLAlchemy models (data layer)
├── database.py        # engine / session factory
├── security.py        # Argon2id hashing, JWT creation
├── token_store.py     # session token persistence (0600)
├── policies.py        # role-based permission map
├── validation.py      # input validation rules
├── exceptions.py      # business exception hierarchy
├── logging_conf.py    # Sentry initialization
├── services/          # business logic + all security rules
└── cli.py             # Click commands (thin presentation layer)
scripts/               # init_db, seed_roles, create_admin
tests/                 # pytest suite (unit + CLI)
```

## Quality

- `black` formatting and `flake8` linting, zero warnings
- Business errors exit with code 1 and a message on stderr
- Passwords are hashed with Argon2id, never stored or passed in clear