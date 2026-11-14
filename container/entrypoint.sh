#!/usr/bin/env bash
# Starts Streamlit (internal, 127.0.0.1:8501) and nginx (public, :8080).
# tini is PID 1 and forwards signals here; if either process ends, the other is
# stopped too and the container exits with that status, so the orchestrator restarts it.
set -euo pipefail

streamlit run /app/app.py &
streamlit_pid=$!
nginx -e stderr -c /app/container/nginx.conf -g 'daemon off;' &
nginx_pid=$!

stop() {
    kill -TERM "$streamlit_pid" "$nginx_pid" 2>/dev/null || true
}
trap 'stop; wait; exit 0' TERM INT

set +e
wait -n "$streamlit_pid" "$nginx_pid"
status=$?
set -e
echo "entrypoint: a process exited with status $status - stopping the container" >&2
stop
wait
exit "$status"
