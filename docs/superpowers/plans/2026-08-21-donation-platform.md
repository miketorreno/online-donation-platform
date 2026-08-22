# Online Donation Platform — Full Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing skeleton (auth + Campaign/Donation models) into a complete donation platform — browse, detail, simulated checkout, campaign CRUD, dashboards — with a distinctive Tailwind CSS v4 UI.

**Architecture:** Single Django app (`core`) under config package `odp/`. Domain logic lives in `core/services.py` (`record_donation` is the only writer of `Campaign.current_amount`, using `F()` expressions). Presentation uses server-rendered Django templates styled by a committed Tailwind v4 build (npm `@tailwindcss/cli`, source CSS with `@theme` tokens). SQLite via `.env`.

**Tech Stack:** Python 3.12, Django 6.1, python-decouple, SQLite, Tailwind CSS v4 (@tailwindcss/cli), vanilla JS only (mobile nav toggle, preset amount buttons). Google Fonts via `<link>`.

**Spec:** The "Design Spec" section below is the binding design authority for this plan; tasks argue from it.

## Global Constraints

Every task implicitly includes these. Exact values verbatim:

- All Django commands: `venv/bin/python manage.py …` from repo root. DB is sqlite3 via `.env` (`DB_ENGINE=django.db.backends.sqlite3`). Never switch engines.
- Node/npm are nvm-managed (`node --version` must work before npm scripts; v24 present).
- Locked URL names (used in `{% url %}` and `reverse()` across tasks): `campaign-list`, `campaign-detail`, `campaign-create`, `campaign-edit`, `campaign-delete`, `campaign-donate`, `campaign-toggle-active`, `my-campaigns`, `my-donations`. Existing names `signup`, `login`, `logout` stay.
- In `odp/urls.py`: `campaign-create` pattern (`campaigns/new/`) MUST be registered before the `campaigns/<slug:slug>/…` family so `new` is never eaten as a slug.
- Money: `DecimalField(max_digits=10, decimal_places=2)`; donation min `Decimal("1.00")`; campaign goal min `Decimal("10.00")` (existing validators preserved).
- `Campaign.current_amount` is mutated ONLY inside `core/services.record_donation` using `F("current_amount") + amount`. No other module writes it.
- Simulated transaction ids: `f"SIM-{uuid.uuid4().hex}"`. `transaction_id` stays unique+nullable.
- Users referenced via `settings.AUTH_USER_MODEL`; env-dependent values via python-decouple in settings only.
- UI: Tailwind v4 utilities only — NO Bootstrap classes, no CDN links, no Bootstrap JS. Vanilla JS allowed only for mobile-nav toggle and preset-amount selection. Fonts: Bricolage Grotesque (display) + Public Sans (body) via Google Fonts `<link>` in `base.html`.
- Built CSS `core/static/css/app.css` IS committed (fresh clones work without node); rebuild with `npm run build`.
- Tests live in the `core/tests/` package (created in Task 1, replacing empty `core/tests.py`). Run full suite: `venv/bin/python manage.py test`. Output must be pristine (no warnings noise).
- Commits: concise imperative subject lines (repo style: "implement campaigns and donations; …"). Commit after every green test run.
- Branch: `feature/donation-platform-ui` (already created from `dev`).
- A11y floor on every template: labeled inputs, visible `:focus-visible` styles, `prefers-reduced-motion` respected (see Design Spec), AA contrast.

## Design Spec (binding)

Subject: grassroots fundraising. Audience: donors + creators. Page job: build trust fast, make giving effortless.

**Palette (define exactly these OKLCH tokens in `@theme`):**

```css
--color-porcelain: oklch(98.5% 0.004 160);   /* page bg */
--color-ink: oklch(22% 0.02 170);           /* primary text */
--color-pine-50: oklch(96% 0.015 158);
--color-pine-100: oklch(93% 0.02 158);
--color-pine-500: oklch(52% 0.09 156);
--color-pine-600: oklch(45% 0.09 158);
--color-pine-700: oklch(38% 0.09 160);      /* primary buttons */
--color-pine-900: oklch(28% 0.07 164);
--color-marigold-100: oklch(94% 0.05 85);
--color-marigold-300: oklch(86% 0.12 80);
--color-marigold-400: oklch(80% 0.15 75);   /* progress fills, highlights */
--color-marigold-500: oklch(74% 0.16 70);
--color-rose-500: oklch(58% 0.19 20);       /* destructive accents */
--color-rose-600: oklch(52% 0.19 18);
```

Plus fonts and animation token:

```css
--font-display: "Bricolage Grotesque", "Public Sans", system-ui, sans-serif;
--font-sans: "Public Sans", system-ui, sans-serif;
--animate-fill-up: fill-up 0.9s ease-out both;
```

with keyframes inside `@theme`:

```css
@keyframes fill-up { from { transform: scaleX(0); } to { transform: scaleX(1); } }
```

Base layer:

```css
@layer base {
  html { scroll-behavior: smooth; }
  body { @apply bg-porcelain text-ink font-sans antialiased; }
  :focus-visible { outline: 2px solid var(--color-pine-600); outline-offset: 2px; }
}
@media (prefers-reduced-motion: reduce) {
  *, ::before, ::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; scroll-behavior: auto !important; }
}
```

Component classes (in `@layer components`, reused across templates):

