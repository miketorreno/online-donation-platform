# AGENTS.md

Django project ("Online Donation Platform"). Single app (`core`), config package `odp/`.

## Environment

- There is no `requirements.txt`. Dependencies are just `django` and `python-decouple`. A `venv/` exists (Python 3.12, Django 6.1) — prefer running everything as `venv/bin/python manage.py ...`.
- A root `.env` is **required**: `SECRET_KEY`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` are read via python-decouple with no defaults, so any `manage.py` command fails with `UndefinedValueError` if missing. Copy from `.env.example` and fill in values.
- Default `DB_ENGINE` in `odp/settings.py:82` is **MySQL** (port 3306). For local dev and tests set `DB_ENGINE=django.db.backends.sqlite3` in `.env`. The `"sqlite"` entry in `DATABASES` is only an alias — the `default` connection is what `migrate`/`test` actually use.
- Styling is Tailwind CSS v4 via the CLI (`@tailwindcss/cli`). Source of truth: `core/static/src/app.css` (theme tokens + component classes). Compiled output `core/static/css/app.css` is committed but generated — edit the source, then rebuild.

## Commands

```bash
npm install                              # once
npm run build                            # compile Tailwind (core/static/css/app.css, minified)
npm run watch                            # rebuild on change during dev
venv/bin/python manage.py check          # quick sanity check
venv/bin/python manage.py test           # runs against the default connection (see DB note above)
venv/bin/python manage.py makemigrations core
venv/bin/python manage.py migrate
venv/bin/python manage.py runserver      # http://127.0.0.1:8000/
venv/bin/python manage.py seed_demo [--force]  # demo user + 8 campaigns; --force deletes existing seed-slug campaigns first
```

No CI, lint, formatter config, or pre-commit hooks exist. Tests live in the `core/tests/` package, split per area (`test_models`, `test_services`, `test_views_*`, `test_seed`, `test_templatetags`, ...); shared factories (`make_user`, `make_campaign`) are in `core/tests/test_models.py`.

## Architecture

- `odp/` — settings (`odp/settings.py`), root URLconf. Auth routes are mounted at `/accounts/` via `django.contrib.auth.urls`; signup is `/signup/`.
- `core/models.py` — `Campaign` (auto unique slug, category choices, `percentage_raised`/`days_remaining` properties) and `Donation`.
- `core/services.py` — donation domain logic. **Invariant: `record_donation()` is the sole writer of `Campaign.current_amount`, advanced atomically via `F()` by the QUANTIZED amount** (cents, ROUND_HALF_UP) — never update it elsewhere.
- `core/views.py` — CBVs for browse/search (`CampaignListView`, paginated), detail, donate (`DonateView` → `record_donation`), campaign CRUD + pause/resume, and dashboards (`MyCampaignsView`, `MyDonationsView`).
- `core/templatetags/odp_extras.py` — `cover_art` (deterministic gradient per slug) and `usd` (currency filter).
- Templates are split: project-level `templates/` (in `TEMPLATES["DIRS"]`, holds `registration/login.html`, `base.html`) and app-level `core/templates/core/` (+ `includes/_campaign_card.html`, `_pagination.html`, `_supporters.html`, `_cover_banner.html`).

## URL name map

| Name | Path |
| --- | --- |
| `campaign-list` | `/` |
| `signup` | `/signup/` |
| `my-campaigns` | `/my/campaigns/` |
| `my-donations` | `/my/donations/` |
| `campaign-create` | `/campaigns/new/` (must precede `<slug>` routes) |
| `campaign-edit` / `campaign-delete` / `campaign-toggle-active` | `/campaigns/<slug>/edit\|delete\|toggle-active/` |
| `campaign-donate` | `/campaigns/<slug>/donate/` |
| `campaign-detail` | `/campaigns/<slug>/` |

## Conventions

- All configuration goes through python-decouple `config()` in `settings.py`; don't hardcode env-dependent values elsewhere.
- Reference users via `settings.AUTH_USER_MODEL` in models, never direct `User` imports.
- Money fields are `DecimalField(max_digits=10, decimal_places=2)` with `MinValueValidator` (campaign goal min 10.00, donation min 1.00); amounts are quantized to cents before storage.
- `Donation.donor` is nullable by design (anonymous donations); `transaction_id` is unique/nullable for payment-gateway IDs — keep both semantics when extending.
- Simulated checkout generates transaction ids as `SIM-<uuid4 hex>` (`core.services.generate_transaction_id`) — preserve that prefix convention when a real gateway replaces it.
- Owner-only views use `UserPassesTestMixin` with an explicit `handle_no_permission`: anonymous → login redirect, authenticated non-owner → 403.
