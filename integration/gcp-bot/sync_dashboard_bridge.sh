#!/usr/bin/env bash
set -euo pipefail

SOURCE_URL="${FPL_BRIDGE_SOURCE_URL:-https://raw.githubusercontent.com/lordirfan99/fpl-league-58005-scout/master/integration/gcp-bot/dashboard_bridge.py}"
TARGET="/opt/fpl-autopilot/webapp/dashboard_bridge.py"
PYTHON="/opt/fpl-autopilot/.venv/bin/python"
SERVICE="fpl-dashboard-bridge.service"
TMP_FILE="$(mktemp /tmp/fpl-dashboard-bridge.XXXXXX.py)"
BACKUP="${TARGET}.auto-rollback"
trap 'rm -f "$TMP_FILE"' EXIT

curl --fail --silent --show-error --location --retry 3 --connect-timeout 15 \
  "$SOURCE_URL" --output "$TMP_FILE"
"$PYTHON" -m py_compile "$TMP_FILE"

if cmp --silent "$TMP_FILE" "$TARGET"; then
  exit 0
fi

cp --preserve=mode,ownership,timestamps "$TARGET" "$BACKUP"
install --owner=fpl --group=fpl --mode=0644 "$TMP_FILE" "$TARGET"
systemctl restart "$SERVICE"

for _ in $(seq 1 20); do
  if curl --fail --silent http://127.0.0.1:8787/health >/dev/null; then
    logger --tag fpl-bridge-sync "dashboard bridge updated and verified"
    exit 0
  fi
  sleep 1
done

install --owner=fpl --group=fpl --mode=0644 "$BACKUP" "$TARGET"
systemctl restart "$SERVICE"
logger --tag fpl-bridge-sync "dashboard bridge health check failed; rolled back"
exit 1

