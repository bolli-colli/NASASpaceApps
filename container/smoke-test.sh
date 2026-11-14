#!/usr/bin/env bash
# Smoke test of the built image (`mise run image:smoke`). Fails on the first problem.
#
#  1. container starts and becomes "healthy" (HEALTHCHECK through nginx)
#  2. nginx: /healthz = ok, / serves the Streamlit page, security headers set,
#     no nginx version disclosed, websocket upgrade to /_stcore/stream works
#  3. image config: no Earthdata token baked in, non-root user
#  4. inside the container: a real Demo A1 analysis + headless app run (smoke_app.py)
#  5. no Python traceback in the logs; container stops cleanly on SIGTERM
#
# Variables: IMAGE_NAME, IMAGE_TAG, EXTRAS (as for build-image.sh), SMOKE_PORT (18080).
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-localhost/earth-trail-detective}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || echo dev)}"
EXTRAS="${EXTRAS:-}"
REF="${IMAGE_NAME}:${IMAGE_TAG}${EXTRAS:+-$EXTRAS}"
PORT="${SMOKE_PORT:-18080}"
NAME="etd-smoke-$$"
BASE="http://127.0.0.1:${PORT}"

if command -v buildah >/dev/null 2>&1 && command -v podman >/dev/null 2>&1; then
  engine=podman # shares buildah's image storage
else
  engine="$(command -v podman || command -v docker)"
fi

pass() { echo "  ok   $*"; }
fail() {
  echo "  FAIL $*" >&2
  echo "---- container logs ----" >&2
  "$engine" logs "$NAME" >&2 2>&1 || true
  exit 1
}
cleanup() { "$engine" rm --force "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT

echo "smoke test of $REF with $(basename "$engine")"

# 3. image configuration (before starting anything)
config_env="$("$engine" image inspect "$REF" --format '{{json .Config.Env}}')"
case "$config_env" in *EARTHDATA_TOKEN*) fail "image config contains EARTHDATA_TOKEN" ;; esac
pass "no Earthdata token in the image config"
user="$("$engine" image inspect "$REF" --format '{{.Config.User}}')"
[ -n "$user" ] && [ "$user" != "root" ] && [ "$user" != "0" ] || fail "image runs as root (User='$user')"
pass "runs as non-root user '$user'"

# 1. start and wait for "healthy"
"$engine" run --detach --name "$NAME" --publish "127.0.0.1:${PORT}:8080" "$REF" >/dev/null
status=""
for _ in $(seq 1 60); do
  status="$("$engine" inspect "$NAME" --format '{{.State.Health.Status}}' 2>/dev/null || true)"
  running="$("$engine" inspect "$NAME" --format '{{.State.Running}}' 2>/dev/null || echo false)"
  [ "$running" = "true" ] || fail "container stopped during start-up"
  [ "$status" = "healthy" ] && break
  # podman runs healthchecks only via systemd timers; trigger one by hand
  [ "$(basename "$engine")" = "podman" ] && podman healthcheck run "$NAME" >/dev/null 2>&1 || true
  sleep 2
done
[ "$status" = "healthy" ] || fail "container not healthy after 120 s (status: '$status')"
pass "container healthy"

# 2. HTTP through nginx
[ "$(curl -fsS "$BASE/healthz")" = "ok" ] || fail "/healthz did not answer 'ok'"
pass "/healthz = ok"
headers="$(mktemp)"
body="$(curl -fsS -D "$headers" "$BASE/")" || fail "GET / failed"
grep -qi "<title>Streamlit</title>" <<<"$body" || fail "GET / is not the Streamlit page"
pass "GET / serves the Streamlit page"
grep -qi '^x-content-type-options: nosniff' "$headers" || fail "X-Content-Type-Options header missing"
grep -qi '^x-frame-options: SAMEORIGIN' "$headers" || fail "X-Frame-Options header missing"
if grep -qi '^server: nginx/' "$headers"; then fail "nginx version disclosed"; fi
pass "security headers set, nginx version hidden"
ws_code="$(curl -s -o /dev/null -w '%{http_code}' --http1.1 --max-time 3 \
  -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' \
  -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' "$BASE/_stcore/stream" || true)"
[ "$ws_code" = "101" ] || fail "websocket upgrade through nginx returned '$ws_code', expected 101"
pass "websocket upgrade through nginx (101)"

# 4. real analysis and headless app run inside the container
"$engine" exec "$NAME" python /app/container/smoke_app.py || fail "in-container smoke test"
pass "in-container analysis and app run"

# 5. logs and shutdown
if "$engine" logs "$NAME" 2>&1 | grep -q "Traceback"; then fail "traceback in the container logs"; fi
pass "no traceback in the logs"
start=$(date +%s)
"$engine" stop --time 15 "$NAME" >/dev/null
elapsed=$(( $(date +%s) - start ))
[ "$elapsed" -lt 15 ] || fail "container needed ${elapsed}s to stop (signal handling?)"
pass "stopped cleanly in ${elapsed}s"

echo "SMOKE OK: $REF"
