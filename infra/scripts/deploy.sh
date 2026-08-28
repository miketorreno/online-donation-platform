#!/usr/bin/env bash
# Deploy helper for the VPS (host-level Nginx reverse proxy + docker compose).
#
# Usage:   ./infra/scripts/deploy.sh
# Assumes: run from the project directory on the VPS, .env present.
# This mirrors the steps in .github/workflows/cd.yml for manual deploys.
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "==> Pulling latest image"
docker compose pull web

echo "==> Recreating web + dependencies"
docker compose up -d --no-deps web

echo "==> Migrations"
docker compose exec -T web python manage.py migrate --noinput

echo "==> Collect static"
docker compose exec -T web python manage.py collectstatic --noinput

echo "==> Prune stale images"
docker image prune -f

echo "==> Done. Reload nginx if its config changed:"
echo "    sudo nginx -t && sudo systemctl reload nginx"
