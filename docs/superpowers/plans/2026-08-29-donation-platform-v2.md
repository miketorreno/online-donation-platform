# Online Donation Platform — v2 Feature Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the completed MVP (auth, browse, donate, campaign CRUD, dashboards, 79 tests) into a production-grade platform across six phases: foundation/infra, creator updates & photos, accounts & profiles, email notifications, analytics, and a public REST API.

**Architecture:** Single Django app (`core`) under config package `odp/`; domain logic in `core/services.py` (`record_donation` is the sole writer of `Campaign.current_amount` via `F()`). Celery app in `odp/celery.py`, tasks in `core/tasks.py`. Server-rendered Django templates + committed Tailwind v4 build. Deployment via Docker Compose on a VPS with a **host-level Nginx** reverse proxy.

**Tech Stack:** Python 3.12/3.14, Django 6.1, python-decouple, PostgreSQL (prod) / SQLite (dev+CI), Celery 5.4 + Redis, Tailwind v4, uv, Gunicorn + WhiteNoise, DRF (Phase 6).

## Global Constraints

Every task implicitly includes these. Exact values verbatim:

- All Django commands: `uv run python manage.py …` from repo root. Dev/CI DB is SQLite via `.env` (`DB_ENGINE=django.db.backends.sqlite3`); `DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT` must all be **non-empty** (`DB_PORT` is `cast=int` and an empty string crashes settings import).
- Locked URL names preserved: `campaign-list`, `campaign-detail`, `campaign-create`, `campaign-edit`, `campaign-delete`, `campaign-donate`, `campaign-toggle-active`, `my-campaigns`, `my-donations`, `signup`, `login`, `logout`. New routes follow the existing `campaigns/<slug>/…` family placement rules.
- Money: `DecimalField(max_digits=10, decimal_places=2)`; donation min `Decimal("1.00")`; campaign goal min `Decimal("10.00")`. Money is quantized to cents (ROUND_HALF_UP) before storage.
- `Campaign.current_amount` is mutated ONLY inside `core.services.record_donation` using `F("current_amount") + amount`. No other module writes it.
- Simulated transaction ids: `f"SIM-{uuid.uuid4().hex}"`. `transaction_id` stays unique+nullable. The `PaymentProvider` abstraction must preserve this when a real gateway replaces it.
- Users referenced via `settings.AUTH_USER_MODEL`; env-dependent values via python-decouple in settings only.
- Owner-only views use `UserPassesTestMixin` with an explicit `handle_no_permission` (anonymous → login redirect; authenticated non-owner → 403).
- Additive model fields ONLY (new columns) unless a data migration is explicitly specified; never a lossy rename.
- Celery tasks accept **primary keys**, never ORM instances; must be idempotent. Tests run tasks eagerly via `.apply()`.
- UI: Tailwind v4 utilities only, no Bootstrap/CDN. Compiled `core/static/css/app.css` is committed; edit source `core/static/src/app.css`, rebuild with `npm run build`.
- A11y floor: labeled inputs, visible `:focus-visible`, `prefers-reduced-motion`, AA contrast. New image fields need appropriate `alt` handling.
- Tests live in `core/tests/`. Full suite gate: `uv run python manage.py test` → `OK`. Also `uv run python manage.py check --deploy` for the security block.
- Commits: concise imperative conventional subjects (`feat(phaseN): …`). Commit after every green suite.
- Branch: `infra` (all v2 work lands here until merged).
- Media is stored locally under `MEDIA_ROOT` and served by the **host** Nginx; no S3.

---

## Phase 1 — Foundation & infrastructure hardening (DONE)

Goal: unblock all downstream phases (media, background jobs, host-Nginx static/media serving).

