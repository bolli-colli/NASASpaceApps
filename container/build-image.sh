#!/usr/bin/env bash
# Build the container image with buildah (`mise run image:build`); docker format keeps HEALTHCHECK.
#
# Linux (and GitHub Actions): buildah runs natively; the image lands in the local
# containers storage (usable by podman and `buildah push`).
# macOS / no buildah: buildah runs inside quay.io/buildah/stable via docker or podman,
# writes an OCI archive to dist/ and the image is loaded into that engine.
#
# Variables: IMAGE_NAME (default localhost/earth-trail-detective), IMAGE_TAG (default:
# short git commit), EXTRAS ("" = offline image, "live" = with NASA access libraries).
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-localhost/earth-trail-detective}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || echo dev)}"
EXTRAS="${EXTRAS:-}"
BUILDAH_IMAGE="quay.io/buildah/stable:v1.43.5"
REF="${IMAGE_NAME}:${IMAGE_TAG}${EXTRAS:+-$EXTRAS}"

if ! ls data/*.parquet >/dev/null 2>&1; then
  echo "warning: data/ has no Parquet files – the image will show empty cards (fill the cache first)" >&2
fi

build_args=(build --layers --format docker --file Containerfile --build-arg "EXTRAS=${EXTRAS}" --tag "$REF" .)

if command -v buildah >/dev/null 2>&1; then
  buildah "${build_args[@]}"
  echo "built $REF (buildah storage)"
  exit 0
fi

engine="$(command -v podman || command -v docker || true)"
if [ -z "$engine" ]; then
  echo "error: neither buildah nor docker/podman found" >&2
  exit 1
fi
mkdir -p dist
archive="dist/earth-trail-detective${EXTRAS:+-$EXTRAS}.tar"
echo "buildah not installed – running it in $BUILDAH_IMAGE via $(basename "$engine")"
"$engine" run --rm --privileged \
  -v "$PWD":/work:ro -v "$PWD/dist":/out -w /work \
  "$BUILDAH_IMAGE" sh -c "
    set -e
    buildah --storage-driver vfs ${build_args[*]}
    buildah --storage-driver vfs push $REF docker-archive:/out/$(basename "$archive"):$REF
  "
"$engine" load --input "$archive"
echo "built $REF (loaded into $(basename "$engine"); archive: $archive)"
