#!/usr/bin/env bash
# Private local compiler and GitHub release storage (no Actions / CI build).
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
REPO="${WAREXT_GITHUB_REPO:-benjamin1734/Warext-Studios-Optimized-Minecraft-Fork}"
VERSION="$(tr -d '[:space:]' < build-tools/VERSION)"
UPSTREAM_REF="$(tr -d '[:space:]' < build-tools/UPSTREAM_REF)"
TAG="v${VERSION}"
MODE="${1:-publish}"
die() { echo "[warext-local-build] ERROR: $*" >&2; exit 1; }
[[ "$MODE" == "publish" ]] || die "Usage: bash build-tools/build-local.sh publish"
for app in git java javac python3 sha256sum gh find; do
    command -v "$app" >/dev/null 2>&1 || die "Required local tool is missing: $app"
done
JAVAC_VERSION="$(javac -version 2>&1)"
JAVAC_MAJOR="${JAVAC_VERSION#javac }"
JAVAC_MAJOR="${JAVAC_MAJOR%%.*}"
[[ "$JAVAC_MAJOR" =~ ^[0-9]+$ ]] && (( JAVAC_MAJOR >= 25 )) ||
    die "Leaf 26.3 requires a local JDK 25+ (found: $JAVAC_VERSION)"
[[ "$VERSION" == 26.3-exp.* ]] || die "Unexpected build-tools/VERSION: $VERSION"
[[ "$UPSTREAM_REF" =~ ^[0-9a-f]{40}$ ]] || die "Invalid pinned upstream commit"
git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
    die "Must run from local Warext Git checkout"
[[ -z "$(git -C "$ROOT" status --porcelain)" ]] ||
    die "Source has uncommitted changes; commit/push before publishing"
FORK_COMMIT="$(git -C "$ROOT" rev-parse HEAD)"
gh auth status >/dev/null 2>&1 ||
    die "Private compiler needs authenticated GitHub CLI for Releases storage"
if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
    die "Release $TAG exists; increment VERSION before publishing"
fi

# All generated content stays in a temporary private directory and is deleted.
BUILD_ROOT="$(mktemp -d -t warext-external-builder-XXXXXXXX)"
cleanup() { rm -rf -- "$BUILD_ROOT"; }
trap cleanup EXIT INT TERM
mkdir -p "$BUILD_ROOT/artifacts"
cp -a "$ROOT/build-tools" "$BUILD_ROOT/build-tools"
cp "$ROOT/README.md" "$ROOT/RELEASE_NOTES.md" "$BUILD_ROOT/"
echo "[warext-local-build] Building $TAG locally, Leaf SHA $UPSTREAM_REF"
git init -q "$BUILD_ROOT/upstream-src"
git -C "$BUILD_ROOT/upstream-src" remote add origin https://github.com/Winds-Studio/Leaf.git
git -C "$BUILD_ROOT/upstream-src" fetch --depth=1 origin "$UPSTREAM_REF"
git -C "$BUILD_ROOT/upstream-src" checkout -q -B dev/26.3 FETCH_HEAD
ACTUAL_UPSTREAM="$(git -C "$BUILD_ROOT/upstream-src" rev-parse HEAD)"
[[ "$ACTUAL_UPSTREAM" == "$UPSTREAM_REF" ]] || die "Unexpected Leaf SHA"
printf '%s\n' "$ACTUAL_UPSTREAM" > "$BUILD_ROOT/UPSTREAM_COMMIT.txt"
(
    cd "$BUILD_ROOT/upstream-src"
    ./gradlew applyAllPatches --stacktrace --no-daemon
)
python3 "$BUILD_ROOT/build-tools/patch_engine_263.py" "$BUILD_ROOT/upstream-src"
(
    cd "$BUILD_ROOT/upstream-src"
    ./gradlew createPaperclipJar --stacktrace --no-daemon
)
JAR="$(find "$BUILD_ROOT/upstream-src/leaf-server/build/libs" -maxdepth 1 -type f -name '*paperclip-26.3*.jar' -print -quit)"
[[ -n "$JAR" && -s "$JAR" ]] || die "Paperclip JAR not found"
cp "$JAR" "$BUILD_ROOT/artifacts/Warext-Server-Engine-26.3.jar"
WAREXT_FORK_COMMIT="$FORK_COMMIT" python3 "$BUILD_ROOT/build-tools/package_source.py"
ZIP="Warext-Server-Engine-${VERSION}-source.zip"
[[ -s "$BUILD_ROOT/artifacts/$ZIP" ]] || die "Full patched source ZIP missing"
cp "$BUILD_ROOT/UPSTREAM_COMMIT.txt" "$BUILD_ROOT/artifacts/UPSTREAM_COMMIT.txt"
(
    cd "$BUILD_ROOT/artifacts"
    sha256sum "Warext-Server-Engine-26.3.jar" "$ZIP" > SHA256SUMS.txt
    sha256sum --check SHA256SUMS.txt
)
# GitHub is storage, never the build machine. Refuse overwriting existing releases.
gh release create "$TAG" \
    "$BUILD_ROOT/artifacts/Warext-Server-Engine-26.3.jar" \
    "$BUILD_ROOT/artifacts/$ZIP" \
    "$BUILD_ROOT/artifacts/SHA256SUMS.txt" \
    "$BUILD_ROOT/artifacts/UPSTREAM_COMMIT.txt" \
    --repo "$REPO" \
    --target "$FORK_COMMIT" \
    --title "Warext Server Engine $VERSION" \
    --notes-file "$ROOT/RELEASE_NOTES.md" \
    --prerelease
gh release view "$TAG" --repo "$REPO" --json assets -q '.assets[].name' |
    grep -Fqx 'Warext-Server-Engine-26.3.jar' ||
    die "Release verification failed; JAR missing"
echo "[warext-local-build] Published $TAG; temporary files will be deleted."