- [x] Phase 0 — Reconcile doc/code drift: `AGENTS.md` DB engine claim (now Postgres/5432), install tooling (uv), CI note.
- [x] Media settings: `MEDIA_URL="media/"`, `MEDIA_ROOT=BASE_DIR/"media"` in `odp/settings.py`.
- [x] Host-level Nginx + media: `infra/nginx/odp.conf` (reverse proxy `/` → gunicorn, serve `/static/` + `/media/`), `infra/scripts/deploy.sh`, `infra/docker/.gitkeep`.
- [x] Compose: bind Gunicorn to loopback (`127.0.0.1:${WEB_PORT}`); host bind-mounts `${HOST_STATIC_DIR}`/`${HOST_MEDIA_DIR}`; add `redis`, `worker`, `beat` services.
- [x] Celery foundation: deps (`celery[redis]`, `redis`), `odp/celery.py`, `odp/__init__.py` imports `celery_app`, `core/tasks.py` (`ping`), settings (`CELERY_*`, `EMAIL_*` with file backend default).
- [x] `entrypoint.py` command-aware dispatch: `celery` arg → run celery (no collectstatic), else web startup (migrate + collectstatic + seed + gunicorn); create media/static dirs.
- [x] `BaseModel(created_at, updated_at)`; `Campaign` inherits it (migration `0003_campaign_updated_at_alter_campaign_created_at`). `Donation` intentionally keeps `donated_at` (timeline semantics; no lossy rename).
- [x] `.env.example`, `.gitignore` (`media/`), `AGENTS.md`, `README.md` updated for media/Celery/email/Nginx/uv.

**Verification (done):** `manage.py check` clean; full suite **81 OK** (79 + 2 task tests); Celery `ping` returns `pong:hello` via `.apply()`.

---

## Phase 2 — Creator features (updates/photos)

Goal: let creators post public updates/milestones and attach a real cover image.

### 2.1 `CampaignUpdate` model
- [x] New model in `core/models.py`: FK → `Campaign` (`related_name="updates"`, CASCADE), `title` (CharField 200), `body` (TextField), optional `image` (ImageField, blank/null, upload_to `updates/`), `is_pinned` (BooleanField default False), inherits `BaseModel` (`created_at`/`updated_at`).
- [x] `Meta.ordering = ["-is_pinned", "-created_at"]`, `__str__`.
- [x] Migration (additive) + `core/admin.py` registration (list_display, list_filter campaign, search title/body).
- [x] Tests in `core/tests/test_views_updates.py`: creation, ordering, image blank default.

### 2.2 Campaign cover image
- [x] Add optional `Campaign.cover_image` (ImageField, blank/null, upload_to `covers/`).
- [x] Template: `campaign_detail.html` + `_campaign_card.html` render `cover_image` when present, else fall back to `{% cover_art %}` gradient.
- [x] Migration + admin `prepopulated` untouched; add `cover_image` to admin fields.
- [ ] Tests: cover image shows vs gradient fallback.

### 2.3 Update CRUD (owner-guarded)
- [x] `CampaignUpdateCreateView`, `UpdateView`, `DeleteView` (LoginRequired + `OwnerOrDeniedMixin`; `handle_no_permission` pattern).
- [x] Routes (before `<slug>` detail): `campaigns/<slug>/updates/new/`, `…/updates/<pk>/edit/`, `…/updates/<pk>/delete/`.
- [x] Public timeline on `campaign_detail.html` (capped list) + "Post update" button for owner.
- [x] Templates: `core/campaignupdate_form.html`, `core/campaignupdate_confirm_delete.html`; `enctype="multipart/form-data"` on forms with images.
- [~] Tests: owner can CRUD; non-owner 403; anonymous redirect; image upload writes to MEDIA_ROOT (image-upload case not yet asserted).

### 2.4 PaymentProvider seam (folded into Phase 2)
- [x] `core/payments.py`: `PaymentProvider` protocol + `SimulatedProvider` (`SIM-<uuid4 hex>`), selected via `PAYMENT_PROVIDER` setting.
- [x] `record_donation` calls the configured provider via `get_provider()`.
- [x] Tests in `core/tests/test_payments.py`: default simulated, `SIM-` prefix, unknown provider raises.

