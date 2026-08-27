#!/usr/bin/env python
"""Docker entrypoint: wait for DB, run migrations + collectstatic, then exec CMD."""
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


def main():
    try:
        wait_for_db()

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
        os.execvp("gunicorn", ["gunicorn", "odp.wsgi:application", "--bind", bind])

    except subprocess.CalledProcessError as e:
        print(f"ERROR: Command failed with exit code {e.returncode}: {e.cmd}")
        sys.exit(e.returncode)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
