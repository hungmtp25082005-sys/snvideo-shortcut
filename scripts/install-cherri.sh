#!/usr/bin/env bash
set -euo pipefail

readonly CHERRI_REPOSITORY="https://github.com/electrikmilk/cherri.git"
readonly DEFAULT_VERSION="v2.4.0"
readonly DEFAULT_COMMIT="2afd41f96988ca4a20aa0afcbf763251e4b20fb7"

version="${1:-$DEFAULT_VERSION}"
destination="${2:-$(go env GOPATH)/bin}"
expected_commit="${CHERRI_COMMIT:-$DEFAULT_COMMIT}"
source_dir="$(mktemp -d "${TMPDIR:-/tmp}/snvideo-cherri.XXXXXX")"

cleanup() {
    rm -rf "$source_dir"
}
trap cleanup EXIT

git clone \
    --depth 1 \
    --branch "$version" \
    --single-branch \
    "$CHERRI_REPOSITORY" \
    "$source_dir"

actual_commit="$(git -C "$source_dir" rev-parse HEAD)"
if [[ "$actual_commit" != "$expected_commit" ]]; then
    printf 'Cherri commit mismatch: expected %s, got %s\n' \
        "$expected_commit" "$actual_commit" >&2
    exit 1
fi

mkdir -p "$destination"
go build -C "$source_dir" -trimpath -o "$destination/cherri" .

if [[ -n "${GITHUB_PATH:-}" ]]; then
    printf '%s\n' "$destination" >> "$GITHUB_PATH"
fi

"$destination/cherri" --version
