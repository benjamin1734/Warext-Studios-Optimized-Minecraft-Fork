# Warext Server Engine 26.3 exp.21

Experimental Leaf 26.3 build #4 integration candidate (GitHub-only).

## Leaf upstream synchronization (2026-10-15)
- Advance pinned Leaf `ver/26.3` source from `0edc7f3b7d79b0e2e16a0ed1df8278c02c73537f` to `4b0dcd264996f18b48f783c58390a9090ba1964b` (#954).
- Bring the new Paper base `f68a55a8964e02b11a0951b971951963da5f0276` and upstream's patch adaptations into the source used by the Warext patch layer.
- Upstream archived the superseded C2ME Beardifier worldgen and Lithium hash-palette patches because equivalent functionality now comes through Paper/Moonrise. These optimizations are not blindly re-applied.
- Keep Warext-specific adaptive scheduling, p99-latency measures, pregeneration path, and optional Moonrise ticking cache; no fixed 4-core/6-GB assumptions.
- Java 25 remains the required build and smoke-test runtime; this is a 26.3 prerelease, not a new stable Minecraft version.

## Release verification gates
- Fetch and verify the exact pinned Leaf upstream commit.
- Apply Leaf/Paper patch stack followed by the Warext performance layer.
- Build runnable Paperclip JAR, bundle the patched Java source ZIP on GitHub Actions, validate SHA-256 checksums.
- Run balanced/extreme/pregeneration/compatibility startup smoke checks, worldgen save/reload checks, and opt-in ticking-cache parity tests.
- Publish both the runnable JAR and complete source ZIP to GitHub Releases **only when the main-branch workflow succeeds**.

**Status:** Experimental integration. Do not treat the feature-branch comparison itself as proof of build, runtime correctness, benchmark gains or production readiness.
