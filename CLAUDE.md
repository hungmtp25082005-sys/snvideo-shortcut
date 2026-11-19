# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Source of truth

`README.md` is the normative product and technical specification. Preserve its trust boundaries, error model, test gates, and feature-status distinctions. In particular, do not mark Gate A–D items complete without evidence from an actual iPhone; static tests and successful Cherri compilation do not prove Shortcuts runtime behavior.

SNVideo has no project-operated backend. It sends validated TikTok URLs directly to TikWM, hands other HTTPS URLs to Cobalt, and optionally reads an update manifest from GitHub Raw. Network/action hard failures may terminate an iOS Shortcut before custom error handling runs.

## Development commands

Install the pinned compiler by cloning the release tag, verifying its commit, and building locally (upstream cannot be installed with `go install ...@v2.4.0` because its module path omits `/v2`):

```bash
bash scripts/install-cherri.sh v2.4.0
```

Run all source-contract tests:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

Run one test:

```bash
python -m unittest tests.test_source_contract.SourceContractTests.test_tikwm_endpoint_and_single_encoding_stage -v
```

Validate Cherri syntax without signing (Linux/macOS):

```bash
mkdir -p build
"$(go env GOPATH)/bin/cherri" src/SNVideo.cherri \
  --skip-sign --comments --derive-uuids --no-ansi
mv src/SNVideo_unsigned.shortcut build/SNVideo.unsigned.shortcut
```

Build and sign a distributable Shortcut on macOS:

```bash
mkdir -p dist
"$(go env GOPATH)/bin/cherri" src/SNVideo.cherri \
  --share=anyone --comments --derive-uuids \
  --output=dist/SNVideo.shortcut
```

There is no separate linter configured. The required automated checks are the Python contract suite followed by Cherri compilation. `.github/workflows/build-shortcut.yml` performs both, then signs on `macos-15`; a `v*` tag also creates a GitHub Release.

## Architecture

`src/SNVideo.cherri` is the composition root. It declares Share Sheet metadata, imports all non-basic Cherri action categories, resolves Share Sheet versus explicit Clipboard input, validates the selected URL, and routes by parsed hostname. TikWM must only be called after the hostname is exactly `tiktok.com` or ends with `.tiktok.com`; never route by searching the full URL string.

`src/config.cherri` holds release identity, fixed service endpoints, and guarded feature flags. `MANIFEST_URL` intentionally remains empty until a real repository and tested iCloud link exist. `ENABLE_AUDIO` intentionally remains false until Gate B verifies the TikWM audio key, media type, and save flow on-device.

The modules under `src/lib/` form the processing pipeline:

1. Shared URL normalization accepts HTTPS, trims outer whitespace, and removes fragments without expanding short links.
2. TikWM input is URL-encoded exactly once, then the response contract checks `code` and `data`.
3. Content classification checks `data.images` before reading video keys.
4. Video selection implements `hdplay -> play` fallback; slideshow processing downloads and saves one image at a time rather than retaining album binaries.
5. Audio saves through Files, not Photos. Non-TikTok URLs are copied and handed to the fixed Cobalt URL.
6. Update checks are an explicit menu flow, separate from media downloads, and allowlist GitHub Raw for manifests and `www.icloud.com` for installation links.

Cherri functions compile into a generated header and nested Shortcut invocations. The header is parsed before top-level `const` declarations, so function bodies must receive values from `src/config.cherri` through parameters rather than reference those constants directly. A `stop()` inside a helper function stops that child invocation, not necessarily its caller. Keep terminal error handling (`alert(...); stop()`) in the same function or top-level flow that must not continue; do not reintroduce a generic `stopWithError()` helper without an explicit caller stop.

`tests/test_source_contract.py` verifies architectural invariants such as action imports, explicit Clipboard access, hostname routing order, one-layer URL encoding, sequential slideshow handling, disabled unverified features, update-domain allowlists, and absence of obvious credentials. These tests inspect source structure; they do not replace API, permission, Share Sheet, memory, or network-failure testing on iOS.

`manifest.example.json` is a template only. Keep `minimum_ios` as `TBD` until device testing establishes it, and keep placeholder iCloud data out of a production `manifest.json`. Build outputs belong in ignored `build/` or `dist/` directories.