```css
.btn-primary { @apply inline-flex items-center justify-center gap-2 rounded-full bg-pine-700 px-6 py-3 font-semibold text-white transition hover:bg-pine-900 active:scale-[0.98]; }
.btn-ghost { @apply inline-flex items-center justify-center gap-2 rounded-full border border-pine-100 bg-white px-5 py-2.5 font-semibold text-pine-700 transition hover:border-pine-500 hover:text-pine-900; }
.btn-danger-ghost { @apply inline-flex items-center justify-center gap-2 rounded-full border border-rose-500/30 bg-white px-5 py-2.5 font-semibold text-rose-600 transition hover:bg-rose-500/10; }
.card { @apply rounded-3xl bg-white shadow-[0_1px_2px_rgba(24,58,48,0.06),0_12px_32px_-16px_rgba(24,58,48,0.18)]; }
.field-label { @apply block text-sm font-semibold mb-1.5; }
.field-input { @apply w-full rounded-xl border border-pine-100 bg-white px-4 py-3 text-ink placeholder:text-ink/35 focus:border-pine-500 focus:outline-none focus:ring-2 focus:ring-pine-500/30; }
.field-error { @apply mt-1.5 text-sm font-medium text-rose-600; }
.chip { @apply inline-flex items-center rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wide; }
.progress-rail { @apply h-2.5 w-full overflow-hidden rounded-full bg-pine-100; }
.progress-fill { @apply block h-full origin-left rounded-full bg-gradient-to-r from-marigold-400 to-marigold-500; animation: var(--animate-fill-up); }
```

**Type roles:** Display face (Bricolage Grotesque, weights 700–800, tight tracking) ONLY for brand wordmark, page headlines, and the oversized detail-page percentage. Everything else Public Sans (400/600/700); amounts always `tabular-nums`.

**Layout concepts:**
- Sticky translucent header: `sticky top-0 z-40 backdrop-blur bg-porcelain/85 border-b border-pine-100`. Brand "ODP" wordmark + marigold dot. Right: Explore link, Start a campaign btn-primary (sm), auth dropdown / Login+Sign up.
- Home: hero band (display headline "Fund what matters." + one-line subhead + inline search bar), toolbar row (category pills + sort select), 1/2/3-col card grid (gap-6), centered pagination.
- Campaign detail: two-column on lg — main col: cover banner (rounded-3xl, h-56 md:h-72, `{% cover_art %}` gradient, white category chip) then title, creator/date meta, description prose; below: "Supporters" wall (latest 10 donations). Sidebar (sticky top-24): donate card with big numbers (raised, %, days left), Give-now button, progress rail. **Signature element:** an oversized percentage figure (`font-display text-7xl md:text-8xl font-extrabold text-pine-700`) sits absolutely at the cover banner's bottom-left corner, overlapping its edge onto the page background, above a thin marigold underline sweep. Used ONLY here.
- Cards: cover strip h-36 with gradient + category chip overlay; body: title (2-line clamp, display font 600), progress rail, raised-of-goal row, meta row (days left · supporter count).
- Auth pages: centered `.card max-w-md`, stacked fields using `.field-*` recipes.
- Messages: fixed top-right stack of toast-style alerts (`success`→pine-700 bg, `error`→rose-600, `warning`→marigold-500, default→pine-900), auto-styled from `message.tags`.

**Generated cover art:** templatetag `{% cover_art campaign %}` returns an inline `style` string: linear-gradient over curated OKLCH pairs chosen by SHA-256 of `campaign.slug` (see Task 4 code — exact pairs verbatim).

**Copy voice:** plain active verbs, sentence case: "Give now", "Start a campaign", "Explore campaigns", "Supporters", "Raised", "Goal", "Days left". Empty states instruct: e.g. "No campaigns match your search. Try different keywords or clear filters."

---

### Task 1: Model extensions — slug, category, message + admin

**Files:**
- Modify: `core/models.py`
- Create: `core/migrations/0002_<auto>.py` (via makemigrations)
- Create: `core/tests/__init__.py` (empty), `core/tests/test_models.py`
- Delete: `core/tests.py`
- Modify: `core/admin.py`

**Interfaces (produced; later tasks rely on exact names):**
- `Campaign.slug: SlugField(unique=True)` — auto-generated in `save()` from title when blank.
- `Campaign.category: CharField(max_length=20)` with nested `class Category(models.TextChoices)` on `Campaign`: EMERGENCY="emergency", MEDICAL="medical", EDUCATION="education", ANIMALS="animals", ENVIRONMENT="environment", COMMUNITY="community", SPORTS="sports", ARTS="arts"; field default `Category.COMMUNITY`.
- `Campaign.get_absolute_url()` → `reverse("campaign-detail", kwargs={"slug": self.slug})`. Do NOT test it in this task — the URL name is registered in Task 4; Task 4's tests cover it.
- `Donation.message: TextField(blank=True)`.
- Admin: both models registered.

- [ ] **Step 1: Write failing tests** — create `core/tests/__init__.py` (empty) and `core/tests/test_models.py`; delete `core/tests.py`:

```python
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from core.models import Campaign, Donation


def make_user(username="creator"):
    return get_user_model().objects.create_user(username=username, password="test-pass-123")


def make_campaign(**overrides):
    defaults = dict(
        title="Clean Water Wells",
        description="Drilling wells.",
        goal_amount=Decimal("500.00"),
        end_date=timezone.now().date() + timedelta(days=30),
        creator=make_user(),
    )
    defaults.update(overrides)
    return Campaign.objects.create(**defaults)


class CampaignSlugTests(TestCase):
    def test_slug_generated_from_title(self):
        c = make_campaign()
        self.assertEqual(c.slug, "clean-water-wells")

    def test_slug_collision_gets_numeric_suffix(self):
        c1 = make_campaign()
        c2 = make_campaign(title="Clean Water Wells!", creator=make_user(username="other"))
        self.assertEqual(c1.slug, "clean-water-wells")
        self.assertEqual(c2.slug, "clean-water-wells-2")

    def test_explicit_slug_preserved(self):
        c = make_campaign()
        c.slug = "custom"
        c.save()
        c.refresh_from_db()
        self.assertEqual(c.slug, "custom")

    def test_category_default_and_choices(self):
        c = make_campaign()
        self.assertEqual(c.category, Campaign.Category.COMMUNITY)
        self.assertIn(("animals", "Animals"), Campaign.Category.choices)


class DonationModelTests(TestCase):
    def setUp(self):
        self.campaign = make_campaign()

    def test_message_blank_allowed(self):
        d = Donation.objects.create(
            campaign=self.campaign,
            amount=Decimal("25.00"),
            donor=None,
            message="",
        )
        self.assertEqual(d.message, "")
        self.assertIsNone(d.donor)

    def test_str_anonymous(self):
        d = Donation.objects.create(campaign=self.campaign, amount=Decimal("5.00"))
        self.assertIn("Anonymous", str(d))
```

