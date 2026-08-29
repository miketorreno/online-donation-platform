# Online Donation Platform

A Django web application for community fundraising: anyone can browse campaigns, give to them through a simulated checkout, and launch campaigns of their own with live progress tracking.

## Tech Stack

- Python 3.12+
- Django 6.1
- Tailwind CSS v4
- PostgreSQL (production) / SQLite (local dev)
- python-decouple
- Gunicorn + WhiteNoise
- Celery + Redis (background tasks / scheduled jobs)
- Docker + Docker Compose
- uv (package manager)

## Getting Started

### Prerequisites

- Python 3.12+ and `uv` (see https://docs.astral.sh/uv/)
- Node.js (any recent LTS) + npm — only for building the stylesheet

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/miketorreno/online-donation-platform.git
   cd online-donation-platform
   ```

2. Install Python dependencies with uv (creates `.venv/`):

   ```bash
   uv sync
   ```

3. Install frontend dependencies and build the stylesheet:

   ```bash
   npm install
   npm run build      # one-off production build (minified)
   npm run watch      # optional: rebuild on change while developing
   ```

4. Configure environment variables:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set `SECRET_KEY` (required), plus your database values. For local development use SQLite (make all of `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` non-empty — `DB_PORT` is cast to `int`):

   ```
   DB_ENGINE=django.db.backends.sqlite3
   DB_USER=dummy
   DB_PASSWORD=dummy
   DB_HOST=dummy
   DB_PORT=5432
   ```

5. Apply migrations and start the server:

   ```bash
   uv run python manage.py migrate
   uv run python manage.py runserver
   ```

Open http://127.0.0.1:8000/ in your browser.

### Docker

1. Copy the environment file and set your values:

   ```bash
   cp .env.example .env
   ```

   At minimum, set `SECRET_KEY` to a random string. The defaults work with the Compose PostgreSQL and Redis services.

2. Build and start (web + db + redis + celery worker/beat):

   ```bash
   docker compose up --build
   ```

   On first start the `web` entrypoint runs migrations, collects static files, and starts Gunicorn. The app is available at http://localhost:8000/.

3. Seed demo data (optional):

   ```bash
   docker compose exec web python manage.py seed_demo
   ```

   Demo credentials: `demo` / `demo-pass-1234`.

4. Stop:

   ```bash
   docker compose down         # stop containers
   docker compose down -v      # stop and wipe database volume
   ```

### Celery / background tasks

- `worker` runs `celery -A odp worker`; `beat` runs `celery -A odp beat` for scheduled jobs. Both are part of `docker compose up`.
- The Celery app lives in `odp/celery.py`; tasks are declared in `core/tasks.py` (`@shared_task`, always accept primary keys — never ORM instances).
- In CI/tests tasks run eagerly (no broker needed) via `.apply()`.

### Production deployment (VPS + host Nginx)

The app runs in Docker Compose on the VPS; Nginx runs **on the host** as a reverse proxy (the same host may serve other services), proxying `/` to Gunicorn and serving `/static/` and `/media/` directly.

1. Set `WEB_PORT` and bind Gunicorn to loopback only; the `web` service publishes
   `127.0.0.1:8000` so it is reachable only via the host proxy.
2. Configure host paths for static/media via `.env`:

   ```
   HOST_STATIC_DIR=/srv/online-donation-platform/staticfiles
   HOST_MEDIA_DIR=/srv/online-donation-platform/media
   ```

   These directories are bind-mounted into the `web` container (which writes
   `collectstatic` output and uploads) and read directly by host Nginx.

3. Install the reference config with your domain (see `infra/nginx/odp.conf`),
   then issue a TLS cert with certbot:

   ```bash
   sudo cp infra/nginx/odp.conf /etc/nginx/sites-available/odp
   sudo ln -s /etc/nginx/sites-available/odp /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   sudo certbot --nginx -d example.com
   ```

4. Deploy via the helper script (`infra/scripts/deploy.sh`) or the CI/CD
   pipeline (tagged `v*` releases build the image and deploy over Tailscale).

## Feature Tour

- **Explore** (`/`) — active campaigns in a responsive card grid with full-text search, category filters, sorting (newest / most funded / closing soon), and pagination.
- **Campaign detail** — cover art, raised/goal progress bar, supporter count, days remaining, and a recent donations feed.
- **Give now** (`/campaigns/<slug>/donate/`) — donation form with preset amounts ($10/$25/$50/$100), an optional public message, and a simulated checkout (no real payment is processed; transaction IDs are generated as `SIM-<uuid>`).
- **Accounts** — sign up at `/signup/`, log in at `/accounts/login/`. Anonymous donations are supported.
- **Dashboards** — `/my/campaigns/` lists your campaigns with edit/pause/resume/delete controls; `/my/donations/` totals everything you've given.
- **Demo data** — `python manage.py seed_demo` creates a demo user and eight deterministic campaigns with donations. Re-run with `--force` to wipe and reseed those campaigns.

Demo credentials: username `demo`, password `demo-pass-1234`.

## URL Map

| Path                               | Name                     | Purpose                  |
| ---------------------------------- | ------------------------ | ------------------------ |
| `/`                                | `campaign-list`          | Browse/search campaigns  |
| `/signup/`                         | `signup`                 | Create an account        |
| `/my/campaigns/`                   | `my-campaigns`           | Your campaigns dashboard |
| `/my/donations/`                   | `my-donations`           | Your donations history   |
| `/campaigns/new/`                  | `campaign-create`        | Start a campaign         |
| `/campaigns/<slug>/edit/`          | `campaign-edit`          | Edit your campaign       |
| `/campaigns/<slug>/delete/`        | `campaign-delete`        | Delete confirmation      |
| `/campaigns/<slug>/toggle-active/` | `campaign-toggle-active` | Pause/resume (POST)      |
| `/campaigns/<slug>/donate/`        | `campaign-donate`        | Donation form            |
| `/campaigns/<slug>/`               | `campaign-detail`        | Campaign page            |
| `/accounts/login/` etc.            | Django auth URLs         | Login/logout/password    |

## Project Structure

- `manage.py` — Django administration entrypoint
- `odp/` — project configuration and settings (incl. `celery.py`)
- `core/` — application logic: models, views, forms, services layer, celery tasks, management commands
- `core/static/src/app.css` — Tailwind v4 entrypoint (theme tokens + component classes)
- `core/static/css/app.css` — compiled stylesheet (generated by `npm run build`; don't edit by hand)
- `templates/` — shared base and authentication templates
- `core/templates/core/` — app-specific templates
- `infra/` — host-level deployment assets (Nginx reverse-proxy config + scripts)

## Notes

- All money fields are `DecimalField(max_digits=10, decimal_places=2)`; donation amounts are rounded to cents (half-up) before storage, and campaign totals are advanced by the same quantized amount.
- `Donation.donor` is nullable by design (anonymous donations); `transaction_id` is unique/nullable for payment-gateway IDs.
- The services layer (`core/services.py`) is the single writer of `Campaign.current_amount`.

## License

This project is released under the terms of the [MIT License](LICENSE).
