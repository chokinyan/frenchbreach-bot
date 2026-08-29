#!/bin/sh
set -e

mkdir -p /app/src/json
chown -R appuser:appuser /app/src/json

exec gosu appuser "$@"