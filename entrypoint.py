#!/usr/bin/env python
"""Docker entrypoint: run migrations + collectstatic, then exec CMD."""
import os
import subprocess
import sys


def main():
    # Run database migrations
    print("Running migrations...")
    subprocess.check_call([sys.executable, "manage.py", "migrate", "--noinput"])

    # Collect static files
    print("Collecting static files...")
    subprocess.check_call([sys.executable, "manage.py", "collectstatic", "--noinput"])

    # Optionally seed demo data
    if os.environ.get("SEED", "").lower() in ("1", "true"):
        print("Seeding demo data...")
        subprocess.check_call([sys.executable, "manage.py", "seed_demo"])

    # Exec the CMD (e.g. gunicorn) — replaces this process
    print("Starting server...")
    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
