# Online Donation Platform (ODP)

A Django-based web application designed to help individuals and organizations create, manage, and support fundraising campaigns.

## Overview

ODP is an online donation platform built with Django. It provides a foundation for:

- user registration and authentication
- campaign creation and management
- donation tracking and campaign progress
- a clean, template-driven interface for contributors

This repository includes the core app, a simple signup flow, and data models for campaigns and donations.

## Key Features

- User sign-up and authentication
- Campaign creation with goal tracking
- Donation records tied to campaigns and users
- Campaign metadata such as deadline, current amount, and progress percentage
- Django-friendly architecture for rapid extension and payment gateway integration

## Tech Stack

- Python
- Django 5.2
- Django-environ / python-decouple for environment configuration
- Django templates for frontend rendering

## Repository Structure

- `manage.py` — Django administration entrypoint
- `odp/` — project configuration and settings
- `core/` — application logic, models, views, URLs
- `templates/` — shared base and authentication templates
- `core/templates/core/` — app-specific templates

## Getting Started

### Prerequisites

- Python 3.11+ (recommended)
- `pip` package manager
- Optional: virtual environment tool such as `venv`

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/miketorreno/odp.git
   cd odp
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install django python-decouple
   ```

4. Configure environment variables:

   ```bash
   cp .env.example .env.local
   ```

   > If you prefer SQLite for development, use `DB_ENGINE=django.db.backends.sqlite3` and leave database user/password blank.

### Apply Migrations

```bash
python manage.py migrate
```

### Create a Superuser (Optional)

```bash
python manage.py createsuperuser
```

### Run the Development Server

```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser.

## Usage

- Visit `/signup/` to create a new account.
- Use Django admin or extend the application to add campaign creation and donation flows.
- Customize templates and views to add campaign browsing, donation payment integration, and reporting.

## Extending ODP

This project is intentionally lightweight so it can be extended easily.

Recommended next steps:

- Add campaign creation and listing views
- Implement donation checkout using Stripe, PayPal, or another gateway
- Add campaign detail pages with donation forms
- Enable email notifications for campaign updates and donation receipts
- Add administrative dashboards for campaign performance

## Notes

- `core/models.py` contains the `Campaign` and `Donation` models.
- `core/views.py` currently provides a signup view.
- `core/urls.py` includes the signup route and can be expanded for campaign-related URLs.

## License

This project is released under the terms of the [MIT License](LICENSE).
