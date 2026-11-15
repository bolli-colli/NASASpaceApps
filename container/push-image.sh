#!/usr/bin/env bash
# Push the image built by build-image.sh to a registry with buildah (`mise run image:push`).
#
# Needs: IMAGE_NAME (e.g. ghcr.io/bolli-colli/nasaspaceapps), IMAGE_TAG, optional EXTRAS,
# REGISTRY_USER and REGISTRY_PASSWORD (in GitHub Actions: github.actor / GITHUB_TOKEN),
# optional EXTRA_TAGS (space separated, e.g. "dev2 latest").
set -euo pipefail

: "${IMAGE_NAME:?set IMAGE_NAME, e.g. ghcr.io/bolli-colli/nasaspaceapps}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"
EXTRAS="${EXTRAS:-}"
suffix="${EXTRAS:+-$EXTRAS}"
REF="${IMAGE_NAME}:${IMAGE_TAG}${suffix}"
registry="${IMAGE_NAME%%/*}"

if ! command -v buildah >/dev/null 2>&1; then
  echo "error: pushing needs buildah (runs in CI on Linux)" >&2
  exit 1
fi
if [ -n "${REGISTRY_USER:-}" ] && [ -n "${REGISTRY_PASSWORD:-}" ]; then
  printf '%s' "$REGISTRY_PASSWORD" | buildah login --username "$REGISTRY_USER" --password-stdin "$registry"
fi

buildah push "$REF" "docker://$REF"
echo "pushed $REF"
for tag in ${EXTRA_TAGS:-}; do
  tag="${tag//\//-}" # registry tags must not contain "/" (e.g. branch feature/x)
  buildah tag "$REF" "${IMAGE_NAME}:${tag}${suffix}"
  buildah push "${IMAGE_NAME}:${tag}${suffix}" "docker://${IMAGE_NAME}:${tag}${suffix}"
  echo "pushed ${IMAGE_NAME}:${tag}${suffix}"
done
