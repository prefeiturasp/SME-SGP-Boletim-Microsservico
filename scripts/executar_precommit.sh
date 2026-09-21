#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
docker compose -f docker-compose-dev.yml run --rm boletim \
  pre-commit run --all-files

