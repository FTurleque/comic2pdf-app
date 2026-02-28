#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
echo "docker compose up -d --build ..."
docker compose up -d --build

