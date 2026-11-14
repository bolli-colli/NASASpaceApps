# Earth Trail Detective – container image (built with buildah: `mise run image:build`)
#
# nginx (:8080, public) -> Streamlit (127.0.0.1:8501, internal); tini is PID 1 and
# container/entrypoint.sh supervises both. Smoke test: `mise run image:smoke`.
#
#   EXTRAS=""      (default) offline image: reads the Parquet cache in data/ only.
#                  Right for the pitch, judges and public deployments.
#   EXTRAS="live"  adds earthaccess, harmony-py, xarray, h5py: live mode and
#                  ETD_FETCH work when EARTHDATA_TOKEN is passed at run time.
#
# The Earthdata token is never baked into the image; pass it with `-e` or an env file.

ARG PYTHON_VERSION=3.13

# ---- build stage: install the package and its dependencies into a venv ----------
FROM docker.io/library/python:${PYTHON_VERSION}-slim AS build
ARG EXTRAS=""
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN if [ -n "$EXTRAS" ]; then pip install ".[$EXTRAS]"; else pip install .; fi

# ---- runtime stage: nginx + venv + app + catalog + data cache, non-root ----------
FROM docker.io/library/python:${PYTHON_VERSION}-slim
LABEL org.opencontainers.image.title="Earth Trail Detective" \
      org.opencontainers.image.description="Follow a pollutant through the water cycle and test every step for a trend (NASA Space Apps 2026)." \
      org.opencontainers.image.source="https://github.com/bolli-colli/NASASpaceApps" \
      org.opencontainers.image.licenses="Apache-2.0"

RUN apt-get update \
 && apt-get install --yes --no-install-recommends nginx tini \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 10001 app
COPY --from=build /opt/venv /opt/venv
WORKDIR /app
COPY app.py ./
COPY catalog ./catalog
COPY container/nginx.conf container/entrypoint.sh container/smoke_app.py ./container/
COPY --chown=app:app data ./data

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    ETD_CATALOG_DIR=/app/catalog \
    ETD_DATA_DIR=/app/data \
    ETD_FETCH=off \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=127.0.0.1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=4)"
ENTRYPOINT ["/usr/bin/tini", "--", "/app/container/entrypoint.sh"]