- [ ] **Step 2: Run to verify failure** — `venv/bin/python manage.py test core.tests.test_models -v 1` → FAIL (`AttributeError`/field errors: no `slug`/`category`/`message`).
- [ ] **Step 3: Implement** in `core/models.py`: add imports `from django.urls import reverse`, `from django.utils.text import slugify`; add `Category` TextChoices + fields; `save()` override + `_generate_unique_slug()` (base = `slugify(self.title)[:200] or "campaign"`; loop suffix `-2`, `-3`… checking `Campaign.objects.filter(slug=...).exclude(pk=self.pk)`); add `message` to Donation. Generate migration: `venv/bin/python manage.py makemigrations core` (name auto; simple AddField migrations — no data migration needed, no database exists yet).
- [ ] **Step 4: Register admin** (`core/admin.py`):

```python
from django.contrib import admin
from .models import Campaign, Donation


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("title", "creator", "category", "goal_amount", "current_amount", "end_date", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("__str__", "amount", "campaign", "donor", "donated_at")
    list_filter = ("donated_at",)
    search_fields = ("transaction_id", "donor__username")
```

- [ ] **Step 5: Run suite** — `venv/bin/python manage.py test` → ALL PASS, pristine output. Also `venv/bin/python manage.py makemigrations core --check --dry-run` → no changes.
- [ ] **Step 6: Commit** — `git add -A && git commit -m "add slug, category, message fields; register admin"`

---

### Task 2: Tailwind v4 pipeline, design tokens, base layout, auth pages

**Files:**
- Create: `package.json`, `core/static/src/app.css`, `core/static/css/app.css` (built output, committed)
- Rewrite: `templates/registration/base.html`
- Rewrite: `templates/registration/login.html`
- Rewrite: `core/templates/core/signup.html`
- Create: `core/tests/test_ui_base.py`

**Interfaces (consumes/produces):**
- Consumes: URL names `login`, `logout`, `signup` (exist today).
- Produces: `templates/registration/base.html` with blocks `title`, `content`; component classes `.btn-primary .btn-ghost .btn-danger-ghost .card .field-label .field-input .field-error .chip .progress-rail .progress-fill`; `{% static 'css/app.css' %}` linked; toast-style messages block; mobile-nav toggle script. All later templates extend `"base.html"` (project-level path works because `templates/` is in DIRS).
- Produces: `package.json` scripts `build` / `watch` (tailwindcss CLI).

- [ ] **Step 1: Failing test** — `core/tests/test_ui_base.py`:

```python
from django.test import TestCase


class BaseUITests(TestCase):
    def test_login_page_uses_new_shell(self):
        resp = self.client.get("/accounts/login/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "css/app.css")
        self.assertContains(resp, "fonts.googleapis.com")
        self.assertContains(resp, "skip-link")
        self.assertNotContains(resp, "bootstrap")

    def test_signup_page_renders_in_card(self):
        resp = self.client.get("/signup/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Start your ODP account")
```

Run: `venv/bin/python manage.py test core.tests.test_ui_base -v 1` → FAIL (no app.css; bootstrap still present).

- [ ] **Step 2: Install toolchain** — verify `node --version`; create `package.json`:

```json
{
  "name": "odp-frontend",
  "private": true,
  "scripts": {
    "build": "tailwindcss -i core/static/src/app.css -o core/static/css/app.css --minify",
    "watch": "tailwindcss -i core/static/src/app.css -o core/static/css/app.css --watch"
  },
  "devDependencies": {
    "@tailwindcss/cli": "^4.1.13",
    "tailwindcss": "^4.1.13"
  }
}
```

Run `npm install` (creates `package-lock.json`; commit it). Add nothing to `.gitignore` for `core/static/css/app.css` — built output is committed.

