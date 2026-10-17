# Warext Server Engine 26.3 exp.27 — private build candidate

This is a **source-only development candidate** until a private JDK 25+ compiler produces and publishes the runnable JAR plus source ZIP. Unlike exp.26 and earlier, no GitHub Actions compiler may be used.

## Optimizations (source changes)
1. **Chunk I/O:** Fixed signed 32-bit multiplication overflow in the pending-write pressure calculation using 64-bit interpolation. Configured pending-write soft and hard limits are bounded to 16,777,216 and 33,554,432 respectively, preventing integer overflow and implausibly large queue ceilings. Existing capped extra-drain turns and pregeneration-only default are unchanged.
2. **Adaptive CPU budgeting:** Background save worker headroom now checks **actual configured enabled state** of AsyncPathfinding and MultithreadedTracker, not just the selected performance profile's defaults. Explicitly disabling either component no longer reserves a virtual budget for it; explicit worker overrides remain authoritative.
3. **Pathfinding saturation:** When an administrator opts into `FLUSH_ALL`, the executor drains at most the number of queued tasks present at rejection using a bounded, allocation-free `poll()` loop, rather than allocating a temporary list proportional to the saturated queue. Caller-runs policy remains the default.
4. **Private release integrity:** The local compilation/publish command now verifies the precise source commit exists on GitHub before building and confirms JAR, complete patched-source ZIP, checksums, and upstream metadata are all present in the published GitHub Release.

## Unchanged principles
- Minecraft 26.3, **Java 25** and pinned Leaf Build #4 commit `4b0dcd264996f18b48f783c58390a9090ba1964b`.
- No fixed CPU/RAM assumptions or new performance-test development.
- GitHub is **source storage and compiled Release artifact storage only**. JAR compilation runs in the private local environment and uses the repository's `build-tools/build-local.sh publish`. GitHub Actions is disabled.

**Release status:** Do not label exp.27 as built, tested or released until the external local JDK 25+ environment has actually built the JAR and the GitHub Release lists all four assets. Existing published exp.26 remains the last downloadable version until then.
