#!/usr/bin/env python
"""Docker entrypoint: wait for DB, run migrations + collectstatic, then exec CMD.

The first CLI argument selects the command mode:
  * "celery"            -> wait for DB, then run the given celery command
                           (worker/beat). No collectstatic/seed here.
  * (anything else)     -> web server startup: migrate + collectstatic +
                           optional seed, then gunicorn (default).
"""
import os
import socket
import subprocess
import sys
import time


def wait_for_db(max_retries=30, delay=2):
    """Wait for the database port to accept connections."""
    engine = os.environ.get("DB_ENGINE", "django.db.backends.sqlite3")
    if engine == "django.db.backends.sqlite3":
        return  # SQLite doesn't need a readiness check

    host = os.environ.get("DB_HOST", "localhost")
    port = int(os.environ.get("DB_PORT", "5432"))

    print(f"Waiting for database at {host}:{port}...")
    for attempt in range(1, max_retries + 1):
        try:
            with socket.create_connection((host, port), timeout=2):
                print("Database is ready.")
                return
        except OSError:
            if attempt == max_retries:
                print("ERROR: Database not ready after maximum retries.")
                sys.exit(1)
            print(f"  Attempt {attempt}/{max_retries} — retrying in {delay}s...")
            time.sleep(delay)


def run_celery(args):
    """Wait for DB then exec the celery command (worker/beat)."""
    wait_for_db()
    os.execvp("celery", ["celery"] + args)


def run_web():
    """Standard web startup: migrate, collectstatic, optional seed, gunicorn."""
    # Ensure writable media/static dirs exist (may be bind-mounted from host).
    os.makedirs("media", exist_ok=True)
    os.makedirs("staticfiles", exist_ok=True)

    print("Running migrations...")
    subprocess.check_call([sys.executable, "manage.py", "migrate", "--noinput"])

    print("Collecting static files...")
    subprocess.check_call(
        [sys.executable, "manage.py", "collectstatic", "--noinput"]
    )

    if os.environ.get("SEED", "").lower() in ("1", "true"):
        print("Seeding demo data...")
        subprocess.check_call([sys.executable, "manage.py", "seed_demo"])

    print("Starting server...")
    bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")
    workers = os.environ.get("GUNICORN_WORKERS", "3")
    timeout = os.environ.get("GUNICORN_TIMEOUT", "120")
    os.execvp(
        "gunicorn",
        [
            "gunicorn",
            "odp.wsgi:application",
            "--bind",
            bind,
            "--workers",
            workers,
            "--timeout",
            timeout,
        ],
    )


def main():
    try:
        args = sys.argv[1:]
        if args and args[0] == "celery":
            run_celery(args[1:])
        else:
            run_web()
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Command failed with exit code {e.returncode}: {e.cmd}")
        sys.exit(e.returncode)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