**Verification:** `makemigrations`, migrate on SQLite, full suite green, manual owner flow with an image.

---

## Phase 3 — User accounts & profiles

Goal: richer identities, verified emails, password reset, donation export, saved campaigns.

### 3.1 `Profile`
- [ ] `Profile` model: `OneToOneField(AUTH_USER_MODEL, related_name="profile", CASCADE)`, `display_name`, `bio` (TextField blank), `avatar` (ImageField blank/null, upload_to `avatars/`), `timezone` (CharField default UTC), `email_verified` (BooleanField default False), `receives_email_updates` (BooleanField default True), inherits `BaseModel`.
- [ ] Signal `post_save` (or `Profile` creation in signup view) to autocreate profile for new users; auto-create/backfill for existing users in a data migration or management command.
- [ ] `ProfileView` + `ProfileUpdateView` (owner-only via UserPassesTestMixin), avatar upload → MEDIA_ROOT; template `core/profile.html`, `core/profile_form.html`.
- [ ] Admin registration.
- [ ] Tests: autocreation, owner-only edit, avatar upload, bio/display saved.

### 3.2 Email verification
- [ ] `EmailVerificationToken` model (OneToOne user, token, created_at, expiry), or utils using signed tokens.
- [ ] Send verification email on signup (via email module / Celery task from Phase 4); verify route `/accounts/verify/<token>/`; mark `email_verified`; resend endpoint with cooldown; expiry handling.
- [ ] Tests: valid token verifies, invalid/expired token rejected, resend.

### 3.3 Password reset
- [ ] Custom `PasswordResetForm`/templates replacing stock `auth.urls` defaults (template files under `templates/registration/`): `password_reset_form.html`, `password_reset_email.html`, `password_reset_done.html`, `password_reset_confirm.html`, `password_reset_complete.html`, styled with design system.
- [ ] Wire in `odp/urls.py` (custom `PasswordResetView`/`ConfirmView`).
- [ ] Tests: email generated, token flow completes.

### 3.4 Donation history export & saved campaigns
- [ ] CSV export on `MyDonationsView` (`?export=csv` or dedicated route `/my/donations/export/`) streaming rows (donated_at, campaign, amount, message, transaction_id).
- [ ] `SavedCampaign` model (FK user, FK campaign, unique_together, created_at) + `{% url %}` toggle + `SavedCampaignsView` dashboard + "save" button on campaign card/detail.
- [ ] Tests: CSV content/headers, toggle, saved list isolation, anonymous redirect.

**Verification:** full suite green; manual signup → verify → reset → export → save flows.

---

## Phase 4 — Email notifications

Goal: transactional + in-app notifications, using the Celery foundation.

### 4.1 Email module
- [ ] `core/emails.py` (or `core/services/email.py`): template-backed senders using `django.core.mail` (`send_mail`/`EmailMultiAlternatives`); config already in settings (`EMAIL_BACKEND` default file backend for dev/CI).
- [ ] Templates dir `core/templates/core/emails/`: donation receipt, verification, password reset (Phase 3), campaign funded, update posted, expiring soon.
- [ ] Tests: `assertNumEmails`/`assertStartsWith` using file or locmem backend; correct recipients & context.

### 4.2 Celery tasks (idempotent, PK-based)
- [ ] `record_donation` (or donate view) enqueues `send_donation_receipt.delay(donation_pk)` (skip if anonymous donor).
- [ ] Beat schedule (code-defined `CELERY_BEAT_SCHEDULE` in settings): `check_campaign_lifecycle` — daily scan for newly-funded campaigns (goal met) and expiring-soon (N days out) → send notifications (idempotent, e.g. guard on a `funded_notified`/`expiring_notified` BooleanField on Campaign to avoid duplicate sends).
- [ ] `notify_update_posted(update_pk)` → email+in-app to `Profile.receives_email_updates=True` followers (Phase 3.4 `SavedCampaign` users or explicit followers).