- [ ] **Step 3: Write `core/static/src/app.css`** — exactly per the Design Spec: `@import "tailwindcss";` then the `@theme` block with ALL palette/font/animate tokens and `fill-up` keyframes, the `@layer base` rules, the reduced-motion media query, and the `@layer components` classes (.btn-primary, .btn-ghost, .btn-danger-ghost, .card, .field-label, .field-input, .field-error, .chip, .progress-rail, .progress-fill) — verbatim from the Design Spec section. Then build: `npm run build` → confirm `core/static/css/app.css` exists and contains e.g. `.btn-primary`.
- [ ] **Step 4: Rewrite `templates/registration/base.html`** — remove every Bootstrap reference (links, integrity attrs, classes, JS). Structure: skip-link (`<a href="#main-content" class="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-3 …">Skip to content</a>`), sticky translucent header per Design Spec with brand (`ODP` in `font-display` + marigold dot span), auth area (authenticated → dropdown "Hi, {{ user.username }}" with divider + Logout `{% url 'logout' %}` as POST form per Django 5+ logout requirement; anonymous → Login link + Sign up `.btn-primary`), hamburger button `#nav-toggle` toggling a `#mobile-menu` panel (inline `<script>`: `document.getElementById('nav-toggle')?.addEventListener('click', () => document.getElementById('mobile-menu')?.classList.toggle('hidden'))`). NAV LINK RULE: ship the header with brand + auth area ONLY — no Explore/Start-a-campaign/dashboard links yet; Task 5 adds Explore, Task 6 adds Start-a-campaign and the dashboard dropdown items (their URL names don't resolve until those tasks exist).
  `<main id="main-content">` wraps `{% block content %}{% endblock %}`; messages toasts per Design Spec (loop `messages`, map `message.tags`: success→pine-700 bg, error→rose-600, warning→marigold-500, default→pine-900, all white text); footer (© 2026 ODP, muted). `<title>{% block title %}ODP — Fund what matters{% endblock %}</title>`, Google Fonts `<link>` (preconnect ×2 + css2 families `Bricolage+Grotesque:opsz,wght@12..96,400..800` and `Public+Sans:wght@400;600;700`, display=swap), `{% load static %}` + `<link rel="stylesheet" href="{% static 'css/app.css' %}">`.
- [ ] **Step 5: Styled forms + login/signup templates** — create `core/forms.py`:

```python
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "field-input")


class StyledUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "field-input")
```

Update `core/views.py`: `SignUpView.form_class = StyledUserCreationForm`. Update `odp/urls.py`: add BEFORE the existing include so it wins first-match: `path("accounts/login/", LoginView.as_view(template_name="registration/login.html", authentication_form=StyledAuthenticationForm, redirect_authenticated_user=True), name="login")` — keep `path("accounts/", include("django.contrib.auth.urls"))` after it. Import from core.forms.
Rewrite both templates extending `base.html`: centered `.card max-w-md mx-auto my-10 p-8` with display-font headline (`font-display text-3xl font-bold` — "Welcome back" / "Start your ODP account"), then `{{ form.non_field_errors }}` styled `.field-error`, then loop `form.visible_fields` rendering per Design Spec field recipe: `<label class="field-label" for="{{ field.id_for_label }}">{{ field.label }}</label> {{ field }} {{ field.errors }}` plus for signup password fields render `field.help_text` items as `<p class="text-xs text-ink/60 mt-1">{{ help }}</p>`. Submit `.btn-primary w-full` ("Log in" / "Create account"); under each form a muted swap link to the other page.
- [ ] **Step 6: Verify** — `npm run build`; `venv/bin/python manage.py test core.tests.test_ui_base -v 1` PASS; full `venv/bin/python manage.py test` PASS.
- [ ] **Step 7: Commit** — stage ONLY these paths: `package.json package-lock.json core/static/src/app.css core/static/css/app.css templates/ core/templates/core/signup.html core/tests/test_ui_base.py core/forms.py core/views.py odp/urls.py` — `git commit -m "replace Bootstrap with Tailwind v4 design system; restyle auth pages"`

---

### Task 3: Donation domain service

**Files:**
- Create: `core/services.py`
- Create: `core/tests/test_services.py`

**Interfaces:**
- Consumes: `Campaign` (is_active, end_date, current_amount), `Donation` (Task 1).
- Produces (locked signatures):

```python
class DonationError(Exception): ...

def generate_transaction_id() -> str  # "SIM-" + uuid4().hex
def record_donation(*, campaign: Campaign, amount: Decimal, donor=None, message: str = "") -> Donation
```

Behavior: validate `amount >= Decimal("1.00")` else `DonationError("Minimum donation is $1.00.")`; reject when `not campaign.is_active` or `campaign.end_date < timezone.now().date()` with `DonationError("This campaign is not accepting donations.")`; inside `transaction.atomic`: create `Donation(campaign, amount quantized to 0.01, donor, message=(message or "").strip(), transaction_id=generate_transaction_id())` then `Campaign.objects.filter(pk=campaign.pk).update(current_amount=F("current_amount") + amount)` and `campaign.refresh_from_db(fields=["current_amount"])`; return donation.

- [ ] **Step 1: Failing tests** — `core/tests/test_services.py` (reuse `make_campaign` helper by importing from `core.tests.test_models`):

```python
from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone

from core.models import Campaign
from core.services import DonationError, record_donation
from core.tests.test_models import make_campaign


class RecordDonationTests(TestCase):
    def setUp(self):
        self.campaign = make_campaign(goal_amount=Decimal("1000.00"))

    def test_successful_donation_updates_total_and_returns_record(self):
        d = record_donation(campaign=self.campaign, amount=Decimal("25.00"))
        self.assertEqual(d.amount, Decimal("25.00"))
        self.assertTrue(d.transaction_id.startswith("SIM-"))
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.current_amount, Decimal("25.00"))

    def test_two_donations_accumulate(self):
        record_donation(campaign=self.campaign, amount=Decimal("10.00"))
        record_donation(campaign=self.campaign, amount=Decimal("15.50"))
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.current_amount, Decimal("25.50"))

    def test_anonymous_donor_allowed(self):
        d = record_donation(campaign=self.campaign, amount=Decimal("5.00"))
        self.assertIsNone(d.donor)

    def test_message_is_stripped(self):
        d = record_donation(campaign=self.campaign, amount=Decimal("5.00"), message="  go team  ")
        self.assertEqual(d.message, "go team")

    def test_minimum_amount_enforced(self):
        with self.assertRaises(DonationError):
            record_donation(campaign=self.campaign, amount=Decimal("0.99"))
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.current_amount, Decimal("0"))

    def test_inactive_campaign_rejected(self):
        self.campaign.is_active = False
        self.campaign.save()
        with self.assertRaises(DonationError):
            record_donation(campaign=self.campaign, amount=Decimal("10.00"))

    def test_ended_campaign_rejected(self):
        self.campaign.end_date = timezone.now().date() - timedelta(days=1)
        self.campaign.save()
        with self.assertRaises(DonationError):
            record_donation(campaign=self.campaign, amount=Decimal("10.00"))

    def test_transaction_ids_unique(self):
        a = record_donation(campaign=self.campaign, amount=Decimal("5.00"))
        b = record_donation(campaign=self.campaign, amount=Decimal("5.00"))
        self.assertNotEqual(a.transaction_id, b.transaction_id)
```

Run focused → FAIL (module missing). Implement `core/services.py` per Interfaces. Re-run → PASS; full suite PASS.
- [ ] **Step 2: Commit** — `git commit -am "add record_donation service with atomic totals"`

---

### Task 4: Campaign detail page + donate flow + cover art

**Files:**
- Create: `core/templatetags/__init__.py`, `core/templatetags/odp_extras.py`
- Create: `core/templates/core/campaign_detail.html`, `core/templates/core/donate.html`, `core/templates/core/includes/_cover_banner.html`, `core/templates/core/includes/_supporters.html`
- Modify: `core/forms.py` (append `DonateForm`), `core/views.py` (append views), `core/urls.py`
- Create: `core/tests/test_templatetags.py`, `core/tests/test_views_donate.py`, `core/tests/test_views_detail.py`

**Interfaces:**
- Consumes: `record_donation`/`DonationError` (Task 3); `Campaign.slug`, `.percentage_raised`, `.days_remaining`, `Category.choices` (Task 1); `.card/.btn-primary/...` (Task 2).
- Produces: URL names `campaign-detail` (`campaigns/<slug:slug>/`), `campaign-donate` (`campaigns/<slug:slug>/donate/`); templatetags `{% cover_art campaign %}` (returns style string) and `usd` filter (`"$1,234.50"`); `DonateForm` fields: `amount` (DecimalField min 1.00, max_digits 10, dp 2, initial `Decimal("25.00")`), `message` (CharField required=False, max_length=280, Textarea rows=3); preset buttons in template are labels-for-radio-free JS: four buttons ($10/$25/$50/$100) setting `#id_amount` value (vanilla, progressive enhancement — input remains usable without JS).

Cover art gradients (VERBATIM pairs — order matters, index = hash % len):

```python
GRADIENTS = [
    ("oklch(42% 0.11 155)", "oklch(65% 0.13 170)"),
    ("oklch(38% 0.10 250)", "oklch(55% 0.14 230)"),
    ("oklch(40% 0.12 320)", "oklch(60% 0.15 340)"),
    ("oklch(45% 0.12 60)", "oklch(70% 0.14 80)"),
    ("oklch(35% 0.09 190)", "oklch(58% 0.11 205)"),
    ("oklch(42% 0.13 140)", "oklch(66% 0.14 120)"),
]

@register.simple_tag
def cover_art(campaign):
    digest = hashlib.sha256(campaign.slug.encode("utf-8")).hexdigest()
    h = int(digest, 16)
    c1, c2 = GRADIENTS[h % len(GRADIENTS)]
    angle = 100 + (h // 7) % 80
    return f"background-image:linear-gradient({angle}deg,{c1},{c2})"

@register.filter
def usd(value):
    try:
        return f"${Decimal(value):,.2f}"
    except Exception:
        return value
```

Views:

```python
class CampaignDetailView(DetailView):
    model = Campaign
    context_object_name = "campaign"
    template_name = "core/campaign_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        campaign = self.object
        ctx["recent_donations"] = campaign.donations.select_related("donor")[:10]
        ctx["supporter_count"] = campaign.donations.count()
        ctx["can_receive"] = campaign.is_active and campaign.days_remaining > 0
        return ctx


class DonateView(FormView):
    form_class = DonateForm
    template_name = "core/donate.html"

    def dispatch(self, request, *args, **kwargs):
        self.campaign = get_object_or_404(Campaign, slug=self.kwargs["slug"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["campaign"] = self.campaign
        return ctx

    def get(self, request, *args, **kwargs):
        if not (self.campaign.is_active and self.campaign.days_remaining > 0):
            messages.error(request, "This campaign is not accepting donations.")
            return redirect("campaign-detail", slug=self.campaign.slug)
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        donor = self.request.user if self.request.user.is_authenticated else None
        try:
            record_donation(
                campaign=self.campaign,
                amount=form.cleaned_data["amount"],
                donor=donor,
                message=form.cleaned_data.get("message", ""),
            )
        except DonationError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        amount = form.cleaned_data["amount"]
        messages.success(self.request, f'Thank you! Your ${amount:,.2f} gift to "{self.campaign.title}" is confirmed.')
        return redirect("campaign-detail", slug=self.campaign.slug)
```

URLs appended (order irrelevant here; `new/` precedence rule applies in Task 6):

```python
path("campaigns/<slug:slug>/", CampaignDetailView.as_view(), name="campaign-detail"),
path("campaigns/<slug:slug>/donate/", DonateView.as_view(), name="campaign-donate"),
```

Templates per Design Spec layout concepts. `campaign_detail.html` MUST include the signature element: cover banner (`_cover_banner.html` partial: div with `{% cover_art campaign %}` style, rounded-3xl, h-56 md:h-72, category `.chip` white/70 backdrop) and immediately after it the overlapping figure:

```html
<div class="relative -mt-10 ml-4 md:ml-8 inline-block">
  <span class="font-display text-7xl md:text-8xl font-extrabold tracking-tight text-pine-700 tabular-nums">
    {{ campaign.percentage_raised }}<span class="text-4xl md:text-5xl align-top">%</span>
  </span>
  <div class="h-1.5 w-24 rounded-full bg-gradient-to-r from-marigold-400 to-marigold-500"></div>
</div>
```

Donate CTA in sticky sidebar card: if `can_receive` → `.btn-primary w-full` "Give now" linking to `campaign-donate`; else rose-tinted chip "This campaign has ended". Sidebar shows Raised (`{{ campaign.current_amount|usd }}`), Goal, Days left, supporter count; `.progress-rail/.progress-fill` with width `style="width: {{ campaign.percentage_raised }}%"`. Supporters wall (`_supporters.html`): latest 10 rows (name = `{{ d.donor.username|default:"Anonymous" }}`, `timesince d.donated_at` ago, optional quoted message, `d.amount|usd`); empty state text "Be the first to support this campaign."
`donate.html`: two-column lg (summary card: cover mini-banner, title, raised/goal, rail; form card: headline "Give now", preset buttons row, amount input `.field-input`, message textarea, submit `.btn-primary` "Complete gift", microcopy "Demo checkout — no real payment is processed."), hidden CSRF, non-field errors as `.field-error`.

- [ ] **Step 1: Failing tests** — three test modules. Key assertions (write full TestCase classes):

test_views_detail.py: `setUp` creates user+campaign; `test_detail_renders_title_progress_and_supporters` (GET `/{slug}/` → 200, contains title, `$500.00`, "Give now"); `test_signature_percentage_present` (contains `%` figure container class `text-7xl`); `test_supporters_wall_lists_recent` (create 12 donations via `record_donation`, assert first-page shows most recent donor username and count capped at 10 rows — count occurrences of a stable marker like `data-supporter-row` == 10); `test_empty_wall_message` (contains "Be the first"); `test_ended_campaign_shows_closed_chip` (end_date yesterday → contains "has ended", NOT "Give now"); `test_unknown_slug_404`; `test_get_absolute_url` (`self.assertEqual(c.get_absolute_url(), f"/campaigns/{c.slug}/")`).
test_views_donate.py: `test_donate_page_get_renders` (200, contains `id="id_amount"`, "Complete gift"); `test_post_valid_anonymous_creates_donation` (POST amount 40.00 → 302 to detail; follow → contains "Thank you! Your $40.00 gift"; DB: donation exists, campaign total updated, donor None); `test_post_valid_authed_attaches_donor` (client.force_login(user)); `test_post_invalid_negative_shows_error` (amount 0.50 → 200, contains "Minimum donation"); `test_post_to_ended_redirects_with_error` (ended campaign POST → follows to detail, message present, no donation created); `test_preset_buttons_present` (contains "$25").
test_templatetags.py: deterministic checks — `cover_art(make_campaign(slug="abc"))` starts with `background-image:linear-gradient(`, same slug twice → identical string, two known slugs map to expected pair indices (compute expected in test with same hashlib code — acceptable duplication for pinning); `usd(Decimal("1234.5")) == "$1,234.50"`; `usd("x") == "x"`.
- [ ] **Step 2:** Run focused → FAIL; implement everything; run again → PASS; full suite PASS; `npm run build` (templates changed → new utility classes must compile; confirm build exits 0 and output grows).
- [ ] **Step 3: Commit** — `git commit -am "add campaign detail, supporters wall, simulated give flow"`

---

### Task 5: Browse & discovery (home page)

**Files:**
- Modify: `core/views.py` (append `CampaignListView`), `core/urls.py` (prepend list route), `templates/registration/base.html` (add Explore nav link)
- Create: `core/templates/core/home.html`, `core/templates/core/includes/_campaign_card.html`, `core/templates/core/includes/_pagination.html`
- Create: `core/tests/test_views_browse.py`

**Interfaces:**
- Consumes: `campaign-detail` (cards link out), templatetags, component classes.
- Produces: URL name `campaign-list` at `""` (MUST be first entry in `core/urls.py` urlpatterns). ListView contract: `model=Campaign`, `paginate_by=9`, `context_object_name="campaigns"`; query params: `q` (icontains across title+description), `category` (validated against `Campaign.Category.values`, ignored if unknown), `sort` in `{"newest": "-created_at", "funded": "-current_amount", "closing": "end_date"}` (default `newest`); base filter `is_active=True`. Context extras: `q`, `active_category`, `active_sort`, `categories=Campaign.Category.choices`.

View sketch (implement fully):

```python
SORTS = {"newest": "-created_at", "funded": "-current_amount", "closing": "end_date"}

class CampaignListView(ListView):
    model = Campaign
    paginate_by = 9
    context_object_name = "campaigns"
    template_name = "core/home.html"

    def get_queryset(self):
        qs = Campaign.objects.filter(is_active=True)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        category = self.request.GET.get("category", "")
        if category in Campaign.Category.values:
            qs = qs.filter(category=category)
        sort = self.request.GET.get("sort", "newest")
        return qs.order_by(SORTS.get(sort, SORTS["newest"]))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(q=self.request.GET.get("q", ""), active_category=self.request.GET.get("category", ""),
                   active_sort=self.request.GET.get("sort", "newest"), categories=Campaign.Category.choices)
        return ctx
```

`home.html`: hero band (display headline "Fund what matters.", subhead "Back community projects...", search `<form method="get">` with `q` input `.field-input` + submit `.btn-primary` "Search"); toolbar: category pill links (All + each choice; `href="?{% qt params %}"` — implement with Django's built-in `{% querystring category=value %}` tag, Django ≥5.1, keeping q/sort; active pill gets `bg-pine-700 text-white` else `.btn-ghost`), sort `<select name="sort">` with onchange submit (vanilla `this.form.submit()`); grid `grid gap-6 sm:grid-cols-2 lg:grid-cols-3` looping `{% include "core/includes/_campaign_card.html" with campaign=campaign %}`; empty state card when no results (copy from Global Constraints example); `_pagination.html`: prev/next + page numbers using `{% querystring page=n %}`, hide when `page_obj.paginator.num_pages <= 1`.
`_campaign_card.html`: `<a>` wrapping whole card to `{% url 'campaign-detail' campaign.slug %}`; cover strip h-36 (`{% cover_art %}`, category chip, "Ended" chip when `days_remaining == 0`); body: title clamp-2 `font-display font-semibold`, progress rail + fill (width percentage), row `{{ current_amount|usd }} raised` + `of {{ goal_amount|usd }}`, meta row `days left|Ended · N supporters`.
base.html: insert Explore link (`{% url 'campaign-list' %}`) in desktop nav + mobile menu.

- [ ] **Step 1: Failing tests** — `test_views_browse.py`: seed 12 campaigns (mix categories, one inactive, one with distinct funding totals via direct `Campaign.objects.create(current_amount=...)`); assert: root 200 + uses template `core/home.html`; only active listed (count marker `data-campaign-card` == 9 page 1, `?page=2` shows remaining); `?q=wells` narrows to matching titles only; `?category=animals` filters; unknown category param ignored; `?sort=funded` orders by current_amount desc (first card title matches richest); `?sort=bogus` falls back to newest (first card == latest created); empty-state copy appears when q matches nothing; pagination absent when ≤9 results; nav contains "Explore".
- [ ] **Step 2:** RED → implement → GREEN → full suite → `npm run build`.
- [ ] **Step 3: Commit** — `git commit -am "add browsable campaign home with search, filters, pagination"`

---

### Task 6: Campaign management + personal dashboards

**Files:**
- Modify: `core/forms.py` (append `CampaignForm`), `core/views.py`, `core/urls.py`, `templates/registration/base.html` (nav links + dropdown items)
- Create: `core/templates/core/campaign_form.html`, `core/templates/core/campaign_confirm_delete.html`, `core/templates/core/my_campaigns.html`, `core/templates/core/my_donations.html`
- Create: `core/tests/test_views_manage.py`, `core/tests/test_views_dashboards.py`

**Interfaces:**
- Consumes: everything prior; `LOGIN_URL` default `/accounts/login/`.
- Produces: URL names `campaign-create` (`campaigns/new/`, registered BEFORE `<slug:slug>` routes), `campaign-edit` (`campaigns/<slug:slug>/edit/`), `campaign-delete` (`campaigns/<slug:slug>/delete/`), `campaign-toggle-active` (`campaigns/<slug:slug>/toggle-active/`), `my-campaigns` (`my/campaigns/`), `my-donations` (`my/donations/`); `CampaignForm(ModelForm)` fields `["title", "description", "category", "goal_amount", "end_date"]`, widgets: TextInput `.field-input`-classed attrs, Textarea rows=6, Select, DateInput `type="date"`; help_texts short.

Views (exact contracts):
- `CampaignCreateView(LoginRequiredMixin, CreateView)`: model Campaign, form_class CampaignForm; `form_valid` sets `form.instance.creator = self.request.user` then super(); success → `get_absolute_url()` (detail exists since Task 4) + `messages.success(self.request, "Campaign created.")`.
- `CampaignUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView)`: same form; `test_func`: `self.get_object().creator_id == self.request.user.id`; raise_exception=True (403 for non-owners); success message "Campaign updated."
- `CampaignDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView)`: owner-only 403; `success_url = reverse_lazy("my-campaigns")`; message "Campaign deleted."; template warns "Deleting removes its donation records too." (FK CASCADE).
- `toggle_active(request, slug)` function view: `@require_POST` (GET → 405), `@login_required`; fetch campaign or 404; 403 if not owner; flip `is_active`, save, message "Campaign paused." / "Campaign resumed."; redirect to detail.
- `MyCampaignsView(LoginRequiredMixin, ListView)`: own campaigns `-created_at`; template lists each with stats: raised `aggregate Sum("donations__amount")` (coalesce None→0), supporter count, percentage, status chip (Active/Paused/Ended by is_active+days_remaining), Edit/Delete/Pause-Resume buttons; header CTA "Start a campaign".
- `MyDonationsView(LoginRequiredMixin, ListView)`: `request.user.donations.select_related("campaign")`; total given via aggregate; rows: campaign title (link), amount, date, message snippet.
- base.html additions: desktop nav gains "Start a campaign" `.btn-primary` → `campaign-create`; authenticated dropdown gains My campaigns / My donations items (the ones omitted in Task 2).

- [ ] **Step 1: Failing tests.** test_views_manage.py (two users A/B): anonymous GET create → redirect to `/accounts/login/?next=/campaigns/new/`; logged-in GET 200 renders form; valid POST creates campaign with creator=A, slug auto, redirects to detail; edit by owner 200 + POST changes title and keeps slug stable (assert slug unchanged after title change — slug only generated when blank); edit by B → 403; delete by owner GET shows confirm + POST removes campaign AND its donations (create donation first); delete by B → 403; toggle GET → 405; toggle POST by owner flips is_active + redirects; toggle POST by B → 403. test_views_dashboards.py: my-campaigns anonymous → login redirect; A sees only A's campaigns with correct raised sums (use record_donation); my-donations lists A's donations with campaign links and total (e.g. 10+15=25 shown as "$25.00"); B's dashboard doesn't contain A's items.
- [ ] **Step 2:** RED → implement → GREEN → full suite → `npm run build`.
- [ ] **Step 3: Commit** — `git commit -am "add campaign CRUD, pause/resume, and personal dashboards"`

---

### Task 7: Seed demo data command

**Files:**
- Create: `core/management/__init__.py`, `core/management/commands/__init__.py`, `core/management/commands/seed_demo.py`
- Create: `core/tests/test_seed.py`

**Interfaces:**
- Consumes: `record_donation` (Task 3), `Campaign.Category` (Task 1).
- Produces: management command `seed_demo` with optional `--force` (delete existing demo-user campaigns first, then reseed). Idempotent WITHOUT force: `get_or_create` by slug; donations inserted only at creation time.

Command spec (verbatim data):

```python
CAMPAIGNS = [
    # slug, title, category, goal, days_offset(end), donations_count
    ("rebuild-maple-street-community-garden", "Rebuild Maple Street Community Garden", "community", "5000.00", 45, 12),
    ("emergency-vet-care-for-rescue-puppies", "Emergency Vet Care for Rescue Puppies", "animals", "2500.00", 20, 9),
    ("laptops-for-linwood-middle-school", "Laptops for Linwood Middle School", "education", "8000.00", 60, 15),
    ("wildfire-relief-for-cedar-county", "Wildfire Relief for Cedar County", "emergency", "15000.00", 30, 34),
    ("riverside-trail-restoration", "Riverside Trail Restoration", "environment", "6000.00", -5, 11),
    ("youth-soccer-scholarships", "Youth Soccer Scholarships", "sports", "4000.00", 90, 5),
    ("community-mural-project", "Community Mural Project", "arts", "3000.00", 25, 8),
    ("free-dental-clinic-days", "Free Dental Clinic Days", "medical", "12000.00", 120, 19),
]
AMOUNTS = ["5.00", "10.00", "20.00", "25.00", "50.00", "75.00", "100.00", "250.00"]
MESSAGES = ["Happy to help!", "Great cause.", "", "", "For the kids.", "Keep going!", "", "In memory of Nan."]
```

Demo user: username `demo`, email `demo@example.com`, password `demo-pass-1234` (set only when created). Determinism: `rng = random.Random(42)`; donor: `demo` user for odd indexes, `None` (anonymous) for even; descriptions: 2–3 sentence plausible copy per campaign (write them in the command). Each donation via `record_donation(...)` wrapped in try/except DonationError (skip silently for the ended campaign once its window closes). Output via `self.stdout.write(self.style.SUCCESS(f"..."))`: per-campaign line `slug: $raised of $goal (N donations)` and final summary.

- [ ] **Step 1: Failing test** — `test_seed.py`: `call_command("seed_demo")` → user demo exists with usable password (`check_password`); 8 campaigns exist with expected categories; totals > 0 for future campaigns; second `call_command("seed_demo")` → still exactly 8 (idempotent), donation count unchanged; `call_command("seed_demo", "--force")` after manually adding a stray campaign with slug `community-mural-project` owned by demo → stray removed, recreated cleanly.
- [ ] **Step 2:** RED → implement → GREEN → full suite.
- [ ] **Step 3: Commit** — `git commit -am "add seed_demo management command with deterministic demo data"`

---

### Task 8: Polish, visual QA, documentation

**Files:**
- Modify: cross-cutting (any template/CSS gaps found), `README.md`, `AGENTS.md`
- Create/extend: `core/tests/test_ui_polish.py` (only if fixes introduce behavior worth locking)

**Steps:**
- [ ] **Step 1: Static audits.** Grep all templates for: any leftover `bootstrap` string; unlabeled inputs; `<img>` (should be none — visuals are CSS); hardcoded hex colors outside `app.css` (move to tokens if found); missing `{% block title %}` overrides (every page template sets one: "Explore campaigns", campaign title, "Give now · {title}", "Start a campaign", "Edit {title}", "Delete {title}", "My campaigns", "My donations", "Log in", "Sign up"). Add `<meta name="description">` block on detail page (truncated description |strip 150 chars). Verify reduced-motion + focus-visible present in app.css (they are — don't regress during edits).
- [ ] **Step 2: Live browser QA.** Start server: `venv/bin/python manage.py migrate && venv/bin/python manage.py seed_demo && venv/bin/python manage.py runserver` (background). Using the agent-browser skill: screenshot at mobile (390×844) and desktop (1440×900): home, a campaign detail, donate page, login, signup, (after logging in as demo) my campaigns + my donations + create form. Check: no horizontal overflow; grids collapse correctly; toasts appear after actions (give flow, create flow); signature percentage overlap looks intentional not broken; contrast reads well. Fix visual defects found (spacing, overflow, wrap issues) — small CSS/template edits, rerun `npm run build` if classes added.
- [ ] **Step 3: Docs.** Update `README.md`: Tech Stack (Django 6.1, Tailwind v4, SQLite dev), Getting Started gains node steps (`npm install`, `npm run build` / `npm run watch`), feature tour (browse/search/give/dashboard/seed_demo incl. demo credentials), remove stale django-environ/`.env.local`/Django 5.2 claims. Update `AGENTS.md`: commands gain npm build/watch; tests location now `core/tests/` package; architecture section reflects services layer, templatetags, URL map; drop "views not built yet"/TODO claims; note `SIM-` transaction-id convention.
- [ ] **Step 4: Final verification.** `venv/bin/python manage.py check`; `venv/bin/python manage.py test` (all green, pristine); `npm run build`; kill server. Commit — `git commit -am "polish responsive details; refresh docs"`