### 4.3 In-app notifications
- [ ] `Notification` model (recipient FK, verb, target Campaign/Update generic FK or nullable FKs, read BooleanField, created_at via BaseModel).
- [ ] `NotificationsView` (inbox, mark-read, mark-all-read) + unread badge in `base.html` nav for authenticated users.
- [ ] Tests: creation on triggers, mark-read, unread count, anonymous redirect.

**Verification:** full suite green; with file backend, run a donation + an expiring campaign and confirm `.eml` files with correct recipients/subject.

---

## Phase 5 — Analytics & reporting

Goal: creator dashboards for campaign performance.

- [ ] `CampaignStatsView` at `/my/campaigns/<slug>/stats/` (owner-guarded): daily/trend donations (annotate `TruncDate`), cumulative total, `avg`/`max` donation, top supporters (group by donor), donation counts by message presence.
- [ ] Use ORM aggregates/`Coalesce` (existing pattern); add DB indexes on hot query fields (`Donation.campaign`, `Donation.donated_at`) via migration if missing.
- [ ] CSV export of a campaign's donation detail for the owner.
- [ ] Template `core/stats.html` (charts optional — tabular + simple CSS bars; no chart lib unless already present).
- [ ] Tests: aggregate correctness, date-window filtering, ownership isolation, empty-campaign handling.

**Verification:** full suite green; manual per-campaign stats via demo user.

---

## Phase 6 — Public REST API (DRF)

Goal: versioned, documented REST API for campaigns and creators.

- [ ] Add `djangorestframework` (+ `drf-spectacular` for OpenAPI docs) to `pyproject.toml`; `INSTALLED_APPS` (`rest_framework`, `drf_spectacular`); `uv sync`.
- [ ] `/api/v1/` versioned router; root URLs: `campaigns` (list with search/filter/sort/pagination, retrieve), `campaigns/<slug>/updates/`, `campaigns/<slug>/donations/` (public, limited), `/api/v1/auth/` token endpoints.
- [ ] Serializers for Campaign (incl. `percentage_raised`, `days_remaining`, supporter_count), CampaignUpdate, Donation (amount, anonymous/username flag, message, donated_at).
- [ ] Creator/token-authenticated endpoints: create/update campaign, create update, upload cover/update image, own stats.
- [ ] Permissions: read-only anonymous; write requires token + owner; consistent with `handle_no_permission` semantics (401/403).
- [ ] `drf-spectacular` schema at `/api/v1/schema/` (+ optional Swagger UI).
- [ ] Tests: DRF `APIClient` — list/retrieve/filters, auth required for writes, owner-only, schema render works.

**Verification:** full suite green; run server, `curl /api/v1/schema/`, smoke a list + an authenticated create.

---

## Cross-cutting (all phases)

- Keep `record_donation` invariant; preserve `SIM-` tx convention via the `PaymentProvider` abstraction (see below).
- Each phase: additive migrations only, `manage.py check --deploy`, full suite `OK`, README/AGENTS updated, one conventional commit.

## Payment provider abstraction (from Phase 1/2 onward)

Per user decision, the real payment gateway is deferred. Implement a clean seam now so Phase 6 (and a future Stripe adapter) can plug in without changing callers:

- [ ] `core/services.py` or `core/payments.py`: `PaymentProvider` protocol/base with `charge(campaign, amount, donor) -> transaction_id`; `SimulatedProvider` returns `f"SIM-{uuid.uuid4().hex}"` (preserves current behavior); `record_donation` calls the configured provider.
- [ ] Provider selection via decouple `PAYMENT_PROVIDER` (default `simulated`) — no gateway keys required.
- [ ] Tests confirm the existing `SIM-` behavior is unchanged.

*(This is intentionally small and can be folded into Phase 2; note it in the phase commit.)*
